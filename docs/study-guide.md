# Study guide: how to explain VVater

This guide is for presenting the project and answering questions about it. Every number
in it is filled in from `results/results.json`, so it always matches the notebooks and
the dashboard.

Read it in this order: **the pitch**, **the demo script**, then **each chapter**. The
**glossary** and **viva questions** are at the end.

---

## The pitch (say this in under a minute)

> Satellites measure the ocean's surface every day: its temperature, saltiness, height,
> currents and winds. But cyclones are fuelled by heat stored *below* the surface, down
> to a hundred metres or more, and no satellite can see that. Floats called Argo measure
> it directly, but only at a few hundred places a month.
>
> My project asks: **from what a satellite sees, how well can we predict the temperature
> down to 1,000 metres?** I answer it in three acts. **See**: I checked the raw data,
> and found impossible values even in an official product. **Predict**: I used the
> regression methods from our course, and a deep learning model, and scored them all on
> measurements from 112 real Argo floats they had never seen. **Prove**: I tested whether the
> differences are statistically real and whether the model is fair to both seas. I also
> clustered the floats into water types, built a classifier that spots cyclone fuel, and
> made a recommender that finds days in history when the ocean looked like today.

---

## The demo script

Three windows, in this order. Practise the clicks until they are automatic.

| Act | Open | Show | Say |
|---|---|---|---|
| **See** | VVater (P3), the Amphan scenario | Cut the cube open; click a float | "This is real data in 3D. The float's QC flag is shown, and rejected readings are drawn, not hidden." |
| **Predict** | Satelight (P4) viewer | The eight satellite fields; the reconstructed cube; one float's profile | "Eight surface fields go in, temperature at 15 depths comes out. Here is a float the model never saw." |
| **Prove** | `dashboard/index.html` | The depth chart; switch methods on and off; the analog finder with Cyclone Mocha | "This is the evidence: every method on the same floats, with hypothesis tests." |

If anything fails on the day, play the backup video and keep talking over it.

---

## Chapter 1 · See: is the data trustworthy? (Modules 2 and 3)

**What was done.** Three Bay of Bengal datasets from August 2018: the INCOIS gridded
analysis, Argo floats and a glider. They were imported, cleaned, checked for missing
values, summarised and checked for outliers, and the analysis was compared with the
instruments.

**The findings, and how to explain them:**

* **50.1% of the grid is empty.** Not lost data: those cells are
  land or sea floor, where there is no water. *Structurally missing* data must not be
  imputed, because filling it in would invent ocean where there is rock.
* **A cleaning problem found on import.** The QC flag column mixed numbers and text
  (`1` and `"1"`), so the same flag was counted twice. It was converted to numbers
  first.
* **Outliers.** The box-plot rule (1.5 × IQR) flagged 2072
  cells, most of them real variation in the thermocline. The Argo global range test
  (sea water lies between −2.5 and 40 °C) flagged 6, up
  to **44.42 °C at 100 m**.
  That is impossible, and it was in an official product.
  *Point to make:* a statistical rule finds the unusual; a physical rule finds the
  impossible. Use both, and know which one you are using.
* **Agreement with instruments.** The correlation looks excellent (r =
  0.968 against the glider), but only because both columns
  run from warm to cold with depth. Split by depth, the error against the glider is
  **2.57 °C in the top 300 m** against
  0.47 °C below. *Point to make:* a single
  overall number can hide the error that matters.

## Chapter 2 · Explore (Modules 2 and 3)

**The dataset.** 214640 rows. Each row is one 0.25° patch of sea on one day,
2010–2024: 8 satellite inputs plus the temperature at 15 depths from GLORYS.

**Descriptive statistics.** Mean, median, variance and standard deviation of every
input. Salinity is skewed (the fresh Bay of Bengal), so its mean and median differ. The
median is the more honest "typical value" for skewed data.

**Correlation, and what it shows:**

* Sea surface temperature vs temperature at 0 m: r = 0.96. At 125 m
  it is about zero. The satellite sees only the top layer.
