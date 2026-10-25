"""Bundle the results into dashboard/data.js, so the dashboard opens from disk with no
server and no internet (a browser will not fetch() a local file).

    python dashboard/build.py
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
results = json.loads((ROOT / "results" / "results.json").read_text(encoding="utf-8"))
analogs = json.loads((ROOT / "results" / "analogs.json").read_text(encoding="utf-8"))
out = ROOT / "dashboard" / "data.js"
out.write_text("window.RESULTS = " + json.dumps(results, ensure_ascii=False) + ";\n"
               "window.ANALOGS = " + json.dumps(analogs) + ";\n", encoding="utf-8")
print(f"wrote {out.name}: {out.stat().st_size / 1024:.0f} KB")
