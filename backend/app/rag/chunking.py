import re
from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    page_number: int
    position: int
    text: str


def normalize_text(text: str) -> str:
    text = text.replace("\x00", "").replace("\r\n", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_pages(pages: list[tuple[int, str]], size: int = 900, overlap: int = 140) -> list[TextChunk]:
    if size <= 0 or overlap < 0 or overlap >= size:
        raise ValueError("Chunk size must be positive and overlap smaller than size")
    chunks: list[TextChunk] = []
    for page_number, raw in pages:
        text = normalize_text(raw)
        start, position = 0, 0
        while start < len(text):
            end = min(start + size, len(text))
            if end < len(text):
                boundary = max(text.rfind(". ", start, end), text.rfind("\n", start, end))
                if boundary > start + size // 2:
                    end = boundary + 1
            passage = text[start:end].strip()
            if passage:
                chunks.append(TextChunk(page_number, position, passage))
                position += 1
            if end >= len(text):
                break
            start = max(start + 1, end - overlap)
    return chunks

