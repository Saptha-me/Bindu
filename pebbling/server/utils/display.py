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


def prepare_server_display(host: str = None, port: int = None, agent_id: str = None) -> str:
    """Prepare the colorful ASCII display for the server.

    Args:
        host: Server hostname
        port: Server port
        agent_id: Agent identifier

    Returns:
        A string containing a formatted ASCII art display for the server
    """
    # Define ASCII art once for reuse
    pebbling_art = r"""
#####################################################################
                 ____       _     _     _ _                                       
                |  _ \ ___ | |__ | |__ | (_)_ __   __ _                           
                | |_) / _ \| '_ \| '_ \| | | '_ \ / _` |                          
                |  __/  __/| |_) | |_) | | | | | | (_| |                          
                |_|   \___||_.__/|_.__/|_|_|_| |_|\__, |
                                                     | | 
                                                   |___/                           
#####################################################################
#####################################################################

                              ⣀⣠⣤⣤⣤⣤⣤⣤⣀⡀                              
                          ⣠⣴⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣶⣤⡀                            
                          ⣠⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣦⡀                            
                          ⣼⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡄                            
                          ⣼⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡀                          
                          ⢠⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣇                           
                          ⢸⣿⣿⣿⣿⣿⣿⣿⣿⣿⠿⠿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿                           
                          ⢸⡟⠁⠀⠙⢿⣿⣿⣿⡿⠋⠀⠀⠀⠙⣿⣿⣿⣿⣿⣿⣿⡇                          
                          ⢹⡀⠀⠀⠀⠈⣿⣿⣿⠁⠀⠀⠀⠀⠀⠸⣿⣿⣿⣿⣿⣿⡇                          
                          ⢨⠁⢠⣾⣶⣦⠀⢸⣿⣿⢠⣾⣿⣶⡀⠀⠀⣿⣿⣿⣿⣿⣿⡇                         
                          ⢸⠀⢸⣿⣿⣿⠤⠘⠀⠘⠼⣿⣿⣿⡇⠀⢀⣿⣿⣿⣿⣿⣿⣿                         
                          ⢀⡟⠉⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⠉⠉⠻⣿⣿⣿⣿⣿⣿⡄                          
                          ⢸⡆⠣⡀⠀⠀⠀⠀⠀⠀⢀⣀⡤⠖⠀⠀⣠⣿⣿⣿⣿⣿⣿⣧                          
                          ⣼⣿⣦⡘⠢⠤⠤⠤⠤⠤⠒⠉⠁⠀⢀⣠⣴⣿⣿⣿⣿⣿⣿⣿⣇                         
                        ⣼⣿⣿⠟⠉⠢⣄⣢⠐⣄⠠⣄⢢⣼⠞⠉⠀⠈⠻⢿⣿⣿⣿⣿⣿⣿⣿⣆                        
                        ⢀⣼⣿⣿⡟⠀⠀⠀⠉⠙⠚⠓⠊⠉⠀⠀⠀⠀⠀⠀⢻⣿⣿⣿⣿⣿⣿⣿⣆                       
                       ⢠⣾⣿⣿⣿⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⣿⣿⣿⣿⣿⣿⣿⣧                     
                      ⣰⣿⣿⣿⣿⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢿⣿⣿⣿⣿⣿⣿⣿⣿⣷⡀                   
                     ⣴⣿⣿⣿⣿⣿⡏⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⡀                  
                    ⣰⣿⣿⣿⣿⣿⠟⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷                  


#####################################################################
#####################################################################
"""

    try:
        console = Console(record=True)

        version_info = Text("v0.1.0", style="bold bright_yellow")

        # Create colorful display with the pebbling art
        display_content = (
            Text(pebbling_art, style="bold bright_cyan")
            + "\n\n"
            + Text("Pebbling ", style="bold bright_magenta")
            + version_info
            + "\n"
            + Text("🐧 A Protocol Framework for Agent to Agent Communication", style="bold bright_green italic")
        )

        # Add server information if provided
        if host or port or agent_id:
            display_content += "\n\n"

            if host and port:
                display_content += Text("🚀 Starting Pebbling Server...\n", style="bold bright_yellow")
                display_content += Text("📡 Server URL: ", style="bold bright_blue")
                display_content += Text(f"http://{host}:{port}", style="bold bright_cyan underline")
                display_content += "\n"

            if agent_id:
                display_content += Text("🐧 Penguine ID: ", style="bold bright_magenta")
                display_content += Text(f"{agent_id}", style="bold bright_yellow")

        display_panel = Panel.fit(
            display_content,
            title="[bold rainbow]🐧 Pebbling Protocol Framework[/bold rainbow]",
            border_style="bright_blue",
            box=box.DOUBLE,
        )

        # Don't print here, just capture and return the output
        with console.capture() as capture:
            console.print(display_panel)
        return capture.get()
    except ImportError:
        # Fallback display without rich formatting - reuse the same art
        fallback = (
            pebbling_art
            + "\n\n🐧 Pebbling Protocol Framework v0.1.0\nPebbling - A Protocol Framework for Agent to Agent Communication"
        )

        if host and port:
            fallback += f"\n🚀 Starting Pebbling Server...\n📡 Server URL: http://{host}:{port}"
        if agent_id:
            fallback += f"\n🐧 Agent ID: {agent_id}"

        return fallback
