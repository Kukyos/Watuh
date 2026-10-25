# %% [markdown]
# # 2 · Explore: what can a satellite see, and what lies beneath?
#
# **Syllabus:** Module 2 (import, filter, group, rank, plots) and Module 3 (descriptive
# statistics, correlation, estimation, hypothesis testing).
#
# Satellites measure the ocean's **surface** every day: temperature, salinity, sea
# level, currents and winds. Cyclone forecasters need the heat **below** the surface,
# which satellites cannot see. Argo floats measure it, but only at a few hundred places a
# month.
#
# The prediction task of this project: **from what a satellite sees today, estimate the
# temperature at 15 depths, from 0 to 1,000 m**.
#
# The dataset: 217,120 rows. Each row is one 0.25° patch of the North Indian Ocean on one
# day between 2010 and 2024, sampled at random (40 patches a day). It holds the 8
# satellite measurements of that patch and the temperature at 15 depths from GLORYS, the
# European ocean reanalysis (the best available estimate of the true 3D ocean).

# %%
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import common as C

C.style()
df = C.load_cells()
df = df[df["split"] != "gap"]           # the month-long gaps between the train, validation and test years
SEASONS = {1: "Winter", 2: "Winter", 3: "Pre-monsoon", 4: "Pre-monsoon", 5: "Pre-monsoon",
           6: "Monsoon", 7: "Monsoon", 8: "Monsoon", 9: "Monsoon",
           10: "Post-monsoon", 11: "Post-monsoon", 12: "Post-monsoon"}     # India Meteorological Department
df["season"] = df["day"].dt.month.map(SEASONS)
print(df.shape)
df.head()

# %% [markdown]
# ## 2.1 Select, filter, group

# %%
summary = df.groupby("split").agg(rows=("day", "size"), first=("day", "min"), last=("day", "max"),
                                  days=("day", "nunique"))
summary.loc[["train", "val", "test"]]

# %%
C.record("explore.rows", int(len(df)))
C.record("explore.splits", {k: int(v) for k, v in summary["rows"].items()})
df.groupby("basin")[["sst", "sss", "sla"]].mean().round(2)

# %% [markdown]
# **Missing values.** The surface is complete, but deeper levels are missing more often:
# 24% of patches have no value at 1,000 m. The reason is the same as in chapter 1. Near
# the coast the sea is shallower than 1,000 m, so there is no water at that depth.

# %%
miss = df[C.TARGETS].isna().mean().mul(100).round(1)
miss.index = [f"{d} m" for d in C.DEPTHS]
C.record("explore.missing_pct_by_depth", miss.to_dict())
shallow = df.loc[df["t1000"].isna(), "bathy"].describe()[["count", "mean", "max"]].round(0)
print(miss.to_string()); print("\nSea-floor depth where 1,000 m is missing:\n", shallow.to_string())

# %% [markdown]
# ## 2.2 Descriptive statistics of the satellite inputs

# %%
desc = df[C.INPUTS].agg(["mean", "median", "var", "std", "min", "max"]).T.round(3)
desc.index = [C.INPUT_NAMES[i] for i in desc.index]
C.record("explore.inputs", {k: desc.loc[C.INPUT_NAMES[k]].to_dict() for k in C.INPUTS})
desc

# %%
fig, axes = plt.subplots(2, 4, figsize=(14, 6))
for ax, col in zip(axes.flat, C.INPUTS):
    sns.histplot(df[col], bins=60, ax=ax, color=C.PALETTE["course"], edgecolor=None)
    ax.axvline(df[col].mean(), color="k", lw=1); ax.axvline(df[col].median(), color=C.PALETTE["accent"], lw=1, ls="--")
    ax.set_title(C.INPUT_NAMES[col], fontsize=9); ax.set_xlabel(""); ax.set_ylabel("")
fig.suptitle("Distribution of each satellite input (black: mean, red dashed: median)", y=1.01)
fig.tight_layout(); C.save(fig, "explore_inputs_hist")

