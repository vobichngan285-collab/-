"""Measure real Windows CPU Medium OCR threading on identical synthetic menus.

Compare baseline ONNX Runtime automatic thread count vs explicit 1, 2, 4.
The candidate controls BOTH DET+REC sessions for Medium ONLY, while Small
keeps its original configuration; no personal screens or text are collected.
"""
from __future__ import annotations

import gc
import json
import statistics
from pathlib import Path

from game_reader.ocr_backend import LocalOCR
from tools.benchmark_medium_batch import scene, signature


def measure(threads: int | None, scenes: dict) -> dict:
    worker = LocalOCR(medium_rec_batch_num=2, medium_ort_threads=threads)
    warmup_ms = worker.prepare("medium")
    results = {"warmup_ms": warmup_ms, "scenes": {}}
    for name, image in scenes.items():
        durations = []
        current_sig = None
        current_stage = None
        for _ in range(2):
            lines, t = worker.recognize_timed(image, (0, 0), "medium")
            if not lines:
                raise RuntimeError(f"Empty Medium OCR: threads={threads}, scene={name}")
            durations.append(t["inference_ms"])
            current_sig = signature(lines)
            current_stage = t["engine_stages"]
        results["scenes"][name] = {
            "inference_ms_repeats": durations,
            "median_inference_ms": statistics.median(durations),
            "signature": current_sig,
            "engine_stages": current_stage,
        }
    del worker
    gc.collect()
    return results


def main() -> None:
    images = {"short": scene(False), "dense": scene(True)}
    trials = {}
    for threads in (None, 1, 2, 4):
        key = "auto" if threads is None else str(threads)
        trials[key] = measure(threads, images)
    # Re-test automatic threading LAST to detect warmup/order bias.
    trials["auto_recheck"] = measure(None, images)
    comparisons = {}
    for threads in (1, 2, 4):
        details = {}
        for name in images:
            base = trials["auto"]["scenes"][name]
            candidate = trials[str(threads)]["scenes"][name]
            details[name] = {
                "baseline_ms": base["median_inference_ms"],
                "candidate_ms": candidate["median_inference_ms"],
                "speedup": round(base["median_inference_ms"] /
                                 max(candidate["median_inference_ms"], 1), 3),
                "text_equal": base["signature"]["text_sha256"] ==
                              candidate["signature"]["text_sha256"],
                "boxes_equal": base["signature"]["boxes_sha256"] ==
                               candidate["signature"]["boxes_sha256"],
                "lines_equal": base["signature"]["count"] ==
                               candidate["signature"]["count"],
            }
        comparisons[str(threads)] = details
    order_check = {}
    for name in images:
        first = trials["auto"]["scenes"][name]["median_inference_ms"]
        final_auto = trials["auto_recheck"]["scenes"][name]["median_inference_ms"]
        fixed_two = trials["2"]["scenes"][name]["median_inference_ms"]
        order_check[name] = {
            "first_auto_ms": first,
            "final_auto_ms": final_auto,
            "fixed2_ms": fixed_two,
            "speedup_vs_final_auto": round(final_auto / max(fixed_two, 1), 3),
            "text_equal": (trials["auto_recheck"]["scenes"][name]["signature"]["text_sha256"]
                           == trials["2"]["scenes"][name]["signature"]["text_sha256"]),
        }
    report = {
        "order_check": order_check,
        "warning": "Windows GitHub CI synthetic images; user computer not yet validated.",
        "medium_batch": 2,
        "auto": "RapidOCR 3.10.0 default ONNX Runtime CPU threads",
        "trials": trials,
        "comparisons": comparisons,
    }
    file = Path("medium_ocr_threads_ab.json")
    file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("MEDIUM_THREAD_AB_REPORT=" + str(file.resolve()))
    print("AUTO_RECHECK=" + json.dumps(order_check, ensure_ascii=False))
    for k, scenes in comparisons.items():
        for name, s in scenes.items():
            print(f"threads={k} {name}: auto={s['baseline_ms']}ms "
                  f"candidate={s['candidate_ms']}ms "
                  f"speedup={s['speedup']}x text_equal={s['text_equal']}, "
                  f"boxes_equal={s['boxes_equal']}")


if __name__ == "__main__":
    main()
