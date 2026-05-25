import sys
import os
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.columns import Columns
from rich import box

if sys.platform == "win32":
    os.system("")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

console = Console(force_terminal=True)

BANNER = """
[bold red]⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⠴⣾⢿⣯⣉⡙⢗⣄⠀⠀⠀⠀⠀[/bold red]
[bold red]⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣴⡽⡽⠊⠉⠉⠺⣿⣆⢋⢵⡀⠀⠀⠀[/bold red]
[bold red]⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡄⠀⠀⢀⣾⣿⠟⠀⠀⠀⠀⠀⣟⠗⠠⣾⣇⠀⠀⠀[/bold red]
[bold bright_red]⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣷⣤⣴⣟⡿⠋⠀⠀⠀⠀⠀⢠⣟⡎⠩⢸⣻⠀⠀⠀[/bold bright_red]
[bold bright_red]⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠉⠉⠉⠀⠀⠀⢀⣀⡠⢶⣱⢚⡴⣵⣿⡿⠀⠀⠀[/bold bright_red]
[bold yellow]⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⡤⣖⣿⢿⢟⢛⡼⣛⣞⣵⣿⠇⠀⠀⠀[/bold yellow]
[bold yellow]⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡠⢺⣭⡗⢭⣀⣵⠋⠅⣡⡋⢸⠙⣿⡀⠀⠀⠀[/bold yellow]
[bold red]⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⢴⢳⢻⢶⡔⡫⢍⣫⠴⣾⢣⡼⢃⣦⡨⢻⣆⠀⠀[/bold red]
[bold red]⡠⡪⠍⢨⠷⢤⡤⢐⠤⠚⣫⣷⣿⡙⢃⡨⣚⢋⣧⣤⣾⣉⢴⣿⡟⠻⡿⠟⣢⣄[/bold red]
[bold bright_red]⠻⣄⡀⣀⣀⣠⡅⠃⡀⢀⠀⠐⠉⠉⠑⢲⣦⢷⠋⠒⢶⢶⣿⡋⠁⠈⠉⠈⠐⠛[/bold bright_red]
[bold yellow]⠀⠀⠙⠋⠉⢉⣿⢿⢿⡶⠾⣷⠽⣠⠁⣈⣿⣶⣷⣧⡔⣁⣠⣉⡄⠀⠀⠀⠀⠀[/bold yellow]
[bold yellow]⠀⠀⣀⢀⡤⣾⢗⠕⠁⣐⠤⠉⡴⢂⡯⡻⠙⠉⠉⠸⠁⣀⣹⠟⠀⠀⠀⠀⠀⠀[/bold yellow]
[bold red]⠀⣰⡓⠑⢯⣼⢲⣖⡫⣵⠧⠾⠾⠛⠋⠀⠀⠀⡠⠇⠸⡿⡗⣀⠀⠀⠀⠀⠀⠀[/bold red]
[bold red]⠀⠘⠛⠋⠛⠂⠉⠉⠉⠀⠀⠀⠀⠀⠀⠀⠀⠘⠓⠺⣤⠛⢺⣿⠅⠀⠀⠀⠀⠀[/bold red]

[bold cyan]  ____                               _ ____            [/bold cyan]
[bold cyan] |  _ \\  ___  ___  ___ ___ _ __   __| / ___|  ___  ___ [/bold cyan]
[bold white] | | | |/ _ \\/ __|/ __/ _ \\ '_ \\ / _` \\___ \\ / _ \\/ __|[/bold white]
[bold white] | |_| |  __/\\__ \\ (_|  __/ | | | (_| |___) |  __/ (__ [/bold white]
[bold cyan] |____/ \\___||___/\\___\\___|_| |_|\\__,_|____/ \\___|\\___| [/bold cyan]
"""

SUBTITLE = "[dim white]Discord OSINT Intelligence Framework[/dim white]"
VERSION = "1.0.0"
AUTHOR = "Nixovena Labs"


