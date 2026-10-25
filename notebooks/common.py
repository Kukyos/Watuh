"""Shared by every notebook: paths, loaders, the ocean formulas, and the results file.

Every number the dashboard, the study guide or the report shows is written here by
`record()` into results/results.json, from the notebook that computed it.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
FIGURES = ROOT / "figures"
RESULTS = ROOT / "results" / "results.json"

DEPTHS = np.array([0, 5, 10, 20, 30, 50, 75, 100, 125, 150, 200, 300, 500, 700, 1000])
INPUTS = ["sst", "sss", "adt", "sla", "uc", "vc", "uw", "vw"]
INPUT_NAMES = {
    "sst": "Sea surface temperature (°C)", "sss": "Sea surface salinity (PSU)",
    "adt": "Sea level, absolute (m)", "sla": "Sea level anomaly (m)",
    "uc": "Current, eastward (m/s)", "vc": "Current, northward (m/s)",
    "uw": "Wind, eastward (m/s)", "vw": "Wind, northward (m/s)",
}
SPLITS = {"train": ("2010-02-04", "2020-12-31"), "val": ("2021-02-01", "2022-11-30"),
          "test": ("2023-01-01", "2024-12-15")}
BASINS = {"Bay of Bengal": {"lon": (78.0, 100.0), "lat": (5.0, 23.0)},
          "Arabian Sea": {"lon": (50.0, 77.0), "lat": (5.0, 26.0)}}
TARGETS = [f"t{d}" for d in DEPTHS]
SEED = 2026

# Cyclone heat potential above which the ocean is usually able to support intensification
# (NOAA State of the Climate 2020, citing Shay et al. 2000 and Mainelli et al. 2008).
TCHP_THRESHOLD = 50.0
TCHP_T, CP0, RHO_REF = 26.0, 3991.86795711963, 1025.0

PALETTE = {"climatology": "#9aa3ad", "glorys": "#1f2a44", "deep": "#e8833a",
           "course": "#2f7fc1", "accent": "#c94f4f"}


def style() -> None:
    plt.rcParams.update({"figure.dpi": 110, "savefig.dpi": 200, "axes.spines.top": False,
                         "axes.spines.right": False, "axes.grid": True, "grid.alpha": 0.25,
                         "font.size": 10, "axes.titleweight": "bold"})


def save(fig, name: str) -> None:
    FIGURES.mkdir(exist_ok=True)
    fig.savefig(FIGURES / f"{name}.png", bbox_inches="tight")


def record(key: str, value) -> None:
    """Write one result under a dotted key, keeping everything else in the file."""
    RESULTS.parent.mkdir(exist_ok=True)
    res = json.loads(RESULTS.read_text(encoding="utf-8")) if RESULTS.exists() else {}
    node = res
    *path, last = key.split(".")
    for p in path:
        node = node.setdefault(p, {})
    node[last] = _no_nan(json.loads(json.dumps(value, default=_plain)))
    RESULTS.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")


def _no_nan(o):
    """NaN is not valid JSON for a browser: it becomes null."""
    if isinstance(o, float) and o != o:
        return None
    if isinstance(o, dict):
        return {k: _no_nan(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_no_nan(v) for v in o]
    return o


def _plain(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return round(float(o), 4)
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(type(o))


def basin_of(lon, lat) -> np.ndarray:
    lon, lat = np.asarray(lon), np.asarray(lat)
    out = np.full(lon.shape, "Other", dtype=object)
    for name, b in BASINS.items():
        inside = (lon >= b["lon"][0]) & (lon <= b["lon"][1]) & (lat >= b["lat"][0]) & (lat <= b["lat"][1])
        out[inside] = name
    return out


def load_cells() -> pd.DataFrame:
    df = pd.read_csv(DATA / "cells_sample.csv.gz", parse_dates=["day"])
    df["doy"] = df["day"].dt.dayofyear
    df["doy_sin"] = np.sin(2 * np.pi * df["doy"] / 365.25)
    df["doy_cos"] = np.cos(2 * np.pi * df["doy"] / 365.25)
    df["basin"] = basin_of(df["lon"], df["lat"])
    return df


def load_casts() -> pd.DataFrame:
    df = pd.read_csv(DATA / "argo_casts.csv.gz", parse_dates=["day"])
    df["doy"] = df["day"].dt.dayofyear
    df["doy_sin"] = np.sin(2 * np.pi * df["doy"] / 365.25)
    df["doy_cos"] = np.cos(2 * np.pi * df["doy"] / 365.25)
    df["basin"] = basin_of(df["lon"], df["lat"])
    return df


def profiles(df: pd.DataFrame, prefix: str) -> np.ndarray:
    """(rows, 15) array from columns '<prefix>t0' ... '<prefix>t1000'."""
    return df[[f"{prefix}t{d}" for d in DEPTHS]].to_numpy(dtype=float)


# ---- Ocean formulas, copied from Satelight (satelight/evaluate.py) so labels match its numbers.

def isotherm_depth(t: np.ndarray, iso: float) -> float:
    """Depth (m) where a 15-level profile first cools through `iso`; NaN if unknown."""
    z = DEPTHS
    if not np.isfinite(t[0]) or t[0] <= iso:
        return np.nan
    for k in range(z.size - 1):
        if not np.isfinite(t[k + 1]):
            return np.nan
        if t[k + 1] <= iso:
            return float(z[k] + (t[k] - iso) / (t[k] - t[k + 1]) * (z[k + 1] - z[k]))
    return np.nan


def tchp(t: np.ndarray) -> float:
    """Tropical cyclone heat potential (kJ/cm²): heat in the water above 26 °C.
    0 when the surface is at or below 26 °C; NaN when the crossing cannot be found."""
    z, a = DEPTHS, t - TCHP_T
    if not np.isfinite(a[0]):
        return np.nan
    if a[0] <= 0:
        return 0.0
    area = 0.0
    for k in range(z.size - 1):
        if not np.isfinite(a[k + 1]):
            return np.nan
        if a[k + 1] > 0:
            area += 0.5 * (a[k] + a[k + 1]) * (z[k + 1] - z[k])
        else:
            area += 0.5 * a[k] * (a[k] / (a[k] - a[k + 1])) * (z[k + 1] - z[k])
            return float(RHO_REF * CP0 * area / 1e7)
    return np.nan


def demo() -> None:
    lin = np.interp(DEPTHS, [0, 100, 1000], [30.0, 22.0, 5.0])
    assert abs(isotherm_depth(lin, 26.0) - 50.0) < 1e-9
    area = 0.5 * 4.0 * 50.0                       # triangle from 30 °C at 0 m to 26 °C at 50 m
    assert np.isclose(tchp(lin), RHO_REF * CP0 * area / 1e7)
    assert tchp(lin - 5) == 0.0 and np.isnan(tchp(np.full(15, 29.0)))
    assert list(basin_of([85, 60, 47], [15, 15, 28])) == ["Bay of Bengal", "Arabian Sea", "Other"]
    print("common ok")


if __name__ == "__main__":
    demo()
