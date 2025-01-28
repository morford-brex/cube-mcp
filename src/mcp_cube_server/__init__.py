from . import server
import asyncio
import argparse
import dotenv
import os
import json
import logging


def args_to_kwargs(unknown):
    extras = {}
    i = 0
    while i < len(unknown):
        if unknown[i].startswith("--"):
            key = unknown[i][2:]  # Remove '--' prefix
            if i + 1 >= len(unknown) or unknown[i + 1].startswith("--"):
                extras[key] = True  # Flag argument
                i += 1
            else:
                extras[key] = unknown[i + 1]  # Key-value pair
                i += 2
        else:
            i += 1

    return extras


def main():
    """Main entry point for the package."""
    parser = argparse.ArgumentParser(description="Cube MCP Server")
    parser.add_argument("--log_dir", required=False, default=None, help="Directory to log to")
    parser.add_argument("--log_level", required=False, default="INFO", help="Logging level")

    dotenv.load_dotenv()

    required = {
        "endpoint": os.getenv("CUBE_ENDPOINT"),
        "api_secret": os.getenv("CUBE_API_SECRET"),
        "token_payload": os.getenv("CUBE_TOKEN_PAYLOAD", "{}"),
    }

    parser.add_argument("--endpoint", required=not required["endpoint"], default=required["endpoint"])
    parser.add_argument("--api_secret", required=not required["api_secret"], default=required["api_secret"])

    args, unknown = parser.parse_known_args()
    additional_kwargs = args_to_kwargs(unknown)

    token_payload = json.loads(required["token_payload"])
    for key, value in additional_kwargs.items():
        token_payload[key] = value

    logging.basicConfig(
        level=args.log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()]
        + ([logging.FileHandler(os.path.join(args.log_dir, "server.log"))] if args.log_dir else []),
    )

    logger = logging.getLogger("mcp_cube_server")

    try:
        credentials = {
            "endpoint": args.endpoint,
            "api_secret": args.api_secret,
            "token_payload": token_payload,
        }
    except json.JSONDecodeError:
        logger.error("Invalid JSON in token_payload: %s", args.token_payload)
        return

    server.main(
        credentials=credentials,
    )


# Optionally expose other important items at package level
__all__ = ["main", "server"]

if __name__ == "__main__":
    main()
