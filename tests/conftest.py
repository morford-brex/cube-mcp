"""Common test fixtures and configuration."""

import json
from typing import Any, Dict, Generator

import pytest
import responses
from mcp.server.fastmcp import FastMCP

from mcp_cube_server.server import CubeClient


@pytest.fixture
def mock_cube_endpoint() -> str:
    """Mock Cube.dev API endpoint."""
    return "https://cube.example.com/cubejs-api/v1"


@pytest.fixture
def mock_api_secret() -> str:
    """Mock API secret for JWT generation."""
    return "test-secret-key"


@pytest.fixture
def mock_token_payload() -> Dict[str, Any]:
    """Mock JWT token payload."""
    return {"user_id": "test-user", "role": "admin"}


@pytest.fixture
def mock_meta_response() -> Dict[str, Any]:
    """Mock Cube.dev meta API response."""
    return {
        "cubes": [
            {
                "name": "Orders",
                "title": "Orders",
                "description": "Order data",
                "dimensions": [
                    {
                        "name": "Orders.id",
                        "type": "string",
                        "title": "Order ID",
                        "description": "Unique order identifier",
                    },
                    {
                        "name": "Orders.status",
                        "type": "string",
                        "title": "Status",
                        "description": "Order status",
                    },
                    {
                        "name": "Orders.created_at",
                        "type": "time",
                        "title": "Created At",
                        "description": "Order creation timestamp",
                    },
                ],
                "measures": [
                    {
                        "name": "Orders.count",
                        "type": "number",
                        "title": "Count",
                        "description": "Number of orders",
                    },
                    {
                        "name": "Orders.total_amount",
                        "type": "number",
                        "title": "Total Amount",
                        "description": "Total order amount",
                    },
                ],
            }
        ]
    }


@pytest.fixture
def mock_query_response() -> Dict[str, Any]:
    """Mock Cube.dev query response."""
    return {
        "data": [
            {"Orders.status": "completed", "Orders.count": "42", "Orders.total_amount": "1234.56"},
            {"Orders.status": "pending", "Orders.count": "10", "Orders.total_amount": "567.89"},
        ],
        "annotation": {
            "measures": {
                "Orders.count": {"type": "number"},
                "Orders.total_amount": {"type": "number"},
            },
            "dimensions": {"Orders.status": {"type": "string"}},
        },
    }


@pytest.fixture
def mock_logger(mocker) -> Any:
    """Mock logger for testing."""
    return mocker.Mock()


@pytest.fixture
def cube_client(
    mock_cube_endpoint: str,
    mock_api_secret: str,
    mock_token_payload: Dict[str, Any],
    mock_logger: Any,
    mock_meta_response: Dict[str, Any],
) -> Generator[CubeClient, None, None]:
    """Create a CubeClient instance with mocked responses."""
    with responses.RequestsMock() as rsps:
        # Mock the initial meta call in __init__
        rsps.add(
            responses.GET,
            f"{mock_cube_endpoint}/meta",
            json=mock_meta_response,
            status=200,
        )
        
        client = CubeClient(
            endpoint=mock_cube_endpoint,
            api_secret=mock_api_secret,
            token_payload=mock_token_payload,
            logger=mock_logger,
        )
        
        yield client


@pytest.fixture
def mcp_server() -> FastMCP:
    """Create a FastMCP server instance for testing."""
    return FastMCP("Test Cube Server")


@pytest.fixture
def mock_error_response() -> Dict[str, Any]:
    """Mock error response from Cube.dev."""
    return {
        "error": "Query execution error",
        "stack": "Error: Query execution failed\n    at QueryEngine.execute",
    }


@pytest.fixture
def mock_continue_wait_response() -> Dict[str, Any]:
    """Mock 'continue wait' response from Cube.dev."""
    return {"error": "Continue wait"}