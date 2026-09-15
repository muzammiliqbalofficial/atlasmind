"""
AtlasMind - Document Processor & Section-Aware Chunker
Parses corporate policy documents (.md, .txt, .pdf), extracts rich metadata,
and segments content into semantic sections while strictly preserving table
structures and policy bullet points.
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from src.config import DOCS_DIR, ALLOWED_EXTENSIONS


def sanitize_filename(filename: str) -> str:
    """
    Sanitize an uploaded file name to prevent directory traversal and path injection.
    Strips path components, replaces unsafe characters with underscores, and prevents hidden files.
    """
    # Strip any leading directories
    clean = os.path.basename(filename.strip().replace("\\", "/"))
    # Remove leading dots to prevent hidden files
    clean = clean.lstrip(".")
    # Replace any character other than alphanumerics, dash, underscore, dot
    clean = re.sub(r"[^a-zA-Z0-9_\.\-]", "_", clean)
    # Collapse consecutive underscores
    clean = re.sub(r"_{2,}", "_", clean)
    return clean or "uploaded_document.txt"


def is_allowed_file(filename: str) -> bool:
    """Verify if the uploaded file has a permissible extension (.md, .txt, .pdf)."""
    suffix = Path(filename).suffix.lower()
    return suffix in ALLOWED_EXTENSIONS


class DocumentChunk:
    """
    Represents an indexed semantic chunk of a policy document.
    Stores rich metadata including chunk_id, document_id, doc_name, category, and content.
    """
    def __init__(
        self,
        chunk_id: str,
        document_id: str,
        doc_name: str,
        category: str,
        content: str,
        section_title: str = "",
        section_number: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.chunk_id = chunk_id
        self.document_id = document_id
        self.doc_id = document_id           # Alias for backwards compatibility
        self.doc_name = doc_name
        self.doc_title = doc_name           # Alias for backwards compatibility
        self.category = category
        self.classification = category     # Alias for backwards compatibility
        self.section_title = section_title
        self.section_number = section_number
        self.content = content.strip()
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert chunk into a dictionary representation."""
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "doc_id": self.doc_id,
            "doc_name": self.doc_name,
            "doc_title": self.doc_title,
            "category": self.category,
            "classification": self.classification,
            "section_title": self.section_title,
            "section_number": self.section_number,
            "content": self.content,
            "metadata": self.metadata
        }

    def __repr__(self) -> str:
        return f"<DocumentChunk id={self.chunk_id} doc={self.document_id} sec='{self.section_title}'>"


