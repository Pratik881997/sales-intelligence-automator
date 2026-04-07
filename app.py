from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

from sales_intel.lead_sources import parse_csv_text, parse_leads_text
from sales_intel.pipeline import PipelineConfig, run_pipeline


st.set_page_config(page_title="Sales Intelligence Automator", page_icon=":mag:", layout="wide")

st.markdown(
    """
<style>
.stApp {
    background: radial-gradient(circle at 10% 20%, #111827 0%, #0b1220 40%, #05070d 100%);
    color: #f3f4f6;
}
.card {
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.10);
    border-radius: 14px;
    padding: 14px;
}
</style>
""",
    unsafe_allow_html=True,
)

st.title("Sales Intelligence Automator")
st.caption("URL / domain → open site directly · Text lead → Google (3 pages, organic only) → crawl · Ollama")

with st.sidebar:
    st.subheader("Pipeline Settings")
    model_name = st.selectbox(
        "LLM Model (Ollama)",
        options=["mistral:latest", "gemma3:4b", "gemma4:latest"],
        index=0,
    )
    headless = st.checkbox("Headless Chrome", value=True, help="Turn off to watch the browser.")
    save_output = st.checkbox("Save results to output/results.json", value=True)
    st.caption(
        "Company **names** are searched on Google (organic only, sponsored excluded). "
        "**URLs** or **domains** are opened directly. Requires Chrome installed."
    )

input_col, preview_col = st.columns([1, 1])
with input_col:
    st.markdown("### Lead Input")
    text_input = st.text_area(
        "Paste one lead per line (URL or company name)",
        height=230,
        placeholder="https://example.com\nAcme Roofing - Dallas TX",
    )
    upload = st.file_uploader("Or upload a leads CSV", type=["csv"])

    use_default = st.button("Load bundled leads.csv")
    run_button = st.button("Run Analysis", type="primary", use_container_width=True)

leads: list[str] = []
if upload is not None:
    leads = parse_csv_text(upload.getvalue().decode("utf-8", errors="ignore"))
elif text_input.strip():
    leads = parse_leads_text(text_input)
elif use_default and Path("leads.csv").exists():
    leads = parse_csv_text(Path("leads.csv").read_text(encoding="utf-8", errors="ignore"))

with preview_col:
    st.markdown("### Input Preview")
    st.markdown(f'<div class="card">Total Leads: <b>{len(leads)}</b></div>', unsafe_allow_html=True)
    if leads:
        st.dataframe(pd.DataFrame({"lead": leads}), use_container_width=True, hide_index=True)


def briefs_to_table_rows(briefs: list) -> list[dict]:
    rows: list[dict] = []
    for b in briefs:
        d = b.model_dump()
        d["sections"] = json.dumps(d.get("sections") or [], ensure_ascii=False)
        rows.append(d)
    return rows


if run_button:
    if not leads:
        st.warning("Add leads first to run the analysis.")
        st.stop()

    progress = st.progress(0.0, text="Starting pipeline...")
    status = st.empty()
    status.info("Crawling pages and generating dynamic section summaries.")

    config = PipelineConfig(model_name=model_name, headless=headless)
    results, errors = run_pipeline(leads, config)

    progress.progress(1.0, text="Pipeline complete")
    status.success(f"Completed {len(results)} leads with {len(errors)} errors.")

    result_rows = briefs_to_table_rows(results)
    df = pd.DataFrame(result_rows)

    st.markdown("### Results (summary table)")
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        st.download_button(
            label="Download JSON",
            data=json.dumps(result_rows, indent=2, ensure_ascii=False),
            file_name="sales_briefs.json",
            mime="application/json",
        )
        st.download_button(
            label="Download CSV",
            data=df.to_csv(index=False),
            file_name="sales_briefs.csv",
            mime="text/csv",
        )
    else:
        st.warning("No successful results returned.")

    st.markdown("### Detailed briefs (dynamic sections)")
    for idx, brief in enumerate(results, start=1):
        title = brief.company_name or brief.lead_input or f"Lead {idx}"
        with st.expander(f"{idx}. {title}", expanded=(len(results) <= 3)):
            st.markdown(f"**Resolved URL:** {brief.resolved_url or '—'}")
            if brief.contact_details:
                st.markdown("**Contact (extracted)**")
                st.write(brief.contact_details)
            if brief.sections:
                for sec in brief.sections:
                    st.markdown(f"#### {sec.title}")
                    st.write(sec.content)
            else:
                st.write(brief.company_overview or brief.rationale or "No section data.")
            if brief.research_notes:
                st.caption(f"Research notes: {brief.research_notes}")
            if brief.sales_questions:
                st.markdown("**Sales questions**")
                for q in brief.sales_questions:
                    st.markdown(f"- {q}")

    if errors:
        st.markdown("### Errors")
        for err in errors:
            st.error(err)

    if save_output and result_rows:
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        (output_dir / "results.json").write_text(
            json.dumps(result_rows, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        st.success("Saved to output/results.json")
