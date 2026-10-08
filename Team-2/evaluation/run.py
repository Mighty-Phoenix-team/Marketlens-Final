"""Evaluate captured samples only. This module never fetches asset data."""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import time

# Explicitly turn off optional third-party tracing/telemetry before importing Ragas.
os.environ["RAGAS_DO_NOT_TRACK"] = "true"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["LANGSMITH_TRACING"] = "false"

from .criteria import CRITERIA_VERSION, LIMITATION_RETENTION, PROFILE_ALIGNMENT
from .dataset import ROOT, canonical, load_samples, sample_directory, write_json
from .report import write_reports
from .errors import error_label, provider_diagnostic, stops_run


def evaluation_signature(model, version, name):
    # Code and criteria changes invalidate prior results, as does the judge model.
    files = [Path(__file__), Path(__file__).with_name("judge.py"), Path(__file__).with_name("criteria.py"),
             Path(__file__).with_name("errors.py")]
    implementation = hashlib.sha256(b"\n".join(p.read_bytes() for p in files)).hexdigest()
    return hashlib.sha256(canonical([model, version, name, CRITERIA_VERSION, implementation,
                                     LIMITATION_RETENTION, PROFILE_ALIGNMENT, "temperature=0;strictness=1"]).encode()).hexdigest()


async def score_sample(sample, metrics, judge, *, model, version, cache_dir, timeout,
                       refresh=False, retry_errors=False):
    from ragas.dataset_schema import SingleTurnSample
    row = {key: sample[key] for key in ("sample_id", "symbol", "captured_at", "generation_model",
                                       "user_input", "response", "retrieved_contexts")}
    row.update(evaluation_model=model, metrics={})
    stop = False
    for name, metric in metrics.items():
        signature = evaluation_signature(model, version, name)
        cache_path = Path(cache_dir) / f"{sample['sample_id']}_{signature}.json"
        cached = None
        if not refresh and cache_path.exists():
            try:
                loaded = json.loads(cache_path.read_text(encoding="utf-8"))
                if loaded.get("sample_id") == sample["sample_id"] and loaded.get("signature") == signature:
                    cached = loaded["result"]
            except (ValueError, OSError, KeyError):
                pass
        if cached and (cached["status"] == "ok" or not retry_errors):
            row["metrics"][name] = {**cached, "cached": True}
            if stops_run(cached.get("error")):
                stop = True
            continue
        if stop or judge.calls >= judge.max_calls:
            row["metrics"][name] = {"score": None, "status": "not_run", "error": "run_stopped_or_budget_reached", "cached": False}
            continue
        judge.begin_metric()
        started = time.monotonic()
        try:
            user_input = sample["user_input"]
            if name != "faithfulness":
                user_input += "\nOriginal system instructions for this explanation:\n" + sample["request"]["system_instruction"]
            turn = SingleTurnSample(user_input=user_input, response=sample["response"],
                                    retrieved_contexts=sample["retrieved_contexts"])
            value = float(await metric.single_turn_ascore(turn, timeout=timeout))
            if not math.isfinite(value):
                result = {"score": None, "status": "unscored", "error": "no_claims_or_invalid_score"}
            elif not 0 <= value <= 1 or (name != "faithfulness" and value not in (0, 1)):
                result = {"score": None, "status": "error", "error": "invalid_score_range"}
            else:
                result = {"score": value, "status": "ok", "error": None}
        except Exception as exc:
            reason = error_label(exc)
            result = {"score": None, "status": "error", "error": reason,
                      "provider_error": provider_diagnostic(exc)}
            stop = stops_run(reason)
        result.update(trace=list(judge.trace), api_calls=judge.metric_calls,
                      seconds=round(time.monotonic() - started, 3),
                      evaluated_at=datetime.now(timezone.utc).isoformat(), cached=False)
        row["metrics"][name] = result
        write_json(cache_path, {"sample_id": sample["sample_id"], "signature": signature, "result": result})
    return row, stop