# %% [markdown]
# Salinity has a long tail to the left (25–33 PSU). That is the **Bay of Bengal**, which
# receives fresh water from the Ganges, Brahmaputra and Irrawaddy. Mean and median
# disagree when a distribution is skewed like this, and the median is the more honest
# "typical value". Winds and currents are centred near zero because they blow and flow
# both ways.

# %% [markdown]
# ## 2.3 What the water column looks like, by sea and by season

# %%
prof = df.groupby(["basin", "season"])[C.TARGETS].mean()
order = ["Winter", "Pre-monsoon", "Monsoon", "Post-monsoon"]
cols = dict(zip(order, ["#2f7fc1", "#e8833a", "#3a9e6f", "#8c5bb5"]))
fig, axes = plt.subplots(1, 2, figsize=(11, 5.5), sharey=True)
for ax, basin in zip(axes, ["Arabian Sea", "Bay of Bengal"]):
    for s in order:
        ax.plot(prof.loc[(basin, s)].values, C.DEPTHS, label=s, color=cols[s], marker=".")
    ax.set_title(basin); ax.set_xlabel("Temperature (°C)"); ax.set_yscale("symlog", linthresh=50)
    ax.set_yticks([0, 20, 50, 100, 200, 500, 1000]); ax.set_yticklabels([0, 20, 50, 100, 200, 500, "1,000"])
axes[0].invert_yaxis(); axes[0].set_ylabel("Depth (m)"); axes[1].legend()
fig.tight_layout(); C.save(fig, "explore_profiles_season")

# %%
rank = (df.groupby(["basin", "season"])["t0"].mean().rename("surface °C").reset_index()
        .assign(rank=lambda d: d["surface °C"].rank(ascending=False).astype(int)).sort_values("rank"))
rank.round(2)

# %% [markdown]
# The two seas are different worlds. The Bay of Bengal is warmer at the surface but
# colder below 150 m: its thermocline is sharper (it cools by about 11 °C between 50 and
# 150 m, against about 7 °C in the Arabian Sea). The pre-monsoon (March to May) is the hottest
# season at the surface in both seas, which is when the strongest cyclones of the year
# form. Below 300 m the seasons almost coincide: the deep ocean does not feel the
# monsoon.

# %% [markdown]
# ## 2.4 Correlation: which surface signal speaks for which depth?

# %%
features = C.INPUTS + ["lat", "lon", "bathy"]
corr = df[features + C.TARGETS].corr().loc[features, C.TARGETS]
corr.columns = [f"{d}" for d in C.DEPTHS]
corr.index = [C.INPUT_NAMES.get(f, {"lat": "Latitude", "lon": "Longitude", "bathy": "Sea-floor depth"}.get(f)) for f in features]
fig, ax = plt.subplots(figsize=(12, 5))
sns.heatmap(corr, cmap="RdBu_r", vmin=-1, vmax=1, annot=True, fmt=".2f", annot_kws={"size": 7}, ax=ax,
            cbar_kws={"label": "Pearson r"})
ax.set_xlabel("Temperature at depth (m)"); ax.set_title("Correlation between each surface input and the temperature at each depth")
C.save(fig, "explore_corr_heatmap")
C.record("explore.corr", {i: corr.loc[C.INPUT_NAMES[i]].round(3).to_dict() for i in ["sst", "sss", "adt", "sla"]})

# %% [markdown]
# Three patterns stand out:
#
# * **Sea surface temperature** is almost perfectly correlated with the temperature at
#   0–20 m, and the link fades to nothing by 100–125 m. The satellite sees the top layer
#   and nothing below.
# * **Sea level anomaly** (how much higher or lower the sea stands than its long-term
#   average) is weakly related to the surface but strongly to **75–150 m**, the
#   thermocline. Warm water takes up more space than cold water, so when the warm layer
#   is thicker than usual the sea surface bulges up by a few centimetres. A satellite
#   measuring sea height is indirectly measuring the heat underneath.
# * **Salinity correlates with the deep water (500–1,000 m)**, but not because salt
#   warms the deep ocean. The salty Arabian Sea also happens to have warmer deep water
#   than the Bay of Bengal. The correlation comes from *geography*, a hidden third
#   variable. **Correlation is not causation.**
#
# This is why a model can predict below the surface at all, and why it needs sea level
# and not just temperature.

