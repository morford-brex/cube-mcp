from __future__ import annotations
from typing import Annotated, Any, Literal, Optional, Union
from mcp.server.fastmcp import FastMCP
import jwt
from pydantic import BaseModel, Field
import requests
import json
import logging
import yaml
import uuid
import time


def data_to_yaml(data: Any) -> str:
    return yaml.dump(data, indent=2, sort_keys=False)


class CubeClient:
    Route = Literal["meta", "load"]
    max_retries = 10
    wait_time = 1

    def __init__(self, endpoint: str, api_secret: str, token_payload: dict):
        self.endpoint = endpoint
        self.api_secret = api_secret
        self.token_payload = token_payload
        self.token = None
        self.logger = logging.getLogger("mcp_cube_server")
        self.retry_count = 0
        self._refresh_token()
        self.meta = self.describe()

    def _generate_token(self):
        return jwt.encode(self.token_payload, self.api_secret, algorithm="HS256")

    def _refresh_token(self):
        self.token = self._generate_token()

    def _request(self, route: Route, **params):
        if self.retry_count >= self.max_retries:
            self.logger.error("Max retries exceeded")
            self.retry_count = 0
            return {"error": "Request timeout"}
        headers = {"Authorization": self.token}
        url = f"{self.endpoint if self.endpoint[-1] != '/' else self.endpoint[:-1]}/{route}"
        serialized_params = {k: json.dumps(v) for k, v in params.items()}
        response = requests.get(url, headers=headers, params=serialized_params)

        if response.status_code == 400:
            if response.json().get("error") == "Continue wait":
                self.retry_count += 1
                time.sleep(self.wait_time)
                return self._request(route, **params)
        elif response.status_code == 403:
            self._refresh_token()
            self.retry_count = self.max_retries
            return self._request(route, **params)

        json_response = response.json()
        self.retry_count = 0
        return json_response

    def describe(self):
        return self._request("meta")

    def _cast_numerics(self, response):
        if response.get("data") and response.get("annotation"):
            # Find which keys are numeric
            numeric_keys = set()
            dimensions_and_measures = dict(
                response["annotation"].get("dimensions", {}), **response["annotation"].get("measures", [])
            )
            for column_name, column in dimensions_and_measures.items():
                if column.get("type") == "number":
                    numeric_keys.add(column_name)
            # Cast numeric values to numbers
            for row in response["data"]:
                for key in numeric_keys:
                    try:
                        row[key] = float(row[key])
                        if row[key].is_integer():
                            row[key] = int(row[key])
                    except (ValueError, TypeError):
                        pass
        return response

    def query(self, query, cast_numerics=True):
        response = self._request("load", query=query)
        if cast_numerics:
            response = self._cast_numerics(response)
        return response


