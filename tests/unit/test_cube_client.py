"""Unit tests for CubeClient class."""

import json
import time
from typing import Any, Dict
from unittest.mock import Mock, patch

import jwt
import pytest
import responses
from requests.exceptions import RequestException

from mcp_cube_server.server import CubeClient


class TestCubeClient:
    """Test cases for CubeClient class."""

    def test_init_success(
        self,
        mock_cube_endpoint: str,
        mock_api_secret: str,
        mock_token_payload: Dict[str, Any],
        mock_logger: Mock,
        mock_meta_response: Dict[str, Any],
    ) -> None:
        """Test successful CubeClient initialization."""
        with responses.RequestsMock() as rsps:
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
            
            assert client.endpoint == mock_cube_endpoint
            assert client.api_secret == mock_api_secret
            assert client.token_payload == mock_token_payload
            assert client.token is not None
            assert client.meta == mock_meta_response

    def test_init_with_trailing_slash(
        self,
        mock_cube_endpoint: str,
        mock_api_secret: str,
        mock_token_payload: Dict[str, Any],
        mock_logger: Mock,
        mock_meta_response: Dict[str, Any],
    ) -> None:
        """Test CubeClient initialization with trailing slash in endpoint."""
        endpoint_with_slash = f"{mock_cube_endpoint}/"
        
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                f"{mock_cube_endpoint}/meta",
                json=mock_meta_response,
                status=200,
            )
            
            client = CubeClient(
                endpoint=endpoint_with_slash,
                api_secret=mock_api_secret,
                token_payload=mock_token_payload,
                logger=mock_logger,
            )
            
            assert client.endpoint == endpoint_with_slash

    def test_generate_token(self, cube_client: CubeClient) -> None:
        """Test JWT token generation."""
        token = cube_client._generate_token()
        
        # Decode and verify token
        decoded = jwt.decode(
            token,
            cube_client.api_secret,
            algorithms=["HS256"],
        )
        
        assert decoded == cube_client.token_payload

    def test_refresh_token(self, cube_client: CubeClient) -> None:
        """Test token refresh mechanism."""
        old_token = cube_client.token
        cube_client._refresh_token()
        
        assert cube_client.token is not None
        # Tokens should be different due to timestamp
        assert cube_client.token == old_token  # Same payload produces same token

    def test_request_success(
        self,
        cube_client: CubeClient,
        mock_cube_endpoint: str,
        mock_query_response: Dict[str, Any],
    ) -> None:
        """Test successful API request."""
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                f"{mock_cube_endpoint}/load",
                json=mock_query_response,
                status=200,
            )
            
            query = {"measures": ["Orders.count"]}
            result = cube_client._request("load", query=query)
            
            assert result == mock_query_response
            assert len(rsps.calls) == 1
            assert rsps.calls[0].request.headers["Authorization"] == cube_client.token

    def test_request_with_continue_wait(
        self,
        cube_client: CubeClient,
        mock_cube_endpoint: str,
        mock_continue_wait_response: Dict[str, Any],
        mock_query_response: Dict[str, Any],
    ) -> None:
        """Test request handling with 'Continue wait' response."""
        cube_client.request_backoff = 0.1  # Speed up test
        
        with responses.RequestsMock() as rsps:
            # First response: Continue wait
            rsps.add(
                responses.GET,
                f"{mock_cube_endpoint}/load",
                json=mock_continue_wait_response,
                status=200,
            )
            # Second response: Success
            rsps.add(
                responses.GET,
                f"{mock_cube_endpoint}/load",
                json=mock_query_response,
                status=200,
            )
            
            query = {"measures": ["Orders.count"]}
            result = cube_client._request("load", query=query)
            
            assert result == mock_query_response
            assert len(rsps.calls) == 2

    def test_request_timeout_on_continue_wait(
        self,
        cube_client: CubeClient,
        mock_cube_endpoint: str,
        mock_continue_wait_response: Dict[str, Any],
    ) -> None:
        """Test request timeout when receiving continuous 'Continue wait' responses."""
        cube_client.request_backoff = 0.1
        cube_client.max_wait_time = 0.2
        
        with responses.RequestsMock() as rsps:
            # Always return Continue wait
            rsps.add(
                responses.GET,
                f"{mock_cube_endpoint}/load",
                json=mock_continue_wait_response,
                status=200,
            )
            
            query = {"measures": ["Orders.count"]}
            result = cube_client._request("load", query=query)
            
            assert "error" in result
            assert "timed out" in result["error"]

    def test_request_with_403_refresh(
        self,
        cube_client: CubeClient,
        mock_cube_endpoint: str,
        mock_query_response: Dict[str, Any],
    ) -> None:
        """Test automatic token refresh on 403 response."""
        with responses.RequestsMock() as rsps:
            # First response: 403
            rsps.add(
                responses.GET,
                f"{mock_cube_endpoint}/load",
                json={"error": "Unauthorized"},
                status=403,
            )
            # Second response after refresh: Success
            rsps.add(
                responses.GET,
                f"{mock_cube_endpoint}/load",
                json=mock_query_response,
                status=200,
            )
            
            query = {"measures": ["Orders.count"]}
            result = cube_client._request("load", query=query)
            
            assert result == mock_query_response
            assert len(rsps.calls) == 2
            cube_client.logger.warning.assert_called_with(
                "Received 403, attempting token refresh"
            )

    def test_request_non_200_status(
        self,
        cube_client: CubeClient,
        mock_cube_endpoint: str,
        mock_error_response: Dict[str, Any],
    ) -> None:
        """Test handling of non-200 status codes."""
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                f"{mock_cube_endpoint}/load",
                json=mock_error_response,
                status=500,
            )
            
            query = {"measures": ["Orders.count"]}
            result = cube_client._request("load", query=query)
            
            assert result == mock_error_response
            cube_client.logger.error.assert_called()

    def test_request_exception_handling(
        self,
        cube_client: CubeClient,
        mock_cube_endpoint: str,
    ) -> None:
        """Test exception handling during request."""
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                f"{mock_cube_endpoint}/load",
                body=RequestException("Network error"),
            )
            
            query = {"measures": ["Orders.count"]}
            result = cube_client._request("load", query=query)
            
            assert "error" in result
            assert "Request failed" in result["error"]
            cube_client.logger.error.assert_called()

    def test_describe_method(
        self,
        cube_client: CubeClient,
        mock_cube_endpoint: str,
        mock_meta_response: Dict[str, Any],
    ) -> None:
        """Test describe method."""
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                f"{mock_cube_endpoint}/meta",
                json=mock_meta_response,
                status=200,
            )
            
            result = cube_client.describe()
            
            assert result == mock_meta_response

    def test_cast_numerics_with_valid_data(
        self,
        cube_client: CubeClient,
        mock_query_response: Dict[str, Any],
    ) -> None:
        """Test numeric casting with valid data."""
        response = cube_client._cast_numerics(mock_query_response.copy())
        
        # Check that numeric strings are converted
        assert response["data"][0]["Orders.count"] == 42
        assert response["data"][0]["Orders.total_amount"] == 1234.56
        assert response["data"][1]["Orders.count"] == 10
        assert response["data"][1]["Orders.total_amount"] == 567.89

    def test_cast_numerics_with_invalid_data(
        self,
        cube_client: CubeClient,
    ) -> None:
        """Test numeric casting with invalid numeric data."""
        response = {
            "data": [{"amount": "not-a-number"}],
            "annotation": {
                "measures": {"amount": {"type": "number"}},
            },
        }
        
        result = cube_client._cast_numerics(response.copy())
        
        # Should not raise exception, value remains as string
        assert result["data"][0]["amount"] == "not-a-number"

    def test_cast_numerics_without_annotation(
        self,
        cube_client: CubeClient,
    ) -> None:
        """Test numeric casting without annotation data."""
        response = {"data": [{"amount": "123"}]}
        
        result = cube_client._cast_numerics(response.copy())
        
        # Should not modify data without annotation
        assert result["data"][0]["amount"] == "123"

    def test_query_method_success(
        self,
        cube_client: CubeClient,
        mock_cube_endpoint: str,
        mock_query_response: Dict[str, Any],
    ) -> None:
        """Test query method with successful response."""
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                f"{mock_cube_endpoint}/load",
                json=mock_query_response,
                status=200,
            )
            
            query = {"measures": ["Orders.count"]}
            result = cube_client.query(query)
            
            # Check that numerics were cast
            assert result["data"][0]["Orders.count"] == 42

    def test_query_method_without_numeric_casting(
        self,
        cube_client: CubeClient,
        mock_cube_endpoint: str,
        mock_query_response: Dict[str, Any],
    ) -> None:
        """Test query method without numeric casting."""
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                f"{mock_cube_endpoint}/load",
                json=mock_query_response,
                status=200,
            )
            
            query = {"measures": ["Orders.count"]}
            result = cube_client.query(query, cast_numerics=False)
            
            # Check that numerics were not cast
            assert result["data"][0]["Orders.count"] == "42"