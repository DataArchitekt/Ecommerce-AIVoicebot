"""
Multimodal Video / Audio Loader
--------------------------------
- Source-agnostic (local audio/video file)
- Whisper transcription
- Chunking + embedding
- Indexed into vector DB for multimodal RAG
"""

import os
from typing import Optional

import whisper
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter

from backend.app.rag import get_vectorstore


# ─────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────

WHISPER_MODEL = "small"

TEXT_SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=100,
)


# ─────────────────────────────────────────────
# Core loader
# ─────────────────────────────────────────────

def load_video_to_vectorstore(
    media_path: str,
    product_id: Optional[str] = None,
    source: str = "video",
    video_id: Optional[str] = None,
):
    """
    Ingest audio/video into vector DB using Whisper.

    Args:
        media_path: path to local .wav / .mp3 / .mp4 file
        product_id: optional product reference
        source: 'youtube' | 'video' | 'audio'
        video_id: optional external video id
    """

    if not os.path.exists(media_path):
        raise FileNotFoundError(f"Media file not found: {media_path}")

    print(f"🎬 Loading media: {media_path}")

    # 1️⃣ Transcribe
    model = whisper.load_model(WHISPER_MODEL)
    result = model.transcribe(media_path)

    transcript_text = result.get("text", "").strip()
    if not transcript_text:
        raise ValueError("Empty transcript generated")

    print("📝 Transcription completed")

    # 2️⃣ Chunk
    chunks = TEXT_SPLITTER.split_text(transcript_text)
    print(f"✂️ Split into {len(chunks)} chunks")

    # 3️⃣ Build documents
    docs = []
    for chunk in chunks:
        docs.append(
            Document(
                page_content=chunk,
                metadata={
                    "type": "video_transcript",
                    "modality": "video",
                    "source": source,
                    "product_id": product_id,
                    "video_id": video_id,
                    "media_path": media_path,
                },
            )
        )

    # 4️⃣ Index
    vectorstore = get_vectorstore()
    vectorstore.add_documents(docs)

    print(f"✅ Indexed {len(docs)} video transcript chunks")


# ─────────────────────────────────────────────
# CLI usage
# ─────────────────────────────────────────────

if __name__ == "__main__":
    """
    Example usage:

    python backend/app/video_loader.py
    """

    load_video_to_vectorstore(
        media_path="backend/data/demo_video.wav",
        product_id="1",
        source="youtube",
        video_id="demo-video-001",
    )