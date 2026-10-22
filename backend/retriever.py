import re
from functools import lru_cache

from langchain_community.retrievers import BM25Retriever

from backend.data_loader import get_data, to_item

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")

STOPWORDS = {
    "a", "an", "and", "or", "of", "the", "for", "with", "in", "on", "to", "by",
    "from", "other", "others", "not", "elsewhere", "specified", "included",
    "parts", "thereof", "hsn", "chapter", "is", "are", "as", "at", "its", "their",
}


def tokenize(text: str) -> list:
    return [t for t in TOKEN_PATTERN.findall(text.lower()) if t not in STOPWORDS]


@lru_cache(maxsize=1)
def _all_docs():
    return get_data().search_documents()


@lru_cache(maxsize=1)
def _all_retriever():
    # Keyword (BM25) index over every specific code. Built once at startup.
    return BM25Retriever.from_documents(_all_docs(), preprocess_func=tokenize, k=300)


def warm_up() -> None:
    _all_retriever()


def _keep_relevant(docs, query_tokens: set) -> list:
    """Drop results that share no real word with the query."""
    kept = []
    for doc in docs:
        if query_tokens & set(tokenize(doc.page_content)):
            kept.append(doc)
    return kept


def search_candidates(query: str, preferred_chapters: list, top_n: int = 15) -> list:
    query_tokens = set(tokenize(query))
    if not query_tokens:
        return []

    pool = []

    # 1. Search only inside the chapters the AI suggested
    if preferred_chapters:
        subset = [d for d in _all_docs() if d.metadata["chapter"] in preferred_chapters]
        if subset:
            subset_retriever = BM25Retriever.from_documents(
                subset, preprocess_func=tokenize, k=len(subset)
            )
            pool = _keep_relevant(subset_retriever.invoke(query), query_tokens)

    # 2. If that found too little, search every chapter
    if len(pool) < 5:
        pool = _keep_relevant(_all_retriever().invoke(query), query_tokens)

    # 3. Show 8-digit codes first, keeping keyword-score order inside each group
    pool.sort(key=lambda d: len(d.metadata["code"]) != 8)
    return [to_item(d.metadata) for d in pool[:top_n]]