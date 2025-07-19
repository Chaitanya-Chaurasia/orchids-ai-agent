import sys
import os
import typer

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from rich.console import Console
from rich.panel import Panel
from src.agentic_ai import Agent
from pyfiglet import Figlet

app = typer.Typer(
    name="orchid",
    help="Orchid AI Agent: Your AI pair programmer for database tasks.",
    add_completion=False,
)
console = Console()


def _print_welcome_banner():
    """Display a fancy multi-line welcome banner similar to Claude Code preview."""
    console.print(Panel("[bold]Welcome to the [bright_magenta]Orchid AI Agent[/bright_magenta]![/bold]", border_style="magenta"))

    banner_text = Figlet(font="banner3").renderText("ORCHID AI")

    console.print(f"[bold deep_pink3]{banner_text}[/bold deep_pink3]", overflow="ignore")
    console.print("[bold green]🎉 Ready. Press Enter to continue[/bold green]")


@app.command()
def run():

    _print_welcome_banner()
    
    console.print("[bold cyan]Describe your task. Submit an empty line when done:[/bold cyan]")
    lines: list[str] = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip() == "":
            break
        lines.append(line)
    full_task = "\n".join(lines).strip()

    if not full_task:
        console.print("[yellow]No task provided. Exiting.[/yellow]")
        return

    try:
        agent = Agent()
        agent.start(full_task)
    except Exception as e:
        console.print(f"[bold red]An unexpected error occurred: {e}[/bold red]")
        console.print_exception()

if __name__ == "__main__":
    app()