* Sea level anomaly vs temperature at 100 m: r = 0.69. Warm
  water expands, so a thicker warm layer lifts the sea surface by a few centimetres.
  Sea height is an indirect measurement of the heat underneath, which is why prediction
  is possible at all.
* Salinity vs temperature at 700 m: r = 0.78. That is not
  because salt heats the deep sea. The salty Arabian Sea also has warmer deep water.
  **Correlation is not causation**: a third variable (geography) drives both.

**First hypothesis test.** H₀: the Bay of Bengal and the Arabian Sea have the same mean
surface salinity. A paired t-test on 5366 daily means gives a
difference of 3.37 PSU, 95% CI
[3.35, 3.39]. Reject
H₀. *Why daily means?* Patches sampled on the same day are not independent, and
treating 200,000 rows as independent would overstate the evidence.

## Chapter 3 · Predict: regression (Module 4)

**The task.** Predict the temperature at 15 depths from 13 inputs: the 8 satellite
fields, latitude, longitude, sea-floor depth and the day of the year (as sine and
cosine, so 31 December sits next to 1 January).

**The methods, in one line each:**

| Method | Idea | Setting chosen on validation |
|---|---|---|
| Simple linear | A straight line from SST alone | none |
| Multiple linear | A weighted sum of all 13 inputs | none |
| Polynomial | Also squares and products of inputs, so curves and interactions | degree 3 |
| KNN | Average the k most similar training patches | k = 20 |
| Decision tree | A flowchart of yes/no questions | depth 14 |
| Satelight hybrid | A deep network (CNN + transformer) that sees the whole sea at once | (Satelight's own selection) |

**The fair-test rules:**

1. **Split by time.** Train 2010–2020, validate 2021–2022, test 2023–2024. A random split
   would leak: neighbouring days are nearly identical.
2. **Settings are chosen on validation only.** The test years are used once.
3. **Same judge for everyone.** 88829 measurements from real Argo
   floats, the same points for every model. The scoring code reproduces Satelight's
   published numbers exactly, which proves it is the same test.

**The result (mean RMSE over 15 depths, whole box):**

| | RMSE (°C) | Gap closed |
|---|---:|---:|
| Climatology (floor) | 1.036 | 0% |
| Simple linear (SST only) | 1.642 | -184% |
| Multiple linear | 1.020 | 5% |
| Polynomial | 0.843 | 59% |
| KNN | 0.900 | 41% |
| Decision tree | 0.889 | 44% |
| Satelight hybrid | 0.843 | 59% |
| GLORYS (ceiling) | 0.707 | 100% |

**"Gap closed"** = (climatology − model) / (climatology − GLORYS). 0% means no better
than the long-term average for that place and date; 100% means as good as GLORYS. GLORYS
is a ceiling, not a rival, because these floats were fed into it.

**What to say about it (the five findings):**

1. **At the surface the simplest model wins.** Simple linear regression from SST alone
   scores 0.42 °C at 0 m, better than Satelight
   (0.54) and even GLORYS (0.43),
   because the satellite measures that very layer. At 50 m the same line is the worst
   model: 2.45 °C. *Lesson: the right model depends
   on the question.*
2. **Straight lines are not enough below the surface.** Multiple linear regression closes
   only 5% of the gap.
   The relationship bends, and the methods that can bend do far better.
3. **The headline: a cubic polynomial from the syllabus is level with the deep learning
   model on average** (0.843 vs
   0.843 °C). Satelight is better in the Bay of Bengal
   (0.701 vs
   0.737), the polynomial in the Arabian
   Sea (0.824 vs
   0.847).
4. **Sea level is the key input** (permutation importance) from the surface to 150 m.
   At 300 m longitude (which sea) matters most; at 1,000 m, sea-floor depth.
5. **The thermocline is hard for everyone,** GLORYS included: every method's largest error
   is around 100 m.

*If asked "so is deep learning pointless?"*: No. Satelight is better in the Bay, it
predicts the whole sea at once rather than patch by patch, and its embedding is used
elsewhere. The finding is that **careful feature choice and a well-tuned classical model
get most of the way**, which is worth knowing before spending GPU hours.

## Chapter 4 · Classify: cyclone fuel (Module 4)

**The question.** Is the tropical cyclone heat potential (TCHP: the heat in water warmer
than 26 °C) at least 50 kJ/cm²? Above that, the ocean can usually support a cyclone
strengthening (NOAA *State of the Climate 2020*, citing Shay et al. 2000 and Mainelli et
al. 2008).

**Training labels** come from GLORYS profiles (2010–2020). **Test labels** come from the
floats themselves: 5793 casts with a measurable TCHP.

**Metrics, in plain words:**

* **Accuracy:** share of answers that are right. Misleading when classes are unequal.
* **Precision:** when it says "fuel", how often is it right?
* **Recall:** of all the fuelled ocean, how much did it find?
* **F1:** a single score that is high only when precision and recall are both high (their harmonic mean).
* **ROC AUC:** the chance that a random fuelled patch gets a higher score than a random
  unfuelled one. 0.5 is guessing, 1 is perfect.

| Method | Accuracy | Precision | Recall | F1 | ROC AUC |
|---|---:|---:|---:|---:|---:|
| Logistic regression | 0.884 | 0.845 | 0.946 | 0.893 | 0.955 |
| KNN | 0.894 | 0.904 | 0.886 | 0.895 | 0.965 |
| Decision tree | 0.890 | 0.886 | 0.902 | 0.894 | 0.957 |
| Satelight hybrid → TCHP | 0.907 | 0.918 | 0.898 | 0.908 | 0.972 |
| Always "fuel" (baseline) | 0.511 | 0.511 | 1.000 | 0.676 | – |

**What to say about it:**

* **Class balance:** 48.9% of the test
  floats have fuel. Always answering "fuel" already gets
  51% accuracy and a recall of 100%, which is why
  one metric alone is never enough.
* **All three course classifiers land close together** (F1 about 0.89, ROC AUC about
  0.96). Reconstructing the whole profile with Satelight and computing TCHP from it does
  slightly better (F1 0.908). Climatology does
  worst on recall (0.736): the long-term average
  misses the unusually warm days, which are exactly the dangerous ones.
* **Logistic regression has the highest recall of the course classifiers**
  (0.946), at the cost of more false alarms.
  For a warning system that trade can be the right one.
* **Explainability:** the logistic weights and the three-level decision tree in the
  notebook show which inputs push towards "fuel".

## Chapter 5 · Discover: clustering (Module 4)

**Data.** 5649 float profiles, temperature at 14 depths from 0 to
700 m. 1,000 m was left out because a fifth of the floats do not reach it.

**Distance.** Euclidean distance between two profiles: roughly, the typical temperature
difference at each depth. Not standardised, because every column is already in °C.

**Choosing k.** The silhouette score (how much closer each profile is to its own cluster
than to the next) was highest at **k = 3**. The elbow plot shows the same
trade-off by eye.

**k-means vs agglomerative.** k-means moves k centres until every profile sits with its
nearest one. Agglomerative (Ward) starts with every profile alone and merges the closest
groups step by step (the dendrogram). On the same data they agree with an adjusted Rand
index of 0.60 (1 = identical, 0 = chance).

**The check, made only after choosing k.** The clusters match the sea each float was in
with an ARI of 0.10, against 0.00
for shuffled labels, and the season with an ARI of 0.02.

**What to say about it, honestly:** the types do not split neatly into "Bay" and
"Arabian Sea", so the overall agreement is modest. But they are far from random:
87% of Bay of Bengal floats fall into cluster 0,
and cluster 2 holds 51% of Arabian Sea floats but
0% of the Bay's. Season explains almost nothing.
Water types are a property of *place*.

*If asked "why not more clusters?"*: the silhouette score falls after k = 3, so more
clusters would split real groups rather than find new ones.

## Chapter 6 · Prove: hypothesis tests and fairness (Modules 3 and 6)

**Why test at all?** A lower RMSE on one set of floats might be luck. A test asks how
likely a difference this large would be if the two models were really equal.

**Three choices to explain:**

1. **The float is the unit of evidence.** One float reports every 10 days along a
   drifting path, so its measurements are not independent. Per-float average errors go
   into a paired t-test, and confidence intervals come from a **bootstrap**: resample
   whole floats with replacement 2,000 times and recompute the difference each time.
2. **Holm correction.** Testing 15 depths at 5% each gives about a 54% chance of at least
   one false alarm. Holm's method raises the bar for each test so the overall false
   alarm rate stays at 5%.
3. **Two-sided tests,** fixed before computing. We did not decide the direction after
   seeing the data.

**Fairness.** Raw error is not fair between seas: the Bay of Bengal's sharp thermocline
makes every method miss by more there. **Skill** = 1 − MSE(model) / MSE(climatology)
compares each sea against what the long-term average achieves in that same sea.

**The results:**

* **Test A, Satelight vs climatology:** significantly better at every depth from 0 to
  200 m. No significant difference at 300–700 m. Significantly *worse* at 1,000 m (by
  0.020 °C). Say this plainly: an honest report includes
  where the model loses.
* **Test B, Satelight vs polynomial:** no significant difference at 14 of 15 depths. The
  polynomial is significantly better at 0 m. The deep model's advantage over the best
  course method is not statistically real on these floats.
* **Test C, fairness:** Satelight's skill is *higher* in the Bay of Bengal, even though
  the Bay has fewer floats (37 against
  76). Less data did not mean a worse model there.

**Transparency:** of 6144 casts,
5136 are delayed-mode (checked by a scientist),
576 adjusted and 432 real-time.
1172 levels failed QC and were counted, not hidden.

## Chapter 7 · Recommend: analog days (Module 5)

**Items** are days. Each day is described by what satellites saw of the whole sea,
compressed by PCA into 30 numbers (keeping 69.6%
of the variation). **Similarity** is cosine similarity: the angle between two days'
descriptions.

**Content-based, not collaborative.** Collaborative filtering needs users and ratings
("people who liked this also liked..."). Days have no users, but they do have content.

**Evaluation, decided in advance.** A recommended day is only useful if it is also similar
*below* the surface, which the recommender never saw. So each pick is scored by the RMSE
between its 50–200 m temperature field and the query day's.

| Strategy | Subsurface RMSE of picks (°C) | Precision@5 |
|---|---:|---:|
| Recommender (cosine on the surface) | 1.18 | 70% |
| Same date, another year | 1.41 | 31% |
| Random day | 1.94 | 5% |
| Best possible (oracle) | 1.02 | – |

The recommender beats "same date" on 85% of days.

**A surprise worth mentioning:** within 2023–2024, the plain PCA description
(1.28 °C) recommends better than
Satelight's learned embedding (1.46 °C).
One likely reason: the embedding was trained to help predict each patch's own column of water, not to compare whole days. Learned features are not automatically better for every task.

**The demo moment:** pick Cyclone Mocha's formation day, 9 May 2023. Among the analogs is
**6 May 2020, ten days before Cyclone Amphan formed** in the same sea. Say it as an
observation, not a forecast: the recommender was never told about cyclones.

---

## Glossary

| Term | Meaning |
|---|---|
| **Argo float** | A robot that drifts at depth, rises to the surface every 10 days measuring temperature and salinity, and radios the profile home |
| **GLORYS** | A European ocean *reanalysis*: a physics model corrected with all available observations, giving a best estimate of the 3D ocean every day |
| **Climatology** | The long-term average for that place and day of the year. The baseline every model must beat |
| **Thermocline** | The layer (here about 50–200 m) where temperature drops fastest with depth. Hardest to predict |
| **TCHP** | Tropical cyclone heat potential: heat stored in water above 26 °C, in kJ/cm² |
| **QC flag** | A quality label on each measurement: 1 good, 2 probably good, 3 probably bad, 4 bad |
| **RMSE** | Root mean squared error: the typical size of an error, in °C. Large errors count extra |
| **Bias** | The average error with its sign: whether a model runs warm or cold |
| **Correlation (r)** | How closely two variables move together, from −1 to 1. Says nothing about cause |
| **Overfitting** | Learning the training data's noise instead of its pattern: great on training, worse on new data |
| **Train / validation / test** | Learn on one block, choose settings on the second, report on the third, used once |
| **Data leakage** | Information from the test set reaching training, making scores look better than they are |
| **Standardisation** | Rescaling each input to mean 0 and std 1, so no input dominates distances by its units |
| **p-value** | If H₀ were true, the chance of seeing a difference at least this large |
| **Confidence interval** | A range that, built this way, contains the true value 95% of the time |
| **Bootstrap** | Estimating uncertainty by resampling the data with replacement many times |
| **Holm correction** | Adjusting p-values when running many tests at once, to keep false alarms rare |
| **PCA** | Finding the few directions that capture most of the variation in many columns |
| **Silhouette score** | How well each point fits its own cluster compared with the next nearest, from −1 to 1 |
| **Adjusted Rand index** | Agreement between two groupings, corrected for chance: 1 identical, 0 random |
| **Cosine similarity** | Similarity of two vectors by the angle between them: 1 same direction, 0 unrelated |
| **Precision@k** | Of the top k recommendations, the share that is actually relevant |

---

## Viva questions

Read the question, answer it aloud in your own words, then check against the answer.

### About the problem and the data

**Why is this a data science problem and not just an oceanography problem?**
It is about learning a relationship from data (surface → subsurface), checking data
quality, choosing and evaluating models, and testing whether results are real. The ocean
is the domain; the method is data science.

**Where did the data come from? Did you scrape it?**
It was collected by script from public data servers: ERDDAP servers (Ifremer for Argo,
INCOIS for its analysis), the IOOS Glider DAC, Copernicus Marine and NASA PO.DAAC. The
scripts query each server for a region and time window and parse the response. About
10 GB was reduced to the small files in `data/`.

**Why not just use satellites? Why do you need a model?**
Satellites see only the surface skin. Cyclones draw on heat down to 100 m and more, and
light and radar do not reach down there. Argo floats do measure it, but there are only a
few hundred profiles a month across this whole sea.

**What is GLORYS and why do you call it a ceiling?**
A reanalysis: a physics model of the ocean continuously corrected with real
observations, including these Argo floats. Because it has seen the floats, it is
expected to score best against them. It is the target to approach, not a fair rival.

**What is climatology and why is it the floor?**
The average temperature for that place and day of the year over 2010–2020. It knows the
season but nothing about today. A model that cannot beat it has learned nothing useful.

**How did you handle missing values?**
Mostly they are structural: land, or sea floor shallower than the depth. Those are left
missing and excluded, never imputed. Measurements failing QC are counted and excluded.
A day with a missing satellite input is dropped and reported.

**What was wrong with the QC column?**
Mixed types: some flags were stored as numbers and some as text, so `value_counts`
showed the same flag twice. It was converted to numbers before use.

### About the methods

**What is the difference between simple and multiple linear regression?**
Simple uses one input (here SST); multiple uses several (all 13), each with its own
weight.

**What does polynomial regression add?**
Squares and products of the inputs, so the model can bend (curves) and combine inputs
(interactions such as "sea level matters more in the Bay"). It is still linear in its
weights, so it is fitted the same way.

**How did you choose the polynomial degree, k for KNN and the tree depth?**
By validation: train on 2010–2020 for each candidate, score on 2021–2022, keep the best.
The test years were not used.

**Why does KNN need standardised inputs?**
It measures distance. Without scaling, an input measured in large numbers (sea-floor
depth in metres) would swamp one measured in small numbers (sea level in metres, ~0.1).

**Why not split the data randomly?**
Neighbouring days are almost identical. With a random split, the model would see
yesterday in training and be tested on today, a form of data leakage that inflates
scores. Splitting by years tests it on a genuinely unseen future.

**What is overfitting? Where did you see it?**
Learning noise instead of pattern. The tuning curves show it: deeper trees and KNN with
very few neighbours do worse on the validation years even though they fit training
better.

**Why RMSE and not accuracy for regression?**
Accuracy is for categories. RMSE gives the typical error in °C, and squaring makes large
misses count extra, which matters in a forecast.

**What is the "gap closed" number?**
(climatology − model) / (climatology − GLORYS). It puts every model on one scale: 0% is
the floor and 100% the ceiling.

**What is the deep learning model?**
Satelight's hybrid encoder: a convolutional network compresses each day's satellite maps
into 32 numbers per patch, and a transformer lets every patch look at every other patch
of the sea. A small network then decodes the 32 numbers into 15 depths. Unlike the course
methods, it sees the neighbourhood, not just one patch.

**Logistic regression is a regression. Why use it for classification?**
It predicts a probability between 0 and 1 by passing a weighted sum through an S-shaped
curve. Above 0.5 we say "fuel". It is regression on the probability scale.

**Why report precision and recall instead of just accuracy?**
The classes are not 50/50, so always guessing the bigger class already gets a high
accuracy. Precision and recall show whether the model actually finds the fuelled ocean.

**Which matters more here, precision or recall?**
Recall: missing fuelled water ahead of a cyclone is worse than a false alarm.

**How did you choose k for clustering?**
With the silhouette score, chosen before looking at any labels. The elbow plot agrees.

**What is the difference between k-means and agglomerative clustering?**
k-means fixes k centres and moves them; agglomerative builds a tree by merging the
closest groups and cuts it at k. k-means needs k up front; the tree shows every k at once.

**What does PCA do in your project?**
It compresses many correlated numbers into a few that keep most of the variation. It was
used to see the main shapes of float profiles (chapter 5) and to describe each day's
satellite picture in 30 numbers for the recommender (chapter 7).

**Why is your recommender content-based, not collaborative?**
Collaborative filtering needs users and their ratings. Days have no users. They have
content (the satellite picture), so content-based filtering fits.

**How did you evaluate the recommender?**
A good analog day should also match below the surface, which the recommender never saw.
Each pick was scored by its subsurface RMSE against the query day, compared with a random
day and with the same date in another year, and with precision@5.

### About statistics

**What exactly did your hypothesis test test?**
H₀: at this depth, Satelight's error equals the other model's. H₁: they differ. Paired
t-test on per-float average squared errors, two-sided, α = 0.05 after Holm correction.

**Why per float and not per measurement?**
A float's measurements are not independent: it drifts slowly and samples similar water
each time. Treating them as independent overstates the evidence.

**What is a bootstrap confidence interval?**
Resample the floats with replacement many times (2,000), recompute the difference each
time, and take the middle 95% of those values.

**Why the Holm correction?**
Fifteen tests at 5% each would give about a 54% chance of at least one false positive.
Holm keeps the chance of any false positive at 5%.

**With so many data points, isn't everything significant?**
That is why the unit is the float and why effect sizes and confidence intervals are
reported, not just p-values. A tiny difference can be significant without mattering.

**Your fairness test: why skill and not RMSE?**
The Bay of Bengal is harder for every model (sharper thermocline), so raw RMSE would
blame the model for the sea. Skill compares each sea against its own climatology.

### About ethics and honesty

**Where is ethics in your project?**
Transparency (every measurement carries its QC flag, data mode and source file);
accountability (every number is written by the code that computed it into one file);
explainability (feature importance, logistic weights, a readable tree); fairness (skill
by sea, and how many floats each sea has).

**Did you remove any data that disagreed with you?**
No. Rejected measurements are counted and reported, and the rule (Argo QC flags) is
published, not chosen by me.

**What are the limits of your project?**
GLORYS is the training target and is not perfect. The test covers only 2023–2024. The 15
depths are coarse. Course methods see only one patch at a time. TCHP needs 26 °C water,
so it is undefined in some casts.
