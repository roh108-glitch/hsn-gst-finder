# HSN Code and GST Rate Finder

A small RAG-based chatbot that finds the **HSN code** and **GST rate** for a product.

Type a product name (for example, `robotic cat`) or an HSN code (2 to 8 digits), and the app returns the matching code, its GST rate, and the reasoning behind the choice.

**Live app:** https://hsn-gst-finder-mxvwb7vhlh5gzgdytymwhe.streamlit.app
**Backend API docs:** https://hsn-gst-finder.onrender.com/docs

---

## What are HSN and GST?

- **HSN (Harmonized System of Nomenclature)** is an international numbering system for goods. Each product has a code, for example `9503` for toys. The first two digits are the chapter, and more digits make the description more specific.
- **GST (Goods and Services Tax)** is India's tax on goods and services. Each HSN code has a GST rate attached to it.
- **CGST, SGST and IGST** are the parts of the GST rate. Within the same state, the rate is split into CGST (central) and SGST (state), with each taking half. Across state lines, the full rate is charged as IGST.

## Features

- Search by product name or description (for example, `stuffed teddy bear`)
- Direct lookup by HSN code, from 2 to 8 digits (for example, `9503` or `95034100`)
- Shows the chapter-to-code path, the CGST, SGST, IGST and total GST rate
- Shows the reason for the choice, a confidence level, and up to two alternative codes
- Shows the candidate codes the AI compared, so the result can be checked
- Chapter view for 2-digit input, listing the headings in that chapter
- Safe by design: the AI can only choose from real codes in the data, and rates always come from the data, never from the AI

## How it works

1. **Digits only?** The app looks up the code directly in the data. No AI is used.
2. **Product name?** The AI (Groq, `openai/gpt-oss-120b`) suggests the likely HSN chapters and search keywords.
3. **Keyword search (RAG retrieval).** The app searches about 21,900 HSN and SAC records using BM25 keyword search. It looks inside the suggested chapters first, and searches all chapters if that finds too little.
4. **AI choice.** The AI picks one code from the candidate list and explains why. If it picks a code that isn't in the list, the app doesn't show it and shows the candidates instead.
5. **Rates from the data.** The GST rates are read from the data file, not from the AI.

## Tech stack

| Part | Technology |
|---|---|
| Language | Python 3.11 |
| AI / RAG framework | LangChain (`langchain-groq`, `langchain-community`) |
| LLM | Groq API, model `openai/gpt-oss-120b` |
| Keyword search | BM25 (`rank-bm25`, through LangChain) |
| Backend API | FastAPI with Uvicorn |
| Frontend | Streamlit |
| Hosting | Render (backend), Streamlit Community Cloud (frontend) |

## Project structure

```
hsn-gst-finder/
├── README.md
├── requirements.txt
├── .gitignore
├── .env
├── backend/
│   ├── __init__.py
│   ├── config.py           # settings from environment variables
│   ├── data_loader.py      # loads and cleans the HSN/GST data
│   ├── lookup.py           # direct lookup for digit-only input
│   ├── retriever.py        # BM25 keyword search with chapter filter
│   ├── llm_chains.py       # Groq prompts: suggest chapters, pick a code
│   ├── search_service.py   # the full search flow
│   ├── main.py             # FastAPI app and endpoints
│   └── data/
│       └── gst_hsn_sac_records.json
└── frontend/
    └── app.py              # Streamlit user interface
```

## Running locally

1. Clone the repository and open the project folder.
2. Create and activate a virtual environment:
   ```
   python -m venv .venv
   .venv\Scripts\activate
   ```
   (On Mac or Linux, use `source .venv/bin/activate`.)
3. Install the requirements:
   ```
   python -m pip install -r requirements.txt
   ```
4. Create a file named `.env` in the project folder (copy `.env.example`) and add your Groq key:
   ```
   GROQ_API_KEY=your_groq_api_key_here
   GROQ_MODEL=openai/gpt-oss-120b
   ```
5. Start the backend in one terminal:
   ```
   python -m uvicorn backend.main:app --reload
   ```
6. Start the frontend in a second terminal:
   ```
   python -m streamlit run frontend/app.py
   ```
7. Open the Streamlit address shown in the terminal (usually http://localhost:8501).

Optional: open http://127.0.0.1:8000/docs to test the API directly.

## API

**`POST /search`**

Request:
```json
{ "query": "robotic cat" }
```

Response (shortened):
```json
{
  "status": "found",
  "query": "robotic cat",
  "result": {
    "code": "95030010",
    "description": "...",
    "cgst": 2.5,
    "sgst": 2.5,
    "igst": 5.0,
    "total_gst": 5.0
  },
  "path": [ { "code": "95", "description": "..." } ],
  "confidence": "medium",
  "reason": "...",
  "alternatives": [],
  "candidates": []
}
```

The `status` field is one of `found`, `uncertain`, `chapter`, `not_found` or `invalid`.

**`GET /health`** returns the server status and the number of records loaded.

## Deployment

- **Backend (Render, Web Service):**
  - Build command: `pip install -r requirements.txt`
  - Start command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
  - Environment variables: `GROQ_API_KEY`, `GROQ_MODEL`, `PYTHON_VERSION=3.11`
- **Frontend (Streamlit Community Cloud):**
  - Main file: `frontend/app.py`
  - Secret: `API_URL = "https://hsn-gst-finder.onrender.com"`

The free Render service sleeps after about 15 minutes without requests. The first search after a quiet period can take 30 to 60 seconds.

## Limitations

- **Not official tax advice.** The rates come from a data snapshot extracted from EZTax India on 12 August 2026. Confirm the code and rate with official GST sources before filing.
- **AI choices can vary.** For ambiguous products, the same search may give a different top code. The app shows alternatives and a confidence level for this reason.
- **Keyword search, not semantic search.** Product names that use very different words from the official descriptions may need the synonyms the AI suggests. Searching for the official wording, or entering the code directly, gives the most reliable result.


