"""Offline tests for document parsing (text, PDF, and Word DOCX)."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.exceptions import ParsingError
from src.ingestion.parser import (
    SUPPORTED_EXTENSIONS,
    load_documents,
    parse_document,
)


def test_supported_extensions_include_word_documents() -> None:
    assert ".docx" in SUPPORTED_EXTENSIONS
    assert ".doc" in SUPPORTED_EXTENSIONS
    assert ".pdf" in SUPPORTED_EXTENSIONS


def test_parse_docx_extracts_paragraphs() -> None:
    from docx import Document as WordDocument

    path = Path("tmp_test_parser.docx")
    document = WordDocument()
    document.add_paragraph("Zorbak is a fictional port city on the west coast of Kelmar.")
    document.add_paragraph("Zorbak was founded in the year 1420 by Captain Rosa Venn.")
    document.save(str(path))
    try:
        document_id, documents = load_documents(path)
        assert document_id
        assert len(documents) == 1
        assert "Zorbak was founded" in documents[0].page_content
        assert documents[0].metadata["file_name"] == path.name
    finally:
        Path(path).unlink(missing_ok=True)


def test_parse_docx_extracts_tables() -> None:
    from docx import Document as WordDocument

    path = Path("tmp_test_parser_table.docx")
    document = WordDocument()
    table = document.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "City"
    table.cell(0, 1).text = "River"
    table.cell(1, 0).text = "Zorbak"
    table.cell(1, 1).text = "Lys"
    document.save(str(path))
    try:
        _, documents = load_documents(path)
        content = documents[0].page_content
        assert "Zorbak" in content
        assert "Lys" in content
    finally:
        Path(path).unlink(missing_ok=True)


def test_parse_document_chunks_docx(tmp_path: Path) -> None:
    from docx import Document as WordDocument

    path = tmp_path / "notes.docx"
    document = WordDocument()
    for _ in range(30):
        document.add_paragraph(
            "The guild leaders of Nyra meet in the Salt Tower every month to review harbor taxes."
        )
    document.save(str(path))
    parsed = parse_document(path)
    assert parsed.child_documents
    assert all(doc.metadata.get("document_id") for doc in parsed.child_documents)
    assert "Nyra" in parsed.full_text


def test_unsupported_extension_rejected(tmp_path: Path) -> None:
    path = tmp_path / "data.exe"
    path.write_bytes(b"not a real document")
    with pytest.raises(ParsingError):
        load_documents(path)


def test_legacy_doc_text_extraction() -> None:
    from src.ingestion.parser import _extract_legacy_doc_text

    prose = "Alder was founded in 1150. The river Bramble runs through the town."
    payload = b"\x00" * 64 + prose.encode("utf-16-le") + b"\xff" * 64
    text = _extract_legacy_doc_text(payload)
    assert "Alder was founded" in text
    assert "Bramble" in text


def test_legacy_doc_rejects_binary_garbage(tmp_path: Path) -> None:
    path = tmp_path / "notes.doc"
    path.write_bytes(b"\x00\x01\x02\x03" * 100)
    with pytest.raises(ParsingError):
        load_documents(path)
