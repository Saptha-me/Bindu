"""Display utilities for the bindu server."""

from __future__ import annotations

from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.console import Group


def prepare_server_display(host: str = None, port: int = None, agent_id: str = None) -> None:
    """Prepare a beautiful display for the server using rich.

    Args:
        host: Server hostname
        port: Server port
        agent_id: Agent identifier
    """
    console = Console()

    # ASCII art with gradient colors
    ascii_art = r"""[cyan]}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}[/cyan]
[cyan]{{[/cyan]            [yellow]+[/yellow]             [yellow]+[/yellow]                  [yellow]+[/yellow]   [yellow]@[/yellow]          [cyan]{{[/cyan]
[cyan]}}[/cyan]   [yellow]|[/yellow]                [yellow]*[/yellow]           [yellow]o[/yellow]     [yellow]+[/yellow]                [yellow].[/yellow]    [cyan]}}[/cyan]
[cyan]{{[/cyan]  [yellow]-O-[/yellow]    [yellow]o[/yellow]               [yellow].[/yellow]               [yellow].[/yellow]          [yellow]+[/yellow]       [cyan]{{[/cyan]
[cyan]}}[/cyan]   [yellow]|[/yellow]                    [magenta]_,.-----.,_[/magenta]         [yellow]o[/yellow]    [yellow]|[/yellow]          [cyan]}}[/cyan]
[cyan]{{[/cyan]           [yellow]+[/yellow]    [yellow]*[/yellow]    [magenta].-'.         .'-.          -O-[/magenta]         [cyan]{{[/cyan]
[cyan]}}[/cyan]      [yellow]*[/yellow]            [magenta].'.-'   .---.   `'.'.[/magenta]         [yellow]|[/yellow]     [yellow]*[/yellow]    [cyan]}}[/cyan]
[cyan]{{[/cyan] [yellow].[/yellow]                [magenta]/_.-'   /     \   .'-.[/magenta]\                   [cyan]{{[/cyan]
[cyan]}}[/cyan]         [yellow]'[/yellow] [yellow]-=*<[/yellow]  [magenta]|-._.-  |   @   |   '-._|[/magenta]  [yellow]>*=-[/yellow]    [yellow].[/yellow]     [yellow]+[/yellow] [cyan]}}[/cyan]
[cyan]{{[/cyan] [yellow]-- )--[/yellow]           [magenta]\`-.    \     /    .-'/[/magenta]                   [cyan]{{[/cyan]
[cyan]}}[/cyan]       [yellow]*[/yellow]     [yellow]+[/yellow]     [magenta]`.'.    '---'    .'.'[/magenta]    [yellow]+[/yellow]       [yellow]o[/yellow]       [cyan]}}[/cyan]
[cyan]{{[/cyan]                  [yellow].[/yellow]  [magenta]'-._         _.-'[/magenta]  [yellow].[/yellow]                   [cyan]{{[/cyan]
[cyan]}}[/cyan]         [yellow]|[/yellow]               [magenta]`~~~~~~~`[/magenta]       [yellow]- --===D[/yellow]       [yellow]@[/yellow]   [cyan]}}[/cyan]
[cyan]{{[/cyan]   [yellow]o[/yellow]    [yellow]-O-[/yellow]      [yellow]*[/yellow]   [yellow].[/yellow]                  [yellow]*[/yellow]        [yellow]+[/yellow]          [cyan]{{[/cyan]
[cyan]}}[/cyan]         [yellow]|[/yellow]                      [yellow]+[/yellow]         [yellow].[/yellow]            [yellow]+[/yellow]    [cyan]}}[/cyan]
[cyan]{{[/cyan] [dim]jgs[/dim]          [yellow].[/yellow]     [yellow]@[/yellow]      [yellow]o[/yellow]                        [yellow]*[/yellow]       [cyan]{{[/cyan]
[cyan]}}[/cyan]       [yellow]o[/yellow]                          [yellow]*[/yellow]          [yellow]o[/yellow]           [yellow].[/yellow]  [cyan]}}[/cyan]
[cyan]{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{[/cyan]"""

    # Create title
    title = Text("Bindu 🌻", style="bold magenta")
    
    # Create info table
    table = Table(show_header=False, box=None, padding=(0, 2))
    
    if host and port:
        table.add_row(
            Text("Server:", style="bold cyan"),
            Text(f"http://{host}:{port}", style="bold green")
        )
    
    if agent_id:
        table.add_row(
            Text("Agent:", style="bold cyan"),
            Text(agent_id, style="bold blue")
        )
    
    # Create tagline
    tagline = Text("a bindu, part of Saptha.me", style="italic magenta")
    
    # Group ASCII art and tagline together
    panel_content = Group(
        Align.center(ascii_art),
        "",
        Align.center(tagline)
    )
    
    # Print everything
    console.print()
    console.print(Panel(
        panel_content,
        title=title,
        border_style="bright_cyan",
        padding=(1, 2)
    ))
    console.print()
    
    if host or agent_id:
        console.print(Align.center(table))
    
    console.print()
