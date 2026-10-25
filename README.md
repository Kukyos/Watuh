# VVater: the ocean below the surface

A data science study of the North Indian Ocean: what satellites can see of the sea
surface, what lies beneath it, and how well the methods of a data science course,
and deep learning, can predict one from the other.

**See it** (data quality and exploration), **predict it** (regression and
classification), **prove it** (hypothesis tests, fairness), plus clustering of water
types and a recommender that finds days in history when the ocean looked like today.

## Contents

| Path | What |
|---|---|
| `notebooks/` | The analysis, one notebook per chapter. Each `.ipynb` is executed and keeps its outputs |
| `notebooks/src/` | The same notebooks as plain Python, which is what gets edited |
| `results/results.json` | Every number the project reports, written by the notebook that computed it |
| `figures/` | Every figure, written by the notebooks |
| `dashboard/index.html` | The results dashboard. Opens offline from disk |
| `data/` | The datasets, small enough to run anywhere |
| `export/` | How the datasets were produced from the full data |

## The chapters

1. **See**: missing data, descriptive statistics, outliers and agreement between a
   gridded ocean analysis and real instruments (Bay of Bengal, 2018).
2. **Explore**: the satellite inputs, the water column by sea and season, correlation,
   and a first hypothesis test.
3. **Predict**: simple, multiple and polynomial regression, KNN and decision trees,
   scored against held-out Argo floats beside deep learning models.
4. **Classify**: can satellite data alone tell whether the ocean holds enough heat to
   fuel a strong cyclone?
5. **Discover**: k-means and agglomerative clustering of float profiles into water
   types.
6. **Prove**: hypothesis tests with a correction for multiple comparisons, bootstrap
   confidence intervals, and fairness between the two seas.
7. **Recommend**: content-based filtering on daily ocean states, evaluated below the
   surface.

## Run it

```
pip install -r requirements.txt
python notebooks/build.py        # executes every notebook and rewrites results and figures
python dashboard/build.py        # bundles the results for the dashboard
```

Then open `dashboard/index.html` in a browser.

To run a notebook in Google Colab, start with `!git clone https://github.com/Kukyos/Watuh.git`
and `%cd Watuh/notebooks`. Notebook 03 is the slowest (about 8 minutes on an 8-core laptop, longer on Colab's two cores).

## Data

| Source | Used for |
|---|---|
| Argo floats, via the Ifremer ERDDAP server | Ground truth: temperature profiles with QC flags |
| INCOIS Argo 10-day variational analysis, via the INCOIS ERDDAP server | Gridded analysis, Bay of Bengal (chapter 1) |
| IOOS Glider DAC, glider ru29 | Independent check (chapter 1) |
| OSTIA, Multi-Observation SSS, DUACS (Copernicus Marine) | Satellite sea surface temperature, salinity, sea level |
| OSCAR (NASA PO.DAAC), CCMP v3.1 (Remote Sensing Systems) | Satellite currents and winds |
| GLORYS12 reanalysis (Copernicus Marine) | Training target and subsurface reference |

The `export/` scripts reduce about 10 GB of daily fields to the files in `data/`.
