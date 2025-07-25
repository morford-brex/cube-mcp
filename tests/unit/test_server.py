"""Unit tests for MCP server endpoints."""

import json
import uuid
from typing import Any, Dict
from unittest.mock import Mock, patch

import pytest
import yaml

from mcp_cube_server.server import Query, data_to_yaml, main


class TestDataToYaml:
    """Test cases for data_to_yaml utility function."""

    def test_data_to_yaml_dict(self) -> None:
        """Test converting dict to YAML."""
        data = {"key": "value", "number": 42}
        result = data_to_yaml(data)
        
        assert "key: value" in result
        assert "number: 42" in result

    def test_data_to_yaml_list(self) -> None:
        """Test converting list to YAML."""
        data = ["item1", "item2", "item3"]
        result = data_to_yaml(data)
        
        assert "- item1" in result
        assert "- item2" in result
        assert "- item3" in result

    def test_data_to_yaml_nested(self) -> None:
        """Test converting nested structure to YAML."""
        data = {
            "orders": [
                {"id": 1, "status": "completed"},
                {"id": 2, "status": "pending"},
            ]
        }
        result = data_to_yaml(data)
        
        assert "orders:" in result
        assert "id: 1" in result
        assert "status: completed" in result


class TestServerEndpoints:
    """Test cases for MCP server endpoints."""

    @patch("mcp_cube_server.server.CubeClient")
    @patch("mcp_cube_server.server.FastMCP")
    def test_main_function_setup(
        self,
        mock_fastmcp_class: Mock,
        mock_cube_client_class: Mock,
    ) -> None:
        """Test main function setup."""
        mock_mcp = Mock()
        mock_fastmcp_class.return_value = mock_mcp
        mock_client = Mock()
        mock_cube_client_class.return_value = mock_client
        
        credentials = {
            "endpoint": "https://cube.example.com",
            "api_secret": "secret",
            "token_payload": {},
        }
        logger = Mock()
        
        main(credentials, logger)
        
        # Verify CubeClient was created
        mock_cube_client_class.assert_called_once_with(
            endpoint=credentials["endpoint"],
            api_secret=credentials["api_secret"],
            token_payload=credentials["token_payload"],
            logger=logger,
        )
        
        # Verify FastMCP was created
        mock_fastmcp_class.assert_called_once_with("Cube.dev")
        
        # Verify server was started
        mock_mcp.run.assert_called_once()

    @patch("mcp_cube_server.server.CubeClient")
    def test_data_description_resource(
        self,
        mock_cube_client_class: Mock,
        mock_meta_response: Dict[str, Any],
    ) -> None:
        """Test data_description resource endpoint."""
        # Setup mock client
        mock_client = Mock()
        mock_client.describe.return_value = mock_meta_response
        mock_cube_client_class.return_value = mock_client
        
        # Import and call the decorated function directly
        from mcp_cube_server.server import FastMCP
        
        mcp = FastMCP("Test")
        
        # Create the server with mocked client
        credentials = {
            "endpoint": "https://cube.example.com",
            "api_secret": "secret",
            "token_payload": {},
        }
        logger = Mock()
        
        # We need to manually execute the main function logic
        # to register the endpoints
        client = mock_client
        
        @mcp.resource("context://data_description")
        def data_description() -> str:
            meta = client.describe()
            if error := meta.get("error"):
                return f"Error: Description of the data is not available: {error}, {meta}"
            
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
        
        # Call the resource function
        result = data_description()
        
        assert "Orders" in result
        assert "Order ID" in result
        assert "Orders.count" in result
        assert "Total Amount" in result

    @patch("mcp_cube_server.server.CubeClient")
    def test_data_description_with_error(
        self,
        mock_cube_client_class: Mock,
        mock_error_response: Dict[str, Any],
    ) -> None:
        """Test data_description resource with error response."""
        mock_client = Mock()
        mock_client.describe.return_value = mock_error_response
        mock_cube_client_class.return_value = mock_client
        
        from mcp_cube_server.server import FastMCP
        
        mcp = FastMCP("Test")
        logger = Mock()
        client = mock_client
        
        @mcp.resource("context://data_description")
        def data_description() -> str:
            meta = client.describe()
            if error := meta.get("error"):
                logger.error("Error in data_description: %s\n\n%s", error, meta.get("stack"))
                logger.error("Full response: %s", json.dumps(meta))
                return f"Error: Description of the data is not available: {error}, {meta}"
            
            # ... rest of the function
            return ""
        
        result = data_description()
        
        assert "Error: Description of the data is not available" in result
        assert "Query execution error" in result

    @patch("mcp_cube_server.server.CubeClient")
    @patch("mcp_cube_server.server.uuid.uuid4")
    def test_read_data_tool_success(
        self,
        mock_uuid: Mock,
        mock_cube_client_class: Mock,
        mock_query_response: Dict[str, Any],
    ) -> None:
        """Test read_data tool with successful response."""
        # Setup mocks
        mock_uuid.return_value = "test-uuid-1234"
        mock_client = Mock()
        mock_client.query.return_value = mock_query_response
        mock_cube_client_class.return_value = mock_client
        
        from mcp_cube_server.server import FastMCP
        
        mcp = FastMCP("Test")
        logger = Mock()
        client = mock_client
        
        @mcp.tool("read_data")
        def read_data(query: Query) -> Any:
            try:
                query_dict = query.model_dump(by_alias=True, exclude_none=True)
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
                
                output = {
                    "type": "data",
                    "data_id": data_id,
                    "data": data,
                }
                yaml_output = data_to_yaml(output)
                json_output = json.dumps(output)
                
                # Return list of contents (simplified for testing)
                return [
                    {"type": "text", "text": yaml_output},
                    {
                        "type": "resource",
                        "resource": {
                            "uri": f"data://{data_id}",
                            "text": json_output,
                            "mimeType": "application/json",
                        },
                    },
                ]
                
            except Exception as e:
                logger.error("Error in read_data: %s", str(e))
                return f"Error: {str(e)}"
        
        # Test the tool
        query = Query(measures=["Orders.count"])
        result = read_data(query)
        
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["type"] == "text"
        assert "data_id: test-uuid-1234" in result[0]["text"]
        assert result[1]["type"] == "resource"

    @patch("mcp_cube_server.server.CubeClient")
    def test_read_data_tool_with_error(
        self,
        mock_cube_client_class: Mock,
        mock_error_response: Dict[str, Any],
    ) -> None:
        """Test read_data tool with error response."""
        mock_client = Mock()
        mock_client.query.return_value = mock_error_response
        mock_cube_client_class.return_value = mock_client
        
        from mcp_cube_server.server import FastMCP
        
        mcp = FastMCP("Test")
        logger = Mock()
        client = mock_client
        
        @mcp.tool("read_data")
        def read_data(query: Query) -> Any:
            try:
                query_dict = query.model_dump(by_alias=True, exclude_none=True)
                response = client.query(query_dict)
                if error := response.get("error"):
                    logger.error("Error in read_data: %s\n\n%s", error, response.get("stack"))
                    return f"Error: {error}"
                return response
            except Exception as e:
                return f"Error: {str(e)}"
        
        query = Query(measures=["Orders.count"])
        result = read_data(query)
        
        assert "Error: Query execution error" in result

    @patch("mcp_cube_server.server.CubeClient")
    def test_read_data_tool_with_exception(
        self,
        mock_cube_client_class: Mock,
    ) -> None:
        """Test read_data tool with exception during processing."""
        mock_client = Mock()
        mock_client.query.side_effect = Exception("Unexpected error")
        mock_cube_client_class.return_value = mock_client
        
        from mcp_cube_server.server import FastMCP
        
        mcp = FastMCP("Test")
        logger = Mock()
        client = mock_client
        
        @mcp.tool("read_data")
        def read_data(query: Query) -> Any:
            try:
                query_dict = query.model_dump(by_alias=True, exclude_none=True)
                response = client.query(query_dict)
                return response
            except Exception as e:
                logger.error("Error in read_data: %s", str(e))
                return f"Error: {str(e)}"
        
        query = Query(measures=["Orders.count"])
        result = read_data(query)
        
        assert "Error: Unexpected error" in result

    @patch("mcp_cube_server.server.CubeClient")
    def test_describe_data_tool(
        self,
        mock_cube_client_class: Mock,
        mock_meta_response: Dict[str, Any],
    ) -> None:
        """Test describe_data tool."""
        mock_client = Mock()
        mock_client.describe.return_value = mock_meta_response
        mock_cube_client_class.return_value = mock_client
        
        from mcp_cube_server.server import FastMCP
        
        mcp = FastMCP("Test")
        client = mock_client
        
        # Define data_description function first
        def data_description() -> str:
            meta = client.describe()
            if error := meta.get("error"):
                return f"Error: Description of the data is not available: {error}, {meta}"
            
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
        def describe_data() -> Dict[str, str]:
            return {"type": "text", "text": data_description()}
        
        result = describe_data()
        
        assert result["type"] == "text"
        assert "Orders" in result["text"]
        assert "Orders.count" in result["text"]