class DocumentProcessor:
    """
    Document parser supporting Markdown, Plaintext, and PDF files.
    Features section-aware splitting that preserves Markdown tables and list items.
    """
    def __init__(self, docs_dir: Path = DOCS_DIR):
        self.docs_dir = docs_dir

    def extract_text_from_file(self, file_path: Path) -> str:
        """Extract text from .md, .txt, or .pdf files."""
        ext = file_path.suffix.lower()
        if ext in [".md", ".txt"]:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        elif ext == ".pdf":
            # Attempt PyMuPDF (fitz)
            try:
                import fitz
                doc = fitz.open(str(file_path))
                pages = []
                for page in doc:
                    pages.append(page.get_text("text"))
                return "\n\n".join(pages)
            except Exception as e:
                # Fallback to pdfminer if present
                try:
                    from pdfminer.high_level import extract_text
                    return extract_text(str(file_path))
                except Exception as inner:
                    raise RuntimeError(f"Could not extract text from PDF ({file_path.name}): {e}; fallback: {inner}")
        else:
            raise ValueError(f"Unsupported file type: {ext}")

    def extract_metadata(self, text: str, fallback_filename: str = "") -> Dict[str, str]:
        """Extract metadata header block from markdown or policy document."""
        # Derive fallback ID from filename if possible (e.g., POL-01)
        fallback_id = "DOC-GEN"
        if fallback_filename:
            id_match = re.match(r"^([A-Z]{3,4}-\d{2,3})", fallback_filename)
            if id_match:
                fallback_id = id_match.group(1)

        meta = {
            "doc_id": fallback_id,
            "title": Path(fallback_filename).stem.replace("_", " ") if fallback_filename else "Atlas Honda Policy",
            "classification": "General Employee Access",
            "version": "1.0 - Sample",
            "approved_by": "Atlas Honda Management",
            "applicability": "Company-wide"
        }
        
        # Match H1 title
        title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        if title_match:
            raw_title = title_match.group(1).strip()
            # If title starts with POL-XX, extract doc_id and clean title
            id_prefix = re.match(r"^([A-Z]{3,4}-\d{2,3})\s*[:\-\s]?\s*(.+)$", raw_title)
            if id_prefix:
                meta["doc_id"] = id_prefix.group(1).strip()
                meta["title"] = id_prefix.group(2).strip()
            else:
                meta["title"] = raw_title
            
        # Match Key-Value pairs in header preamble
        for line in text.split("\n")[:35]:
            line_str = line.strip()
            if "**Document ID:**" in line_str:
                meta["doc_id"] = line_str.split("**Document ID:**")[-1].strip().strip("`*")
            elif "**Classification:**" in line_str:
                meta["classification"] = line_str.split("**Classification:**")[-1].strip().strip("`*")
            elif "**Version:**" in line_str:
                meta["version"] = line_str.split("**Version:**")[-1].strip().strip("`*")
            elif "**Approved by:**" in line_str:
                meta["approved_by"] = line_str.split("**Approved by:**")[-1].strip().strip("`*")
            elif "**Applicability:**" in line_str or "**Scope:**" in line_str:
                val = line_str.split(":**")[-1].strip().strip("`*") if ":**" in line_str else ""
                if val:
                    meta["applicability"] = val

        return meta

    def _split_into_atomic_blocks(self, text: str) -> List[str]:
        """
        Segment section text into atomic semantic blocks.
        Guarantees that Markdown tables and continuous list items are NOT severed midway.
        """
        lines = text.split("\n")
        blocks = []
        current_block = []
        in_table = False
        in_list = False

        for line in lines:
            trimmed = line.strip()
            is_table_line = trimmed.startswith("|") and trimmed.endswith("|")
            is_list_line = bool(re.match(r"^(\*|-|\d+\.)\s+", trimmed))
            is_blank = not trimmed

            if is_table_line:
                # Start or continue table block
                in_table = True
                current_block.append(line)
                continue
            elif in_table:
                # Table ended
                in_table = False
                if current_block:
                    blocks.append("\n".join(current_block))
                    current_block = []

            if is_list_line:
                in_list = True
                current_block.append(line)
                continue
            elif in_list and (line.startswith("   ") or line.startswith("\t")):
                # Sub-bullet continuation
                current_block.append(line)
                continue
            elif in_list and is_blank:
                # Blank line inside or after list
                current_block.append(line)
                continue
            elif in_list:
                in_list = False

            if is_blank:
                if current_block:
                    blocks.append("\n".join(current_block))
                    current_block = []
            else:
                current_block.append(line)

        if current_block:
            blocks.append("\n".join(current_block))

        return [b.strip() for b in blocks if b.strip()]

    def chunk_text(
        self,
        text: str,
        doc_id: Optional[str] = None,
        doc_name: Optional[str] = None,
        classification: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[DocumentChunk]:
        """
        Split text into structured DocumentChunk objects.
        Preserves Markdown tables, bullet points, and section hierarchies.
        """
        meta = self.extract_metadata(text)
        final_doc_id = doc_id or meta.get("doc_id", "DOC-01")
        final_doc_name = doc_name or meta.get("title", "Atlas Honda Policy")
        final_classification = classification or meta.get("classification", "General Employee Access")
        combined_meta = {**meta, **(metadata or {})}

        # Split primary sections by Markdown ## Header
        raw_sections = re.split(r"(?=\n##\s+)", text)
        chunks: List[DocumentChunk] = []
        chunk_idx = 0

        for sec in raw_sections:
            sec = sec.strip()
            if not sec:
                continue

            # Identify H2 Header
            h2_match = re.match(r"^##\s+([0-9\.]*\s*)?(.+)$", sec, re.MULTILINE)
            if h2_match:
                sec_num = (h2_match.group(1) or "").strip()
                sec_title = h2_match.group(2).strip()

                # If section has H3 subheadings and is large (> 900 chars), split by H3
                subsections = re.split(r"(?=\n###\s+)", sec)
                if len(subsections) > 1 and len(sec) > 900:
                    for sub in subsections:
                        sub = sub.strip()
                        if not sub:
                            continue
                        sub_match = re.match(r"^###\s+([0-9\.]*\s*)?(.+)$", sub, re.MULTILINE)
                        if sub_match:
                            sub_num = (sub_match.group(1) or "").strip()
                            sub_title = sub_match.group(2).strip()
                            full_sub_title = f"{sec_title} - {sub_title}"
                            
                            # If sub-section is huge (> 1500 chars), group atomic blocks with overlap
                            if len(sub) > 1500:
                                blocks = self._split_into_atomic_blocks(sub)
                                acc_text = []
                                acc_len = 0
                                for blk in blocks:
                                    acc_text.append(blk)
                                    acc_len += len(blk)
                                    if acc_len >= 1000:
                                        chunk_id = f"{final_doc_id}_chunk_{chunk_idx:02d}"
                                        chunks.append(DocumentChunk(
                                            chunk_id=chunk_id,
                                            document_id=final_doc_id,
                                            doc_name=final_doc_name,
                                            category=final_classification,
                                            content="\n\n".join(acc_text),
                                            section_title=full_sub_title,
                                            section_number=sub_num or sec_num,
                                            metadata=combined_meta
                                        ))
                                        chunk_idx += 1
                                        # Overlap: keep last block if reasonable
                                        acc_text = acc_text[-1:] if len(acc_text[-1]) < 300 else []
                                        acc_len = sum(len(b) for b in acc_text)
                                if acc_text and len("\n\n".join(acc_text).strip(" -\n\r\t*#")) > 20:
                                    chunk_id = f"{final_doc_id}_chunk_{chunk_idx:02d}"
                                    chunks.append(DocumentChunk(
                                        chunk_id=chunk_id,
                                        document_id=final_doc_id,
                                        doc_name=final_doc_name,
                                        category=final_classification,
                                        content="\n\n".join(acc_text),
                                        section_title=full_sub_title,
                                        section_number=sub_num or sec_num,
                                        metadata=combined_meta
                                    ))
                                    chunk_idx += 1
                            else:
                                chunk_id = f"{final_doc_id}_chunk_{chunk_idx:02d}"
                                chunks.append(DocumentChunk(
                                    chunk_id=chunk_id,
                                    document_id=final_doc_id,
                                    doc_name=final_doc_name,
                                    category=final_classification,
                                    content=sub,
                                    section_title=full_sub_title,
                                    section_number=sub_num or sec_num,
                                    metadata=combined_meta
                                ))
                                chunk_idx += 1
                    continue
            else:
                sec_num = "Overview"
                sec_title = "Document Overview & Governance Header"

            # Check if section needs atomic block grouping
            if len(sec) > 1600:
                blocks = self._split_into_atomic_blocks(sec)
                acc_text = []
                acc_len = 0
                for blk in blocks:
                    acc_text.append(blk)
                    acc_len += len(blk)
                    if acc_len >= 1100:
                        chunk_id = f"{final_doc_id}_chunk_{chunk_idx:02d}"
                        chunks.append(DocumentChunk(
                            chunk_id=chunk_id,
                            document_id=final_doc_id,
                            doc_name=final_doc_name,
                            category=final_classification,
                            content="\n\n".join(acc_text),
                            section_title=sec_title,
                            section_number=sec_num,
                            metadata=combined_meta
                        ))
                        chunk_idx += 1
                        acc_text = acc_text[-1:] if len(acc_text[-1]) < 300 else []
                        acc_len = sum(len(b) for b in acc_text)
                if acc_text and len("\n\n".join(acc_text).strip(" -\n\r\t*#")) > 20:
                    chunk_id = f"{final_doc_id}_chunk_{chunk_idx:02d}"
                    chunks.append(DocumentChunk(
                        chunk_id=chunk_id,
                        document_id=final_doc_id,
                        doc_name=final_doc_name,
                        category=final_classification,
                        content="\n\n".join(acc_text),
                        section_title=sec_title,
                        section_number=sec_num,
                        metadata=combined_meta
                    ))
                    chunk_idx += 1
            else:
                chunk_id = f"{final_doc_id}_chunk_{chunk_idx:02d}"
                chunks.append(DocumentChunk(
                    chunk_id=chunk_id,
                    document_id=final_doc_id,
                    doc_name=final_doc_name,
                    category=final_classification,
                    content=sec,
                    section_title=sec_title,
                    section_number=sec_num,
                    metadata=combined_meta
                ))
                chunk_idx += 1

        return chunks

    def chunk_document(self, file_path: Path) -> List[DocumentChunk]:
        """Extract and chunk a single file from disk (.md, .txt, .pdf)."""
        full_text = self.extract_text_from_file(file_path)
        meta = self.extract_metadata(full_text, fallback_filename=file_path.name)
        return self.chunk_text(
            text=full_text,
            doc_id=meta["doc_id"],
            doc_name=meta["title"],
            classification=meta["classification"],
            metadata=meta
        )

    def process_all_documents(self) -> List[DocumentChunk]:
        """Process all valid policy documents in the documents directory."""
        all_chunks: List[DocumentChunk] = []
        files = []
        for ext in ALLOWED_EXTENSIONS:
            files.extend(self.docs_dir.glob(f"*{ext}"))
        files = sorted(list(set(files)), key=lambda p: p.name)

        for file_path in files:
            try:
                chunks = self.chunk_document(file_path)
                all_chunks.extend(chunks)
            except Exception as e:
                print(f"Error processing {file_path.name}: {e}")

        return all_chunks
