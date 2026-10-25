# %% [markdown]
# # 6 · Prove: is the difference real, and is it fair?
#
# **Syllabus:** Module 3 (estimation, hypothesis testing) and Module 6 (bias and
# fairness, transparency, accountability).
#
# Chapter 3 found that some models have lower error than others. A lower number is not
# yet proof. With a different two years of floats, would the ranking hold? This chapter
# answers with hypothesis tests, then asks whether the model serves both seas equally
# well.
#
# ## The hypotheses, fixed before computing anything
#
# For each of the 15 depths:
#
# | Test | H₀ (null) | H₁ (alternative) |
# |---|---|---|
# | **A** | Satelight's error equals climatology's | They differ (two-sided) |
# | **B** | Satelight's error equals the best course model's | They differ (two-sided) |
# | **C** | Satelight's skill is the same in the Bay of Bengal and the Arabian Sea | It differs (two-sided) |
#
# **Significance level:** α = 0.05, corrected for testing 15 depths at once (Holm's
# method). Without the correction, 15 tests at 5% would give about a 54% chance of at
# least one false "discovery".
#
# **The unit of evidence is the float, not the measurement.** One float reports every
# 10 days along a slowly drifting path, so its casts are not independent. Counting 6,000
# casts as 6,000 independent facts would make every test "significant". So:
#
# * the tests compare per-float average errors (a paired t-test on floats), and
# * confidence intervals come from a **bootstrap that resamples whole floats**.

# %%
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
import common as C

C.style()
casts = C.load_casts()
course = pd.read_csv(C.ROOT / "results" / "course_predictions_argo.csv.gz")
casts = casts.merge(course, on="cast_id")
res = __import__("json").loads(C.RESULTS.read_text(encoding="utf-8"))
best_course = res["regression"]["best_course_model"]
obs = C.profiles(casts, "obs_")
M = {"Climatology": C.profiles(casts, "climatology|"), "Satelight hybrid": C.profiles(casts, "hybrid (selected)|"),
     best_course: C.profiles(casts, f"{best_course}|"), "GLORYS": C.profiles(casts, "GLORYS (ceiling)|")}
# The same points as chapter 3: where the cast and every model (Satelight's and ours) have a value.
pts = np.isfinite(obs)
for name in {c.split("|")[0] for c in casts.columns if "|" in c}:
    pts &= np.isfinite(C.profiles(casts, f"{name}|"))
floats = casts["platform"].astype(str).to_numpy()
uf, fidx = np.unique(floats, return_inverse=True)
print(f"Casts {len(casts):,} from {len(uf):,} floats; points scored {int(pts.sum()):,}. Best course model: {best_course}")
C.record("prove.floats", len(uf))

# %%
def per_float(model, mask=None):
    """Sum of squared errors and number of points, per float and depth: (F, 15) each."""
    se = np.where(pts, (M[model] - obs) ** 2, 0.0)
    n = pts.astype(float)
    if mask is not None:
        se, n = se * mask[:, None], n * mask[:, None]
    S, N = np.zeros((len(uf), 15)), np.zeros((len(uf), 15))
    np.add.at(S, fidx, se); np.add.at(N, fidx, n)
    return S, N


rng = np.random.default_rng(C.SEED)
W = rng.multinomial(len(uf), np.full(len(uf), 1 / len(uf)), size=2000).astype(float)   # 2,000 resamples of floats


def boot_rmse(S, N):
    return np.sqrt((W @ S) / (W @ N))                                                   # (2000, 15)


def holm(p):
    """Holm–Bonferroni adjusted p-values."""
    p = np.asarray(p); order = np.argsort(p); m = len(p)
    adj = np.empty(m); running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * p[i])); adj[i] = running
    return adj


