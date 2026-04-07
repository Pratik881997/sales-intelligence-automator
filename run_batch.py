"""CLI: process leads.csv → output/results.json (requires Chrome + Ollama)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

from sales_intel.lead_sources import parse_csv_text
from sales_intel.pipeline import PipelineConfig, run_pipeline


def main() -> None:
    csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("leads.csv")
    model = sys.argv[2] if len(sys.argv) > 2 else "mistral:latest"
    text = csv_path.read_text(encoding="utf-8", errors="ignore")
    leads = parse_csv_text(text)
    if not leads:
        print("No leads in file.", file=sys.stderr)
        sys.exit(1)
    cfg = PipelineConfig(model_name=model, headless=True)
    results, errors = run_pipeline(leads, cfg)
    rows = []
    for b in results:
        d = b.model_dump()
        d["sections"] = [s.model_dump() for s in b.sections]
        rows.append(d)
    out = Path("output")
    out.mkdir(exist_ok=True)
    (out / "results.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(rows)} result(s) to output/results.json")
    for e in errors:
        print("Error:", e, file=sys.stderr)


if __name__ == "__main__":
    main()
