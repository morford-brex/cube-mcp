# Cube MCP Server

[![CI](https://github.com/morford-brex/cube-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/morford-brex/cube-mcp/actions/workflows/ci.yml)

MCP Server for Interacting with Cube.dev Semantic Layers

## Features

- Query Cube.dev semantic layers through MCP tools
- Automatic type casting for numeric values
- JWT-based authentication with token refresh
- Resource-based data access pattern
- Comprehensive error handling and logging

## Installation

```bash
pip install mcp-cube-server
```

## Configuration

The server requires the following configuration:

- `CUBE_ENDPOINT`: Your Cube.dev API endpoint (e.g., `https://your-instance.cubecloud.dev/cubejs-api/v1`)
- `CUBE_API_SECRET`: Your Cube.dev API secret for JWT generation
- `CUBE_TOKEN_PAYLOAD`: (Optional) Additional JWT token payload as JSON

### Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

### Command Line Arguments

You can also provide configuration via command line:

```bash
mcp_cube_server --endpoint "https://cube.example.com" --api_secret "your-secret"
```

Additional arguments will be added to the JWT token payload:

```bash
mcp_cube_server --role admin --tenant_id tenant-123
```

## Resources

### `context://data_description`
Contains a description of the data available in the Cube deployment. This is an application controlled version of the `describe_data` tool.

### `data://{data_id}`
Contains the data returned by a `read_data` call in JSON format. This resource is meant for MCP clients that wish to format or otherwise process the output of tool calls.

## Tools

### `describe_data`
Describes the data available in the Cube deployment. Returns metadata about available cubes, dimensions, and measures.

### `read_data`
Accepts a query to the Cube REST API and returns the data in YAML along with a unique identifier for the data returned. This identifier can be used to retrieve a JSON representation of the data from the resource `data://{data_id}`.

Example query:
```python
{
    "measures": ["Orders.count", "Orders.total_amount"],
    "dimensions": ["Orders.status"],
    "timeDimensions": [{
        "dimension": "Orders.created_at",
        "granularity": "day",
        "dateRange": "last 7 days"
    }],
    "limit": 100
}
```

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/isaacwasserman/cube-mcp.git
cd cube-mcp

# Install development dependencies
make install-dev

# Install pre-commit hooks
pre-commit install
```

### Running Tests

```bash
# Run all tests
make test

# Run with coverage
make coverage

# Run specific test suites
make test-unit
make test-integration
```

### Code Quality

```bash
# Run all checks
make check

# Individual checks
make lint      # Run ruff linting
make format    # Format code
make typecheck # Run mypy type checking
```

### Building

```bash
# Build distribution packages
make build

# Build Docker image
make docker-build
```

## Docker Usage

```dockerfile
docker run -e CUBE_ENDPOINT="https://your-cube.com" \
           -e CUBE_API_SECRET="your-secret" \
           mcp-cube-server
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and ensure they pass (`make check`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.