def compare(a, b):
    Sa, Na = per_float(a); Sb, Nb = per_float(b)
    rmse_a, rmse_b = np.sqrt(Sa.sum(0) / Na.sum(0)), np.sqrt(Sb.sum(0) / Nb.sum(0))
    diff_boot = boot_rmse(Sa, Na) - boot_rmse(Sb, Nb)
    lo, hi = np.percentile(diff_boot, [2.5, 97.5], axis=0)
    p = []
    for k in range(15):
        ok = Na[:, k] > 0
        p.append(stats.ttest_rel(Sa[ok, k] / Na[ok, k], Sb[ok, k] / Nb[ok, k]).pvalue)
    out = pd.DataFrame({"depth_m": C.DEPTHS, f"RMSE {a}": rmse_a, f"RMSE {b}": rmse_b, "difference": rmse_a - rmse_b,
                        "CI low": lo, "CI high": hi, "p": p, "p (Holm)": holm(p)})
    out["verdict"] = np.where(out["p (Holm)"] < 0.05, np.where(out["difference"] < 0, f"{a} better", f"{b} better"), "no significant difference")
    return out.round(4)

# %% [markdown]
# ## Test A: is Satelight better than climatology?

# %%
A = compare("Satelight hybrid", "Climatology")
C.record("prove.test_A", A.to_dict("records"))
A

# %% [markdown]
# ## Test B: is Satelight better than the best course method?

# %%
B = compare("Satelight hybrid", best_course)
C.record("prove.test_B", B.to_dict("records"))
B

# %%
fig, axes = plt.subplots(1, 2, figsize=(12, 5.5), sharey=True)
for ax, T, title in [(axes[0], A, "A: Satelight − climatology"), (axes[1], B, f"B: Satelight − {best_course.lower()}")]:
    sig = T["p (Holm)"] < 0.05
    ax.errorbar(T["difference"], T["depth_m"], xerr=[T["difference"] - T["CI low"], T["CI high"] - T["difference"]],
                fmt="none", ecolor="#999", capsize=3)
    ax.scatter(T.loc[sig, "difference"], T.loc[sig, "depth_m"], color=C.PALETTE["deep"], zorder=3, label="significant (Holm, α = 0.05)")
    ax.scatter(T.loc[~sig, "difference"], T.loc[~sig, "depth_m"], facecolor="white", edgecolor="k", zorder=3, label="not significant")
    ax.axvline(0, color="k", lw=0.8); ax.set_title(title); ax.set_xlabel("RMSE difference (°C), left of 0 = Satelight better")
    ax.set_yscale("symlog", linthresh=50); ax.set_yticks([0, 20, 50, 100, 200, 500, 1000]); ax.set_yticklabels([0, 20, 50, 100, 200, 500, "1,000"])
axes[0].invert_yaxis(); axes[0].set_ylabel("Depth (m)"); axes[0].legend(fontsize=8, loc="lower left")
fig.suptitle("Differences with 95% confidence intervals (bootstrap over floats)", y=1.01)
fig.tight_layout(); C.save(fig, "prove_tests")

# %% [markdown]
# A dot with its whole interval left of zero means Satelight is better at that depth with
# 95% confidence. An interval crossing zero means the data cannot tell the two models
# apart there, whatever the raw numbers say. A dot right of zero is a depth where
# Satelight is significantly *worse*, and an honest report says so.

# %% [markdown]
# ## Test C: fairness between the two seas
#
# Raw RMSE cannot answer whether the model is fair. The Bay of Bengal has a sharper
# thermocline, so *every* model, even climatology, has larger errors there. Comparing
# raw errors would confuse "harder sea" with "worse model". So we compare **skill**:
#
# skill = 1 − MSE(model) / MSE(climatology)
#
# 0 means no better than climatology and 1 means perfect, measured against what is
# achievable in each sea.

# %%
bay = casts["basin"].eq("Bay of Bengal").to_numpy()
arab = casts["basin"].eq("Arabian Sea").to_numpy()


def skill_boot(model, mask):
    Sm, Nm = per_float(model, mask); Sc, Nc = per_float("Climatology", mask)
    point = 1 - (Sm.sum(0) / Nm.sum(0)) / (Sc.sum(0) / Nc.sum(0))
    with np.errstate(invalid="ignore", divide="ignore"):
        boot = 1 - (W @ Sm / (W @ Nm)) / (W @ Sc / (W @ Nc))
    return point, boot


