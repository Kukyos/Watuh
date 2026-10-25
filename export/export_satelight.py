"""Export the data this project analyses from the Satelight working copy, read only.

Satelight holds 15 years of daily satellite fields and GLORYS temperature on a 0.25 deg
grid (about 10 GB). This script reduces them to files small enough for a laptop or Colab:

  data/argo_casts.csv.gz     the 6,144 held-out Argo casts Satelight is scored on: what
                             the float measured at 15 depths, every Satelight contender's
                             prediction there, and the 8 satellite inputs at the cast's
                             cell and day
  data/cells_sample.csv.gz   a random sample of (cell, day) rows, 2010-2024: the 8
                             satellite inputs, position, sea-floor depth, and GLORYS
                             temperature at the 15 depths (the training target)
  data/ocean_states.npz      one row per day, 2010-2024: the surface state reduced by
                             PCA, the subsurface (50-200 m) on a 2.5 deg grid, and
                             Satelight's daily embedding for 2023-24 (the recommender)

Run with Satelight's own environment, which has the readers for its cube:

    G:/Projects/SIH26P4/.venv/Scripts/python.exe export/export_satelight.py

Nothing is written to the Satelight folder.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

P4 = Path(os.environ.get("SATELIGHT", "G:/Projects/SIH26P4"))
sys.path.insert(0, str(P4))
from satelight import config, data  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "data"
INPUTS = config.INPUTS                       # sst sss adt sla uc vc uw vw
DEPTHS = [int(d) for d in config.DEPTHS]
CELLS_PER_DAY = 40
SEED = 2026
SUB_LEVELS = [5, 7, 9, 10]                   # 50, 100, 150, 200 m


def split_of(day: np.datetime64) -> str:
    for name, (a, b) in config.SPLITS.items():
        if np.datetime64(a) <= day <= np.datetime64(b):
            return name
    return "gap"


def block_mean(a: np.ndarray, k: int) -> np.ndarray:
    """(T, H, W) -> (T, H/k, W/k), mean over the water cells in each block."""
    T, H, W = a.shape
    with np.errstate(invalid="ignore"), __import__("warnings").catch_warnings():
        __import__("warnings").simplefilter("ignore", RuntimeWarning)
        return np.nanmean(a.reshape(T, H // k, k, W // k, k), axis=(2, 4))


def main() -> None:
    OUT.mkdir(exist_ok=True)
    rng = np.random.default_rng(SEED)
    level_mask = np.load(config.CUBE / "levels_mask.npy")             # (15, H, W)
    sea = level_mask[0]
    with xr.open_dataset(config.CUBE / "static.nc") as s:
        bathy = s["deptho"].values
    lat2, lon2 = np.meshgrid(config.LAT, config.LON, indexing="ij")

    casts = json.loads((config.DATA / "eval-profiles.json").read_text())
    for n, c in enumerate(casts):
        c["cast_id"] = n
        c["i"] = int(np.floor((c["lon"] - config.LON_EDGES[0]) / config.RES))
        c["j"] = int(np.floor((c["lat"] - config.LAT_EDGES[0]) / config.RES))
    by_year: dict[int, list[dict]] = {}
    for c in casts:
        by_year.setdefault(int(c["day"][:4]), []).append(c)

    sample, surf_days, surf_rows, sub_rows = [], [], [], []
    glorys_check = {"compared": 0, "mismatched": 0, "max_abs_diff": 0.0}
    a0, b0 = config.WINDOW
    for year in range(a0.year, b0.year + 1):
        span = (max(a0, date(year, 1, 1)), min(b0, date(year, 12, 31)))
        x, y, t = data.load_raw("train", INPUTS, span=span)           # raw physical units
        y[:, ~level_mask] = np.nan

        # (cell, day) sample: sea cells where every input is present that day.
        ok_all = np.isfinite(x).all(axis=1) & sea[None]
        for d in range(len(t)):
            jj, ii = np.nonzero(ok_all[d])
            pick = rng.choice(jj.size, size=min(CELLS_PER_DAY, jj.size), replace=False)
            for p in pick:
                j, i = jj[p], ii[p]
                sample.append((str(t[d]), split_of(t[d]), float(lat2[j, i]), float(lon2[j, i]),
                               float(bathy[j, i]), *x[d, :, j, i].tolist(), *y[d, :, j, i].tolist()))

        # Casts: inputs at their cell and day, and the GLORYS check.
        for c in by_year.get(year, []):
            d = int(np.searchsorted(t, np.datetime64(c["day"])))
            assert t[d] == np.datetime64(c["day"]), c["day"]
            # The stored position is rounded to 3 decimals, which moves a cast lying just
            # below a cell edge onto it. Satelight placed it with the full position, so the
            # cell is the one (this or the one below) whose GLORYS matches Satelight's record.
            stored = np.array(c["pred"]["GLORYS (ceiling)"], dtype=float)
            for dj, di in ((0, 0), (-1, 0), (0, -1), (-1, -1)):
                g = y[d, :, c["j"] + dj, c["i"] + di]
                both = np.isfinite(g) & np.isfinite(stored)
                if both.any() and np.all(np.abs(g[both] - stored[both]) <= 6e-4):
                    c["j"], c["i"] = c["j"] + dj, c["i"] + di
                    glorys_check["edge_casts_moved"] = glorys_check.get("edge_casts_moved", 0) + ((dj, di) != (0, 0))
                    break
            c["inputs"] = x[d, :, c["j"], c["i"]].tolist()
            c["bathy"] = float(bathy[c["j"], c["i"]])
            g, stored = y[d, :, c["j"], c["i"]], np.array(c["pred"]["GLORYS (ceiling)"], dtype=float)
            both = np.isfinite(g) & np.isfinite(stored)
            diff = np.abs(g[both] - stored[both])
            glorys_check["compared"] += int(both.sum())
            glorys_check["mismatched"] += int((diff > 6e-4).sum())
            glorys_check["max_abs_diff"] = max(glorys_check["max_abs_diff"], float(diff.max(initial=0)))

        # Daily states for the recommender: surface at 1 deg, subsurface at 2.5 deg.
        surf_days.append(t)
        surf_rows.append(np.concatenate([block_mean(x[:, k], 4).reshape(len(t), -1)
                                         for k in range(len(INPUTS))], axis=1).astype(np.float32))
        sub_rows.append(np.concatenate([block_mean(y[:, k], 10).reshape(len(t), -1)
                                        for k in SUB_LEVELS], axis=1).astype(np.float32))
        print(year, len(t), "days,", len(sample), "sample rows so far", flush=True)
        del x, y

    # ---- cells_sample
    cols = (["day", "split", "lat", "lon", "bathy"] + INPUTS + [f"t{d}" for d in DEPTHS])
    pd.DataFrame(sample, columns=cols).to_csv(OUT / "cells_sample.csv.gz", index=False,
                                              float_format="%.4f")

    # ---- argo_casts
    rows = []
    for c in casts:
        r = {k: c[k] for k in ("cast_id", "platform", "cycle", "lat", "lon", "day", "data_mode",
                               "levels_rejected", "source_file")}
        r["bathy"] = c["bathy"]
        r.update(dict(zip(INPUTS, c["inputs"])))
        r.update({f"obs_t{d}": v for d, v in zip(DEPTHS, c["obs"])})
        for model, v in c["pred"].items():
            r.update({f"{model}|t{d}": p for d, p in zip(DEPTHS, v)})
        rows.append(r)
    pd.DataFrame(rows).to_csv(OUT / "argo_casts.csv.gz", index=False)

    # ---- ocean_states: surface PCA fitted on the train block only.
    days = np.concatenate(surf_days)
    surf, sub = np.concatenate(surf_rows), np.concatenate(sub_rows)
    train = np.array([split_of(d) == "train" for d in days])
    keep = np.isfinite(surf[train]).mean(axis=0) >= 0.99                # water columns
    surf = surf[:, keep]
    mu, sd = np.nanmean(surf[train], axis=0), np.nanstd(surf[train], axis=0)
    z = np.nan_to_num((surf - mu) / sd)
    from sklearn.decomposition import PCA
    pca = PCA(n_components=30, random_state=SEED).fit(z[train])
    surf_pcs = pca.transform(z).astype(np.float32)
    sub_keep = np.isfinite(sub).all(axis=0)
    emb_days, emb = [], []
    for yr in (2023, 2024):
        with xr.open_dataset(config.OUTPUT / "embedding" / f"hybrid_{yr}.nc") as e:
            emb_days.append(e["time"].values.astype("datetime64[D]"))
            emb.append(e["daily"].values.astype(np.float32))
    np.savez_compressed(
        OUT / "ocean_states.npz", days=days.astype(str), split=np.array([split_of(d) for d in days]),
        surface_pcs=surf_pcs, surface_explained=pca.explained_variance_ratio_.astype(np.float32),
        subsurface=sub[:, sub_keep].astype(np.float16), subsurface_levels_m=np.array([DEPTHS[k] for k in SUB_LEVELS]),
        embedding_days=np.concatenate(emb_days).astype(str), embedding=np.concatenate(emb))

    (OUT / "export_log.json").write_text(json.dumps({
        "source": "Satelight working copy, read only", "seed": SEED, "cells_per_day": CELLS_PER_DAY,
        "sample_rows": len(sample), "casts": len(casts), "days": int(days.size),
        "surface_columns_kept": int(keep.sum()), "subsurface_columns_kept": int(sub_keep.sum()),
        "glorys_check": glorys_check}, indent=1))
    print("glorys check:", glorys_check)
    assert glorys_check["compared"] > 50_000 and glorys_check["mismatched"] == 0, glorys_check


if __name__ == "__main__":
    main()
