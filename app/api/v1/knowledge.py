"""Knowledge base API — upload and query documents."""
from fastapi import APIRouter, UploadFile, File
from pypdf import PdfReader
import io
from app.core.engine import engine

router = APIRouter(tags=["knowledge"])


@router.post("/knowledge")
async def upload_knowledge(file: UploadFile = File(...)):
    """Upload a document (PDF/TXT/MD) to the knowledge base."""
    content = await file.read()
    filename = file.filename or "unknown"
    if filename.endswith(".pdf"):
        reader = PdfReader(io.BytesIO(content))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    else:
        text = content.decode("utf-8", errors="ignore")
    chunks = await engine.rag.ingest(text, source=filename)
    return {"filename": filename, "chunks": chunks, "status": "indexed"}


@router.get("/knowledge/stats")
async def knowledge_stats():
    count = engine.rag.collection.count()
    return {"total_chunks": count}
