# GATE-CORE: core data availability report (T222)

Date: 5 Nov 2026. Rules: amendments A4. Inputs: discovery tasks T008 (S28), T030 (S40) and
T085 (S43). Each discovery record cites evidence pages by ID; the pages themselves are kept
locally in `data/raw` with their SHA256 in the committed manifests.

**Result: 2 of 3 checks fail.** The A4 fallbacks are proposed as decision D17, which needs
owner approval (H11) before any fallback task starts.

| Check | Result | Evidence |
|---|---|---|
| C1 KWRIS daily history | **Fail** | [s28.yaml](../../configs/sources/s28.yaml), [s28.md](../sources/s28.md), [manifest](../../tests/fixtures/s28/manifest.json) |
| C2 Bengaluru ward flood labels | **Fail** | [s43.yaml](../../configs/sources/s43.yaml), [s43.md](../sources/s43.md), [manifest](../../tests/fixtures/s43/manifest.json) |
| Ward boundary version | **Pass** | [s40.yaml](../../configs/sources/s40.yaml), [s40.md](../sources/s40.md), [manifest](../../tests/fixtures/s40/manifest.json) |

## C1 KWRIS daily history: fail

Criterion: at least 5 reservoirs with daily level or storage for at least 3 monsoon seasons, with
known units and datum. M02 itself needs daily history from 2017 to 2024.

- The only public reservoir data is a map layer with **one latest row per reservoir** (36
  reservoirs). Filtering it to K.R.Sagara returns a single row (S28 e07, e08).
- 10 of the 36 readings are more than nine months old; one dates from 23 Oct 2021 (e07).
- **No units or datum** are stated for level, storage or flow (e01, e06, e07).
- The footer says "All Rights Reserved"; there is no open licence (e01, e04, e05).
- The Web API needs an account. Its sign-up form asks for name, email, mobile number and
  organisation, and the agent does not create accounts (e02, e03).

Measured against the criterion: 0 reservoirs with daily history, 0 monsoon seasons, units
unknown.

## C2 Bengaluru ward flood labels: fail

Criterion: at least 100 documented positive ward-days across at least 3 monsoon seasons, plus an
explicit coverage rule for negatives. M01 adds: at least 10 events, independently documented
inundation, and audited negatives.

- **No official source** (OpenCity, KSNDMC, Bengaluru Megha Sandesha) publishes dated ward-level
  flood impacts (S43 e02 to e05, e09 to e11). The BBMP and GBA websites failed TLS verification
  and were not checked (S43 `failed_fetches`).
- The flood-prone location maps have no dates (e03, e04): they can be features, not labels.
- The only dated ward-level record is the **I Change My City complaints log** (Janaagraha, a
  civic NGO, CC BY-SA): 136 ward-days in June to November with a "Flooding/Waterlogging"
  complaint across 2019 to 2022 (2019: 52, 2020: 34, 2021: 35, 2022: 15) (e07, e08).

The complaints reach the count, but fail the rest of the criterion:

| Requirement | Complaints log |
|---|---|
| At least 100 positive ward-days | Yes: 136 |
| At least 3 monsoon seasons | Yes: 2019, 2020, 2021 (2022 ends on 31 Jul) |
| Independently documented inundation | **No**: citizen complaints; no authority confirms them |
| Explicit coverage rule for negatives | **No**: a ward-day without a complaint is not a verified dry day |
| Stable reporting | **No**: complaints fell from 7,383 in 2019 to 1,551 in 2022 |

## Ward boundary version: pass

Criterion: official ward polygons with a release date.

- The GBA 2025 final ward map has 369 wards across 5 corporations, notified on 19 Nov 2025. Its
  source is listed as GBA, with licence "Other (Public Domain)" (S40 e02 to e04).
- It uses WGS84 coordinates inside Bengaluru, and the published key `(corporation_id, ward_id)`
  is unique for all 369 wards (e04).
- Caveat: OpenCity does not say whether the KML is GBA's own file or digitised from the notified
  maps (e03).
- Past monsoons used the 198-ward BBMP map, which has no licence: local research only (e06, e07).
- No Karnataka taluk polygons were found (e11), so taluk-level work uses district or H3 views.

## Proposed decision D17 (needs owner approval, H11)

| Check | Proposed fallback (A4) | Tasks pulled into P1 |
|---|---|---|
| C1 | **M07 Kerala seven-day dam forecast** replaces M02 as core C1 | T113, T114 (KSEB daily water level), T130 to T132 |
| C2 | **M08 Kerala flood classifier with the 2018 held-out replay** replaces M01 as core C2. If its labels also fail, C2 becomes M05 (taluk drought outlook) | T119 (Kerala 2018 flood dataset), T129, T133 to T135 |
| Ward boundary | No change | none |

Also proposed:

1. **Verify the fallback data first.** T113 (KSEB daily water level) and T119 (Kerala 2018 flood
   data) are unverified, so run them straight after approval. Only then start the C1 and C2 model
   tasks, so a failing fallback shows up within two sessions.
2. **Keep M01, M02 and M03 in the plan as blocked**, with the retry conditions in s28.yaml and
   s43.yaml. M01's model card allows a fallback product, a rainfall exposure index that is
   explicitly not a probability, and it can still use the GBA 2025 wards.
3. **Do not use the complaints log as ground truth.** Without a coverage rule for negatives, any
   precision or PR-AUC computed on it would be inflated or meaningless. It can be shown as a
   separate, clearly labelled "citizen complaints" layer, if its CC BY-SA terms are followed.

### Owner options

- **Approve D17 as proposed** (recommended): Kerala models become C1 and C2. This follows A4
  exactly and keeps the honest-ML rules.
- **Approve D17, but also try to unblock KWRIS**: you register a KWRIS account (personal details)
  or email the ACIWRM helpdesk for daily history. If it arrives with units and a licence, re-run
  T008, and M02 can return as a second reservoir model.
- **Use the complaints log for C2 instead of M08**: needs a written coverage rule for negatives
  and is recorded as non-official labels. Not recommended (see C2 above).