class Query(BaseModel):
    class Filter(BaseModel):
        member: Annotated[Optional[str], Field(..., description="Name of the measure or dimension to filter on")] = None
        operator: Annotated[
            Optional[
                Literal[
                    "equals",
                    "notEquals",
                    "contains",
                    "notContains",
                    "startsWith",
                    "notStartsWith",
                    "endsWith",
                    "notEndsWith",
                    "gt",
                    "gte",
                    "lt",
                    "lte",
                    "set",
                    "notSet",
                    "inDateRange",
                    "notInDateRange",
                    "beforeDate",
                    "afterDate",
                    "measureFilter",
                ]
            ],
            Field(..., description="Operator to apply to the filter"),
        ] = None
        values: Annotated[
            Optional[list[Union[str, int, float]]],
            Field(..., description="Right-hand side of the filter. 0-n values depending on the operator"),
        ] = None
        or_filters: 'Annotated[Optional[list[Filter]], Field(..., description="List of filters to combine with OR logic. If present, other fields are ignored", alias="or")]' = None  # type: ignore # noqa: F821
        and_filters: 'Annotated[Optional[list[Filter]], Field(..., description="List of filters to combine with AND logic. If present, other fields are ignored", alias="and")]' = (  # type: ignore  # noqa: F821
            None  # noqa: F821
        )

    class TimeDimension(BaseModel):
        dimension: Annotated[str, Field(..., description="Name of the time dimension")]
        granularity: Annotated[
            Literal["second", "minute", "hour", "day", "week", "month", "quarter", "year"],
            Field(..., description="Time granularity"),
        ]
        dateRange: Annotated[
            Union[list[str], str],
            Field(
                ...,
                description="Pair of dates ISO dates representing the start and end of the range. Alternatively, a string representing a relative date range of the form: 'last N days', 'today', 'yesterday', 'last year', etc.",
            ),
        ]

    measures: Annotated[list[str], Field(..., description="Names of measures to query")]
    dimensions: Annotated[Optional[list[str]], Field(..., description="Names of dimensions to group by")] = None
    timeDimensions: Annotated[list[TimeDimension], Field(..., description="Time dimensions to group by")] = None
    filters: Annotated[Optional[list[Filter]], Field(..., description="Filters to apply to the query")] = None
    limit: Annotated[Optional[int], Field(..., description="Maximum number of rows to return. Defaults to 500")] = 500
    offset: Annotated[Optional[int], Field(..., description="Number of rows to skip. Defaults to 0")] = 0
    order: Annotated[
        Optional[dict[str, Literal["asc", "desc"]]],
        Field(..., description="Optional ordering of the results. The order is sensitive to the order of keys."),
    ] = None
    ungrouped: Annotated[
        Optional[bool], Field(..., description="Return results without grouping by dimensions. Instead, return all rows.")
    ] = False


# Print json schema
print(json.dumps(Query.model_json_schema(), indent=2))


def main(credentials):
    logger = logging.getLogger("mcp_cube_server")
    mcp = FastMCP("Cube.dev")

    client = CubeClient(**credentials)

    @mcp.resource("context://data_description")
    def data_description() -> str:
        """Describe the data available in Cube."""
        meta = client.describe()
        if error := meta.get("error"):
            logger.error("Error in data_description: %s\n\n%s", error, meta.get("stack"))
            logger.error("Full response: %s", json.dumps(meta))
            return f"Error: Description of the data is not available: {error}"

        description = [
            {
                "name": cube.get("name"),
                "title": cube.get("title"),
                "description": cube.get("description"),
                "dimensions": [
                    {
                        "name": dimension.get("name"),
                        "title": dimension.get("shortTitle") or dimension.get("title"),
                        "description": dimension.get("description"),
                    }
                    for dimension in cube.get("dimensions", [])
                ],
                "measures": [
                    {
                        "name": measure.get("name"),
                        "title": measure.get("shortTitle") or measure.get("title"),
                        "description": measure.get("description"),
                    }
                    for measure in cube.get("measures", [])
                ],
            }
            for cube in meta.get("cubes", [])
        ]
        return "Here is a description of the data available via the read_data tool:\n\n" + yaml.dump(
            description, indent=2, sort_keys=True
        )

    @mcp.tool("describe_data")
    def describe_data() -> str:
        """Describe the data available in Cube."""
        return data_description()

    @mcp.tool("read_data")
    def read_data(query: Query) -> str:
        """Read data from Cube."""
        query_dict = dict(query)
        logger.info("read_data called with query: %s", json.dumps(query_dict))
        response = client.query(query_dict)
        if error := response.get("error"):
            logger.error("Error in read_data: %s\n\n%s", error, response.get("stack"))
            logger.error("Full response: %s", json.dumps(response))
            return f"Error: {error}"
        data = response.get("data", [])
        logger.info("read_data returned %s rows", len(data))

        data_id = str(uuid.uuid4())

        @mcp.resource(f"data://{data_id}")
        def data_resource() -> str:
            return json.dumps(data)

        logger.info("Added results as resource with ID: %s", data_id)

        return f"Data ID: {data_id}\n\n" + data_to_yaml(data)

    mcp.run()
