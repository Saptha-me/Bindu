# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/Saptha-me/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻
"""Bindu UI module.

This module provides chat interfaces for Bindu agents.

Modules:
- client: BinduChatClient for A2A protocol communication
- components: UI helper functions
- styles: CSS styling for Gradio
- html_ui: Minimal HTML/JS launcher function (recommended)
"""

from bindu.ui.client import BinduChatClient
from bindu.ui.html_ui import launch_html_ui

__all__ = ["BinduChatClient", "launch_html_ui"]
