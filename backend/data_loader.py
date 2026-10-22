import json
import re
from functools import lru_cache

from langchain_core.documents import Document

from backend.config import DATA_FILE


def _number(value) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return 0.0


def _clean(text) -> str:
    text = str(text or "").replace("~", " > ")
    return re.sub(r"\s+", " ", text).strip()


def to_item(record: dict) -> dict:
    """Turn an internal record into the small dict the API sends back."""
    cgst = record["cgst"]
    sgst = record["sgst"]
    igst = record["igst"]
    total = igst if igst else cgst + sgst
    return {
        "code": record["code"],
        "chapter": record["chapter"],
        "description": record["description"],
        "cgst": cgst,
        "sgst": sgst,
        "igst": igst,
        "total_gst": total,
        "condition": record.get("condition", ""),
    }


def new_response(status: str, query: str, message: str = "") -> dict:
    """Every search returns this same shape, so the frontend is simple."""
    return {
        "status": status,
        "query": query,
        "message": message,
        "result": None,
        "path": [],
        "confidence": "",
        "reason": "",
        "alternatives": [],
        "candidates": [],
    }


class HSNData:
    def __init__(self, raw_records: list):
        self.records = []      # every cleaned record, in file order
        self.by_code = {}      # "95" -> record, "9503" -> record, ...
        self.chapters = {}     # "95" -> "Toys, Games and Sports Requisites..."

        for raw in raw_records:
            code = str(raw.get("id", "")).strip()
            if not code:
                continue
            record = {
                "code": code,
                "chapter": code[:2],
                "description": _clean(raw.get("display")),
                "cgst": _number(raw.get("CGST")),
                "sgst": _number(raw.get("SGST")),
                "igst": _number(raw.get("IGST")),
                "condition": _clean(raw.get("Condition")),
            }
            self.records.append(record)
            self.by_code.setdefault(code, record)
            if len(code) == 2:
                self.chapters[code] = record["description"]

    def code_path(self, code: str) -> list:
        """Chapter > heading > subheading > code, as a list of dicts."""
        path = []
        for n in (2, 4, 6, 8):
            if len(code) >= n:
                parent = self.by_code.get(code[:n])
                if parent:
                    path.append({"code": parent["code"], "description": parent["description"]})
        return path

    def search_documents(self) -> list:
        """One searchable text per specific code (4 digits or more)."""
        docs = []
        for record in self.records:
            if len(record["code"]) < 4:
                continue  # skip chapter-level rows
            chapter_name = self.chapters.get(record["chapter"], "")
            text = f"HSN {record['code']}. Chapter {record['chapter']} {chapter_name}. {record['description']}"
            docs.append(Document(page_content=text, metadata=record))
        return docs


@lru_cache(maxsize=1)
def get_data() -> HSNData:
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return HSNData(json.load(f))