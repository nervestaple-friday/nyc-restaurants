#!/usr/bin/env python3
"""Build index.html by inlining restaurants.json into the template."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MARKER = "/* %%RESTAURANTS%% */[]"


def build():
    template_path = ROOT / "index.template.html"
    json_path = ROOT / "restaurants.json"
    output_path = ROOT / "index.html"

    template = template_path.read_text(encoding="utf-8")
    if MARKER not in template:
        print("ERROR: marker not found in index.template.html", file=sys.stderr)
        sys.exit(1)

    data = json.loads(json_path.read_text(encoding="utf-8"))

    # Compact each entry onto one line, matching existing format
    entries = [json.dumps(r, ensure_ascii=False, separators=(",", ":")) for r in data]
    inline = "[\n  " + ",  ".join(entries) + "\n]"

    html = template.replace(MARKER, inline)
    output_path.write_text(html, encoding="utf-8")
    print(f"Built index.html with {len(data)} restaurants")


if __name__ == "__main__":
    build()
