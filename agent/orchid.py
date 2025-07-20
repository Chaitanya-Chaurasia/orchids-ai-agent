import sys
import os
import typer
import re

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from src.agentic_ai import Agent
from src import config

from prompt_toolkit.completion import WordCompleter
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.key_binding import KeyBindings

class AtPathCompleter(Completer):
    """
    Offer path completions ONLY when the current word begins with “@”.
    """
    def __init__(self, words: list[str]):
        self.words = words

    def get_completions(self, document, complete_event):
        word = document.get_word_before_cursor(WORD=True)
        if not word.startswith("@"):
            return  
        for w in self.words:
            if w.startswith(word):
                yield Completion(w, start_position=-len(word))

kb = KeyBindings()

@kb.add("enter")
def _(event) -> None:  
    buf = event.app.current_buffer
    if buf.complete_state:                          
        comp = buf.complete_state.current_completion
        if comp:
            buf.apply_completion(comp)              
        buf.complete_state = None                   
    else:
        event.app.exit(result=buf.text)             


app = typer.Typer(
    name="orchid",
    help="Orchid AI Agent: Your AI pair programmer for building features and answering questions.",
    add_completion=False,
)
console = Console()

def get_file_paths(root_dir):
    """Recursively gets all file paths from the src directory for autocompletion."""
    file_paths = []
    for root, _, files in os.walk(root_dir):
        for name in files:
            if "node_modules" not in root and ".next" not in root:
                full_path = os.path.join(root, name)
                relative_path = os.path.relpath(full_path, config.PROJECT_ROOT)
                file_paths.append(f"@{relative_path.replace(os.sep, '/')}")
    return file_paths

def _print_welcome_banner():
    """Display a fancy multi-line welcome banner."""
    console.print(Panel("[bold]Welcome to the [bright_magenta]Orchid AI Agent[/bright_magenta]![/bold]", border_style="magenta"))
    banner_text = """
    ██████╗ ██████╗  ██████╗██╗  ██╗██╗██████╗  █████╗ ██╗
    ██╔═══██╗██╔══██╗██╔════╝██║  ██║██║██╔══██╗██╔══██╗██║
    ██║   ██║██████╔╝██║     ███████║██║██║  ██║███████║██║
    ██║   ██║██╔══██╗██║     ██╔══██║██║██║  ██║██╔══██║██║
    ╚██████╔╝██║  ██║╚██████╗██║  ██║██║██████╔╝██║  ██║██║
    ╚═════╝ ╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚═╝╚═════╝ ╚═╝  ╚═╝╚═╝
    """
    console.print(f"[bold deep_pink3]{banner_text}[/bold deep_pink3]", overflow="ignore")
    console.print("[bold green] Ready to assist you with any sophisticated database operations AND/OR general queries.[/bold green]\n")



@app.callback()
def main(ctx: typer.Context):

    if ctx.invoked_subcommand is None:
        _print_welcome_banner()
        help_text = Text.from_markup(
            """
            [bold cyan]How to use Orchid AI:[/bold cyan]

            [bold]1. Initialize the Agent (run this first!):[/bold]
            [dim]This scans your project and prepares the AI.[/dim]
            [yellow]$ python agent/orchid.py init[/yellow]

            [bold]2. Run a Task or Ask a Question:[/bold]
            [dim]Start an interactive session to build features or ask about your code.[/dim]
            [yellow]$ python agent/orchid.py run[/yellow]
            """
        )
        console.print(Panel(help_text, title="[bold green]Getting Started[/bold green]", border_style="green"))


@app.command()
def init():
    """
    Initializes the agent by scanning the codebase and building the vector store.
    """
    console.print(Panel("[bold magenta]🌸 Initializing Orchid AI Agent 🌸[/bold magenta]"))
    console.print("This may take a moment as the agent analyzes your project...")
    try:
        agent = Agent(initialize=False)
        agent.initialize_project()
    except Exception as e:
        console.print(f"[bold red]An unexpected error occurred during initialization: {e}[/bold red]")
        console.print_exception()


@app.command()
def run() -> None:
    _print_welcome_banner()
    try:
        agent = Agent()

        file_completer = AtPathCompleter(get_file_paths(config.SRC_PATH))
        session = PromptSession(
            completer=file_completer,
            key_bindings=kb,
            complete_while_typing=True,
        )

        while True:
            console.print(
                "[bold cyan]Describe your task, or type 'quit' to exit. "
                "Use '@' for file autocompletion.[/bold cyan]"
            )
            full_task = session.prompt("> ")

            if not full_task.strip():
                continue
            if full_task.strip().lower() == "quit":
                console.print("[bold magenta]Goodbye! 🌸[/bold magenta]")
                break

            mentioned_files = re.findall(r"@([\S]+)", full_task)
            agent.start(full_task, user_files=mentioned_files)
            console.print("\n" + "=" * 80 + "\n")

    except Exception as exc:
        console.print(f"[bold red]Unexpected error: {exc}[/bold red]")
        console.print_exception()


if __name__ == "__main__":
    app()