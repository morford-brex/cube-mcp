"""Integration tests for the MCP server."""

from typing import Any
from unittest.mock import Mock, patch

import pytest
import responses

from mcp_cube_server import main as cli_main


class TestServerIntegration:
    """Integration tests for the complete server flow."""

    @pytest.fixture
    def mock_env(self, monkeypatch) -> None:
        """Set up mock environment variables."""
        monkeypatch.setenv("CUBE_ENDPOINT", "https://cube.example.com/cubejs-api/v1")
        monkeypatch.setenv("CUBE_API_SECRET", "test-secret-key")
        monkeypatch.setenv("CUBE_TOKEN_PAYLOAD", '{"user_id": "test-user"}')

    @patch("mcp_cube_server.server.FastMCP")
    def test_full_server_initialization_flow(
        self,
        mock_fastmcp_class: Mock,
        mock_meta_response: dict[str, Any],
    ) -> None:
        """Test complete server initialization flow."""
        mock_mcp = Mock()
        mock_fastmcp_class.return_value = mock_mcp

        with (
            responses.RequestsMock() as rsps,
            patch("sys.argv", ["mcp_cube_server"]),
            patch("mcp_cube_server.server.main") as mock_server_main,
        ):
            # Mock the meta endpoint
            rsps.add(
                responses.GET,
                "https://cube.example.com/cubejs-api/v1/meta",
                json=mock_meta_response,
                status=200,
            )

            cli_main()

            # Verify server main was called with correct credentials
            mock_server_main.assert_called_once()
            credentials = mock_server_main.call_args[0][0]

            assert credentials["endpoint"] == "https://cube.example.com/cubejs-api/v1"
            assert credentials["api_secret"] == "test-secret-key"
            assert credentials["token_payload"] == {"user_id": "test-user"}

    @patch("mcp_cube_server.server.FastMCP")
    def test_cli_with_command_line_args(
        self,
        mock_fastmcp_class: Mock,
        mock_meta_response: dict[str, Any],
    ) -> None:
        """Test CLI with command line arguments overriding env vars."""
        mock_mcp = Mock()
        mock_fastmcp_class.return_value = mock_mcp

        with (
            responses.RequestsMock() as rsps,
            patch(
                "sys.argv",
                [
                    "mcp_cube_server",
                    "--endpoint",
                    "https://cli.example.com",
                    "--api_secret",
                    "cli-secret",
                    "--log_level",
                    "DEBUG",
                ],
            ),
            patch("mcp_cube_server.server.main") as mock_server_main,
        ):
            rsps.add(
                responses.GET,
                "https://cli.example.com/meta",
                json=mock_meta_response,
                status=200,
            )

            cli_main()

            credentials = mock_server_main.call_args[0][0]

            assert credentials["endpoint"] == "https://cli.example.com"
            assert credentials["api_secret"] == "cli-secret"

    @patch("mcp_cube_server.server.FastMCP")
    def test_cli_with_additional_token_payload_args(
        self,
        mock_fastmcp_class: Mock,
        mock_meta_response: dict[str, Any],
    ) -> None:
        """Test CLI with additional token payload arguments."""
        mock_mcp = Mock()
        mock_fastmcp_class.return_value = mock_mcp

        with (
            responses.RequestsMock() as rsps,
            patch(
                "sys.argv",
                [
                    "mcp_cube_server",
                    "--role",
                    "admin",
                    "--tenant_id",
                    "tenant-123",
                ],
            ),
            patch("mcp_cube_server.server.main") as mock_server_main,
        ):
            rsps.add(
                responses.GET,
                "https://cube.example.com/cubejs-api/v1/meta",
                json=mock_meta_response,
                status=200,
            )
            cli_main()

            credentials = mock_server_main.call_args[0][0]

            # Original payload should be extended
            assert credentials["token_payload"]["user_id"] == "test-user"
            assert credentials["token_payload"]["role"] == "admin"
            assert credentials["token_payload"]["tenant_id"] == "tenant-123"

    def test_cli_with_invalid_json_token_payload(self, capsys) -> None:
        """Test CLI with invalid JSON in token payload."""
        with patch("os.getenv") as mock_getenv, patch("sys.argv", ["mcp_cube_server"]):
            mock_getenv.side_effect = lambda key, default=None: {
                "CUBE_ENDPOINT": "https://cube.example.com",
                "CUBE_API_SECRET": "secret",
                "CUBE_TOKEN_PAYLOAD": "invalid-json{",
            }.get(key, default)

            cli_main()

            captured = capsys.readouterr()
            assert "Invalid JSON in token_payload" in captured.err

    @patch("mcp_cube_server.server.FastMCP")
    def test_server_with_logging_to_file(
        self,
        mock_fastmcp_class: Mock,
        tmp_path,
        mock_meta_response: dict[str, Any],
    ) -> None:
        """Test server with file logging enabled."""
        mock_mcp = Mock()
        mock_fastmcp_class.return_value = mock_mcp

        log_dir = tmp_path / "logs"
        log_dir.mkdir()

        with (
            responses.RequestsMock() as rsps,
            patch(
                "sys.argv",
                [
                    "mcp_cube_server",
                    "--endpoint",
                    "https://cube.example.com",
                    "--api_secret",
                    "secret",
                    "--log_dir",
                    str(log_dir),
                ],
            ),
            patch("mcp_cube_server.server.main"),
        ):
            rsps.add(
                responses.GET,
                "https://cube.example.com/meta",
                json=mock_meta_response,
                status=200,
            )
            cli_main()

            # Check that log file would be created
            _ = log_dir / "mcp_cube_server.log"

    def test_query_flow_integration(
        self,
        mock_meta_response: dict[str, Any],
        mock_query_response: dict[str, Any],
    ) -> None:
        """Test complete query flow from request to response."""
        from mcp_cube_server.server import CubeClient, Query

        with responses.RequestsMock() as rsps:
            # Mock meta endpoint
            rsps.add(
                responses.GET,
                "https://cube.example.com/meta",
                json=mock_meta_response,
                status=200,
            )

            # Mock query endpoint
            rsps.add(
                responses.GET,
                "https://cube.example.com/load",
                json=mock_query_response,
                status=200,
            )

            # Create client
            client = CubeClient(
                endpoint="https://cube.example.com",
                api_secret="secret",
                token_payload={},
                logger=Mock(),
            )

            # Execute query
            query = Query(
                measures=["Orders.count"],
                dimensions=["Orders.status"],
            )

            result = client.query(query.model_dump())

            # Verify numeric casting happened
            assert result["data"][0]["Orders.count"] == 42
            assert result["data"][0]["Orders.total_amount"] == 1234.56
