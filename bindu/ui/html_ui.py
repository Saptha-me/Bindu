"""Minimal HTML/JS chat interface launcher for Bindu agents.

This module provides a lightweight alternative to Gradio using a static HTML page
with embedded JavaScript for A2A protocol communication.
"""

import webbrowser

from bindu.utils.logging import get_logger

logger = get_logger("bindu.ui.html_ui")


def launch_html_ui(
    base_url: str = "http://localhost:3773",
    open_browser: bool = True,
) -> None:
    """Launch minimal HTML chat interface for Bindu agent.

    This function opens the browser to the /docs endpoint which serves
    a static HTML page that communicates directly with the Bindu agent
    server via A2A protocol. The HTML page includes all necessary CSS
    and JavaScript embedded within it.

    Args:
        base_url: Base URL of the Bindu agent server
        open_browser: Whether to automatically open the browser

    Note:
        The chat UI is served from: {base_url}/docs

        Make sure your agent server is running before accessing the UI.
    """
    # Construct the URL
    ui_url = f"{base_url}/docs"

    logger.info(f"Chat interface available at: {ui_url}")

    if open_browser:
        logger.info(f"Opening browser to: {ui_url}")
        webbrowser.open(ui_url)
    else:
        logger.info(f"To access the UI, open your browser to: {ui_url}")

    print("\n" + "=" * 70)
    print("🤖 Bindu Agent Chat Interface")
    print("=" * 70)
    print(f"Agent Server: {base_url}")
    print(f"Chat UI: {ui_url}")
    print("\nThe chat interface will open in your browser.")
    print("Make sure your agent server is running!")
    print("=" * 70 + "\n")
