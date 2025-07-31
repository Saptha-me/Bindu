# 
# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/Pebbling-ai/pebble/issues/new/choose |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🐧

"""Display utilities for the Pebbling server."""
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.text import Text


def prepare_server_display() -> str:
    """Prepare the colorful ASCII display for the server.
    
    Returns:
        A string containing a formatted ASCII art display for the server
    """
    try:
        console = Console(record=True)

        # Create a stylish ASCII art logo with penguin emoji
        logo = """
        ██████╗ ███████╗██████╗ ██████╗ ██╗     ██╗███╗   ██╗ ██████╗
        ██╔══██╗██╔════╝██╔══██╗██╔══██╗██║     ██║████╗  ██║██╔════╝
        ██████╔╝█████╗  ██████╔╝██████╔╝██║     ██║██╔██╗ ██║██║  ███╗
        ██╔═══╝ ██╔══╝  ██╔══██╗██╔══██╗██║     ██║██║╚██╗██║██║   ██║
        ██║     ███████╗██████╔╝██████╔╝███████╗██║██║ ╚████║╚██████╔╝
        ╚═╝     ╚══════╝╚═════╝ ╚═════╝ ╚══════╝╚═╝╚═╝  ╚═══╝ ╚═════╝
        """

        version_info = Text("v" + "0.1.0", style="bright_white")
        
        display_panel = Panel.fit(
            Text(logo, style="bold magenta")
            + "\n\n"
            + version_info
            + "\n\n"
            + Text(
                "🐧 Pebbling - A Protocol Framework for Agent to Agent Communication",
                style="bold cyan italic",
            ),
            title="[bold rainbow]🐧 Pebbling Protocol Framework[/bold rainbow]",
            border_style="bright_blue",
            box=box.DOUBLE,
        )
        
        console.print(display_panel)
        return console.export_text()
    except ImportError:
        return "🐧 Pebbling Protocol Framework v0.1.0"