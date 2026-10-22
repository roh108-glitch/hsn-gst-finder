import re

from backend.data_loader import get_data, new_response
from backend.llm_chains import choose_best_code, suggest_search_hints
from backend.lookup import lookup_digits
from backend.retriever import search_candidates


def search(raw_query: str) -> dict:
    query = (raw_query or "").strip()
    if not query:
        return new_response("invalid", query, "Please type a product name or an HSN code.")

    compact = re.sub(r"[\s.]", "", query)  # "9503 00" and "9503.00" both become "950300"
    if compact.isdigit():
        return lookup_digits(query, compact)

    return search_product(query)


def search_product(query: str) -> dict:
    data = get_data()

    # Step 1: ask the AI for likely chapters and search keywords
    try:
        hints = suggest_search_hints(query)
        chapters = [str(c).zfill(2) for c in hints.get("chapters", [])]
        chapters = [c for c in chapters if c in data.chapters]
        keywords = [str(k) for k in hints.get("keywords", [])]
    except Exception:
        chapters, keywords = [], []

    # Step 2: keyword search over the data
    candidates = search_candidates(" ".join([query] + keywords), chapters)
    if not candidates:
        return new_response(
            "not_found",
            query,
            "No matching products were found. Try different words, or enter an HSN code directly.",
        )

    by_code = {c["code"]: c for c in candidates}

    # Step 3: let the AI pick one code from the candidates
    try:
        decision = choose_best_code(query, candidates)
    except Exception:
        decision = None

    # If the AI failed, or picked something not in the list, do not guess: show the candidates
    chosen_code = str(decision.get("code", "")).strip() if decision else ""
    if chosen_code not in by_code:
        response = new_response(
            "uncertain",
            query,
            "The AI could not pick one code confidently. Choose from the list below, or enter an HSN code directly.",
        )
        response["candidates"] = candidates
        return response

    chosen = by_code[chosen_code]
    alternatives = []
    for code in decision.get("alternatives") or []:
        code = str(code).strip()
        if code in by_code and code != chosen_code and by_code[code] not in alternatives:
            alternatives.append(by_code[code])

    response = new_response("found", query)
    response["result"] = chosen
    response["path"] = data.code_path(chosen_code)
    response["confidence"] = str(decision.get("confidence", "low")).lower()
    response["reason"] = str(decision.get("reason", ""))
    response["alternatives"] = alternatives[:2]
    response["candidates"] = candidates
    return response