async def evaluate(args, samples, invalid, available):
    from .judge import GeminiJudge, make_metrics
    api_key = os.getenv("MARKETLENS_EVAL_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY belum tersedia. Gunakan .env Team-2 atau MARKETLENS_EVAL_API_KEY.")
        return 2
    model = args.model or os.getenv("MARKETLENS_EVAL_MODEL") or os.getenv("GEMINI_MODEL", "gemini-flash-latest")
    version = importlib.metadata.version("ragas")
    if version != "0.4.3":
        print("Paket ini diuji dengan ragas==0.4.3. Install requirements-eval.txt di .venv-ragas.")
        return 2
    output = Path(args.output) if args.output else ROOT / "evaluation_data" / "reports" / datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    judge = GeminiJudge(api_key, model, timeout=min(90, args.timeout), max_calls=args.max_calls)
    metrics = make_metrics(judge, include_profile=not args.core_only)
    run = {"created_at": datetime.now(timezone.utc).isoformat(), "evaluation_model": model,
           "ragas_version": version, "criteria_version": CRITERIA_VERSION, "metrics": list(metrics),
           "max_calls": args.max_calls, "api_calls": 0, "available_samples": available, "invalid_files": invalid}
    rows = []
    print(f"Ragas: {len(samples)} sampel; evaluator={model}; maksimal {args.max_calls} panggilan Gemini.", flush=True)
    print("Data Sectors tidak diambil ulang. Empat panggilan evaluator/sampel biasanya diperlukan untuk tiga metrik; perbaikan respons dan retry server tetap dihitung dalam batas panggilan.", flush=True)
    try:
        for index, sample in enumerate(samples, start=1):
            print(f"[{index}/{len(samples)}] {sample['symbol']} {sample['sample_id'][:12]}", flush=True)
            row, stop = await score_sample(sample, metrics, judge, model=model, version=version,
                                           cache_dir=ROOT / "evaluation_data" / "judge_cache", timeout=args.timeout,
                                           refresh=args.refresh, retry_errors=args.retry_errors)
            rows.append(row)
            run["api_calls"] = judge.calls
            write_reports(output, run, rows)  # Preserve completed work after every sample.
            for name, cell in row["metrics"].items():
                print(f"  {name}: {cell['score'] if cell['status'] == 'ok' else cell['status']}"
                      f"{(' (' + cell['error'] + ')') if cell.get('error') else ''}"
                      f"{' [cached]' if cell.get('cached') else ''}", flush=True)
            if stop or judge.calls >= judge.max_calls:
                print("Evaluasi dihentikan setelah error yang memblokir proses atau batas panggilan tercapai; hasil parsial sudah disimpan.")
                break
    finally:
        await judge.close()
    print(f"Laporan: {output / 'index.html'}", flush=True)
    print(f"CSV: {output / 'results.csv'}", flush=True)
    if not rows or len(rows) < len(samples) or any(cell["status"] != "ok" for row in rows for cell in row["metrics"].values()):
        return 1
    return 0


def main(argv=None):
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env", encoding="utf-8-sig", override=False)
    parser = argparse.ArgumentParser(description="Evaluate captured MarketLens explanations with Ragas + Gemini.")
    parser.add_argument("--samples", type=Path, default=None)
    parser.add_argument("--limit", type=int, default=5, help="Newest unique samples (default 5)")
    parser.add_argument("--check", action="store_true", help="Validate saved samples only; no model calls")
    parser.add_argument("--core-only", action="store_true", help="Faithfulness + limitation retention only")
    parser.add_argument("--model", help="Evaluator model override")
    parser.add_argument("--timeout", type=float, default=120, help="Deadline per metric in seconds")
    parser.add_argument("--max-calls", type=int, default=30, help="Hard budget of evaluator SDK calls per run")
    parser.add_argument("--refresh", action="store_true", help="Re-evaluate even successful cached results; uses quota")
    parser.add_argument("--retry-errors", action="store_true", help="Retry previously failed metrics; uses quota")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if not 1 <= args.limit <= 100 or not 1 <= args.max_calls <= 500 or not 10 <= args.timeout <= 600:
        parser.error("limit harus 1-100; max-calls 1-500; timeout 10-600 detik")
    samples, invalid, available = load_samples(args.samples or sample_directory(), args.limit)
    print(f"Sampel Gemini valid: {available}; dipilih: {len(samples)}; file tidak valid: {len(invalid)}.")
    for item in invalid:
        print(f"  Dilewati: {item['file']} ({item['reason']})")
    if not samples:
        print("Belum ada sampel. Setelah patch dipasang, restart API Team-2, lalu Explain Finding sampai sumbernya Gemini.")
        return 2
    if args.check:
        print("PASS: pasangan input/output valid. Sectors calls: 0; Gemini calls: 0. Belum ada skor Ragas.")
        return 0
    return asyncio.run(evaluate(args, samples, invalid, available))


if __name__ == "__main__":
    raise SystemExit(main())
