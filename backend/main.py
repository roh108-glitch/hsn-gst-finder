from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.data_loader import get_data
from backend.retriever import warm_up
from backend.search_service import search


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the data and build the search index once, when the server starts
    get_data()
    warm_up()
    yield


app = FastAPI(title="HSN and GST Finder API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class SearchRequest(BaseModel):
    query: str = Field(..., max_length=300)


@app.get("/")
def root():
    return {"message": "HSN and GST Finder API is running. Use POST /search."}


@app.get("/health")
def health():
    return {"status": "ok", "records": len(get_data().records)}


@app.post("/search")
def search_endpoint(body: SearchRequest):
    try:
        return search(body.query)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Search failed: {exc}")