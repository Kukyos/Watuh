# VVater: the ocean below the surface

Data Science Ecosystem (23CS2024) project. Evaluated on a presentation, a live demo and a
viva; the printed report is required but read lightly.

## The story: see it, predict it, prove it

| Act | What | Where |
|---|---|---|
| **See** | Real ocean data explored in 3D, and the data-quality story behind it | VVater viewer (`SIH26P3`, read only) |
| **Predict** | Satellites see the surface; models predict temperature down to 1,000 m | Satelight viewer (`SIH26P4`, read only) |
| **Prove** | Course methods against the deep models, statistical tests, clustering, the analog-day recommender | Results dashboard in this repo |

The presentation walks the syllabus modules in order.

| Module | Covered by |
|---|---|
| 1 Basics | Problem, data sources, toolbox |
| 2 Understanding data | Import, filter, group, missing data (land and sea floor), plots |
| 3 Statistical inference | Descriptive statistics, outliers (the 44.42 °C cells), correlation, hypothesis tests |
| 4 Machine learning | Linear, multiple, polynomial and logistic regression, KNN, decision trees, k-means, agglomerative clustering, model evaluation |
| 5 Recommender systems | Analog-day finder: content-based filtering on ocean states, evaluated |
| 6 Ethics | Provenance, QC transparency, explainability, fairness between basins |

## Decisions

- One name: **VVater**, with Satelight as its prediction engine.
- New ML uses **syllabus methods only**; the U-Net and the transformer hybrid are the
  "beyond the course" showcase.
- Same splits as Satelight: train 2010-02-04 → 2020-12-31, validation 2021-02-01 →
  2022-11-30, test 2023-01-01 → 2024-12-15. Hyperparameters are chosen on validation only.
- Every new model is scored on the **same 6,144 held-out Argo casts and the same
  (cast, depth) points** as Satelight's own table.
- Classification target: **can this ocean fuel a strong cyclone?** TCHP above a published
  threshold, from satellite surface data only.
- Clustering: Argo temperature profiles into water types, k-means against agglomerative,
  k chosen by silhouette before any comparison with basin or season labels.
- Hypothesis tests fixed before computing: two-sided, Holm-corrected across depths,
  bootstrap intervals resampled by float.
- Fairness compares skill relative to climatology, not raw RMSE.
- Recommender: surface-state PCA over 2010–2024 as the main representation, Satelight
  embeddings (2023–24) as the second; a ±30-day exclusion around each query; judged by how
  well the recommended days' subsurface matches the query day's, against random days and
  the same calendar day.
- Every number lives in `results/results.json`, written by code. The dashboard, the study
  guide and the report read from it; nothing is typed by hand.
- Dashboard works offline: static HTML, libraries vendored.
- Demo runs from the laptop, with a recorded backup video.
- SIH repositories are only read, never edited.
- Personal documents (certificate, score report, templates) stay in `private/`, untracked.
- Report and guide text written fresh.

## Build order

1. Export: Argo casts with their satellite inputs, a (cell, day) sample, surface-state
   series. Calibration: the exported casts reproduce Satelight's published RMSE, and the
   GLORYS value at each cast's cell and day matches the stored one.
2. Analysis notebooks: data quality (See), EDA and statistics, regression ladder,
   cyclone classifier, clustering, hypothesis tests and fairness, recommender.
3. Results dashboard.
4. Study guide and viva questions.
5. Report (template, certificate page).
6. Backup demo video; mock vivas.
