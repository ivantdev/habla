"""Resume JSONL del banco; los conteos de texto no juzgan la política."""

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np


def summarize(directory):
    rows = [json.loads(line) for line in (directory / "turns.jsonl").read_text().splitlines()]
    groups = defaultdict(list)
    for row in rows:
        groups[(row.get("profile", "other"), row["language"])].append(row)
    output = {"source": directory.name, "total": len(rows), "groups": [],
              "limitation": "Synthetic input; receiver/simulated queue metrics, not audible student latency. Text counts are not semantic compliance."}
    for (profile, lang), group in groups.items():
        texts = Counter(r["text"].strip() for r in group if r["text"].strip())
        result = {"profile": profile, "language": lang, "n": len(group),
                  "unique_exact_texts": len(texts),
                  "most_repeated_exact_text_count": max(texts.values(), default=0),
                  "turns_with_errors": sum(bool(r["errors"]) for r in group),
                  "without_audio": sum(r["first_chunk_at"] is None for r in group),
                  "without_text": sum(not r["text"].strip() for r in group),
                  "text_with_question_mark": sum("?" in r["text"] for r in group),
                  "text_over_30_words": sum(len(r["text"].split()) > 30 for r in group),
                  "text_with_markup": sum(bool(re.search(r"<\w+|\*\*|^\s*[-*]\s", r["text"])) for r in group)}
        for name in ["end_to_first_chunk_ms", "end_to_simulated_signal_ms", "max_send_lateness_ms", "stop_event_ms"]:
            values = [r[name] for r in group if r.get(name) is not None]
            result[name] = {"n": len(values), "negative": sum(v < 0 for v in values),
                            **({"p50": float(np.percentile(values, 50)), "p95": float(np.percentile(values, 95)),
                                "max": float(max(values))} if values else {})}
        output["groups"].append(result)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps(summarize(args.directory), ensure_ascii=False, indent=2) + "\n")
