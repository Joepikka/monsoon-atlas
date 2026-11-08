# How to read Monsoon Atlas: methods and policies

This page explains the rules behind the map, models and Ask. It summarises
the plan (`docs/plan.pdf`), its amendments and the decisions log. Features
marked planned do not exist yet.

## Budget

The project budget is Rs 0. It uses free tiers and open data only: no paid
API, no paid hosting, no purchased domain and no card on file. The planned
address is a free pages.dev subdomain.

## Safety

Monsoon Atlas is an independent research and portfolio project, not an
emergency service. It does not replace official warnings. Follow the linked
official sources and local authorities. Official alerts, model outputs and
inferred items stay visibly separate.

## Provenance

Every record carries a provenance value. Official means the record comes
directly from the publishing agency. Model means a model produced the value;
it is not a direct official observation. Inferred means the value was derived
from other evidence and may be uncertain; check the method it cites.
Reconstructed means it was assembled later from historical sources.

## Forecast vintage

A forecast's issue time is when that particular forecast run was issued.
Different runs for the same future day can disagree, so each forecast keeps
its own issue time and model name.

## Times

Each record keeps separate clocks. Observed or valid time is the time the
measurement represents. Fetch time is when the pipeline retrieved it, and
publication time is when the product published it. Fetch time is never used
as the observation time. Times are stored in UTC. The interface shows
Asia/Kolkata time (UTC+05:30), and daily totals use local calendar days.

## Missing values

A missing value is not a measured zero. Missing rainfall stays null with a
missing reason; it is never filled with 0.

## Places and H3 cells

An H3 cell is a regular analytical hexagon. It ignores administrative
boundaries and is not a ward. A ward view is shown only where verified ward
polygons exist; elsewhere the map uses a coarser district or H3 view and
labels it as such.

## Routing

Planned experimental routing can avoid road segments flagged by evidence. It
cannot establish real-time safety, so no route is a guaranteed safe
evacuation route. Consult official sources.

## Exposure

Population exposure is a spatial estimate: a population raster overlaid on a
risk zone. It is not a count of confirmed victims or casualties.

## Evaluation

Models use time-based splits, and spatial holdouts where stated. Random time
splits are avoided because future conditions can leak into training and make
forecast skill look better than it is. Features must be available at the
issue time.

## Promotion

A model must beat the strongest predeclared simple baseline on the same
held-out rows. Promotion needs the lower bound of the paired 95% bootstrap
confidence interval of the improvement to be above zero, plus the model's own
gates. Otherwise the model is published as research only.

## Metrics

For rare events, ROC-AUC alone can look good while alerts are useless.
Reports show PR-AUC with the event prevalence, Brier score, calibration and
the false-alert burden.

## Intervals

An 80% prediction interval is a range meant to contain about 80% of
comparable outcomes. Actual coverage must be checked on held-out data; the
M05 intervals covered 65%; a rule chosen on pre-test years only (T262)
reached 72.8%, still below the 75-85% gate, so they are not published.

## Explanations

SHAP and similar methods describe how a model used its inputs. They are not
causal effects: they do not show that rain caused a flood.

## Memory and reconstruction

City Memory records what this product published and knew after launch.
Reconstructed history is assembled later from historical sources and is
labelled reconstructed. A 2018 replay cannot show this app operating in 2018,
because the app did not exist then.

## Retention

Published normalized snapshots are kept from launch. Storage is finite: at
80% of the budget future capture slows, and at 95% ingestion pauses in
archive-only mode before capacity runs out. Existing published history is
kept, and paused periods are shown.

## Compute

Free GPU sessions (Colab or Kaggle) are allocated opportunistically and are
not guaranteed. Training saves checkpoints every two hours, and CPU baselines
remain valid if a neural challenger is skipped.

## Ask

Ask answers only from retrieved project documents and cites each claim. When
the language-model quota is exhausted or generation is unavailable, Ask shows
cited excerpts labelled as search results instead of a generated answer. A
citation counts only if it names a retrieved chunk and that chunk supports
the claim. Retrieved text is untrusted evidence: instructions inside a
document cannot change Ask's rules or reveal secrets. Without evidence, Ask
reports insufficient evidence instead of guessing.

## Privacy

The project keeps no personal accounts or subscriber database. Planned place
watches stay in the browser on the user's device. Background web push is
disabled because it would need stored subscription identifiers.

## Offline view

A planned offline view shows the time its content was saved. It cannot show
current alerts or guarantee live conditions.
