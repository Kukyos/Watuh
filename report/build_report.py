"""Fill the college report template with the project report.

Reads the template and the certificate from private/ (not in the repository), every
number from results/results.json, and the figures from figures/. One copy per team
member, each with that member on the cover, certificate page and marks sheet:

    python report/build_report.py           # private/VVater_DSE_Report.docx (Armaan)
    python report/build_report.py jerem     # private/VVater_DSE_Report_Jerem.docx
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / "private"
FIG = ROOT / "figures"
ASSETS = ROOT / "report" / "assets"
R = json.loads((ROOT / "results" / "results.json").read_text(encoding="utf-8"))
EXPORT = json.loads((ROOT / "data" / "export_log.json").read_text(encoding="utf-8"))

# (name, register number, certificate image in private/report_assets, output file)
MEMBERS = {
    "armaan": ("A MOHAMED ARMAAN", "URK24CS1021", "certificate.png", "VVater_DSE_Report.docx"),
    "jerem": ("JEREM AGSAE JEBAZ", "URK24CS1030", "certificate_jerem.png", "VVater_DSE_Report_Jerem.docx"),
}
STUDENT, REG_NO, CERTIFICATE, OUT_NAME = MEMBERS[sys.argv[1] if len(sys.argv) > 1 else "armaan"]
TEAM = [(n, r) for n, r, _, _ in MEMBERS.values()]
HEADING_TITLES = {"INTRODUCTION", "LITERATURE REVIEW", "SYSTEM DESIGN", "IMPLEMENTATION", "TESTING AND VALIDATION",
                  "RESULTS AND DISCUSSION", "ABSTRACT", "CONCLUSION", "REFERENCES", "APPENDICES"}
TITLE = "VVater: Seeing the Ocean Below the Surface"
SUBTITLE = "A data science study of predicting subsurface ocean temperature from satellite observations in the North Indian Ocean"
FONT = "Times New Roman"

reg, gap, summ = R["regression"], R["regression"]["gap_closed_pct"], R["regression"]["argo_summary"]
NIO, BAY, ARA = "North Indian Ocean", "Bay of Bengal", "Arabian Sea"
f2 = lambda v: f"{v:.2f}"
f3 = lambda v: f"{v:.3f}"


# ------------------------------------------------------------------ low-level helpers

def set_font(run, size=12, bold=False, italic=False):
    run.font.name = FONT
    run._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    run.font.size = Pt(size)
    run.bold, run.italic = bold, italic


def delete(p):
    p._element.getparent().remove(p._element)


def set_text(p, text, size=None, bold=None):
    """Replace a paragraph's visible text, keeping page-break runs and the first run's look."""
    runs = [r for r in p.runs if r.text.strip()]
    if not runs:
        runs = [p.add_run()]
    runs[0].text = text
    for r in runs[1:]:
        r.text = ""
    if size or bold is not None:
        set_font(runs[0], size or 12, bold=bool(bold))


class Writer:
    """Writes content in order, immediately before an anchor paragraph."""

    def __init__(self, doc, anchor, chapter, bullet_numpr):
        self.doc, self.anchor, self.ch, self.numpr = doc, anchor, chapter, bullet_numpr
        self.fig = self.tab = 0

    def _p(self, align=WD_ALIGN_PARAGRAPH.JUSTIFY, after=6, line=1.5, before=0):
        p = self.anchor.insert_paragraph_before()
        p.style = self.doc.styles["Normal"]
        pf = p.paragraph_format
        pf.alignment, pf.space_after, pf.space_before, pf.line_spacing = align, Pt(after), Pt(before), line
        return p

    def h(self, text):
        p = self._p(align=WD_ALIGN_PARAGRAPH.LEFT, before=12, after=6, line=1.15)
        p.paragraph_format.keep_with_next = True
        set_font(p.add_run(text), 13, bold=True)

    def para(self, text):
        p = self._p()
        for i, part in enumerate(text.split("**")):        # **bold** inline
            if part:
                set_font(p.add_run(part), 12, bold=bool(i % 2))

    def bullets(self, items):
        for text in items:
            p = self._p(after=3, line=1.3)
            p.style = self.doc.styles["List Paragraph"]
            p._p.get_or_add_pPr().insert(0, copy.deepcopy(self.numpr))
            p.paragraph_format.left_indent, p.paragraph_format.first_line_indent = Cm(0.9), Cm(-0.5)
            for i, part in enumerate(text.split("**")):
                if part:
                    set_font(p.add_run(part), 12, bold=bool(i % 2))

    def code(self, text):
        for line in text.strip("\n").split("\n"):
            p = self._p(align=WD_ALIGN_PARAGRAPH.LEFT, after=0, line=1.0)
            r = p.add_run(line if line else " ")
            r.font.name = "Consolas"; r.font.size = Pt(9.5)

    def figure(self, path, caption, width=15.5):
        self.fig += 1
        p = self._p(align=WD_ALIGN_PARAGRAPH.CENTER, before=6, after=2, line=1.0)
        p.paragraph_format.keep_with_next = True
        p.add_run().add_picture(str(path), width=Cm(width))
        c = self._p(align=WD_ALIGN_PARAGRAPH.CENTER, after=10, line=1.0)
        set_font(c.add_run(f"Figure {self.ch}.{self.fig}: {caption}"), 10.5, italic=True)

    def table(self, header, rows, caption, widths=None):
        self.tab += 1
        c = self._p(align=WD_ALIGN_PARAGRAPH.CENTER, before=6, after=4, line=1.0)
        c.paragraph_format.keep_with_next = True
        set_font(c.add_run(f"Table {self.ch}.{self.tab}: {caption}"), 10.5, italic=True)
        t = self.doc.add_table(rows=1 + len(rows), cols=len(header))
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        borders = OxmlElement("w:tblBorders")
        for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
            e = OxmlElement(f"w:{edge}")
            e.set(qn("w:val"), "single"); e.set(qn("w:sz"), "4"); e.set(qn("w:color"), "808080")
            borders.append(e)
        t._tbl.tblPr.append(borders)
        for i, row in enumerate([header] + rows):
            for j, val in enumerate(row):
                cell = t.cell(i, j)
                if widths:
                    cell.width = Cm(widths[j])
                p = cell.paragraphs[0]
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT if j == 0 else WD_ALIGN_PARAGRAPH.CENTER
                set_font(p.add_run(str(val)), 10.5, bold=(i == 0))
                if i == 0:
                    shd = OxmlElement("w:shd"); shd.set(qn("w:val"), "clear"); shd.set(qn("w:fill"), "E8EEF4")
                    cell._tc.get_or_add_tcPr().append(shd)
        for i, row in enumerate(t.rows):
            trpr = row._tr.get_or_add_trPr()
            trpr.append(OxmlElement("w:cantSplit"))
            if i == 0:
                trpr.append(OxmlElement("w:tblHeader"))
            if i < len(t.rows) - 1:
                for cell in row.cells:
                    for cp in cell.paragraphs:
                        cp.paragraph_format.keep_with_next = True
        self.anchor._p.addprevious(t._tbl)
        self._p(after=4, line=1.0)


# ------------------------------------------------------------------ the content

def abstract(w):
    w.para(f"Satellites observe the ocean surface every day, but the heat that fuels tropical cyclones is stored "
           f"tens to hundreds of metres below it, where no satellite can see. This project is a data science study of "
           f"how well that hidden temperature, from the surface down to 1,000 m, can be predicted from satellite "
           f"surface observations over the North Indian Ocean (45–105°E, 5–30°N).")
    w.para(f"The data were collected by script from public ocean data servers: satellite sea surface temperature, "
           f"salinity, sea level, currents and winds for 2010–2024, the GLORYS12 reanalysis as the training target, and "
           f"{R['prove']['paper_trail']['casts']:,} temperature profiles from {R['prove']['floats']} Argo floats as an independent test set. "
           f"The project follows the full data science workflow: a data-quality audit, exploratory analysis and "
           f"hypothesis testing, supervised regression and classification, unsupervised clustering, a content-based "
           f"recommender, and an ethics review covering transparency, explainability and fairness.")
    w.para(f"Five regression methods from the course (simple, multiple and polynomial regression, KNN and decision "
           f"trees) were compared with a deep learning model (a CNN and transformer hybrid) on exactly the same held-out "
           f"floats. A cubic polynomial regression closed {gap[NIO]['Polynomial']:.0f}% of the gap between climatology and the "
           f"reanalysis, level with the deep model ({gap[NIO]['Satelight hybrid']:.0f}%); after correcting for multiple "
           f"comparisons, the two could not be told apart at 14 of 15 depths. A classifier for cyclone-supporting ocean "
           f"heat reached an F1 score of {R['classify']['test']['KNN']['F1']:.2f} from satellite inputs alone, and the analog-day "
           f"recommender returned days whose subsurface matched the query day better than the same date in another "
           f"year on {R['recommend']['beats_calendar_pct_of_days']:.0f}% of days.")
    w.para("Key features: an interactive offline results dashboard; two 3D viewers for the ocean data and the "
           "predictions; executed notebooks for every analysis; and a single results file from which every number in "
           "this report, the dashboard and the study guide is read.")


def chapter1(w):
    w.h("1.1 Background")
    w.para("The North Indian Ocean produces some of the most destructive tropical cyclones on Earth. Whether a cyclone "
           "intensifies depends strongly on the ocean beneath it: a thick layer of water warmer than 26 °C is a "
           "reservoir of energy the storm can draw on, while a thin warm layer is quickly churned up and cooled. "
           "Forecasters therefore need to know the temperature of the upper few hundred metres of the ocean, not only "
           "its surface.")
    w.para("Satellites measure the sea surface daily and globally, but their signals do not penetrate the water. "
           "Below the surface the main source of measurements is the Argo array: robotic floats that drift at depth and "
           "rise every ten days, recording a temperature profile on the way up [3]. Argo is invaluable but sparse: "
           "each float samples one point every ten days. Ocean reanalyses such as GLORYS12 [4] fill the gaps by "
           "combining a physical ocean model with all available observations, at a large computational cost and "
           "with a delay.")
    w.h("1.2 Problem statement and motivation")
    w.para("**Problem.** Given only what satellites observe at the sea surface on a given day, estimate the temperature "
           "of the ocean at 15 standard depths from 0 to 1,000 m, for every 0.25° patch of the North Indian Ocean, and "
           "measure how accurate that estimate is against real floats it has never seen.")
    w.para("**Motivation.** A fast, data-driven estimate of the subsurface from satellite data alone could support "
           "cyclone forecasting, fisheries and ocean monitoring wherever floats are absent. Just as important, the "
           "question is a natural test of the data science toolkit: the relationship between the surface and the deep "
           "ocean is non-linear, the data are messy, and an honest evaluation needs careful statistics.")
    w.h("1.3 Objectives")
    w.bullets(["Audit the raw ocean data for missing values, impossible values and disagreement between sources.",
               "Explore the relationship between surface observations and subsurface temperature with descriptive "
               "statistics, correlation and hypothesis tests.",
               "Predict temperature at 15 depths with the regression methods of the course, and compare them with a "
               "deep learning model on the same held-out Argo measurements.",
               "Classify whether the ocean holds enough heat to support a strong cyclone.",
               "Discover natural water types in the float profiles by clustering.",
               "Build and evaluate a recommender that finds past days whose ocean resembled a given day.",
               "Test whether the observed differences are statistically real and whether the model is fair to both seas."])
    w.h("1.4 Overview of the concepts used")
    w.para("The project applies every module of the Data Science Ecosystem course to one real problem. Table 1.1 "
           "maps each module to where it is used.")
    w.table(["Course module", "Concepts", "Where used"],
            [["1 Basics of data science", "Data repositories, toolboxes", "Data acquisition from ERDDAP, Copernicus and NASA servers; Python, pandas, scikit-learn"],
             ["2 Understanding data", "Import, select, filter, group, rank, missing data, plots", "Chapter 4 (data quality, exploration)"],
             ["3 Statistical inference", "Descriptive statistics, correlation, estimation, hypothesis testing", "Data audit, salinity t-test, model significance tests"],
             ["4 Machine learning", "Linear, multiple, polynomial, logistic regression; KNN; decision trees; k-means; agglomerative clustering; evaluation", "Regression, cyclone-fuel classifier, water types"],
             ["5 Recommender systems", "Content-based filtering, similarity, evaluation", "Analog-day recommender"],
             ["6 Ethics", "Transparency, explainability, bias and fairness, accountability", "QC provenance, feature importance, fairness by sea"]],
            "Course modules and where each is applied", widths=[3.6, 5.6, 6.3])


def chapter2(w):
    w.h("2.1 Observing the subsurface ocean")
    w.para("The Argo programme has collected more than two million temperature and salinity profiles since 1999, with "
           "temperature accurate to about 0.002 °C after delayed-mode quality control [3]. Every measurement carries a "
           "quality-control flag and a data mode (real-time, adjusted, or delayed-mode checked by a scientist), which "
           "this project uses throughout. Reanalyses such as GLORYS12 [4] assimilate Argo profiles, satellite sea level "
           "and sea surface temperature into a 1/12° ocean model, producing a complete daily 3D ocean from 1993.")
    w.h("2.2 Reconstructing the subsurface from satellite data")
    w.para("Estimating the interior ocean from surface observations has a long history. Guinehut et al. [5] derived "
           "synthetic temperature profiles from satellite sea level and sea surface temperature with multiple linear "
           "regression, then merged them with Argo profiles by optimal interpolation; this became the ARMOR3D product. "
           "Su et al. [6] used geographically weighted regression, letting the regression coefficients vary from place "
           "to place. More recently, deep neural networks have been trained on multi-source satellite data to "
           "reconstruct subsurface temperature and salinity anomalies at high resolution [7]. A common thread is that "
           "sea level carries the strongest information about the interior, because a warmer water column expands "
           "and raises the sea surface.")
    w.h("2.3 Ocean heat and cyclones")
    w.para("Leipper and Volgenau [8] defined the tropical cyclone heat potential (TCHP) as the heat stored in water "
           "warmer than 26 °C. Shay et al. [9] showed the effect of a warm ocean feature on the rapid intensification "
           "of Hurricane Opal, and Mainelli et al. [10] brought ocean heat content into operational intensity "
           "forecasting. Values above about 50 kJ/cm² are associated with intensification when the atmosphere is also "
           "favourable [11]; this project uses that threshold as its classification target.")
    w.h("2.4 Methods")
    w.para("The supervised methods (linear and polynomial regression, KNN, decision trees [22], logistic regression) "
           "and clustering methods (k-means, Ward's agglomerative clustering [21]) follow the course textbook [1] and "
           "are implemented with scikit-learn [17]. Clusters are assessed with the silhouette score [15] and compared "
           "with labels by the adjusted Rand index [16]. Significance testing uses the bootstrap [14] and Holm's "
           "correction for multiple comparisons [13]. The recommender applies the idea of analog forecasting [12], "
           "finding past states similar to the present, as content-based filtering. The ethics review follows the "
           "course's ethics textbook [2].")
    w.h("2.5 Comparison with existing solutions")
    w.table(["Approach", "Inputs", "Method", "Limitation addressed here"],
            [["ARMOR3D [5]", "Satellite + Argo", "Multiple linear regression + optimal interpolation", "Linear; this project tests non-linear methods on the same idea"],
             ["Su et al. [6]", "Satellite", "Geographically weighted regression", "Global focus; here a regional test against held-out floats"],
             ["Deep networks [7]", "Satellite", "Deep neural network", "Rarely compared with simple methods on identical test points"],
             ["GLORYS12 [4]", "Model + all observations", "Data assimilation", "Expensive and delayed; used here as the ceiling"],
             ["This project", "Satellite only", "Course methods vs deep learning, with significance tests", "Same held-out floats for every method; fairness by sea"]],
            "Related approaches compared with this project", widths=[2.8, 2.9, 4.6, 5.2])


def chapter3(w):
    w.h("3.1 Architecture")
    w.para("Figure 3.1 shows the architecture. Three families of public data sources feed an acquisition layer that "
           "regrids everything onto one 0.25° grid as daily files (about 10 GB). Two interactive 3D viewers are built on "
           "this layer: VVater, which shows the ocean data and the instruments together, and Satelight, which shows the "
           "deep-learning prediction. An export step reduces the full data to small files for analysis. Seven notebooks "
           "carry out the analysis and write every result into one file, results.json, from which the dashboard, this "
           "report and the study guide are produced.")
    w.figure(ASSETS / "architecture.png", "System architecture")
    w.h("3.2 Analysis flow")
    w.para("Figure 3.2 shows the order in which the analysis runs. The central design decision is the split by time: "
           "models learn from 2010–2020, their settings are chosen on 2021–2022, and they are tested once on 2023–2024. "
           "A random split would let a model see a day in training and be tested on the almost identical next day, "
           "a form of data leakage that inflates scores.")
    w.figure(ASSETS / "flow.png", "Analysis flow from cleaning to statistical proof")
    w.h("3.3 The product and how it is used")
    w.para("The product is presented in three steps that mirror the project's question. First, see: the VVater viewer "
           "lifts a box of ocean out as a 3D block that can be cut open, with real Argo floats standing inside it, each "
           "carrying its quality flags (Figure 3.3). Second, predict: the Satelight viewer shows the eight satellite "
           "fields for a day and the temperature reconstructed beneath them, with held-out floats inside the cube for "
           "comparison (Figure 3.4). Third, prove: the results dashboard (Figure 3.5) presents the evidence from every "
           "analysis, interactively and offline.")
    w.figure(Path("C:/Users/Cleo/Desktop/SIH26P3/docs/img/shot-hero.png"), "VVater: the Bay of Bengal cut open to 1,000 m, with Argo floats inside")
    w.figure(Path("G:/Projects/SIH26P4/submission/figures/readme-hero.jpg"), "Satelight: satellite inputs, the reconstructed ocean, and a float profile compared")
    w.figure(PRIVATE / "report_assets" / "dashboard.png", "The results dashboard: error at every depth for every method")


def chapter4(w):
    s = R["see"]
    w.h("4.1 Data acquisition")
    w.para("All data were collected by script from public servers, without manual downloads. Argo profiles were "
           "requested from the Ifremer ERDDAP server and the INCOIS gridded analysis from the INCOIS ERDDAP server, both "
           "as region-and-time queries returning CSV or NetCDF. Satellite fields and the GLORYS12 reanalysis were read "
           "from the Copernicus Marine cloud stores, and currents and winds from NASA PO.DAAC by server-side subsetting "
           "(OPeNDAP), so that only the study region was transferred. Table 4.1 lists the datasets used for analysis.")
    w.table(["File", "Rows", "Contents"],
            [["argo_casts", f"{R['prove']['paper_trail']['casts']:,}", "Held-out Argo casts 2023–24: measured temperature at 15 depths, satellite inputs, every model's prediction"],
             ["cells_sample", f"{EXPORT['sample_rows']:,}", "Random (patch, day) rows 2010–24: 8 satellite inputs, position, sea-floor depth, GLORYS temperature at 15 depths"],
             ["ocean_states", f"{R['recommend']['days']:,}", "One row per day: surface state (30 principal components), subsurface field, learned embedding"],
             ["vvater_*", "about 200,000", "INCOIS analysis, Argo levels and glider profiles, Bay of Bengal, July–October 2018"]],
            "Datasets used in the analysis", widths=[2.8, 2.4, 10.3])
    w.h("4.2 Data cleaning and quality audit")
    w.para(f"The INCOIS analysis grid was {s['missing_share_pct']}% empty. Mapping the empty cells showed they were land and sea "
           f"floor: structurally missing values that must not be imputed. On import, the Argo quality-flag column was "
           f"found to mix numbers and text, so the same flag was counted twice; it was converted to numbers before use. "
           f"Adjusted temperatures were used where available, and only levels flagged good or probably good were kept, "
           f"with rejected levels counted ({s['argo']['levels_rejected']} of {s['argo']['levels_in_box']:,}, {s['argo']['rejected_pct']}%).")
    w.para(f"Two outlier rules were compared. The box-plot rule (1.5 × IQR) flagged {s['outliers']['iqr_flagged']:,} of "
           f"{s['outliers']['cells_checked']:,} cells, most of them genuine variation in the thermocline. The published Argo global "
           f"range test (−2.5 to 40 °C) flagged {s['outliers']['range_test_failed']} cells, up to {s['outliers']['max_temp']:.2f} °C at "
           f"{s['outliers']['max_temp_depth_m']:.0f} m: physically impossible values in an official product (Figure 4.1).")
    w.figure(FIG / "see_outliers.png", "Outliers in the INCOIS analysis between 50 and 150 m", 13.5)
    w.h("4.3 Exploratory analysis")
    e = R["explore"]
    w.para(f"Correlation analysis (Figure 4.2) shows what a satellite can and cannot see. Sea surface temperature "
           f"correlates with the temperature at 0 m (r = {e['corr']['sst']['0']:.2f}), but not at all by 125 m. The sea level anomaly "
           f"correlates weakly with the surface but strongly with the thermocline (r = {e['corr']['sla']['100']:.2f} at 100 m), "
           f"because a thicker warm layer raises the sea surface. Salinity correlates with deep temperature "
           f"(r = {e['corr']['sss']['700']:.2f} at 700 m) only through geography, an instance of correlation without causation.")
    w.figure(FIG / "explore_corr_heatmap.png", "Correlation between each surface input and the temperature at each depth")
    st = e["salinity_test"]
    w.para(f"A first hypothesis test asked whether the Bay of Bengal and the Arabian Sea have the same mean surface "
           f"salinity. Because patches sampled on the same day are not independent, each sea was reduced to one mean per "
           f"day and the seas were compared with a paired t-test over {st['days']:,} days. The Arabian Sea was saltier by "
           f"{st['diff']:.2f} PSU (95% CI {st['ci95'][0]:.2f} to {st['ci95'][1]:.2f}), so the null hypothesis was rejected.")
    w.h("4.4 Regression")
    ch = reg["chosen"]
    w.para(f"Each method predicts the temperature at 15 depths from 13 inputs: the 8 satellite fields, latitude, "
           f"longitude, the logarithm of sea-floor depth, and the day of the year as a sine and cosine pair (so that "
           f"31 December lies next to 1 January). Inputs were standardised with training-year statistics. Settings were "
           f"chosen on the validation years only: polynomial degree {ch['polynomial']}, k = {ch['knn']} for KNN and a maximum depth "
           f"of {ch['tree']} for the decision tree (Figure 4.3).")
    w.figure(FIG / "regression_tuning.png", "Choosing each method's setting on the validation years 2021–2022")
    w.para("A KNN prediction for every depth needs the same neighbours, because neighbours depend only on the inputs. "
           "The implementation therefore searches once and averages the neighbours' temperatures at each depth, "
           "skipping neighbours with no water at that depth (so near the coast fewer than k may be averaged at deep levels):")
    w.code('''
def average(self, dist, idx):
    w = (1 / np.maximum(dist, 1e-9))[..., None]    # closer neighbours count more
    y = self.Y[idx]                                 # (rows, k, 15 depths)
    ok = np.isfinite(y)                             # skip neighbours without water there
    return (np.where(ok, y, 0) * w).sum(1) / (ok * w).sum(1)''')
    w.h("4.5 Classification, clustering and the recommender")
    w.para(f"For classification, each profile's TCHP was computed by integrating the heat above 26 °C, and labelled "
           f"'fuel' when it reached {50} kJ/cm². Logistic regression, KNN and a decision tree were trained on GLORYS "
           f"labels (2010–2020) and tested on labels measured by the floats themselves. For clustering, "
           f"{R['cluster']['profiles_used']:,} complete float profiles (0–700 m) were grouped by Euclidean distance with k-means and "
           f"Ward's agglomerative clustering, with k chosen by the silhouette score before any comparison with labels. "
           f"For the recommender, each day's satellite picture was compressed by PCA into {R['recommend']['pcs']} numbers "
           f"({R['recommend']['pcs_explained_pct']}% of the variance), and days were compared by cosine similarity.")
    w.h("4.6 Statistical tests")
    w.para("Differences between models were tested depth by depth with a paired t-test on per-float mean squared "
           "errors, two-sided, at α = 0.05 after Holm's correction for 15 tests. Confidence intervals came from 2,000 "
           "bootstrap resamples of whole floats. The float, not the single measurement, is the unit of evidence, "
           "because successive measurements from one drifting float are not independent.")
    w.code('''
def holm(p):
    order, m, running, adj = np.argsort(p), len(p), 0.0, np.empty(len(p))
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * p[i]))
        adj[i] = running
    return adj''')


def chapter5(w):
    pts = reg["argo_points"]
    w.h("5.1 Testing approach")
    w.para("Testing had three layers. First, calibration checks proved that the exported data and the scoring code "
           "reproduce the published scores of the deep learning model exactly, so any difference between methods comes "
           "from the methods. Second, every module that contains non-trivial logic carries a runnable self-check. "
           "Third, the models were validated against an independent truth: Argo floats from 2023–2024 that no model "
           "saw in training or tuning.")
    w.h("5.2 Test cases and results")
    w.table(["ID", "Test", "Expected", "Result"],
            [["T1", "Recompute the published RMSE from the stored casts (climatology and deep model, 0 m and 1,000 m)", "0.869, 0.543, 0.308, 0.328 °C", "Matched exactly"],
             ["T2", "GLORYS value at each cast's cell and day equals the stored value", "No mismatch", f"{EXPORT['glorys_check']['mismatched']} mismatches in {EXPORT['glorys_check']['compared']:,} values ({EXPORT['glorys_check']['edge_casts_moved']} edge casts reassigned)"],
             ["T3", "Every course model predicts every scored point", "0 unpredicted", f"0 unpredicted of {pts:,}"],
             ["T4", "Heat potential and isotherm formulas on known profiles", "Analytic values", "Pass (self-check)"],
             ["T5", "Self-checks: basin assignment, guide number filling, results file stays valid JSON for a browser (no NaN)", "Pass", "Pass"],
             ["T6", "Test years never used in training or tuning", "By construction", "Split by date; tuning on 2021–22 only"],
             ["T7", "Dashboard opens offline and every figure reads results.json", "No missing value", "Verified by rendering"]],
            "Test cases and results", widths=[1.0, 7.0, 3.5, 4.0])
    w.h("5.3 Validation against the requirements")
    w.para(f"Each objective in Section 1.3 has a measurable outcome: prediction on {pts:,} measurements at 15 depths "
           f"from {R['prove']['floats']} floats, classification on {R['classify']['casts_labelled']:,} measured heat "
           f"potentials, the recommender on every day of 2023–2024 against two baselines, and the statistical claims "
           f"with corrected tests and confidence intervals. T2 found one defect: casts exactly on a grid-cell edge had "
           f"been placed in the neighbouring cell. Each is now assigned to the cell whose reanalysis value matches.")


def chapter6(w):
    A, B = R["prove"]["test_A"], R["prove"]["test_B"]
    better_a = sum(1 for r in A if r["verdict"].startswith("Satelight"))
    tie_b = sum(1 for r in B if r["verdict"] == "no significant difference")
    w.h("6.1 Prediction accuracy")
    rows = []
    for k in ["Climatology (floor)", "Simple linear (SST only)", "Multiple linear", "Polynomial", "KNN", "Decision tree",
              "Satelight per-cell ridge", "Satelight U-Net", "Satelight hybrid", "GLORYS (ceiling)"]:
        rows.append([k, f3(summ[NIO][k]), f3(summ[BAY][k]), f3(summ[ARA][k]), f"{gap[NIO][k]:.0f}%"])
    w.table(["Method", "RMSE whole box (°C)", "Bay of Bengal", "Arabian Sea", "Gap closed"], rows,
            f"Mean RMSE over 15 depths against held-out Argo floats, 2023–2024 ({reg['argo_points']:,} measurements)",
            widths=[4.8, 2.8, 2.6, 2.6, 2.4])
    w.figure(FIG / "regression_rmse_by_depth.png", "Error at every depth for every method, by region")
    fa = reg["facts"]
    w.para(f"Five findings stand out. At the surface the simplest model wins: a straight line from sea surface "
           f"temperature scores {fa['simple_linear_0m']:.2f} °C at 0 m, better even than the reanalysis, because the satellite "
           f"measures that very layer; by 50 m it is the worst model ({fa['simple_linear_50m']:.2f} °C). Straight lines "
           f"are not enough below the surface: multiple linear regression closes only {gap[NIO]['Multiple linear']:.0f}% of the gap. "
           f"Methods that can bend do far better, and the cubic polynomial is level with the deep model on average "
           f"({fa['best_course_mean']:.3f} against {fa['satelight_mean']:.3f} °C); the deep model is better in the Bay of Bengal and the "
           f"polynomial in the Arabian Sea. Permutation importance shows the models relying most on sea level near the "
           f"top. Finally, every method, the reanalysis included, has its largest error in the thermocline near 100 m.")
    w.h("6.2 Are the differences real?")
    w.para(f"Against climatology, the deep model is significantly better at {better_a} of 15 depths (0–200 m), shows no "
           f"significant difference at 300–700 m, and is significantly worse at 1,000 m. Against the cubic polynomial, "
           f"the two cannot be told apart at {tie_b} of 15 depths; the polynomial is significantly better at 0 m "
           f"(Figure 6.2). The deep model's advantage over the best course method is therefore not statistically "
           f"supported on these floats.")
    w.figure(FIG / "prove_tests.png", "RMSE differences with 95% bootstrap confidence intervals; filled points are significant after Holm correction")
    rep = R["prove"]["representation"]
    w.para(f"Fairness was assessed with skill relative to climatology, because the Bay of Bengal's sharp thermocline "
           f"makes every method's raw error larger there. The deep model's skill is higher in the Bay of Bengal than in "
           f"the Arabian Sea, even though the Bay contributed fewer floats ({rep[BAY]['floats']} against {rep[ARA]['floats']}).")
    w.figure(FIG / "prove_fairness.png", "Skill against climatology in each sea")
    c = R["classify"]["test"]
    w.h("6.3 Cyclone-fuel classification")
    w.table(["Method", "Accuracy", "Precision", "Recall", "F1", "ROC AUC"],
            [[k, f3(v["accuracy"]), f3(v["precision"]), f3(v["recall"]), f3(v["F1"]), f3(v["ROC AUC"])] for k, v in c.items()] +
            [["Always 'fuel' (baseline)", f3(R["classify"]["majority_baseline"]["accuracy"]), f3(R["classify"]["majority_baseline"]["precision"]), "1.000",
              f3(R["classify"]["majority_baseline"]["F1"]), "–"]],
            "Classifying ocean heat potential of at least 50 kJ/cm² on held-out floats", widths=[4.6, 2.0, 2.0, 2.0, 1.8, 2.0])
    w.para(f"All three course classifiers reach an F1 near 0.89 and a ROC AUC near 0.96, well above the majority-class "
           f"baseline. Computing the heat potential from the deep model's full profile does slightly better "
           f"(F1 {c['Satelight hybrid → TCHP']['F1']:.3f}). Climatology has the weakest recall ({c['Climatology → TCHP']['recall']:.3f}): the long-term "
           f"average misses unusually warm days, which are precisely the dangerous ones.")
    w.figure(FIG / "classify_roc_pr.png", "ROC and precision–recall curves for every classifier")
    cl = R["cluster"]
    w.h("6.4 Water types")
    w.para(f"The silhouette score selected k = {cl['k']}. The water types do not split cleanly by sea (adjusted Rand index "
           f"{cl['match']['basin']['ARI']:.2f}, against {cl['match']['shuffled control (basin)']['ARI']:.3f} for shuffled labels), but they are far from "
           f"random: {cl['by_basin_pct'][BAY]['0']:.0f}% of Bay of Bengal floats fall in one cluster, and another holds "
           f"{cl['by_basin_pct'][ARA]['2']:.0f}% of Arabian Sea floats and none from the Bay. Season explains almost nothing "
           f"(ARI {cl['match']['season']['ARI']:.2f}). k-means and agglomerative clustering agree at an ARI of {cl['methods']['ari_kmeans_vs_agglomerative']:.2f}.")
    w.figure(FIG / "cluster_profiles_map.png", "Mean profile of each k-means water type and where its floats were")
    ev = R["recommend"]["evaluation"]
    key = "Subsurface RMSE of recommended days (°C)"
    w.h("6.5 Analog-day recommender")
    w.para(f"Days recommended by surface similarity were {ev[0][key]:.2f} °C from the query day below the surface, against "
           f"{ev[1][key]:.2f} °C for the same date in another year and {ev[2][key]:.2f} °C for a random day; the best possible was "
           f"{ev[0]['Best possible (oracle) RMSE (°C)']:.2f} °C. Precision@5 was {ev[0]['Precision@5']:.0%} against {ev[2]['Precision@5']:.0%} by chance. "
           f"Within 2023–2024, the plain PCA description recommended better than the deep model's learned embedding. "
           f"For the formation day of Cyclone Mocha (9 May 2023), one recommended analog was 6 May 2020, ten days before "
           f"Cyclone Amphan formed in the same sea.")
    w.figure(FIG / "recommend_over_time.png", "How similar the recommended days are below the surface, 2023–2024")
    w.h("6.6 Challenges")
    w.bullets(["**Data at scale.** About 10 GB of daily fields were reduced to small, faithful samples so that every "
               "analysis runs on a laptop or in Colab.",
               "**A silent placement error.** Rounded positions moved casts on cell edges into the wrong cell; it was "
               "found only because the export compares every value with the published record.",
               "**Computation time.** KNN with one model per depth took hours; recognising that the neighbours do not "
               "depend on the depth cut the search to one per query.",
               "**Statistics that overstate.** Thousands of correlated measurements make every difference look "
               "significant; testing per float with a multiple-comparison correction gave honest answers.",
               "**Reporting results that disagree with the hypothesis.** The clusters did not separate the two seas "
               "cleanly and the deep model did not beat the polynomial; both are reported as found."])


def conclusion(w):
    w.h("Summary")
    w.para("This project asked how far down a satellite can see. Using the full data science workflow on real ocean "
           "data, it found that satellite observations predict the upper ocean measurably better than the long-term "
           f"average down to about 200 m, and that a cubic polynomial regression from the course is statistically "
           f"indistinguishable from a deep learning model at {sum(1 for r in R['prove']['test_B'] if r['verdict'] == 'no significant difference')} of 15 depths.")
    w.h("Achievements")
    w.bullets(["Every course module applied to one real problem, with every number traceable to the code that produced it.",
               "A fair comparison of course methods and deep learning on identical held-out measurements, with corrected significance tests.",
               "A cyclone-fuel classifier, a water-type clustering and an evaluated recommender built on the same data.",
               "An offline interactive dashboard and two 3D viewers presenting the results."])
    w.h("Limitations")
    w.bullets(["The training target, GLORYS12, is itself a model and inherits its errors.",
               "The test covers two years (2023–2024); the 15 depth levels are coarse in the thermocline.",
               "The course methods see one patch at a time and cannot use the surrounding ocean.",
               "Heat potential is undefined where the water never reaches 26 °C, so those casts are excluded."])
    w.h("Future enhancements")
    w.bullets(["Add neighbouring patches as inputs to the course methods, to test how much of the deep model's Bay of Bengal advantage comes from spatial context.",
               "Use the recommender for analog forecasting: what happened below the surface in the days after each analog.",
               "Extend the test period as new Argo data arrive, and evaluate during individual cyclones."])


REFERENCES = [
    "Igual, L., & Seguí, S. (2017). Introduction to Data Science: A Python Approach to Concepts, Techniques and Applications. Springer.",
    "Martens, D. (2022). Data Science Ethics: Concepts, Techniques and Cautionary Tales. Oxford University Press.",
    "Wong, A. P. S., et al. (2020). Argo data 1999–2019: Two million temperature-salinity profiles and subsurface velocity observations from a global array of profiling floats. Frontiers in Marine Science, 7, 700. https://doi.org/10.3389/fmars.2020.00700",
    "Lellouche, J.-M., et al. (2021). The Copernicus Global 1/12° Oceanic and Sea Ice GLORYS12 Reanalysis. Frontiers in Earth Science, 9, 698876. https://doi.org/10.3389/feart.2021.698876",
    "Guinehut, S., Dhomps, A.-L., Larnicol, G., & Le Traon, P.-Y. (2012). High resolution 3-D temperature and salinity fields derived from in situ and satellite observations. Ocean Science, 8, 845–857. https://doi.org/10.5194/os-8-845-2012",
    "Su, H., et al. (2018). Retrieving ocean subsurface temperature using a satellite-based geographically weighted regression model. Journal of Geophysical Research: Oceans. https://doi.org/10.1002/2018JC014246",
    "Meng, L., et al. (2022). Reconstructing high-resolution ocean subsurface and interior temperature and salinity anomalies from satellite observations. IEEE Transactions on Geoscience and Remote Sensing, 60. https://doi.org/10.1109/TGRS.2021.3109979",
    "Leipper, D. F., & Volgenau, D. (1972). Hurricane heat potential of the Gulf of Mexico. Journal of Physical Oceanography, 2, 218–224.",
    "Shay, L. K., Goni, G. J., & Black, P. G. (2000). Effects of a warm oceanic feature on Hurricane Opal. Monthly Weather Review, 128, 1366–1383.",
    "Mainelli, M., DeMaria, M., Shay, L. K., & Goni, G. (2008). Application of oceanic heat content estimation to operational forecasting of recent Atlantic category 5 hurricanes. Weather and Forecasting, 23, 3–16.",
    "Goni, G. J., et al. (2021). Tropical cyclone heat potential. In State of the Climate in 2020. Bulletin of the American Meteorological Society, 102(8), S252–S255.",
    "Lorenz, E. N. (1969). Atmospheric predictability as revealed by naturally occurring analogues. Journal of the Atmospheric Sciences, 26, 636–646.",
    "Holm, S. (1979). A simple sequentially rejective multiple test procedure. Scandinavian Journal of Statistics, 6, 65–70.",
    "Efron, B. (1979). Bootstrap methods: Another look at the jackknife. The Annals of Statistics, 7, 1–26.",
    "Rousseeuw, P. J. (1987). Silhouettes: A graphical aid to the interpretation and validation of cluster analysis. Journal of Computational and Applied Mathematics, 20, 53–65.",
    "Hubert, L., & Arabie, P. (1985). Comparing partitions. Journal of Classification, 2, 193–218.",
    "Pedregosa, F., et al. (2011). Scikit-learn: Machine learning in Python. Journal of Machine Learning Research, 12, 2825–2830.",
    "Copernicus Marine Service. GLORYS12 reanalysis (https://doi.org/10.48670/moi-00021); OSTIA sea surface temperature (https://doi.org/10.48670/moi-00168); Multi-Observation sea surface salinity (https://doi.org/10.48670/moi-00051); DUACS sea level (https://doi.org/10.48670/moi-00145).",
    "NASA PO.DAAC. OSCAR L4 ocean surface currents, version 2.0. Remote Sensing Systems. CCMP 10 m winds, version 3.1.",
    "INCOIS ERDDAP (https://erddap.incois.gov.in/erddap/), dataset incois_argo_10d_VAM; Ifremer ERDDAP Argo floats; IOOS Glider DAC (https://gliders.ioos.us/erddap/).",
    "Ward, J. H. (1963). Hierarchical grouping to optimize an objective function. Journal of the American Statistical Association, 58, 236–244.",
    "Breiman, L., Friedman, J. H., Olshen, R. A., & Stone, C. J. (1984). Classification and Regression Trees. Wadsworth.",
]


def appendices(w):
    w.h("A. Repository")
    w.para("All code, data, notebooks, figures and results are in the repository https://github.com/Kukyos/Watuh. "
           "Running python notebooks/build.py executes every notebook and rewrites results.json and the figures; "
           "python dashboard/build.py bundles the results for the dashboard.")
    w.table(["Notebook", "Contents", "Course modules"],
            [["01_see_data_quality", "Missing data, descriptive statistics, outliers, agreement with instruments", "2, 3"],
             ["02_explore_satellite_data", "Distributions, profiles by sea and season, correlation, t-test", "2, 3"],
             ["03_predict_regression", "Simple, multiple, polynomial regression, KNN, tree; Argo test; importance", "4, 6"],
             ["04_classify_cyclone_fuel", "Logistic regression, KNN, tree; confusion matrix, ROC", "4, 6"],
             ["05_cluster_water_types", "PCA, k-means, agglomerative, silhouette, ARI", "4"],
             ["06_prove_tests_fairness", "Paired tests, Holm correction, bootstrap, fairness, provenance", "3, 6"],
             ["07_recommend_analog_days", "Content-based recommender and its evaluation", "5"]],
            "The analysis notebooks", widths=[4.6, 8.4, 2.5])
    w.h("B. Additional figures")
    w.figure(FIG / "explore_profiles_season.png", "Mean temperature profile by sea and season")
    w.figure(FIG / "classify_confusion.png", "Confusion matrices of the classifiers on held-out floats")
    w.figure(FIG / "cluster_choose_k.png", "Choosing the number of clusters: elbow and silhouette", 13)
    w.figure(FIG / "recommend_pca.png", "Each day as a point in surface-state space: the year traces a loop")


# ------------------------------------------------------------------ assembling the template

GUIDE_TEXT = {
    "A brief summary of the project", "Objectives and scope of the project", "Key features and functionalities",
    "Background information about the project", "Problem statement and motivation",
    "Overview of the concepts used (Micro Processor & concepts in COA)", "Comparison with similar projects or existing solutions",
    "Architecture and high-level design of the system", "Block diagrams (architecture diagram, flow diagram, etc.)",
    "Description of the product working flow with necessary diagram", "Detailed explanation of the implementation process",
    "Example real time application or product", "Description of the testing approach and methodologies used",
    "Test cases and results", "Validation of the system against the requirements", "Presentation of the final system",
    "Evaluation of the project's success in achieving its objectives",
    "Discussion of any challenges faced during the development process", "Summary of the project",
    "Achievements and limitations", "Future enhancements and recommendations",
    "List of all the references and resources used in the project",
}
PLACEHOLDERS = ("<< Font size-12>>", "<<Font- Times new Roman>>")
GUIDE_PREFIXES = ("Review of relevant literature", "IoT module includes")
SECTIONS = [abstract, chapter1, chapter2, chapter3, chapter4, chapter5, chapter6, conclusion, None, appendices]


def main():
    doc = Document(PRIVATE / "Template for Skill based Evaluation(23CS2024).docx")
    paras = doc.paragraphs
    numpr = copy.deepcopy(next(p for p in paras if p.text.strip() == "A brief summary of the project")._p.pPr.numPr)

    # Cover, title page, evaluation sheet
    for p in paras:
        t = p.text.strip()
        if t == "STUDENT NAME (REG.NO)":
            set_text(p, f"{STUDENT} ({REG_NO})")
        elif t == "TITLE":
            set_text(p, TITLE)
        elif t.startswith("<Font Size 18>"):
            set_text(p, SUBTITLE, size=14)
            p.runs[0].italic = True
        elif t.startswith("TEAM MEMBERS NAME"):
            set_text(p, "\n".join(f"{n} ({r})" for n, r in TEAM), size=16, bold=True)
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif t == "Name:":
            p.add_run(STUDENT.title()).font.size = Pt(12)
        elif t == "Register Number:":
            p.add_run(REG_NO).font.size = Pt(12)
        elif t == "Any additional information, diagrams, or code snippets that are relevant but not included in the main report":
            delete(p)
        elif t.startswith("<<The certificate"):
            p.clear()
            # Page 1 of each member's certificate PDF in private/, rendered at 220 dpi.
            p.add_run().add_picture(str(PRIVATE / "report_assets" / CERTIFICATE), width=Cm(16))

    # Chapter headings: one consistent look.
    for p in doc.paragraphs:
        t = p.text.strip()
        if t.startswith("CHAPTER ") or t in HEADING_TITLES:
            set_text(p, t, size=14 if t.startswith("CHAPTER") else 16, bold=True)
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.left_indent = None
            p.paragraph_format.first_line_indent = None
            p._p.get_or_add_pPr()
            if p._p.pPr.numPr is not None:
                p._p.pPr.remove(p._p.pPr.numPr)

    # Content: each "<<write the content here>>" (and the references one) in order.
    anchors = [p for p in doc.paragraphs if p.text.strip() in ("<<write the content here>>", "<<list the reference here with bullet>>")]
    assert len(anchors) == len(SECTIONS), len(anchors)
    for i, (anchor, fn) in enumerate(zip(anchors, SECTIONS)):
        chapter = {1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6}.get(i, "A" if fn is appendices else "")
        w = Writer(doc, anchor, chapter, numpr)
        if fn is None:                      # references
            for n, ref in enumerate(REFERENCES, 1):
                p = w._p(align=WD_ALIGN_PARAGRAPH.LEFT, after=4, line=1.15)
                p.paragraph_format.left_indent, p.paragraph_format.first_line_indent = Cm(0.9), Cm(-0.9)
                set_font(p.add_run(f"[{n}]\t{ref}"), 11)
        else:
            fn(w)
        delete(anchor)

    for p in list(doc.paragraphs):
        t = p.text.strip()
        if t in GUIDE_TEXT or t in PLACEHOLDERS or t.startswith(GUIDE_PREFIXES):
            delete(p)

    # 2. One page per chapter: drop the template's scattered page breaks between the abstract and
    #    the evaluation sheet, and start every heading on a new page instead.
    body = doc.paragraphs
    start = next(i for i, p in enumerate(body) if p.text.strip() == "ABSTRACT")
    sheet = next(i for i, p in enumerate(body) if p.text.strip() == "School of Computer Science and Technology")
    sheet_top = sheet - 1 if body[sheet - 1]._p.xpath(".//w:drawing") else sheet
    for p in body[start:sheet_top]:
        for br in p._p.xpath('.//w:br[@w:type="page"]'):
            br.getparent().remove(br)
    for p in body[start:sheet_top]:
        t = p.text.strip()
        if t == "ABSTRACT" or t.startswith("CHAPTER ") or t in ("CONCLUSION", "REFERENCES", "APPENDICES"):
            p.paragraph_format.page_break_before = True
        if t.startswith("CHAPTER "):
            p.paragraph_format.keep_with_next = True
    body[sheet_top].paragraph_format.page_break_before = True

    # 3. The template's empty spacer paragraphs leave gaps under headings, and where they spill
    #    past the end of a page they make a blank one. Drop them; headings get fixed spacing.
    for p in body[start:sheet_top]:
        if not p.text.strip() and not p._p.xpath(".//w:drawing") and not p.paragraph_format.page_break_before:
            delete(p)
    for p in doc.paragraphs:
        if p.text.strip() in HEADING_TITLES:
            p.paragraph_format.space_after = Pt(24)

    # Centred lines: the template pads some with spaces and tabs, and its list style indents
    # them, both of which push the text off centre.
    for p in doc.paragraphs:
        if p.alignment != WD_ALIGN_PARAGRAPH.CENTER or not p.text.strip():
            continue
        f = p.paragraph_format
        f.left_indent = f.right_indent = f.first_line_indent = Pt(0)
        runs = [r for r in p.runs if not r._r.xpath("./w:br")]
        for r in runs:
            if not r.text.strip():
                r.text = ""
        texts = [r for r in runs if r.text]
        if texts:
            texts[0].text = texts[0].text.lstrip()
            texts[-1].text = texts[-1].text.rstrip()

    out = PRIVATE / OUT_NAME
    doc.save(out)
    print("wrote", out)


if __name__ == "__main__":
    main()
