"""Tests for RAG pipeline."""
import pytest


class TestRAGPipeline:
    @pytest.fixture
    def rag(self, tmp_path):
        """Create a RAG pipeline with a temp ChromaDB directory."""
        from app.core.rag.pipeline import RAGPipeline
        return RAGPipeline(persist_dir=str(tmp_path / "chroma"))

    @pytest.mark.asyncio
    async def test_ingest_and_retrieve(self, rag):
        text = "OmniBot is an MCP-native AI agent framework. It supports tool calling and RAG."
        count = await rag.ingest(text, source="test.md")
        assert count >= 1

        context, sources = await rag.retrieve("What is OmniBot?")
        assert "OmniBot" in context
        assert "test.md" in sources

    @pytest.mark.asyncio
    async def test_retrieve_empty(self, rag):
        context, sources = await rag.retrieve("anything")
        assert context == ""
        assert sources == []

    @pytest.mark.asyncio
    async def test_ingest_empty_text(self, rag):
        count = await rag.ingest("", source="empty.md")
        assert count == 0

    @pytest.mark.asyncio
    async def test_ingest_multiple_sources(self, rag):
        await rag.ingest("Python is a programming language.", source="python.md")
        await rag.ingest("Rust is a systems language.", source="rust.md")

        context, sources = await rag.retrieve("programming language")
        assert context != ""
        assert len(sources) >= 1
