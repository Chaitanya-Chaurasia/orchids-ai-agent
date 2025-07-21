# OrchidAI – Developer‑First Coding Assistant

OrchidAI indexes your entire codebase in a local vector store so you can ask natural‑language questions and get context‑aware answers in seconds. Think **`git grep` plus Stack Overflow plus ChatGPT—tuned for _your_ repository**.

---

## Table of Contents

1. [Why OrchidAI?](#why-orchidai)
2. [Prerequisites](#prerequisites)
3. [Installation](#installation)
4. [Getting Started](#getting-started)
   - [Initialize the Vector Store](#1-initialize-the-vector-store)
   - [Run the AI Agent](#2-run-the-ai-agent)
5. [How It Works](#how-it-works)
6. [Configuration](#configuration)
7. [Troubleshooting](#troubleshooting)
8. [License](#license)

---

## Why OrchidAI?

- **Semantic search, not string search** Find concepts even when filenames or function names don't match.
- **Language‑agnostic** Works with any text‑based source—TypeScript, Python, Go, Rust, or plain Markdown.
- **Local‑first** Your code never leaves your machine. OrchidAI runs entirely on your workstation.
- **Fast re‑indexing** Incremental updates keep the vector store in sync without rebuilding from scratch.
- **Extensible by design** The core is a small Python script—swap in another LLM or vector database if you prefer.

---

## Prerequisites

| Tool   | Version       | Notes                  |
| :----- | :------------ | :--------------------- |
| Python | 3.8 or higher | Tested on 3.8–3.12    |
| Node   | 16 or higher  | Required for CLI tooling |
| npm    | bundled with Node | `yarn` works as well |

---

## Installation

1. **Install JavaScript dependencies**
   ```bash
   npm install --legacy-peer-deps
   ```

2. **Create and activate a Python virtual environment**
   ```bash
   # Windows PowerShell
   python -m venv orchid_venv
   .\orchid_venv\Scripts\activate

   # macOS/Linux/Git Bash
   python3 -m venv orchid_venv
   source orchid_venv/bin/activate
   ```

3. **Install Python requirements**
   ```bash
   pip install -r requirements.txt
   ```
4. Make your .env file in the agent folder, and paste your GEMINI KEY (you will need to get your own).
---

## Getting Started

OrchidAI is driven by a small command‑line tool defined in `orchid.py`.
All commands are run from the `agent/` folder unless noted otherwise.

### 1. Initialize the Vector Store

The first time you run OrchidAI—or any time your codebase changes significantly—index it:

```bash
python orchid.py init
```

This command:
- Scans your repository for source files
- Generates vector embeddings for each code chunk
- Stores the embeddings in a local Qdrant database
- You only need to re‑run init when you want a fresh index (e.g., after a large refactor)

### 2. Run the AI Agent

Start an interactive session:

```bash
python orchid.py run
```

Ask questions such as:

> How is authentication wired up?

> Where do we create Stripe customers?

> Show me tests related to the cache layer.

OrchidAI finds the most relevant snippets and explains how they fit together.

---

## How It Works

- **Vector Database** → Qdrant stores all embeddings for blazingly fast nearest‑neighbor search
- **LLM‑Backed Reasoning** → A large language model takes the retrieved snippets and crafts a focused answer
- **Incremental Indexing** → A file‑hash cache means only changed files are re‑embedded on subsequent init runs

---

## Configuration

Key settings live in `config.py`:

| Setting | Description |
| :------ | :---------- |
| `QDRANT_PATH` | Where the local database files are stored |
| `EMBED_MODEL_NAME` | Hugging Face or OpenAI embedding model |
| `MAX_CHUNK_TOKENS` | Chunk size for splitting large files |
| `GEMINI_API_URL` | Endpoint for LLM completions |

---

## Troubleshooting

| Symptom | Possible Cause / Fix |
| :------ | :------------------- |
| `ModuleNotFoundError: qdrant-client` | `pip install -r requirements.txt` wasn't run |
| CLI hangs on first query | Large repo + cold LLM start; give it a minute |
| Queries return irrelevant snippets | Re‑index: `python orchid.py init` |
| "Vector dimensions mismatch" errors | Switched embedding model without re‑indexing |

---

## License

[Add your license information here]
