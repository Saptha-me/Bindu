"""Display utilities for the bindu server."""

from __future__ import annotations

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table


def prepare_server_display(host: str = None, port: int = None, agent_id: str = None) -> str:
    """Prepare the colorful ASCII display for the server.

    Args:
        host: Server hostname
        agent_id: Agent identifier

    Returns:
        A string containing a formatted ASCII art display for the server
    """
    # ASCII art components
    bindu_text = r"""
                 ____  _           _       
                | __ )(_)_ __   __| |_   _ 
                |  _ \| | '_ \ / _` | | | |
                | |_) | | | | | (_| | |_| |
                |____/|_|_| |_|\__,_|\__,_|
"""
    
    bindu_symbol = r"""
                     .-( : )-.
                    (   \''/   )
                   ( `'.;;;.'`  )
                  ( :-=;;;;;=-: )
                   (  .';;;'.  )
                    (`  /.\  ` )
                     '-(_:_)-'
"""
    
    space_art = r"""
{{            +             +                  +   @          {{
}}   |                *           o     +                .    }}
{{  -O-    o               .               .          +       {{
}}   |                    _,.-----.,_         o    |          }}
{{           +    *    .-'.         .'-.          -O-         {{
}}      *            .'.-'   .---.   `'.'.         |     *    }}
{{ .                /_.-'   /     \   .-'.\                   {{
}}         ' -=*<  |-._.-  |   @   |   '-._|  >*=-    .     + }}
{{ -- )--           \`-.    \     /    .-'/                   {{
}}       *     +     `.'.    '---'    .'.'    +       o       }}
{{                  .  '-._         _.-'  .                   {{
}}         |               `~~~~~~~`       - --===D       @   }}
{{   o    -O-      *   .                  *        +          {{
}}         |                      +         .            +    }}
{{ jgs          .     @      o                        *       {{
}}       o                          *          o           .  }}
"""

    try:
        console = Console(record=True)

        # Create colorful header with gradient effect
        header = Text()
        header.append(bindu_text, style="bold magenta")
        header.append(bindu_symbol, style="bold yellow")
        header.append("\n")
        header.append(space_art, style="cyan")
        
        # Version and tagline with vibrant colors
        info = Text()
        info.append("\n")
        info.append("bindu ", style="bold bright_magenta")
        info.append("v0.1.0", style="bold bright_yellow on black")
        info.append("\n")
        info.append("🌻 A Protocol Framework for Agent to Agent Communication", style="bold bright_green italic")
        
        # Server info table for better organization
        if host or port or agent_id:
            info.append("\n\n")
            
            table = Table(show_header=False, box=None, padding=(0, 1))
            table.add_column(style="bold bright_blue")
            table.add_column(style="bold bright_cyan")
            
            if host and port:
                table.add_row("🚀 Status:", "Starting bindu Server...")
                table.add_row("📡 Server URL:", f"[underline]http://{host}:{port}[/underline]")
            
            if agent_id:
                table.add_row("🌻 Agent ID:", f"[bright_yellow]{agent_id}[/bright_yellow]")
            
            with console.capture() as table_capture:
                console.print(table)
            info.append(table_capture.get())
        
        # Combine all elements
        display_content = header + info
        
        # Create panel with gradient border
        display_panel = Panel.fit(
            display_content,
            title="[bold cyan on blue]🌻 bindu Protocol Framework 🌻[/bold cyan on blue]",
            border_style="bright_magenta",
            box=box.DOUBLE,
        )

        with console.capture() as capture:
            console.print(display_panel)
        return capture.get()
    except ImportError:
        # Fallback display without rich formatting
        fallback_parts = [
            bindu_text,
            bindu_symbol,
            space_art,
            "\n🌻 bindu Protocol Framework v0.1.0",
            "A Protocol Framework for Agent to Agent Communication\n"
        ]
        
        if host and port:
            fallback_parts.extend([
                f"\n🚀 Status: Starting bindu Server...",
                f"📡 Server URL: http://{host}:{port}"
            ])
        
        if agent_id:
            fallback_parts.append(f"🌻 Agent ID: {agent_id}")
        
        return "\n".join(fallback_parts)
