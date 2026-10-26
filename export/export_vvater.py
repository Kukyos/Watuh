"""Export VVater's Bay of Bengal data (August 2018) to plain CSV files, read only.

  data/vvater_incois_analysis.csv.gz   INCOIS Argo 10-day variational analysis, Bay of
                                       Bengal, 2018-07-01 to 2018-10-31: temperature and
                                       its error estimate (TERR) at every grid cell, depth
                                       and analysis step, land and sea floor included as
                                       empty values
  data/vvater_argo.csv.gz              every Argo level VVater fetched from the Ifremer
                                       ERDDAP for the region, with its QC flag and data mode
  data/vvater_glider.csv.gz            glider ru29 (IOOS Glider DAC), Bay of Bengal, August 2018

Set VVATER to the VVater folder and run with any environment that has xarray:

    python export/export_vvater.py
"""

import os
from pathlib import Path

import pandas as pd
import xarray as xr

P3 = Path(os.environ["VVATER"]) / "data" / "cache"
OUT = Path(__file__).resolve().parents[1] / "data"


def main() -> None:
    OUT.mkdir(exist_ok=True)
    with xr.open_dataset(P3 / "incois_argo_10d_VAM_TEMP-TERR_2018-07-01_2018-10-31.nc") as ds:
        df = ds.to_dataframe().reset_index()
    df.to_csv(OUT / "vvater_incois_analysis.csv.gz", index=False, float_format="%.4f")
    print("incois", df.shape, list(df.columns))

    parts = [pd.read_csv(f, skiprows=[1]) for f in sorted((P3 / "argo_erddap").glob("*.csv"))]
    argo = pd.concat(parts).drop_duplicates(["platform_number", "cycle_number", "pres"])
    argo.to_csv(OUT / "vvater_argo.csv.gz", index=False)
    print("argo", argo.shape, argo["time"].min(), argo["time"].max())

    glider = pd.read_csv(P3 / "glider_ru29-20180812T0220_bob.csv", skiprows=[1])
    glider.to_csv(OUT / "vvater_glider.csv.gz", index=False)
    print("glider", glider.shape)


if __name__ == "__main__":
    main()
