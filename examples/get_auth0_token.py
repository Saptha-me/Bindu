#!/usr/bin/env python3
"""Utility script to obtain Auth0 access tokens for testing."""

import argparse
import json
import os
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen

try:
    from rich.console import Console
    from rich.panel import Panel
except ImportError:
    print("Error: rich is required. Install with: pip install rich", file=sys.stderr)
    sys.exit(1)

console = Console()


def get_auth0_token(domain: str, client_id: str, client_secret: str, audience: str | None = None) -> str:
    """Get Auth0 access token using client credentials flow."""
    if audience is None:
        audience = f"https://{domain}/api/v2/"

    request = Request(
        f"https://{domain}/oauth/token",
        data=json.dumps(
            {
                "client_id": client_id,
                "client_secret": client_secret,
                "audience": audience,
                "grant_type": "client_credentials",
            }
        ).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data["access_token"]
    except HTTPError as e:
        error_body = e.read().decode("utf-8")
        console.print(f"[red]HTTP Error {e.code}:[/red] {error_body}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Obtain Auth0 access tokens for testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using command-line arguments
  %(prog)s --domain dev-xxx.us.auth0.com --client-id YOUR_ID --client-secret YOUR_SECRET

  # Using environment variables
  export AUTH0_DOMAIN="dev-xxx.us.auth0.com"
  export AUTH0_CLIENT_ID="YOUR_ID"
  export AUTH0_CLIENT_SECRET="YOUR_SECRET"
  %(prog)s

  # Custom audience
  %(prog)s --audience https://api.example.com
        """,
    )

    parser.add_argument(
        "--domain",
        default=os.getenv("AUTH0_DOMAIN"),
        help="Auth0 domain (e.g., dev-xxx.us.auth0.com). Can also use AUTH0_DOMAIN env var.",
    )
    parser.add_argument(
        "--client-id",
        default=os.getenv("AUTH0_CLIENT_ID"),
        help="Auth0 client ID. Can also use AUTH0_CLIENT_ID env var.",
    )
    parser.add_argument(
        "--client-secret",
        default=os.getenv("AUTH0_CLIENT_SECRET"),
        help="Auth0 client secret. Can also use AUTH0_CLIENT_SECRET env var.",
    )
    parser.add_argument(
        "--audience",
        default=os.getenv("AUTH0_AUDIENCE"),
        help="Auth0 API audience. Defaults to https://{domain}/api/v2/. Can also use AUTH0_AUDIENCE env var.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output token in JSON format",
    )

    args = parser.parse_args()

    # Validate required arguments
    missing = []
    if not args.domain:
        missing.append("--domain or AUTH0_DOMAIN")
    if not args.client_id:
        missing.append("--client-id or AUTH0_CLIENT_ID")
    if not args.client_secret:
        missing.append("--client-secret or AUTH0_CLIENT_SECRET")

    if missing:
        console.print(f"[red]Error:[/red] Missing required arguments: {', '.join(missing)}")
        parser.print_help()
        sys.exit(1)

    # Get token
    with console.status("[bold green]Requesting Auth0 token..."):
        token = get_auth0_token(args.domain, args.client_id, args.client_secret, args.audience)

    # Output token
    if args.json:
        print(json.dumps({"access_token": token}))
    else:
        console.print(
            Panel(
                token,
                title="[bold green]✓ Auth0 Access Token[/bold green]",
                border_style="green",
            )
        )
        console.print("\n[dim]Tip: Use --json flag for machine-readable output[/dim]")


if __name__ == "__main__":
    main()
