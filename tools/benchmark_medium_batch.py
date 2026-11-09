"""Windows CI A/B: Medium REC batch 6 vs 2/4, all at fixed two ONNX CPU threads.

Generate only synthetic game menus, never capture a user screen.
This is CPU CI evidence, not a claim about the user's actual Windows 11 PC.
"""
from __future__ import annotations

import gc
import hashlib
import json
import statistics
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from game_reader.ocr_backend import LocalOCR


def _font(size: int) -> ImageFont.FreeTypeFont:
    for path in ("C:/Windows/Fonts/msyh.ttc",
                 "C:/Windows/Fonts/simhei.ttf",
                 "C:/Windows/Fonts/arialbd.ttf"):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    raise RuntimeError("No Windows font available for OCR experiment")


def scene(dense: bool) -> Image.Image:
    """Two reproducible layouts: short 4-row menu and a crowded 18-row menu."""
    size = (1500, 1300) if dense else (1500, 470)
    image = Image.new("RGB", size, (23, 28, 35))
    draw = ImageDraw.Draw(image)
    font = _font(44 if dense else 68)
    words = [
        "继续游戏 CONTINUE", "游戏设置 SETTINGS", "返回主菜单 BACK",
        "保存进度 SAVE", "查看任务 QUESTS", "装备 INVENTORY",
        "角色属性 CHARACTER", "地图 MAP", "选择角色 SELECT",
        "下一步 NEXT", "打开物品 OPEN", "任务完成 COMPLETE",
        "技能升级 SKILLS", "退出游戏 EXIT", "难度选择 LEVEL",
        "音量设置 SOUND", "读取存档 LOAD", "返回大厅 LOBBY"
    ]
    for i, word in enumerate(words if dense else words[:4]):
        draw.text((90, 42 + i * (67 if dense else 101)),
                  word, fill=(244, 241, 225), font=font)
    return image


def signature(lines) -> dict:
    text = "\n".join(line.text for line in lines)
    boxes = [(line.left, line.top, line.right, line.bottom) for line in lines]
    return {
        "count": len(lines),
        "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "boxes_sha256": hashlib.sha256(repr(boxes).encode("utf-8")).hexdigest(),
    }


def run_batch(batch: int, scenes: dict) -> dict:
    engine = LocalOCR(medium_rec_batch_num=batch, medium_ort_threads=2)
    warmup_ms = engine.prepare("medium")
    out = {"warmup_ms": warmup_ms, "scenes": {}}
    for name, image in scenes.items():
        times = []
        last = None
        for _ in range(2):
            lines, metrics = engine.recognize_timed(image, (0, 0), "medium")
            if not lines:
                raise RuntimeError(f"No OCR lines: batch={batch} scene={name}")
            times.append(metrics["inference_ms"])
            last = dict(signature(lines), raw_lines=metrics["raw_lines"],
                        engine_stages=metrics["engine_stages"])
        out["scenes"][name] = {
            "inference_ms_repeats": times,
            "median_inference_ms": statistics.median(times),
            "result": last,
        }
    del engine
    gc.collect()
    return out


def main() -> None:
    scenes = {"short": scene(False), "dense": scene(True)}
    # Compare baseline and candidate with identical official weights and input.
    trials = {str(batch): run_batch(batch, scenes) for batch in (6, 2, 4)}
    comparisons = {}
    for candidate in (2, 4):
        details = {}
        for name in scenes:
            baseline = trials["6"]["scenes"][name]
            proposal = trials[str(candidate)]["scenes"][name]
            base_ms = baseline["median_inference_ms"]
            new_ms = proposal["median_inference_ms"]
            details[name] = {
                "baseline_ms": base_ms,
                "candidate_ms": new_ms,
                "speedup": round(base_ms / max(1, new_ms), 3),
                "text_equal": (baseline["result"]["text_sha256"] ==
                               proposal["result"]["text_sha256"]),
                "boxes_equal": (baseline["result"]["boxes_sha256"] ==
                                proposal["result"]["boxes_sha256"]),
                "line_count_equal": (baseline["result"]["count"] ==
                                     proposal["result"]["count"]),
            }
        comparisons[str(candidate)] = details
    result = {
        "warning": "Windows GitHub CI synthetic screenshots; not actual game or audio latency.",
        "baseline_batch": 6, "experimental_default_batch": 2,
        "ort_cpu_threads": 2,
        "trials": trials, "comparisons": comparisons,
    }
    output = Path("medium_ocr_ab.json")
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False),
                      encoding="utf-8")
    print("MEDIUM_REC_BATCH_AB_REPORT=" + str(output.resolve()))
    for candidate, details in comparisons.items():
        for name, metrics in details.items():
            print(f"batch={candidate} scene={name}: baseline="
                  f"{metrics['baseline_ms']}ms candidate="
                  f"{metrics['candidate_ms']}ms speedup="
                  f"{metrics['speedup']}x text_equal="
                  f"{metrics['text_equal']} boxes_equal="
                  f"{metrics['boxes_equal']}")


if __name__ == "__main__":
    main()
