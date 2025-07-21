import os
import time
import json
import re
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
            self.console.print(
                Panel(
                    "[bold red]GEMINI_API_KEY is not set. Please add it to your .env.[/bold red]",
                    title="Configuration Error",
                    border_style="red",
                )
            )
            raise SystemExit
        genai.configure(api_key=config.GEMINI_API_KEY)
        if initialize:
            if not os.path.exists(config.QDRANT_PATH):
                self.console.print(
                    Panel(
                        "[bold red]Project not initialized![/bold red]\nRun "
                        "`python agent/orchid.py init` first.",
                        title="Initialization Error",
                        border_style="red",
                    )
                )
                raise SystemExit
            self._load_context()
    
    def think(self, message):
        self.console.print(f"\n[bold cyan]🌸 OrchidAI is thinking...\n[/bold cyan]  [italic]{message}[/italic]\n")

    def act(self, message):
        self.console.print(f"\n[bold green]🌸 OrchidAI is in action...\n[/bold green]  [italic]{message}[/italic]")

    def show_code(self, code, language="typescript"):
        self.console.print(Syntax(code, language, theme="monokai", line_numbers=True, word_wrap=True))

    @staticmethod
    def _project_hash(file_paths: List[str]) -> str:
        hasher = hashlib.sha256()
        for path in sorted(file_paths):
            try:
                hasher.update(path.encode())
                hasher.update(str(os.path.getmtime(path)).encode())
            except OSError:
                continue
        return hasher.hexdigest()

    def _load_context(self):
        if self.vector_store:
            return

        all_files = [
            os.path.join(root, name)
            for root, _, files in os.walk(config.SRC_PATH)
            for name in files
            if "node_modules" not in root
            and ".next" not in root
            and name.endswith((".ts", ".tsx", ".js", ".jsx"))
        ]

        project_hash = self._project_hash(all_files)
        self.vector_store = VectorStore(collection_name=project_hash)

        if not self.vector_store.collection_exists():
            self.console.print(
                Panel(
                    "[bold yellow]Codebase has changed.[/bold yellow] "
                    "Re‑initialization recommended: "
                    "`python agent/orchid.py init`.",
                    title="Stale Cache Warning",
                    border_style="yellow",
                )
            )

    def initialize_project(self):
        """Scans all files and builds the vector store from scratch."""
        self.think("First, I need to analyze the project and build a semantic understanding of the code.")
        all_files = [
            os.path.join(root, name)
            for root, _, files in os.walk(config.SRC_PATH)
            for name in files
            if "node_modules" not in root
            and ".next" not in root
            and name.endswith((".ts", ".tsx", ".js", ".jsx"))
        ]

        project_hash = self._project_hash(all_files)
        self.vector_store = VectorStore(collection_name=project_hash)

        chunks = []
        for file_path in track(all_files, description="[green] ➜  Analyzing project files...[/green]"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    for i in range(0, len(content), 1000):
                        chunks.append({"path": file_path, "code": content[i:i+1000]})
            except Exception as e:
                self.console.print(f"[bold red]Could not read file {file_path}: {e}[/bold red]")
        
        self.vector_store.build_collection(chunks)
        self.console.print("\n[bold green](✓) Project Initialized Successfully![/bold green]\n")

    def _classify_intent(self, query: str) -> str:
        """Classifies the user's intent as a build request or a question."""
        self.think("Classifying user intent...")
        prompt = f"""
        You are a classifier for a command-line code agent.  
        Return exactly TWO lines:

        1. The single word 'build_request' or 'question'.
        2. A one-sentence explanation (≤120 chars) describing *why* you chose that label.

        Do not add anything else—no punctuation before or after the word,
        no Markdown fences, no blank lines.

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
            model = genai.GenerativeModel("gemini-2.5-flash-lite-preview-06-17")
            response = model.generate_content(prompt)
            lines = [l.strip() for l in response.text.strip().splitlines() if l.strip()]
            label = lines[0].lower() if lines else "build_request"
            reason = lines[1] if len(lines) > 1 else "No reason returned."

            if label not in {"build_request", "question"}:
                label, reason = "build_request", "Model returned unexpected label."
            self.last_intent_reason = reason
            self.console.status("[bold blue]Breaking down user's prompt.")
            time.sleep(1)
            self.console.print(f"[bold cyan]➜ Got it, {reason}[/bold cyan]")
            return label

        except Exception as e:
            self.console.print(
                f"[bold red]Could not classify intent: {e}. "
                "Defaulting to build_request.[/bold red]"
            )
            self.last_intent_reason = "Defaulted due to error."
        return "build_request"
    
    def _classify_database_intent(self, task: str) -> str:
    
        self.think("Analyzing prompt for specific database request...")

        prompt = f"""
        You are an ultra-precise **single-word classifier**.

        ────────────────────────────────────────────────────────
        ## Goal
        Look at the **user's request** and output **one word** that best represents the database they intend to use:

        - `SQLite`
        - `MongoDB`
        - `Supabase`   ← interpret as “Postgres-compatible cloud DB”
        - `Unknown`    ← no clear hint
        - `Unsupported`← mentions another DB (MySQL, Redis, etc.) or it's ambiguous and not one of the three above

        Return nothing else—**no punctuation, no code-blocks**.

        ────────────────────────────────────────────────────────
        ## 1. Exact-match keywords → label immediately
        | Keyword variants → Return |
        |---------------------------|
        | sqlite, sqllite, "better-sqlite3", "better sqlite", ".db file", "file-based sql", "local sql db" | **SQLite** |
        | mongo, mongodb, "mongo db", "mongoose", "mongodb+srv://" | **MongoDB** |
        | supabase, postgres, postgresql, pg, neondb, neon database, "postgres://", "pg connection", "drizzle-orm with pg driver", "drizzle-orm/postgres" | **Supabase** |
        | mysql, planetscale, redis, dynamodb, firestore, cassandra, oracle, mssql, duckdb, sqlserver, timescale, prisma (without pg), "any sql" | **Unsupported** |

        > **Rule of thumb:** If the keyword clearly maps, choose it—even with typos ("supa base", "sqllte", "mongo-atlas").

        ────────────────────────────────────────────────────────
        ## 2. Implicit cues (only if no exact keyword)
        ### Treat as **Supabase** when:
        - Mentions **Drizzle** *and* any Postgres hint (`pg` driver, etc.).
        - Mentions **Neon**, Railway Postgres, or “serverless Postgres”.
        - Mentions env vars like `SUPABASE_URL`, `DATABASE_URL=postgres://`.

        ### Treat as **SQLite** when:
        - Mentions “embedded DB”, “single .db file”, “no setup database”.

        ### Treat as **MongoDB** when:
        - Mentions Atlas, Prisma mongodb provider, “NoSQL document store”.

        ────────────────────────────────────────────────────────
        ## 3. Otherwise
        - Generic “implement a database” with no clues → **Unknown**.
        - Conflicting or multiple different DBs → **Unsupported**.

        ────────────────────────────────────────────────────────
        ## 4. Examples

        | Request                                                                                                | Return |
        |--------------------------------------------------------------------------------------------------------|--------|
        | “Set up drizzle-orm with pg in my Next.js app”                                                         | Supabase |
        | “Please add a mongodb model for users”                                                                 | MongoDB |
        | “Use neon serverless database”                                                                         | Supabase |
        | “Store data locally in a .db file so users don't need a server”                                        | SQLite |
        | “Switch from PlanetScale to Drizzle”                                                                   | Unsupported |
        | “Implement database features for @src/components/spotify-main-content.tsx”                             | Unknown |
        | “I want persistence, maybe mysql?”                                                                     | Unsupported |

        ────────────────────────────────────────────────────────
        ## 5.Output FORMAT (STRICT)

        Return **exactly two lines**:

        1. The single word: `SQLite`, `MongoDB`, `Supabase`, `Unknown`, or `Unsupported`.
        2. One sentence (≤120 chars) explaining why you chose that label.

        No blank lines, no extra commentary.

        User request:
        {task}
        """

        try:
            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content(prompt)
            lines = [l.strip() for l in response.text.strip().splitlines() if l.strip()]

            label = lines[0] if lines else "Unknown"
            reason = lines[1] if len(lines) > 1 else "No reason returned."

            if label not in {"SQLite", "MongoDB", "Supabase", "Unknown", "Unsupported"}:
                label, reason = "Unknown", "Model returned unexpected label."

            self.last_db_reason = reason
            self.console.status("\n[bold blue]Is the user asking for database operation/implementation?\n")
            time.sleep(1)
            self.console.print(f"[bold cyan]➜ Perfect, {reason}[/bold cyan]")

            return label

        except Exception as e:
            self.console.print(
                f"[bold red]Could not classify database intent: {e}. Defaulting to Unknown.[/bold red]"
            )
            self.last_db_reason = "Defaulted due to error."
            return "Unknown"

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
                self.console.print(Panel("[bold green](✓) All tasks completed successfully![/bold green]"))
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
                self.console.print("[green](✓) .env file updated successfully.[/green]")
            except IOError as e:
                self.console.print(f"[bold red]Error writing to .env file: {e}[/bold red]")

    def extract_plan(self, raw: str) -> dict | None:
        """
        Pull the first JSON object out of a Gemini response.
        Returns None if nothing valid is found.
        """
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
        if raw.startswith("data:"):
            raw = raw.split("data:", 1)[1].strip()

        match = re.search(r"```json\s*(\{.*?\})\s*```", raw, re.S)
        if match:
            snippet = match.group(1)
            try:
                return json.loads(snippet)
            except json.JSONDecodeError:
                pass

        brace = re.search(r"\{.*\}", raw, re.S)
        if brace:
            try:
                return json.loads(brace.group(0))
            except json.JSONDecodeError:
                pass

        return None
    
    def _extract_json(self, text: str):
        JSON_FENCE = re.compile(r"```json\s*({.*?})\s*```", re.DOTALL)

        text = text.strip()

        match = JSON_FENCE.search(text)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        brace = text.find("{")
        if brace != -1:
            try:
                return json.loads(text[brace:])
            except json.JSONDecodeError:
                pass

        return None

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
                 
        
        prompt = f"""
        You are **Orchid**, an elite Next.js + TypeScript + Drizzle-ORM engineer.  
        Your job is to transform the user's request into a precise, AUTOMATED **build plan** for our CLI agent.

        ────────────────────────────────────────────────────────
        ## 1   Input Context (what you know)

        **User Request (verbatim):**  
        \"{task}\"

        **User-Provided File Context (High Priority):**  
        {user_file_context or "None"}

        **Project Context (Medium Priority):**  
        • Database Type 👉 {db_type}  
        • Relevant existing code snippets (searched automatically):  
        {context}

        _Assume everything not shown to you already exists and compiles._

        ────────────────────────────────────────────────────────
        ## 2   Your Mission

        1. **Analyse** the request:  
        • Does it call for *one* table, multiple tables, or new columns in an existing one?  
        • Does the user need seed/fixture data?  
        • Do we need an **API route** (RESTful or Next.js Route Handler) to fetch/update data?  
        • BONUS (if the request hints at it): Wire the new API into existing React / client code so the UI really works.

        2. **Generate a build plan** consisting of a list of *atomic* actions:  
        - **CREATE_FILE** - for brand-new files (schema, route, seed, utils, etc.)  
        - **UPDATE_FILE** - always include the **full, updated file** (not a diff) when editing.

        3. **Cover edge cases & completeness**  
        - Migrations: include `drizzle.config.ts` or migration files if not present.  
        - Environment variables: if a new `DATABASE_URL`, `SUPABASE_URL`, etc. is needed, create or update `.env.example`.  
        - Type-safety: export proper types (`typeof myTable.$inferSelect`).  
        - Error handling: return 500 JSON on DB failure.  
        - API route headers: set `dynamic = "force-dynamic"` for fresh data if needed.  
        - Pagination / ordering if lists could grow large.  
        - Empty state in the React component (`"No data yet"`).  
        - **NEVER** leave TODOs—produce compile-ready code.

        4. **Dependencies**  
        - List every npm package not already standard in Drizzle/Next.js (e.g. `@planetscale/database`).  
        - Omit duplicates.

        ────────────────────────────────────────────────────────
        ## 3   Common Request Patterns & How to Handle

        | Pattern (examples) | What You Should Produce |
        |--------------------|-------------------------|
        | “Store *X* in a table” | • New `X` table in `schema.ts`<br>• Seed file inserting sample rows (optional but nice)<br>• `src/app/api/x/route.ts` with GET/POST handlers<br>• Update frontend component to fetch from `/api/x` |
        | “Create tables for A and B” | Same as above **for each** table, or a single table with enum `category` if truly appropriate (explain choice in `thought`) |
        | “BONUS: integrate route into existing code” | Modify the specified React/TSX file(s) to call `fetch('/api/...')`, handle loading, and render data. Remove hard‑coded arrays. |
        | “Refactor existing table to add column Y” | Drizzle `ALTER TABLE` migration file + updated `schema.ts` + any necessary UI/api changes. |
        | Database unspecified | Respect **{db_type}**. If `Unknown`, default to Postgres‑style (Supabase) unless the codebase clearly shows SQLite or Mongo pattern. |

        ────────────────────────────────────────────────────────
        ## 4   Output Format (STRICT)

        Return **ONLY** a valid JSON object **exactly** like:  

        ```json
        {{
        "dependencies": ["package-1", "package-2"],
        "plan": [
            {{
            "action": "CREATE_FILE",
            "path": "path/to/new/file.ts",
            "thought": "One-sentence rationale.",
            "code": "FULL COMPILE-READY FILE CONTENT HERE"
            }},
            {{
            "action": "UPDATE_FILE",
            "path": "path/to/existing/file.tsx",
            "thought": "Why we must update it.",
            "code": "ENTIRE UPDATED SOURCE FILE CONTENT"
            }}
        ]
        }}
        """
        headers = {"Content-Type": "application/json"}
        data = {"contents": [{"parts": [{"text": prompt}]}]}
        
        max_retries = 5
        base_wait_time = 2
        
        for i in range(max_retries):
            try:
                with self.console.status("[bold green] 🌸 OrchidAI is thinking...[/bold green]"):
                    response = requests.post(config.GEMINI_API_URL, headers=headers, json=data, timeout=180)
                    response.raise_for_status()
                
                gemini_text = (
                    response.json()["candidates"][0]["content"]["parts"][0]["text"]
                )

                plan = self._extract_json(gemini_text)
                if plan is None:
                    self.console.print(
                        "[red]Response did not contain valid JSON; retrying…[/red]"
                    )
                    continue   

                return plan   

            except (requests.RequestException, KeyError) as err:
                self.console.print(f"[red]HTTP or parsing error: {err} – retrying…[/red]")

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

    def _execute_answer_task(self, query: str, user_files: List[str]):
        """Handles the workflow for answering a question. (wrapper)"""
        self._generate_answer_with_gemini(query, user_files)

    def _generate_answer_with_gemini(self, query, user_files: List[str] = None):
        
        with self.console.status("[bold green]🌸 Searching for relevant code… \n", spinner="dots"):
            relevant_chunks = self.vector_store.search(query)
        context = "\n".join(
            f"--- START OF {c['path']} ---\n{c['code']}\n--- END OF {c['path']} ---"
            for c in relevant_chunks
        )

        user_file_context = ""
        self.think("Loading content from user-specified files...")
        if user_files:
            with self.console.status("[bold green]📂 Loading user files…", spinner="dots"):
                for file_path in user_files:
                    try:
                        full_path = os.path.join(config.PROJECT_ROOT, file_path)
                        with open(full_path, "r", encoding="utf-8") as f:
                            content = f.read()
                        user_file_context += (
                            f"--- START OF {file_path} ---\n{content}\n--- END OF {file_path} ---\n\n"
                        )
                    except FileNotFoundError:
                        self.console.print(
                            f"[yellow]Warning: File not found: {file_path}[/yellow]"
                        )
                    except Exception as e:
                        self.console.print(
                            f"[red]Error reading file {file_path}: {e}[/red]"
                        )
        prompt = f"""
        You are **Orchid**, an expert Next.js / Drizzle-ORM developer and database specialist. 
        ────────────────────────────────────────────────────────
        ## 1   Determine the user's INTENT

        - **Implementation request** the user clearly asks to create, modify, delete, refactor, or set up code or database functionality, or wants step-by-step build instructions.<br>
        *Key verbs / phrases:* add, build, implement, generate, integrate, migrate, refactor, “how do I …”, “set up …”, “please create …”.

        - **Information request** the user only wants an explanation, summary, clarification, comparison, list, or advice, **without** asking for new code or database changes.<br>
        *Key verbs / phrases:* what, why, explain, describe, summarize, list, compare, “do I need to …”, “should I …”.

        **Edge-case rules**

        1. Mixed intent → treat as *implementation* (action overrides inquiry).  
        2. Advice questions (“Should I delete X?”) → *information*.  
        3. Hypothetical “How would I integrate Y?” → *implementation*.  
        4. Brief / ambiguous queries default to *information*.  
        5. Gratitude / small-talk → polite short reply (*information*).  
        6. When unsure, favour *information*.

        ────────────────────────────────────────────────────────
        ## 2   Respond according to INTENT

        ### A) Implementation request  
        *Return **only** the JSON plan* described in **Output Format for Implementation** below.

        ### B) Information request  
        1. Give a clear, technically-accurate Markdown answer using any **User-Provided File Context** and **Relevant Code Snippets**.  
        2. **DO NOT** output a JSON plan.  
        3. End with exactly this line (verbatim, one sentence, italics):  

        > *Because I'm a database agent I focus on implementing data features—if you'd like me to turn this explanation into working code, just ask!*

        ────────────────────────────────────────────────────────
        ## 3- Context Available to You
        **User-Request:** \"{query}\"

        **User-Provided-File-Context (High Priority):**
        {user_file_context or "None"}

        **Relevant-Code-Snippets (from automatic search):**
        {context}

        ────────────────────────────────────────────────────────
        ## Output Format for Implementation
        Respond with **ONLY** a valid JSON object:

        ```json
        {{
        "dependencies": ["package-name-if-needed"],
        "plan": [
            {{
            "action": "CREATE_FILE",
            "path": "path/to/new/file.ts",
            "thought": "Short explanation of why this file is needed.",
            "code": "FULL_CODE_FOR_THE_FILE"
            }},
            {{
            "action": "UPDATE_FILE",
            "path": "path/to/existing/file.tsx",
            "thought": "Short explanation of the update.",
            "code": "ENTIRE_UPDATED_FILE_CONTENT"
            }}
        ]
        }}
        ```
        """

        headers = {"Content-Type": "application/json"}
        data = {"contents": [{"parts": [{"text": prompt}]}]}

        try:
            with self.console.status(
                "[bold green] OrchidAI is thinking and generating answer…", spinner="dots", spinner_style="green"
            ):
                response = requests.post(
                    config.GEMINI_API_URL, headers=headers, json=data, timeout=180
                )
                response.raise_for_status()

            answer = response.json()["candidates"][0]["content"]["parts"][0]["text"].strip()

            md_renderable = Markdown(answer, justify="left", code_theme="monokai")
            panel = Panel(
                Align.left(md_renderable),
                title="[bold cyan]🌸 Orchid's Answer[/bold cyan]",
                border_style="cyan",
                padding=(1, 2),
                expand=True,
            )
            self.console.print(panel)

        except requests.exceptions.RequestException as e:
            self.console.print(f"[bold red]Error during API request: {e}[/bold red]")
        except (KeyError, IndexError, ValueError):
            self.console.print(
                "[bold red]Unexpected response format from Gemini API.[/bold red]"
            )
    
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
                        self.console.print("[green](✓) Dependencies installed.[/green]")
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
                    self.console.print(f"[green](✓) Wrote changes to {path}[/green]")
                except IOError as e:
                    self.console.print(f"[bold red]Error writing file {path}: {e}[/bold red]")
    
    def start(self, query: str, user_files: List[str] = None):
        """Main entry point that classifies intent and routes to the correct workflow."""
        intent = self._classify_intent(query)
        if intent == "question":
            self._execute_answer_task(query, user_files)
        else:
            self._execute_build_task(query, user_files)