fair = []
for model in ["Satelight hybrid", best_course]:
    pb, bb = skill_boot(model, bay); pa, ba = skill_boot(model, arab)
    d = bb - ba
    p_boot = np.minimum(1, 2 * np.minimum(np.nanmean(d <= 0, axis=0), np.nanmean(d >= 0, axis=0)))
    for k, z in enumerate(C.DEPTHS):
        fair.append({"model": model, "depth_m": z, "skill Bay": pb[k], "skill Arabian": pa[k], "difference": pb[k] - pa[k],
                     "CI low": np.nanpercentile(d[:, k], 2.5), "CI high": np.nanpercentile(d[:, k], 97.5), "p": p_boot[k]})
fair = pd.DataFrame(fair)
fair["p (Holm)"] = fair.groupby("model")["p"].transform(lambda p: holm(p.to_numpy()))
fair = fair.round(4)
C.record("prove.test_C", fair.to_dict("records"))
fair[fair["model"] == "Satelight hybrid"]

# %%
fig, axes = plt.subplots(1, 2, figsize=(12, 5.5), sharey=True)
for ax, model in zip(axes, ["Satelight hybrid", best_course]):
    f = fair[fair["model"] == model]
    ax.plot(f["skill Bay"], f["depth_m"], marker="o", color=C.PALETTE["deep"], label="Bay of Bengal")
    ax.plot(f["skill Arabian"], f["depth_m"], marker="o", color=C.PALETTE["course"], label="Arabian Sea")
    ax.axvline(0, color="k", lw=0.8); ax.set_title(model); ax.set_xlabel("Skill vs climatology (1 = perfect, 0 = no better)")
    ax.set_yscale("symlog", linthresh=50); ax.set_yticks([0, 20, 50, 100, 200, 500, 1000]); ax.set_yticklabels([0, 20, 50, 100, 200, 500, "1,000"])
axes[0].invert_yaxis(); axes[0].set_ylabel("Depth (m)"); axes[0].legend()
fig.suptitle("Does the model serve both seas equally?", y=1.01)
fig.tight_layout(); C.save(fig, "prove_fairness")

# %% [markdown]
# ## Representation: who is in the data?
#
# Fairness also depends on how much evidence each place contributes. If one sea has far
# fewer floats, the model is both trained and judged with less information there.

# %%
rep = casts.groupby("basin").agg(casts=("cast_id", "size"), floats=("platform", "nunique"))
area = pd.Series({b: (v["lon"][1] - v["lon"][0]) * (v["lat"][1] - v["lat"][0]) for b, v in C.BASINS.items()})
rep["box area (deg²)"] = area
rep["casts per 100 deg²"] = (100 * rep["casts"] / rep["box area (deg²)"]).round(1)
C.record("prove.representation", rep.drop(index="Other", errors="ignore").to_dict(orient="index"))
rep

# %% [markdown]
# ## Transparency and accountability: the data's paper trail
#
# Every measurement in this project carries where it came from and how much it can be
# trusted. That is what makes the numbers above checkable.

# %%
trail = {"casts": len(casts), "data_mode": casts["data_mode"].value_counts().to_dict(),
         "levels_rejected_by_qc": int(casts["levels_rejected"].sum()),
         "casts_with_any_rejected_level": int((casts["levels_rejected"] > 0).sum()),
         "source_files": int(casts["source_file"].nunique())}
C.record("prove.paper_trail", trail)
trail

# %% [markdown]
# * **Data mode:** D (delayed mode) means a scientist checked and corrected the
#   profile; A means automatically adjusted; R is raw real-time data.
# * **Rejected levels are counted, never hidden:** a measurement failing QC is excluded
#   from scoring, and the count is reported.
# * **Every number in this project is written by the code that computed it** into one
#   results file. The dashboard and the report read that file and nothing is typed by
#   hand, so any figure can be traced back to the notebook cell that produced it.
