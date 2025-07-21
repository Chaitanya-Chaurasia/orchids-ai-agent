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
        self.console.print("[bold blue]I will create a light-weight vector store for your codebase. (using Qdrant)")
        with self.console.status(
            f"[bold cyan]Connecting to vector database (for gathering context on codebase) ({config.QDRANT_PATH})…[/bold cyan]",
            spinner="dots",
        ):
            self.client = QdrantClient(path=config.QDRANT_PATH)
        
        self.console.print(f"[dim]Your vector store & indices are ready to view at {config.QDRANT_PATH}[/dim]\n")

    def collection_exists(self) -> bool:
        try:
            self.client.get_collection(self.collection_name)
            return True
        except Exception:  
            return False

    def build_collection(self, chunks: List[Dict]) -> None: 

        if self.collection_exists():
            self.console.print("\n[bold yellow]I already have latest knowledge of your codebase; you can use the 'run' command.[/bold yellow]")
            return
        if not chunks:
            self.console.print("\n[bold yellow]No chunks provided; skipping indexing.[/bold yellow]")
            return

        self.console.print("\n[bold blue]Codebase indexing in progress[/bold blue]\n")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=20),
            TimeElapsedColumn(),
            console=self.console,
        ) as progress:
            t_embed = progress.add_task("Embedding snippets", total=len(chunks))
            # task_type set to RETRIEVAL but modify it
            embeddings = genai.embed_content(
                model=config.EMBEDDING_MODEL,
                content=[c["code"] for c in chunks],
                task_type="RETRIEVAL_DOCUMENT",
            )["embedding"]

            progress.update(t_embed, completed=len(chunks))

        dim = len(embeddings[0])
        self.console.print(
            f"\n[dim cyan]Created collection [id: {self.collection_name}] [dim cyan]({dim}-dimensional vectors)[/dim cyan]\n"
        )
        self.client.recreate_collection(
            collection_name=self.collection_name,
            vectors_config=models.VectorParams(size=dim, distance=models.Distance.COSINE),
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=20),
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
            f"\n[dim cyan]Indexed {len(chunks)} snippets into [id: {self.collection_name}].[/dim cyan]\n"
        )

    def search(self, query: str, k: int = 15) -> List[Dict]:
        try:
            query_vec = genai.embed_content(
                model=config.EMBEDDING_MODEL,
                content=query,
                task_type="RETRIEVAL_QUERY",
            )["embedding"]

            res = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vec,
                limit=k,
            )
            return [hit.payload for hit in res]
        except Exception as exc: 
            self.console.print(f"[red]Search error: {exc}[/red]")
            return []
