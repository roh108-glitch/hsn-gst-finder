import os

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="HSN & GST Finder", page_icon="🧾", layout="centered")


def get_api_url() -> str:
    try:
        if "API_URL" in st.secrets:
            return str(st.secrets["API_URL"]).rstrip("/")
    except Exception:
        pass
    return os.getenv("API_URL", "http://127.0.0.1:8000").rstrip("/")


def pct(value) -> str:
    return f"{float(value):g}%"


def show_items(items: list) -> None:
    if not items:
        return
    rows = [
        {
            "HSN code": i["code"],
            "Description": i["description"],
            "Total GST": pct(i["total_gst"]),
            "CGST": pct(i["cgst"]),
            "SGST": pct(i["sgst"]),
            "IGST": pct(i["igst"]),
        }
        for i in items
    ]
    st.dataframe(pd.DataFrame(rows), hide_index=True)


def render_result(data: dict) -> None:
    status = data.get("status")
    message = data.get("message", "")
    path = data.get("path", [])

    if status == "found":
        item = data["result"]
        st.success(f"HSN code: **{item['code']}**")
        st.subheader(item["description"])
        if message:
            st.info(message)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total GST", pct(item["total_gst"]))
        c2.metric("CGST", pct(item["cgst"]))
        c3.metric("SGST", pct(item["sgst"]))
        c4.metric("IGST", pct(item["igst"]))

        if item.get("condition"):
            st.warning(f"Condition: {item['condition']}")

        if path:
            st.markdown("**Code path**")
            for p in path:
                st.write(f"- `{p['code']}` {p['description']}")

        if data.get("confidence"):
            st.write(f"**Confidence:** {data['confidence']}")
        if data.get("reason"):
            st.write(f"**Why:** {data['reason']}")

        if data.get("alternatives"):
            st.markdown("**Other possible codes**")
            show_items(data["alternatives"])

        if data.get("candidates"):
            with st.expander("Candidate codes that were compared"):
                show_items(data["candidates"])

    elif status == "uncertain":
        st.warning(message)
        show_items(data.get("candidates", []))

    elif status == "chapter":
        st.info(message)
        if path:
            st.subheader(f"Chapter {path[0]['code']}: {path[0]['description']}")
        show_items(data.get("candidates", []))

    else:  # not_found or invalid
        st.warning(message)


st.title("HSN Code and GST Rate Finder")
st.caption("Type a product name (for example: robotic cat) or an HSN code (2 to 8 digits).")

query = st.text_input("Product or HSN code", placeholder="e.g. robotic cat, or 9503")

if st.button("Search", type="primary"):
    if not query.strip():
        st.warning("Please type a product name or an HSN code first.")
    else:
        with st.spinner("Searching the HSN and GST data..."):
            try:
                response = requests.post(
                    f"{get_api_url()}/search",
                    json={"query": query},
                    timeout=120,
                )
                response.raise_for_status()
                render_result(response.json())
            except requests.RequestException as exc:
                st.error("Could not reach the search service. If it was sleeping, wait a minute and try again.")
                st.caption(str(exc))

st.divider()
st.caption(
    "Rates come from an August 2026 data snapshot. Confirm the final code and rate with official "
    "GST sources before filing."
)
