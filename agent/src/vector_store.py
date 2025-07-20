from __future__ import annotations

import uuid
from typing import List, Dict

import google.generativeai as genai
from qdrant_client import QdrantClient, models
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

from src import config


class VectorStore:
    def __init__(self, collection_name: str) -> None:
        self.console = Console()
        self.collection_name = collection_name
        with self.console.status(
            f"[bold cyan]Connecting to vector database (for gathering context on codebase) ({config.QDRANT_PATH})…[/bold cyan]",
            spinner="dots",
        ):
            self.client = QdrantClient(path=config.QDRANT_PATH)
        self.console.print(f"[green]Your vector store (Qdrant) & indices are ready to view at {config.QDRANT_PATH}[/green]")

    def collection_exists(self) -> bool:
        try:
            self.client.get_collection(self.collection_name)
            return True
        except Exception:  
            return False

    def build_collection(self, chunks: List[Dict]) -> None:
        if not chunks:
            self.console.print("[yellow]No chunks provided; skipping indexing.[/yellow]")
            return

        self.console.rule("[bold blue]Indexing codebase")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=None),
            TimeElapsedColumn(),
            console=self.console,
        ) as progress:
            t_embed = progress.add_task("Embedding snippets", total=len(chunks))
            embeddings = genai.embed_content(
                model=config.EMBEDDING_MODEL,
                content=[c["code"] for c in chunks],
                task_type="RETRIEVAL_DOCUMENT",
            )["embedding"]
            progress.update(t_embed, completed=len(chunks))

        dim = len(embeddings[0])
        self.console.print(
            f"[cyan]Creating collection “{self.collection_name}” "
            f"({dim}-dim vectors)[/cyan]"
        )
        self.client.recreate_collection(
            collection_name=self.collection_name,
            vectors_config=models.VectorParams(size=dim, distance=models.Distance.COSINE),
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=None),
            TimeElapsedColumn(),
            console=self.console,
        ) as progress:
            t_upsert = progress.add_task("Storing embeddings", total=len(chunks))
            points = [
                models.PointStruct(
                    id=str(uuid.uuid4()), vector=emb, payload=chunk
                )
                for emb, chunk in zip(embeddings, chunks, strict=True)
            ]
            self.client.upsert(
                collection_name=self.collection_name,
                points=points,
                wait=True,
            )
            progress.update(t_upsert, completed=len(chunks))

        self.console.print(
            f"[green]Indexed {len(chunks)} snippets "
            f"into “{self.collection_name}”.[/green]"
        )

    def search(self, query: str, k: int = 15) -> List[Dict]:
        try:
            query_vec = genai.embed_content(
                model=config.EMBEDDING_MODEL,
                content=query,
                task_type="RETRIEVAL_QUERY",
            )["embedding"]

            self.console.print(
                f"[bold blue]Searching “{self.collection_name}”…[/bold blue]"
            )
            res = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vec,
                limit=k,
            )
            return [hit.payload for hit in res]
        except Exception as exc: 
            self.console.print(f"[red]Search error: {exc}[/red]")
            return []