# %%
fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
s = df.sample(8000, random_state=C.SEED)
for ax, (x, y) in zip(axes, [("sst", "t0"), ("sla", "t100")]):
    for basin, col in [("Arabian Sea", C.PALETTE["course"]), ("Bay of Bengal", C.PALETTE["deep"])]:
        p = s[s["basin"] == basin]
        ax.scatter(p[x], p[y], s=4, alpha=0.35, color=col, label=basin)
    r = df[[x, y]].corr().iloc[0, 1]
    ax.set_xlabel(C.INPUT_NAMES[x]); ax.set_ylabel(f"Temperature at {y[1:]} m (°C)")
    ax.set_title(f"r = {r:.2f}")
axes[0].legend(markerscale=4)
fig.tight_layout(); C.save(fig, "explore_scatter")

# %% [markdown]
# ## 2.5 Estimation and a first hypothesis test
#
# **Question:** is the surface of the Bay of Bengal fresher than the Arabian Sea's?
#
# * H₀ (null): the mean surface salinity is the same in both seas.
# * H₁ (alternative): the means differ (two-sided).
#
# Patches sampled on the same day are not independent (neighbouring water is alike), so
# a test on 200,000 rows would wildly overstate the evidence. We reduce each sea to one
# mean per day, and compare the two seas **day by day** with a paired t-test.

# %%
daily = (df[df["basin"] != "Other"].groupby(["day", "basin"])["sss"].mean().unstack().dropna())
diff = daily["Arabian Sea"] - daily["Bay of Bengal"]
t, p = stats.ttest_rel(daily["Arabian Sea"], daily["Bay of Bengal"])
ci = stats.t.interval(0.95, len(diff) - 1, loc=diff.mean(), scale=stats.sem(diff))
mean_ci = {b: stats.t.interval(0.95, len(daily) - 1, loc=daily[b].mean(), scale=stats.sem(daily[b])) for b in daily}
print(f"Days compared: {len(daily):,}")
for b, (lo, hi) in mean_ci.items():
    print(f"  {b:14s} mean SSS {daily[b].mean():.2f} PSU, 95% CI [{lo:.2f}, {hi:.2f}]")
print(f"Difference (Arabian − Bay): {diff.mean():.2f} PSU, 95% CI [{ci[0]:.2f}, {ci[1]:.2f}]")
print(f"t = {t:.1f}, p = {p:.1e}")
C.record("explore.salinity_test", {"days": len(daily), "mean_arabian": daily["Arabian Sea"].mean(),
                                   "mean_bay": daily["Bay of Bengal"].mean(), "diff": diff.mean(),
                                   "ci95": list(ci), "t": t, "p": p})

# %% [markdown]
# The Arabian Sea is saltier by more than 3 PSU, and the confidence interval is far from
# zero. We **reject H₀**. The size of the difference matters as much as the p-value:
# 3 PSU is large in ocean terms. That fresh layer keeps the Bay's
# surface warm and stable, which is part of why its cyclones intensify so fast.

# %%
fig, ax = plt.subplots(figsize=(12, 5))
m = df.groupby(["lat", "lon"])["t100"].mean().reset_index()
sc = ax.scatter(m["lon"], m["lat"], c=m["t100"], s=3, cmap="RdYlBu_r", marker="s")
plt.colorbar(sc, ax=ax, label="Mean temperature at 100 m (°C)")
for name, b in C.BASINS.items():
    ax.add_patch(plt.Rectangle((b["lon"][0], b["lat"][0]), b["lon"][1] - b["lon"][0], b["lat"][1] - b["lat"][0],
                               fill=False, lw=1.2, ls="--", color="k"))
    ax.text(b["lon"][0] + 0.5, b["lat"][1] - 1.2, name, fontsize=10, weight="bold")
ax.set_xlabel("Longitude (°E)"); ax.set_ylabel("Latitude (°N)"); ax.set_aspect("equal")
ax.set_title("The study area: every sampled patch, coloured by its mean temperature at 100 m")
C.save(fig, "explore_map_t100")
