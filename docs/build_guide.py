"""Fill the study guide's numbers from results/results.json.

The template writes a number as {{path.to.value|format}}, for example
{{regression.gap_closed_pct.North Indian Ocean.Satelight hybrid|.0f}}. Nothing in the
guide is typed by hand, so it cannot disagree with the notebooks or the dashboard.

    python docs/build_guide.py
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RES = json.loads((ROOT / "results" / "results.json").read_text(encoding="utf-8"))


def lookup(path: str):
    node = RES
    for part in path.split("."):
        node = node[int(part)] if isinstance(node, list) else node[part]
    return node


def fill(text: str) -> str:
    def sub(m):
        path, _, fmt = m.group(1).partition("|")
        v = lookup(path.strip())
        return format(v, fmt) if fmt else str(v)
    return re.sub(r"\{\{(.+?)\}\}", sub, text)


def demo() -> None:
    global RES
    keep, RES = RES, {"a": {"b c": [1.234, 5]}}
    assert fill("x {{a.b c.0|.1f}} y {{a.b c.1}}") == "x 1.2 y 5"
    RES = keep


if __name__ == "__main__":
    demo()
    src = ROOT / "docs" / "study-guide.template.md"
    out = ROOT / "docs" / "study-guide.md"
    out.write_text(fill(src.read_text(encoding="utf-8")), encoding="utf-8")
    print("wrote", out.relative_to(ROOT))
