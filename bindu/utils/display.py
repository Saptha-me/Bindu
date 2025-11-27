"""Display utilities for the bindu server."""

from __future__ import annotations

from rich.align import Align
from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text

from bindu.__version__ import __version__


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
        agent_did: Agent DID
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

    # Create tagline
    tagline = Text("a bindu, part of Night Sky", style="italic magenta")

    # Group ASCII art and tagline together
    title = Text("Bindu 🌻", style="bold magenta")
    panel_content = Group(Align.center(ascii_art), "", Align.center(tagline))

    # Print ASCII art panel
    console.print()
    console.print(
        Panel(panel_content, title=title, border_style="bright_cyan", padding=(1, 2))
    )
    console.print()

    # Print version
    console.print(Text(f"Version: {__version__}", style="bold white"), highlight=False)
    console.print()

    # Print server information
    if host and port:
        console.print(Text("🚀 Bindu Server 🚀", style="bold magenta"), highlight=False)
        console.print(
            Text(f"Agent Server: http://{host}:{port}", style="green"), highlight=False
        )
        console.print()

    if agent_id:
        console.print(Text(f"Agent ID: {agent_id}", style="cyan"), highlight=False)

    if agent_did:
        console.print(Text(f"Agent DID: {agent_did}", style="cyan"), highlight=False)

    if agent_id or agent_did:
        console.print()

    # Print protocol endpoints
    if host and port:
        console.print(Text("Protocol Endpoints:", style="bold white"), highlight=False)
        console.print(
            Text(f"  - A2A: http://{host}:{port}/a2a", style="white"), highlight=False
        )
        console.print(
            Text(
                f"  - DID Resolution: http://{host}:{port}/did/resolve", style="white"
            ),
            highlight=False,
        )
        console.print(
            Text(f"  - Agent Info: http://{host}:{port}/agent/info", style="white"),
            highlight=False,
        )
        console.print(
            Text(f"  - Docs: http://{host}:{port}/docs", style="white"),
            highlight=False,
        )
        console.print()

    # Print community and documentation
    console.print(
        Text("⭐️⭐️⭐️ Support Open Source ⭐️⭐️⭐️", style="bold yellow"),
        highlight=False,
    )
    console.print(
        Text("⭐️⭐️⭐️ Star on GitHub! ⭐️⭐️⭐️", style="bold yellow"), highlight=False
    )
    console.print(
        Text("https://github.com/getbindu/Bindu", style="cyan underline"),
        highlight=False,
    )
    console.print()

    console.print(Text("Join our Community 🤝", style="bold green"), highlight=False)
    console.print(
        Text("https://discord.gg/3w5zuYUuwt", style="cyan underline"), highlight=False
    )
    console.print()

    console.print(Text("Documentation 🌻", style="bold blue"), highlight=False)
    console.print(
        Text("https://docs.getbindu.com", style="cyan underline"), highlight=False
    )
    console.print()
