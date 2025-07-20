import os
import time
import json
import requests
import subprocess
import inquirer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.progress import track
from rich.markdown import Markdown
from rich.align import Align
import google.generativeai as genai
import hashlib
from src import config
from src.vector_store import VectorStore
from typing import List


class Agent:
    def __init__(self, initialize: bool = True):
        self.console = Console()
        self.vector_store: VectorStore | None = None
        if config.GEMINI_API_KEY == "YOUR_API_KEY_HERE":
            self.console.print(Panel("[bold red]Warning:[/bold red] GEMINI_API_KEY is not set. Please set it in your .env file.", title="Configuration Error", border_style="red"))
            exit()
        genai.configure(api_key=config.GEMINI_API_KEY)
        
        if initialize:
            if not os.path.exists(config.QDRANT_PATH):
                self.console.print(Panel("[bold red]Project not initialized![/bold red]\nPlease run `python agent/orchid.py init` first.", title="Initialization Error", border_style="red"))
                exit()
            self._load_context()
    
    def _load_context(self):
        if self.vector_store:
            return
        all_files = []
        for root, _, files in os.walk(config.SRC_PATH):
            for name in files:
                if "node_modules" not in root and ".next" not in root and name.endswith(('.ts', '.tsx', '.js', '.jsx')):
                    all_files.append(os.path.join(root, name))
        project_hash = self.get_project_hash(all_files)
        self.vector_store = VectorStore(collection_name=project_hash)
        if not self.vector_store.collection_exists():
            self.console.print(Panel("[bold yellow]Codebase has changed.[/bold yellow] Re-initializing is recommended. Run `python agent/orchid.py init`.", title="Stale Cache Warning"))

    def think(self, message):
        self.console.print(Panel(f"[bold cyan]🤖 Agent thinking...[/bold cyan]\n[italic]{message}[/italic]"))
        time.sleep(1)

    def act(self, message):
        self.console.print(Panel(f"[bold green]🚀 Agent in action...[/bold green]\n{message}"))
        time.sleep(1)

    def show_code(self, code, language="typescript"):
        self.console.print(Syntax(code, language, theme="monokai", line_numbers=True, word_wrap=True))
        
    def get_project_hash(self, file_paths):
        hasher = hashlib.sha256()
        for path in sorted(file_paths):
            try:
                mod_time = os.path.getmtime(path)
                hasher.update(path.encode())
                hasher.update(str(mod_time).encode())
            except OSError:
                continue
        return hasher.hexdigest()

    def initialize_project(self):
        """Scans all files and builds the vector store from scratch."""
        self.think("First, I need to analyze the project and build a semantic understanding of the code.")
        all_files = []
        for root, _, files in os.walk(config.SRC_PATH):
            for name in files:
                if "node_modules" not in root and ".next" not in root and name.endswith(('.ts', '.tsx', '.js', '.jsx')):
                    all_files.append(os.path.join(root, name))

        project_hash = self.get_project_hash(all_files)
        self.vector_store = VectorStore(collection_name=project_hash)

        self.console.print("[yellow]Building new vector store...[/yellow]")
        chunks = []
        for file_path in track(all_files, description="[green]Analyzing project files...[/green]"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    for i in range(0, len(content), 1000):
                        chunks.append({"path": file_path, "code": content[i:i+1000]})
            except Exception as e:
                self.console.print(f"[yellow]Could not read file {file_path}: {e}[/yellow]")
        
        self.vector_store.build_collection(chunks)
        self.console.print(Panel("[bold green]✅ Project Initialized Successfully![/bold green]", title="Initialization Complete"))


    def _classify_intent(self, query: str) -> str:
        """Classifies the user's intent as a build request or a question."""
        self.think("Classifying user intent...")
        prompt = f"""
        You are a classifier for a command-line code agent.  
        Return **exactly one** of the two labels below—nothing else, no punctuation:

        build_request
        question

        **Definitions**

        build_request — The user wants the agent to create, modify, delete, set up, or otherwise act on code, configuration, or functionality, or is asking for step-by-step directions to do so.  
        Common verbs/phrases: add, implement, set up, create, generate, write, update, refactor, remove, delete, fix, configure, "how do I ...", "can you make ...", "please build ...".

        question — The user is only seeking information, clarification, explanation, or a summary about the existing codebase or a concept, with no request to change or create anything.  
        Common verbs/phrases: what, why, explain, describe, summarize, list, which, where, "do I need to ...".

        **Edgecase rules**

        1. Mixed intent: If the request both asks for information and tells the agent to build or change something, output build_request (action overrides inquiry).  
        2. Advice questions: "Should I delete X?" or "Do I need to refactor Y?" are question (seeking advice).  
        3. Hypothetical implementation: "How would I add logging?" or "Can you show me how to integrate Z?" are build_request (asking for implementation guidance).  
        4. Brief/ambiguous: One-word or fragment queries like "Logging?" default to question unless clearly action oriented.  
        5. Non-requests: Gratitude or small talk ("thanks", "cool") default to question.  
        6. When unsure, favor question—only label build_request when an action is clearly requested.

        Respond with one lowercase word: build_request or question.

        Request: "{query}"
        """

        try:
            model = genai.GenerativeModel('gemini-2.5-pro')
            response = model.generate_content(prompt)
            intent = response.text.strip().lower()
            if intent in ["build_request", "question"]:
                self.console.print(f"[dim]Intent classified as: {intent}[/dim]")
                return intent
            return "build_request" # Default to build if classification is unclear
        except Exception as e:
            self.console.print(f"[bold red]Could not classify intent: {e}. Defaulting to build request.[/bold red]")
            return "build_request"
    
    def _classify_database_intent(self, task: str) -> str:
        """Uses Gemini to classify the user's desired database from the initial prompt."""
        self.think("Analyzing prompt for specific database request...")
        prompt = f"""
        Analyze the user's request and identify which database they want to use.
        The possible databases are "SQLite", "MongoDB", or "Supabase".

        If the user mentions a database that is not one of these three (e.g., "Postgres", "MySQL"), or if it's ambiguous, respond with "Unsupported".
        If the user clearly mentions one of the three, even with typos (e.g., "sqllite", "mongo db", "supa base"), respond with the corrected, single-word name: "SQLite", "MongoDB", or "Supabase".
        If no database is mentioned, respond with "Unknown".

        Respond with only a single word.

        User Request: "{task}"
        """
        try:
            model = genai.GenerativeModel('gemini-2.5-flash')
            response = model.generate_content(prompt)
            db_intent = response.text.strip()
            if db_intent in ["SQLite", "MongoDB", "Supabase", "Unknown", "Unsupported"]:
                self.console.print(f"[dim]Database intent classified as: {db_intent}[/dim]")
                return db_intent
            return "Unknown"
        except Exception as e:
            self.console.print(f"[bold red]Could not classify database intent: {e}. Defaulting to Unknown.[/bold red]")
            return "Unknown"

    def _execute_answer_task(self, query: str, user_files: List[str]):
        """Handles the workflow for answering a question."""
        self._generate_answer_with_gemini(query, user_files)

    def _execute_build_task(self, task: str, user_files: List[str]):
        """Handles the workflow for building a feature."""        
        db_type = self._classify_database_intent(task)

        if db_type == "Unsupported":
            self.console.print("[bold red]Sorry, the database you mentioned is not supported.[/bold red]")
            db_type = "Unknown" 

        package_json_path = os.path.join(config.PROJECT_ROOT, "package.json")
        is_configured = False
        try:
            with open(package_json_path, "r") as f:
                deps = json.load(f).get("dependencies", {})
                drizzle_installed = "drizzle-orm" in deps
                driver_installed = "pg" in deps or "better-sqlite3" in deps
                if drizzle_installed and driver_installed:
                    is_configured = True
        except FileNotFoundError:
            self.console.print("[yellow]Warning: package.json not found.[/yellow]")

        if is_configured:
            self.act("Project analysis complete. It seems Drizzle and a database are already configured.")
            if db_type == "Unknown": 
                with open(package_json_path, "r") as f:
                    deps = json.load(f).get("dependencies", {})
                    if "pg" in deps:
                        db_type = "Supabase"
                    elif "better-sqlite3" in deps:
                        db_type = "SQLite"
        
        elif not is_configured and db_type == "Unknown":
            self.act("I see your project isn't fully configured. Let's set one up!")
            questions = [
                inquirer.List('db_choice',
                              message="Which database would you like to use?",
                              choices=['SQLite (local, no setup)', 'MongoDB', 'Supabase (Postgres)'],
                              ),
            ]
            db_choice = inquirer.prompt(questions)['db_choice'].split(' ')[0]
            db_type = db_choice
            if db_choice in ["MongoDB", "Supabase"]:
                self._setup_env_file(db_choice)
        
        elif not is_configured and db_type != "Unknown":
            self.act(f"Okay, I'll set up your project to use {db_type}.")
            if db_type in ["MongoDB", "Supabase"]:
                self._setup_env_file(db_type)

        plan = self._generate_plan_with_gemini(task, db_type, user_files)
        if plan:
            self._execute_plan(plan)
            if plan.get("plan"):
                 self.console.print(Panel("[bold green]✅ All tasks completed successfully![/bold green]"))
        else:
            self.console.print(Panel("[bold red]❌ Agent could not complete the task.[/bold red]"))


    def _setup_env_file(self, db_choice):
        """Guides the user through setting up their .env file."""
        self.think(f"I need to help the user configure their .env file for {db_choice}.")
        env_vars = {}
        if db_choice == "MongoDB":
            env_vars['DATABASE_URL'] = inquirer.text(message="Please enter your MongoDB connection string (e.g., mongodb+srv://...)")
        elif db_choice == "Supabase":
            env_vars['DATABASE_URL'] = inquirer.text(message="Please enter your Supabase connection string (postgres://...)")
        
        if not env_vars:
            return

        self.act("I will now add the following to your `.env` file. Please confirm.")
        for key, value in env_vars.items():
            self.console.print(f"[yellow]{key}[/yellow]=[green]{value}[/green]")
        
        if inquirer.prompt([inquirer.Confirm('proceed', message="Write these values to .env?", default=True)])['proceed']:
            try:
                env_path = os.path.join(config.PROJECT_ROOT, ".env")
                with open(env_path, "a", encoding="utf-8") as f:
                    f.write("\n\n# Added by Orchid AI Agent\n")
                    for key, value in env_vars.items():
                        f.write(f"{key}={value}\n")
                self.console.print("[green]✅ .env file updated successfully.[/green]")
            except IOError as e:
                self.console.print(f"[bold red]Error writing to .env file: {e}[/bold red]")

    def _generate_plan_with_gemini(self, task, db_type, user_files: List[str] = None):
        self.think(f"Searching for code relevant to '{task}'...")
        relevant_chunks = self.vector_store.search(task)
        context = "\n".join([f"--- START OF {chunk['path']} ---\n{chunk['code']}\n--- END OF {chunk['path']} ---" for chunk in relevant_chunks])

        user_file_context = ""
        if user_files:
            self.think("Loading content from user-specified files...")
            for file_path in user_files:
                try:
                    full_path = os.path.join(config.PROJECT_ROOT, file_path)
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    user_file_context += f"--- START OF {file_path} ---\n{content}\n--- END OF {file_path} ---\n\n"
                except FileNotFoundError:
                    self.console.print(f"[yellow]Warning: File not found: {file_path}[/yellow]")
                except Exception as e:
                    self.console.print(f"[red]Error reading file {file_path}: {e}[/red]")
        
        prompt = f"""
        You are an expert Next.js and Drizzle ORM developer. Your task is to implement a new database feature.
        **User Request:** "{task}"
        **User-Provided File Context (High Priority):**
        {user_file_context or "None"}
        **Project Context:**
        - **Database Type:** {db_type}
        - **Relevant Code Snippets:**
        {context}
        **Your Goal:**
        Generate a step-by-step plan. The plan should consist of `CREATE_FILE` or `UPDATE_FILE` actions. You must also identify any new npm packages that need to be installed.
        **Output Format:**
        Respond with ONLY a valid JSON object.
        ```json
        {{
        "dependencies": ["package-name-if-needed"],
        "plan": [
            {{
            "action": "CREATE_FILE",
            "path": "path/to/new/file.ts",
            "thought": "A brief explanation of why you are creating this file.",
            "code": "FULL_CODE_FOR_THE_FILE"
            }},
            {{
            "action": "UPDATE_FILE",
            "path": "path/to/existing/file.tsx",
            "thought": "A brief explanation of why you are updating this file.",
            "code": "THE_ENTIRE_UPDATED_FILE_CONTENT"
            }}
        ]
        }}
        ```
        """
        headers = {"Content-Type": "application/json"}
        data = {"contents": [{"parts": [{"text": prompt}]}]}
        
        max_retries = 5
        base_wait_time = 2
        
        for i in range(max_retries):
            try:
                with self.console.status("[bold green]🤖 Gemini is thinking...[/bold green]"):
                    response = requests.post(config.GEMINI_API_URL, headers=headers, json=data, timeout=180)
                    response.raise_for_status()
                
                content = response.json()['candidates'][0]['content']['parts'][0]['text']
                if content.startswith("```json"):
                    content = content[7:-3].strip()
                return json.loads(content)

            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    wait_time = base_wait_time ** i
                    self.console.print(f"[bold yellow]Rate limit hit. Waiting for {wait_time}s... ({i+1}/{max_retries})[/bold yellow]")
                    time.sleep(wait_time)
                else:
                    self.console.print(f"[bold red]HTTP error: {e}[/bold red]")
                    return None
            except Exception as e:
                self.console.print(f"[bold red]Error interacting with Gemini: {e}[/bold red]")
                return None
        
        self.console.print(f"[bold red]Failed to get a response from Gemini after {max_retries} retries.[/bold red]")
        return None

    def _generate_answer_with_gemini(self, query, user_files: List[str] = None):
        self.think(f"Searching for code relevant to '{query}'...")
        relevant_chunks = self.vector_store.search(query)
        context = "\n".join(
            f"--- START OF {c['path']} ---\n{c['code']}\n--- END OF {c['path']} ---"
            for c in relevant_chunks
        )

        user_file_context = ""
        if user_files:
            self.think("Loading content from user-specified files...")
            for file_path in user_files:
                try:
                    full_path = os.path.join(config.PROJECT_ROOT, file_path)
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    user_file_context += f"--- START OF {file_path} ---\n{content}\n--- END OF {file_path} ---\n\n"
                except FileNotFoundError:
                    self.console.print(f"[yellow]Warning: File not found: {file_path}[/yellow]")
                except Exception as e:
                    self.console.print(f"[red]Error reading file {file_path}: {e}[/red]")


        prompt = f"""
        You are an expert Next.js and Drizzle ORM developer. Your task is to implement a new database feature.
        **User Request:** "{query}"

        **User-Provided File Context (High Priority):**
        {user_file_context or "None"}

        **Relevant Code Snippets (from automatic search):**
        {context}
        **Your Goal:**
        Generate a step-by-step plan. The plan should consist of `CREATE_FILE` or `UPDATE_FILE` actions. You must also identify any new npm packages that need to be installed.
        **Output Format:**
        Respond with ONLY a valid JSON object.
        ```json
        {{
        "dependencies": ["package-name-if-needed"],
        "plan": [
            {{
            "action": "CREATE_FILE",
            "path": "path/to/new/file.ts",
            "thought": "A brief explanation of why you are creating this file.",
            "code": "FULL_CODE_FOR_THE_FILE"
            }},
            {{
            "action": "UPDATE_FILE",
            "path": "path/to/existing/file.tsx",
            "thought": "A brief explanation of why you are updating this file.",
            "code": "THE_ENTIRE_UPDATED_FILE_CONTENT"
            }}
        ]
        }}
        ```
        """

        headers = {"Content-Type": "application/json"}
        data = {"contents": [{"parts": [{"text": prompt}]}]}

        try:
            response = requests.post(
                config.GEMINI_API_URL, headers=headers, json=data, timeout=180
            )
            response.raise_for_status()
            # thought = response.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            answer = response.json()["candidates"][0]["content"]["parts"][0]["text"].strip()

            md_renderable = Markdown(answer, justify="left", code_theme="monokai")
            panel = Panel(
                Align.left(md_renderable),
                title="[bold cyan]🤖 Orchid's Answer[/bold cyan]",
                border_style="cyan",
                padding=(1, 2),
                expand=True,
            )
            self.console.print(panel)

        except requests.exceptions.RequestException as e:
            self.console.print(f"[bold red]Error during API request: {e}[/bold red]")
        except (KeyError, IndexError, ValueError):
            self.console.print("[bold red]Unexpected response format from Gemini API.[/bold red]")

    def _execute_plan(self, full_plan):

        if not full_plan:
            self.console.print("[bold red]No valid plan received. Aborting.[/bold red]")
            return

        self.console.print(Panel("[bold yellow]Gemini has generated the following plan. Please review carefully.[/bold yellow]", title="Execution Plan"))
        
        plan_steps = full_plan.get("plan", [])
        
        summary_table = Table(title="Execution Plan Summary")
        summary_table.add_column("Step", style="dim")
        summary_table.add_column("Action", style="cyan")
        summary_table.add_column("File Path", style="magenta")
        summary_table.add_column("Thought", style="green")

        for i, step in enumerate(plan_steps):
            summary_table.add_row(
                str(i + 1),
                step.get('action', 'N/A'),
                step.get('path', 'N/A'),
                step.get('thought', 'N/A')
            )
        
        self.console.print(summary_table)
        if not inquirer.prompt([inquirer.Confirm('proceed_summary', message="Do you want to proceed with reviewing this plan step-by-step?", default=True)])['proceed_summary']:
            self.console.print("[bold yellow]Operation cancelled by user.[/bold yellow]")
            return

        dependencies = full_plan.get("dependencies", [])
        if dependencies:
            self.act(f"Plan requires new dependencies: [bold yellow]{', '.join(dependencies)}[/bold yellow]")
            if inquirer.prompt([inquirer.Confirm('install', message="Install them with 'npm install'?", default=True)])['install']:
                try:
                    command = ["npm", "install", "--legacy-peer-deps"] + dependencies
                    with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, shell=True, cwd=config.PROJECT_ROOT) as proc:
                        for line in proc.stdout: self.console.print(line, end='')
                    
                    if proc.returncode == 0:
                        self.console.print("[green]✅ Dependencies installed.[/green]")
                    else:
                        self.console.print(f"[bold red]Installation failed with exit code {proc.returncode}. Aborting.[/bold red]")
                        return
                except Exception as e:
                    self.console.print(f"[bold red]Error installing dependencies: {e}[/bold red]")
                    return
            else:
                self.console.print("[yellow]Skipping dependency installation.[/yellow]")

        staged_changes = {}
        user_cancelled = False

        for i, step in enumerate(plan_steps):
            self.console.print(f"\n--- Step {i+1}/{len(plan_steps)} ---")
            self.think(step.get('thought', 'No thought provided.'))
            action, path, code = step.get('action'), step.get('path'), step.get('code')
            if not all([action, path, code]):
                self.console.print(f"[red]Skipping invalid step.[/red]"); continue
            
            self.act(f"Action: [bold magenta]{action}[/bold magenta] on file: [bold cyan]{path}[/bold cyan]")
            self.show_code(code)
            if inquirer.prompt([inquirer.Confirm('proceed', message="Apply this change?", default=True)])['proceed']:
                staged_changes[path] = code
            else:
                user_cancelled = True
                break
        
        if user_cancelled and staged_changes:
            if inquirer.prompt([inquirer.Confirm('partial_commit', message=f"You cancelled the operation. Apply the {len(staged_changes)} changes you already approved?", default=False)])['partial_commit']:
                 self.act("Applying previously approved changes...")
            else:
                self.console.print("[bold yellow]All changes have been discarded.[/bold yellow]")
                return
        elif user_cancelled:
             self.console.print("[bold yellow]All changes have been discarded.[/bold yellow]")
             return
        
        if staged_changes:
            self.act("Committing all approved changes to the filesystem...")
            for path, code in staged_changes.items():
                try:
                    absolute_path = os.path.join(config.PROJECT_ROOT, path)
                    if (dir_name := os.path.dirname(absolute_path)): os.makedirs(dir_name, exist_ok=True)
                    with open(absolute_path, "w", encoding="utf-8") as f: f.write(code)
                    self.console.print(f"[green]✅ Wrote changes to {path}[/green]")
                except IOError as e:
                    self.console.print(f"[bold red]Error writing file {path}: {e}[/bold red]")

    
    def start(self, query: str, user_files: List[str] = None):
        """Main entry point that classifies intent and routes to the correct workflow."""
        intent = self._classify_intent(query)
        if intent == "question":
            self._execute_answer_task(query, user_files)
        else:
            self._execute_build_task(query, user_files)