"""Document parsing and parent-child chunking."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

from src.config import Settings, get_settings
from src.exceptions import ParsingError

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md"}


@dataclass(frozen=True)
class ParsedDocument:
    document_id: str
    parent_documents: list[Document]
    child_documents: list[Document]
    full_text: str = ""


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _load_pdf(path: Path) -> list[Document]:
    try:
        reader = PdfReader(str(path))
    except Exception as exc:  # pragma: no cover - provider/library specific
        raise ParsingError(f"Unable to read PDF file: {path}") from exc

    documents: list[Document] = []
    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            documents.append(
                Document(
                    page_content=text,
                    metadata={"source": str(path), "file_name": path.name, "page": index},
                )
            )
    return documents


def _load_text(path: Path) -> list[Document]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError as exc:
        raise ParsingError(f"Unable to read text file: {path}") from exc

    if not text.strip():
        return []
    return [
        Document(
            page_content=text, metadata={"source": str(path), "file_name": path.name, "page": None}
        )
    ]


def load_documents(path: str | Path) -> tuple[str, list[Document]]:
    file_path = Path(path).expanduser().resolve()
    if not file_path.exists() or not file_path.is_file():
        raise ParsingError(f"Document path does not exist or is not a file: {file_path}")
    if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ParsingError(f"Unsupported file extension: {file_path.suffix}")

    try:
        document_id = _sha256_bytes(file_path.read_bytes())
    except OSError as exc:
        raise ParsingError(f"Unable to hash document: {file_path}") from exc

    documents = (
        _load_pdf(file_path) if file_path.suffix.lower() == ".pdf" else _load_text(file_path)
    )
    if not documents:
        raise ParsingError(f"No readable text found in document: {file_path}")
    return document_id, documents


def parse_document(path: str | Path, settings: Settings | None = None) -> ParsedDocument:
    settings = settings or get_settings()
    document_id, raw_documents = load_documents(path)

    parent_splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.parent_chunk_size,
        chunk_overlap=settings.parent_chunk_overlap,
    )
    child_splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.child_chunk_size,
        chunk_overlap=settings.child_chunk_overlap,
    )

    parent_documents: list[Document] = []
    child_documents: list[Document] = []
    parent_index = 0
    child_index = 0

    for raw_doc in raw_documents:
        parents = parent_splitter.split_documents([raw_doc])
        for parent in parents:
            parent_id = _sha256_text(f"{document_id}:parent:{parent_index}:{parent.page_content}")
            parent.metadata.update(
                {
                    "document_id": document_id,
                    "parent_id": parent_id,
                    "parent_chunk_index": parent_index,
                    "content_hash": _sha256_text(parent.page_content),
                    "source_type": "document",
                }
            )
            parent_documents.append(parent)

            children = child_splitter.split_documents([parent])
            for child in children:
                child_id = _sha256_text(f"{document_id}:child:{child_index}:{child.page_content}")
                child.metadata.update(
                    {
                        "document_id": document_id,
                        "parent_id": parent_id,
                        "child_id": child_id,
                        "chunk_index": child_index,
                        "parent_chunk_index": parent_index,
                        "content_hash": _sha256_text(child.page_content),
                        "source_type": "document",
                    }
                )
                child_documents.append(child)
                child_index += 1
            parent_index += 1

    return ParsedDocument(
        document_id=document_id,
        parent_documents=parent_documents,
        child_documents=child_documents,
        full_text="\n\n".join(raw.page_content for raw in raw_documents),
    )
