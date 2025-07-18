import typer
from rich.console import Console
from src.agentic_ai import Agent
from rich.panel import Panel

app = typer.Typer(
    name="orchid",
    help="Orchid AI Agent: Your AI pair programmer for database tasks.",
    add_completion=False,
)
console = Console()

@app.command()
def run(
    task: str = typer.Argument(
        ..., help="The high-level task you want the agent to perform."
    )
):
    """
    Starts the AI agent to analyze your codebase and implement the requested feature.
    """
    console.print(Panel("[bold magenta]🌸 Orchid AI Agent Initializing 🌸[/bold magenta]"))
    try:
        agent = Agent()
        agent.start(task)
    except Exception as e:
        console.print(f"[bold red]An unexpected error occurred: {e}[/bold red]")

if __name__ == "__main__":
    app()