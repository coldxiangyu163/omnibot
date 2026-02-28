"""Simple RAG pipeline — registered as a built-in tool in the agent."""
import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.config import settings


class RAGPipeline:
    """Chunk docs → ChromaDB → retrieve on query. Used as a built-in agent tool."""

    COLLECTION = "knowledge"

    def __init__(self, persist_dir: str | None = None):
        path = persist_dir or settings.chroma_persist_dir
        self.client = chromadb.PersistentClient(path=path)
        self.collection = self.client.get_or_create_collection(self.COLLECTION)
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=800, chunk_overlap=100
        )

    async def ingest(self, text: str, source: str = "upload") -> int:
        """Chunk and store a document. Returns number of chunks."""
        chunks = self.splitter.split_text(text)
        if not chunks:
            return 0
        ids = [f"{source}_{i}" for i in range(len(chunks))]
        self.collection.upsert(
            ids=ids,
            documents=chunks,
            metadatas=[{"source": source}] * len(chunks),
        )
        return len(chunks)

    async def retrieve(self, query: str, top_k: int = 3) -> tuple[str, list[str]]:
        """Retrieve relevant chunks for a query."""
        if self.collection.count() == 0:
            return "", []
        results = self.collection.query(query_texts=[query], n_results=top_k)
        docs = results["documents"][0] if results["documents"] else []
        sources = list({m["source"] for m in results["metadatas"][0]}) if results["metadatas"] else []
        context = "\n\n---\n\n".join(docs)
        return context, sources
