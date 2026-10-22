import json
import re
from functools import lru_cache

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from backend.config import GROQ_API_KEY, GROQ_MODEL


@lru_cache(maxsize=1)
def get_llm() -> ChatGroq:
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set")
    return ChatGroq(model=GROQ_MODEL, api_key=GROQ_API_KEY, temperature=0)


def _parse_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"Model did not return JSON: {text[:200]}")
    return json.loads(match.group(0))


HINT_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are an expert in India's GST and HSN (Harmonized System of Nomenclature) "
        "classification. You answer only with JSON.",
    ),
    (
        "human",
        "Product: {product}\n\n"
        "Return JSON with two keys:\n"
        "\"chapters\": up to 3 HSN chapter numbers as two-digit strings (01 to 99) where this "
        "product most likely belongs, most likely first.\n"
        "\"keywords\": 6 to 10 single lowercase words that would appear in the official HSN "
        "description of this product, including synonyms and the material or purpose.\n"
        "Output JSON only, with no explanation.",
    ),
])

PICK_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You classify products under India's HSN codes. You may choose ONLY codes from the "
        "candidate list you are given. Never invent a code. You answer only with JSON.",
    ),
    (
        "human",
        "Product: {product}\n\n"
        "Candidate HSN codes:\n{candidates}\n\n"
        "Pick the single best code for this product. Prefer the most specific (8-digit) code "
        "that fits. Return JSON with these keys:\n"
        "\"code\": the chosen code, copied exactly from the list (empty string if none fits)\n"
        "\"confidence\": \"high\", \"medium\" or \"low\"\n"
        "\"reason\": one or two plain-English sentences explaining the choice\n"
        "\"alternatives\": up to two other codes from the list, or an empty list\n"
        "Output JSON only.",
    ),
])


def suggest_search_hints(product: str) -> dict:
    chain = HINT_PROMPT | get_llm() | StrOutputParser()
    return _parse_json(chain.invoke({"product": product}))


def choose_best_code(product: str, candidates: list) -> dict:
    lines = [
        f"- {c['code']} | {c['description']} | chapter {c['chapter']} | total GST {c['total_gst']:g}%"
        for c in candidates
    ]
    chain = PICK_PROMPT | get_llm() | StrOutputParser()
    return _parse_json(chain.invoke({"product": product, "candidates": "\n".join(lines)}))