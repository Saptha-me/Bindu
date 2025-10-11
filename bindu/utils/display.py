"""Display utilities for the bindu server."""

from __future__ import annotations

from rich.align import Align
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


def prepare_server_display(
    host: str | None = None,
    port: int | None = None,
    agent_id: str | None = None,
    agent_did: str | None = None,
) -> None:
    """Prepare a beautiful display for the server using rich.

    Args:
        host: Server hostname
        port: Server port
        agent_id: Agent identifier
    """
    console = Console()

    # ASCII art with gradient colors
    ascii_art = (
        r"[cyan]}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}[/cyan]"
        "\n"
        r"[cyan]{{[/cyan]            [yellow]+[/yellow]             [yellow]+[/yellow]"
        r"                  [yellow]+[/yellow]   [yellow]@[/yellow]          [cyan]{{[/cyan]"
        "\n"
        r"[cyan]}}[/cyan]   [yellow]|[/yellow]                [yellow]*[/yellow]           "
        r"[yellow]o[/yellow]     [yellow]+[/yellow]                [yellow].[/yellow]    [cyan]}}[/cyan]"
        "\n"
        r"[cyan]{{[/cyan]  [yellow]-O-[/yellow]    [yellow]o[/yellow]               [yellow].[/yellow]"
        r"               [yellow].[/yellow]          [yellow]+[/yellow]       [cyan]{{[/cyan]"
        "\n"
        r"[cyan]}}[/cyan]   [yellow]|[/yellow]                    [magenta]_,.-----.,_[/magenta]"
        r"         [yellow]o[/yellow]    [yellow]|[/yellow]          [cyan]}}[/cyan]"
        "\n"
        r"[cyan]{{[/cyan]           [yellow]+[/yellow]    [yellow]*[/yellow]    [magenta].-'.         .'-.          "
        r"-O-[/magenta]         [cyan]{{[/cyan]"
        "\n"
        r"[cyan]}}[/cyan]      [yellow]*[/yellow]            [magenta].'.-'   .---.   `'.'.[/magenta]"
        r"         [yellow]|[/yellow]     [yellow]*[/yellow]    [cyan]}}[/cyan]"
        "\n"
        r"[cyan]{{[/cyan] [yellow].[/yellow]                [magenta]/_.-'   /     \   .'-.[/magenta]\\"
        r"                   [cyan]{{[/cyan]"
        "\n"
        r"[cyan]}}[/cyan]         [yellow]'[/yellow] [yellow]-=*<[/yellow]  [magenta]|-._.-  |   @   |   '-._|"
        r"[/magenta]  [yellow]>*=-[/yellow]    [yellow].[/yellow]     [yellow]+[/yellow] [cyan]}}[/cyan]"
        "\n"
        r"[cyan]{{[/cyan] [yellow]-- )--[/yellow]           [magenta]\`-.    \     /    .-'/[/magenta]"
        r"                   [cyan]{{[/cyan]"
        "\n"
        r"[cyan]}}[/cyan]       [yellow]*[/yellow]     [yellow]+[/yellow]     [magenta]`.'.    '---'    .'.'[/magenta]"
        r"    [yellow]+[/yellow]       [yellow]o[/yellow]       [cyan]}}[/cyan]"
        "\n"
        r"[cyan]{{[/cyan]                  [yellow].[/yellow]  [magenta]'-._         _.-'[/magenta]  [yellow].[/yellow]"
        r"                   [cyan]{{[/cyan]"
        "\n"
        r"[cyan]}}[/cyan]         [yellow]|[/yellow]               [magenta]`~~~~~~~`[/magenta]"
        r"       [yellow]- --===D[/yellow]       [yellow]@[/yellow]   [cyan]}}[/cyan]"
        "\n"
        r"[cyan]{{[/cyan]   [yellow]o[/yellow]    [yellow]-O-[/yellow]      [yellow]*[/yellow]   [yellow].[/yellow]"
        r"                  [yellow]*[/yellow]        [yellow]+[/yellow]          [cyan]{{[/cyan]"
        "\n"
        r"[cyan]}}[/cyan]         [yellow]|[/yellow]                      [yellow]+[/yellow]"
        r"         [yellow].[/yellow]            [yellow]+[/yellow]    [cyan]}}[/cyan]"
        "\n"
        r"[cyan]{{[/cyan] [dim]jgs[/dim]          [yellow].[/yellow]     [yellow]@[/yellow]      [yellow]o[/yellow]"
        r"                        [yellow]*[/yellow]       [cyan]{{[/cyan]"
        "\n"
        r"[cyan]}}[/cyan]       [yellow]o[/yellow]                          [yellow]*[/yellow]"
        r"          [yellow]o[/yellow]           [yellow].[/yellow]  [cyan]}}[/cyan]"
        "\n"
        r"[cyan]{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{[/cyan]"
    )

    # Create title
    title = Text("Bindu 🌻", style="bold magenta")

    # Create info table
    table = Table(show_header=False, box=None, padding=(0, 2))

    if host and port:
        table.add_row(
            Text("Server:", style="bold cyan"),
            Text(f"http://{host}:{port}", style="bold green"),
        )

    if agent_id:
        table.add_row(
            Text("Agent:", style="bold cyan"), Text(agent_id, style="bold blue")
        )

    if agent_did:
        table.add_row(
            Text("Agent DID:", style="bold cyan"), Text(agent_did, style="bold blue")
        )

    # Create tagline
    tagline = Text("a bindu, part of Saptha.me", style="italic magenta")

    # Group ASCII art and tagline together
    panel_content = Group(Align.center(ascii_art), "", Align.center(tagline))

    # Print everything
    console.print()
    console.print(
        Panel(panel_content, title=title, border_style="bright_cyan", padding=(1, 2))
    )
    console.print()

    if host or agent_id:
        console.print(Align.center(table))

    console.print()
