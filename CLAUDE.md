# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Development Commands

### Installation and Setup

```bash
# Install the package in development mode with all dependencies
make install-dev

# Or manually:
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Testing

```bash
# Run all tests with coverage
make test

# Run specific test suites
make test-unit
make test-integration

# Generate coverage report
make coverage
```

### Code Quality

```bash
# Run all checks (lint, typecheck, tests)
make check

# Run linting
make lint

# Format code
make format

# Run type checking
make typecheck
```

### Build Commands

```bash
# Build distribution packages
make build

# Build Docker image
make docker-build
```

### Running the Server

```bash
# Run the server with default settings
python -m mcp_cube_server

# Run with specific configuration
python -m mcp_cube_server --endpoint "https://your-cube-endpoint.com" --api_secret "your-secret"
```

### Docker

```bash
# Build Docker image
docker build -t mcp_cube_server .

# Run Docker container
docker run -e CUBE_ENDPOINT="https://your-cube-endpoint.com" -e CUBE_API_SECRET="your-secret" mcp_cube_server
```

## Architecture

The cube-mcp repository implements a Model-Client-Provider (MCP) server that interfaces with Cube.dev semantic layers. The architecture consists of:

### Core Components

1. **Entry Point** (`__init__.py`):
   - Handles command-line arguments
   - Sets up logging
   - Loads environment variables
   - Configures Cube credentials

2. **CubeClient** (`server.py`):
   - Manages authentication with Cube.dev API
   - Handles token generation and refresh
   - Executes queries against the Cube REST API
   - Processes and formats responses

3. **FastMCP Server** (`server.py`):
   - Exposes resources and tools for clients
   - Manages data resources and responses
   - Handles query modeling and validation

### API Resources

- `context://data_description`: Provides metadata about available data cubes
- `data://{data_id}`: Exposes query results in JSON format

### Tools

- `describe_data`: Returns metadata about available cubes, measures, and dimensions
- `read_data`: Executes queries against the Cube API and returns formatted results

### Configuration

The server requires:
- Cube API endpoint
- API secret for JWT token generation
- Optional token payload for authentication

Configuration can be provided via:
- Environment variables (CUBE_ENDPOINT, CUBE_API_SECRET, CUBE_TOKEN_PAYLOAD)
- Command-line arguments (--endpoint, --api_secret)
- Additional parameters passed as JWT token payload