"""Standalone HTML, CSV and JSON reports. Unknown/error scores remain blank."""
from __future__ import annotations

import csv
from html import escape
import json
from pathlib import Path
from .dataset import write_json


def summaries(rows, metric_names):
    result = {}
    for name in metric_names:
        cells = [row["metrics"][name] for row in rows]
        values = [cell["score"] for cell in cells if cell["status"] == "ok"]
        result[name] = {"mean": sum(values) / len(values) if values else None,
                        "scored": len(values), "unscored": len(cells) - len(values)}
    return result


def score_text(cell):
    return f"{cell['score']:.3f}" if cell["status"] == "ok" else cell["status"].replace("_", " ")


def write_reports(directory, run, rows):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    summary = summaries(rows, run["metrics"])
    write_json(directory / "results.json", {"run": run, "summary": summary, "samples": rows})
    fields = ["sample_id", "symbol", "captured_at", "generation_model", "evaluation_model"]
    for name in run["metrics"]:
        fields.extend([name, name + "_status", name + "_error", name + "_cached"])
    with (directory / "results.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            entry = {key: row.get(key, "") for key in fields[:5]}
            for name in run["metrics"]:
                cell = row["metrics"][name]
                entry.update({name: cell["score"] if cell["status"] == "ok" else "",
                              name + "_status": cell["status"], name + "_error": cell.get("error", ""),
                              name + "_cached": cell.get("cached", False)})
            # Spreadsheet applications must not execute text as formulas.
            entry = {key: "'" + val if isinstance(val, str) and val.startswith(("=", "+", "-", "@")) else val
                     for key, val in entry.items()}
            writer.writerow(entry)
    cards = []
    for name, item in summary.items():
        mean = f"{item['mean']:.3f}" if item["mean"] is not None else "Unavailable"
        caption = "Mean supported-claim ratio" if name == "faithfulness" else "Pass proportion"
        cards.append(f"<section class='card'><span>{escape(name.replace('_', ' ').title())}</span><strong>{mean}</strong>"
                     f"<small>{caption} · {item['scored']} scored / {item['unscored']} unscored</small></section>")
    table_rows, details = [], []
    for row in rows:
        cells = "".join("<td>" + escape(score_text(row["metrics"][name])) + "</td>" for name in run["metrics"])
        table_rows.append(f"<tr><td>{escape(row['symbol'])}</td><td><code>{row['sample_id'][:12]}</code></td>{cells}</tr>")
        assessments = ""
        for name in run["metrics"]:
            cell = row["metrics"][name]
            verdicts = json.dumps(cell.get("trace", []), ensure_ascii=False, indent=2)
            assessments += (f"<h4>{escape(name)}: {escape(score_text(cell))}</h4>"
                            f"<p>{escape(cell.get('error') or '')} {'Reused evaluation result.' if cell.get('cached') else ''}</p>"
                            f"<pre>{escape(verdicts)}</pre>")
        details.append(f"<details><summary>{escape(row['symbol'])} · {row['sample_id'][:12]} · review evidence and verdicts</summary>"
                       f"<h4>Captured task</h4><pre>{escape(row['user_input'])}</pre>"
                       f"<h4>Generated explanation</h4><pre>{escape(row['response'])}</pre>"
                       f"{assessments}<h4>Exact evidence snapshot</h4>"
                       f"<pre>{escape(json.dumps(json.loads(row['retrieved_contexts'][0]), ensure_ascii=False, indent=2))}</pre></details>")
    headings = "".join("<th>" + escape(n.replace("_", " ").title()) + "</th>" for n in run["metrics"])
    html = """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MarketLens · Explanation Evaluation</title><style>
body{font:16px/1.6 system-ui,sans-serif;color:#17302e;background:#f4f7f7;margin:0;padding:32px}main{max-width:1100px;margin:auto}
h1{font-size:34px;line-height:1.2;margin:12px 0}h2{font-size:22px}.tag{color:#167b68;font-weight:700;letter-spacing:.08em}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:18px;margin:26px 0}.card{background:white;border:1px solid #d8e4e2;border-radius:14px;padding:22px}
.card strong{display:block;font-size:36px}.card small{color:#526a67}.note{border-left:4px solid #14967a;padding:12px 18px;background:#e9f4f0}
table{width:100%;border-collapse:collapse;background:white}th,td{text-align:left;padding:14px;border-bottom:1px solid #dde5e4}th{font-size:13px}code{font-size:13px}
.table{overflow:auto}details{background:white;border:1px solid #d8e4e2;padding:18px;margin:14px 0;border-radius:10px}summary{cursor:pointer;font-weight:600}
pre{font:13px/1.6 ui-monospace,monospace;white-space:pre-wrap;overflow-wrap:anywhere;background:#f4f7f7;padding:16px;max-height:480px;overflow:auto}a{color:#087565}footer{font-size:13px;color:#526a67;margin-top:30px}
</style><main><div class="tag">MARKETLENS / EVALUATION</div><h1>Explanation quality</h1>
"""
    html += (f"<p>{len(rows)} unique captured Gemini explanations · {escape(run['created_at'])}<br>"
             f"Evaluator: <b>{escape(run['evaluation_model'])}</b> · Ragas {escape(run['ragas_version'])} · "
             f"Policy {escape(run['criteria_version'])}<br>Evaluator API calls in this run: {run['api_calls']} "
             f"(limit {run['max_calls']}). Sectors calls by this evaluator: 0.</p>"
             "<p class='note'>Pilot evaluation by an LLM judge. Faithfulness measures support in the captured context; it does not verify the provider's financial data. "
             "Aspect scores are 0/1 against our criteria. Errors are unscored, never zero. No overall accuracy or investment score is calculated. "
             "Review numeric values, units, periods and a sample of judge verdicts manually. Generator and judge may use the same model, so this is not independent human validation.</p>"
             f"<div class='grid'>{''.join(cards)}</div><h2>Per-sample results</h2><div class='table'><table>"
             f"<thead><tr><th>Ticker</th><th>Sample</th>{headings}</tr></thead><tbody>{''.join(table_rows)}</tbody></table></div>"
             f"<h2>Inspect each result</h2>{''.join(details)}"
             f"<p>Valid samples available: {run['available_samples']}. Invalid files skipped: {len(run['invalid_files'])}. "
             "This report covers the selected samples only. Cached explanations are not new samples; deterministic fallback is excluded.</p>"
             "<footer><a href='results.csv'>Download CSV</a> · <a href='results.json'>Full JSON</a> · "
             "<a href='https://docs.ragas.io/en/v0.4.3/concepts/metrics/available_metrics/faithfulness/'>Ragas Faithfulness</a> · "
             "<a href='https://docs.ragas.io/en/v0.4.3/concepts/metrics/available_metrics/general_purpose/'>Aspect Critic</a>"
             "<br>Repeated evaluations can vary. No universal pass threshold is assumed.</footer></main></html>")
    (directory / "index.html").write_text(html, encoding="utf-8")
    return directory / "index.html"
