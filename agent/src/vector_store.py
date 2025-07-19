import uuid
import google.generativeai as genai
from rich.console import Console
from qdrant_client import QdrantClient, models
from rich.progress import track
from src import config

class VectorStore:
    """Manages code embeddings for semantic search using Qdrant."""

    def __init__(self, collection_name: str):
        self.console = Console()
        self.collection_name = collection_name
        self.client = QdrantClient(path=config.QDRANT_PATH)
        self.console.print(f"[green]✅ Qdrant client initialized. Storage path: {config.QDRANT_PATH}[/green]")

    def collection_exists(self) -> bool:
        """Checks if the collection for the current project state exists."""
        try:
            self.client.get_collection(collection_name=self.collection_name)
            return True
        except Exception:
            return False

    def build_collection(self, chunks: list[dict]):
        """Creates embeddings and builds a new Qdrant collection."""
        if not chunks:
            return
        self.console.print("[bold yellow]Creating code embeddings and building Qdrant collection...[/bold yellow]")
        try:
            code_list = [chunk['code'] for chunk in chunks]
            result = genai.embed_content(model=config.EMBEDDING_MODEL, content=code_list, task_type="RETRIEVAL_DOCUMENT")
            embeddings = result['embedding']
            
            self.client.recreate_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(size=len(embeddings[0]), distance=models.Distance.COSINE)
            )

            points = []
            for embedding, chunk in track(zip(embeddings, chunks), description="[green]Preparing points for database...[/green]", total=len(chunks)):
                points.append(
                    models.PointStruct(
                        id=str(uuid.uuid4()),
                        vector=embedding,
                        payload=chunk
                    )
                )

            self.client.upsert(
                collection_name=self.collection_name,
                points=points,
                wait=True
            )
            self.console.print(f"[green]✅ Qdrant collection '{self.collection_name}' built with {len(chunks)} points.[/green]")

        except Exception as e:
            self.console.print(f"[bold red]Error building Qdrant collection: {e}[/bold red]")
            self.console.print_exception()

    def search(self, query: str, k: int = 15) -> list[dict]:
        """Searches the Qdrant collection for the most relevant code chunks."""
        try:
            query_embedding = genai.embed_content(model=config.EMBEDDING_MODEL, content=query, task_type="RETRIEVAL_QUERY")['embedding']
            
            self.console.print("[bold yellow]Searching for relevant code chunks...[/bold yellow]")
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=k
            )
            return [hit.payload for hit in search_result]
        except Exception as e:
            self.console.print(f"[bold red]Error searching Qdrant collection: {e}[/bold red]")
            return []