def print_banner():
    console.print(BANNER)
    console.print(
        Panel(
            f"[bold cyan]DescendSec[/bold cyan] [dim]v{VERSION}[/dim] | "
            f"[bold white]{SUBTITLE}[/bold white]\n"
            f"[dim]Developed by {AUTHOR}[/dim]",
            border_style="red",
            box=box.DOUBLE_EDGE,
            padding=(0, 2),
        )
    )
    console.print(
        Panel(
            "[bold red]LEGAL WARNING:[/bold red] This tool is developed solely for open-source intelligence, "
            "educational, and academic purposes. The author is not responsible for any misuse. "
            "Use it at your own risk.",
            border_style="yellow",
            box=box.ROUNDED,
            padding=(0, 2),
        )
    )
    console.print()


def print_section(title, style="bold cyan"):
    console.print(f"\n[{style}]{'━' * 60}[/{style}]")
    console.print(f"[{style}]  ▸ {title}[/{style}]")
    console.print(f"[{style}]{'━' * 60}[/{style}]")


def print_field(label, value, label_style="bold white", value_style="cyan"):
    if value is None or value == "":
        value = "[dim]N/A[/dim]"
    console.print(f"  [{label_style}]{label:<24}[/{label_style}] [{value_style}]{value}[/{value_style}]")


def print_success(message):
    console.print(f"  [bold green]✓[/bold green] [green]{message}[/green]")


def print_error(message):
    console.print(f"  [bold red]✗[/bold red] [red]{message}[/red]")


def print_warning(message):
    console.print(f"  [bold yellow]⚠[/bold yellow] [yellow]{message}[/yellow]")


def print_info(message):
    console.print(f"  [bold blue]ℹ[/bold blue] [blue]{message}[/blue]")


def print_status(message, style="bold magenta"):
    console.print(f"\n  [{style}]⟐ {message}[/{style}]")


def create_table(title, columns, rows, show_lines=False):
    table = Table(
        title=f"[bold cyan]{title}[/bold cyan]",
        box=box.ROUNDED,
        border_style="dim cyan",
        show_lines=show_lines,
        padding=(0, 1),
        title_style="bold cyan",
    )

    for col_name, col_style, col_justify in columns:
        table.add_column(col_name, style=col_style, justify=col_justify)

    for row in rows:
        table.add_row(*[str(cell) for cell in row])

    console.print(table)


def print_dict_panel(title, data, border_style="cyan"):
    lines = []
    for key, value in data.items():
        if value is None:
            value = "N/A"
        lines.append(f"[bold white]{key:<22}[/bold white] [cyan]{value}[/cyan]")

    panel_content = "\n".join(lines)
    console.print(
        Panel(
            panel_content,
            title=f"[bold]{title}[/bold]",
            border_style=border_style,
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )


def print_list_panel(title, items, border_style="cyan", bullet="▸"):
    lines = [f"[cyan]{bullet}[/cyan] [white]{item}[/white]" for item in items]
    console.print(
        Panel(
            "\n".join(lines),
            title=f"[bold]{title}[/bold]",
            border_style=border_style,
            box=box.ROUNDED,
            padding=(0, 2),
        )
    )


def print_risk_score(score, label="Risk Assessment"):
    if score >= 80:
        color = "red"
        level = "CRITICAL"
    elif score >= 60:
        color = "bright_red"
        level = "HIGH"
    elif score >= 40:
        color = "yellow"
        level = "MEDIUM"
    elif score >= 20:
        color = "green"
        level = "LOW"
    else:
        color = "bright_green"
        level = "MINIMAL"

    bar_filled = int(score / 5)
    bar_empty = 20 - bar_filled
    bar = f"[{color}]{'█' * bar_filled}[/{color}][dim]{'░' * bar_empty}[/dim]"

    console.print(f"\n  [bold white]{label}:[/bold white]")
    console.print(f"  {bar} [{color}]{score}% - {level}[/{color}]")


def print_separator():
    console.print("[dim]" + "─" * 60 + "[/dim]")


def print_json_data(data, title="JSON Output"):
    from rich.syntax import Syntax
    import json
    formatted = json.dumps(data, indent=2, ensure_ascii=False, default=str)
    syntax = Syntax(formatted, "json", theme="monokai", line_numbers=False)
    console.print(Panel(syntax, title=f"[bold]{title}[/bold]", border_style="cyan"))
