"""Karnataka hospital siting by greedy maximal coverage (T286, plan item 11).

Question: if ten hospitals were added, which 1 km cells would bring the most people within 10 km
(straight line) of a hospital? Candidates are the populated S16 cells inside an S17 district;
"gap" cells are those beyond the threshold from every S18 OSM hospital (D195 distances from
`atlas.analysis.access`). Greedy maximal coverage adds, one at a time, the candidate that covers
the most not-yet-covered gap people; it is within 1 - 1/e (63%) of the best possible set, not
guaranteed optimal. Reported against simple baselines (the most populous gap cells, one site in
each worst district, random populated cells) and with sensitivity to the number of sites, the
threshold, and dropping 10% of OSM hospitals at random.

Illustrative siting under stated assumptions, never a recommendation: straight-line distance,
OSM completeness, no capacity, no land, cost or road data, modelled population.
"""

from __future__ import annotations

import math

import numpy as np

from atlas.analysis.access import EARTH_KM, nearest_km, unit

SEED = 0
RANDOM_DRAWS = 200
SITES = (5, 10, 20)
THRESHOLDS_KM = (5.0, 10.0, 15.0)
DROP_SHARE, DROP_SEEDS = 0.10, 5


def reach(cand_lonlat: np.ndarray, gap_lonlat: np.ndarray, radius_km: float):
    """Sparse 0/1 matrix (candidates x gap cells): 1 where the great-circle distance <= radius."""
    from scipy.sparse import csr_matrix
    from scipy.spatial import cKDTree

    chord = 2 * math.sin(radius_km / (2 * EARTH_KM))
    pairs = cKDTree(unit(cand_lonlat)).sparse_distance_matrix(
        cKDTree(unit(gap_lonlat)), chord, output_type="ndarray"
    )
    # ndarray output keeps zero-distance pairs (a candidate on its own gap cell)
    ones = np.ones(len(pairs), dtype=np.float64)
    shape = (len(cand_lonlat), len(gap_lonlat))
    return csr_matrix((ones, (pairs["i"], pairs["j"])), shape=shape)


def covered(reach_m, rows, gap_people: np.ndarray) -> float:
    """Gap people within reach of at least one of the candidate `rows`."""
    if len(rows) == 0:
        return 0.0
    hit = np.asarray(reach_m[list(rows)].sum(axis=0)).ravel() > 0
    return float(gap_people[hit].sum())


def greedy(reach_m, gap_people: np.ndarray, k: int) -> tuple[list[int], list[float]]:
    """Greedy maximal coverage: candidate rows in pick order and each pick's marginal gain."""
    w = gap_people.astype(np.float64).copy()
    gain = reach_m @ w
    by_col = reach_m.tocsc()
    picks, gains = [], []
    for _ in range(k):
        i = int(np.argmax(gain))  # ties go to the lowest row, so the run is deterministic
        if gain[i] <= 0:
            break
        cols = reach_m.indices[reach_m.indptr[i] : reach_m.indptr[i + 1]]
        newly = cols[w[cols] > 0]
        picks.append(i)
        gains.append(float(w[newly].sum()))
        gain -= by_col[:, newly] @ w[newly]
        w[newly] = 0
    return picks, gains


def most_populous(gap_rows: np.ndarray, gap_people: np.ndarray, k: int) -> list[int]:
    """Baseline: the k most populous gap cells that are candidates (`gap_rows` = row or -1)."""
    ok = np.flatnonzero(gap_rows >= 0)
    order = ok[np.lexsort((ok, -gap_people[ok]))]
    return [int(gap_rows[j]) for j in order[:k]]


def worst_districts(
    gap_rows: np.ndarray, gap_people: np.ndarray, gap_district: np.ndarray, share: dict, k: int
) -> list[int]:
    """Baseline: in each of the k districts with the largest share of people in gap cells, its
    most populous gap cell."""
    ranked = sorted((d for d in share if share[d] > 0), key=lambda d: (-share[d], d))
    rows = []
    for d in ranked:
        ok = np.flatnonzero((gap_district == d) & (gap_rows >= 0))
        if len(ok):
            rows.append(int(gap_rows[ok[np.argmax(gap_people[ok])]]))
        if len(rows) == k:
            break
    return rows


def random_sites(n_cand: int, k: int, draws: int, seed: int) -> list[np.ndarray]:
    rng = np.random.default_rng(seed)
    return [rng.choice(n_cand, size=k, replace=False) for _ in range(draws)]


def mean_km(km: np.ndarray, people: np.ndarray) -> float:
    return float((km * people).sum() / people.sum())


class Problem:
    """One threshold over fixed cells and hospitals: gap cells, the reach matrix and baselines."""

    def __init__(self, lonlat, people, district, hospitals, cand, radius_km):
        self.lonlat, self.people, self.cand, self.radius = lonlat, people, cand, radius_km
        self.km = nearest_km(lonlat, hospitals)
        gap = np.flatnonzero((self.km > radius_km) & (people > 0))
        self.gap, self.gap_people = gap, people[gap]
        row_of = np.full(len(people), -1)
        row_of[cand] = np.arange(len(cand))
        self.gap_rows = row_of[gap]
        names = np.array([d or "" for d in district])
        self.gap_district = names[gap]
        totals = {d: people[names == d].sum() for d in set(names) - {""}}
        self.share = {
            d: float(self.gap_people[self.gap_district == d].sum() / totals[d]) for d in totals
        }
        self.reach = reach(lonlat[cand], lonlat[gap], radius_km)

    def covered(self, rows) -> float:
        return covered(self.reach, rows, self.gap_people)

    def mean_km_after(self, rows) -> float:
        new = np.minimum(self.km, nearest_km(self.lonlat, self.lonlat[self.cand[list(rows)]]))
        return mean_km(new, self.people)

    def baselines(self, k: int) -> dict[str, list[int]]:
        return {
            "most_populous_gap_cells": most_populous(self.gap_rows, self.gap_people, k),
            "one_per_worst_district": worst_districts(
                self.gap_rows, self.gap_people, self.gap_district, self.share, k
            ),
        }

    def random(self, k: int) -> np.ndarray:
        draws = random_sites(len(self.cand), k, RANDOM_DRAWS, SEED)
        return np.array([self.covered(r) for r in draws])


def sensitivity_row(p: Problem, picks: list[int], k: int) -> dict:
    base = {name: round(p.covered(r)) for name, r in p.baselines(k).items()}
    rand = p.random(k)
    return {
        "sites": k,
        "threshold_km": p.radius,
        "people_beyond_before": round(float(p.gap_people.sum())),
        "greedy_newly_within": round(p.covered(picks[:k])),
        **{f"{name}_newly_within": v for name, v in base.items()},
        "random_mean_newly_within": round(float(rand.mean())),
        "random_max_newly_within": round(float(rand.max())),
        "greedy_mean_km_after": round(p.mean_km_after(picks[:k]), 3),
    }


def build(out) -> dict:  # pragma: no cover - needs local raw files (data/raw)
    """Write summary.json into `out` (a Path); returns arrays for the notebook's figures."""
    import json
    from pathlib import Path

    from atlas.analysis.access import load_inputs

    data = load_inputs()
    lonlat, people, district, hospitals = (
        data[k] for k in ("lonlat", "people", "district", "sites")
    )
    cand = np.flatnonzero((people > 0) & np.array([d is not None for d in district]))
    k_main, r_main, k_max = 10, 10.0, max(SITES)

    problems = {r: Problem(lonlat, people, district, hospitals, cand, r) for r in THRESHOLDS_KM}
    runs = {r: greedy(p.reach, p.gap_people, k_max) for r, p in problems.items()}
    table = [sensitivity_row(problems[r], runs[r][0], k) for r in THRESHOLDS_KM for k in SITES]

    main = problems[r_main]
    chosen, gains = runs[r_main][0][:k_main], runs[r_main][1][:k_main]
    before_km = mean_km(main.km, people)
    sites = []
    for rank, (row, gain) in enumerate(zip(chosen, gains, strict=True), 1):
        cell = cand[row]
        sites.append(
            {
                "rank": rank,
                "district": district[cell],
                "lon": round(float(lonlat[cell, 0]), 2),
                "lat": round(float(lonlat[cell, 1]), 2),
                "people_newly_within_10km": round(gain),
            }
        )
    greedy_cov = main.covered(chosen)
    rand = main.random(k_main)
    versus = {}
    for name, rows in main.baselines(k_main).items():
        cov = main.covered(rows)
        versus[name] = {
            "newly_within_10km": round(cov),
            "mean_km_after": round(main.mean_km_after(rows), 3),
            "greedy_minus_baseline": round(greedy_cov - cov),
            "greedy_over_baseline": round(greedy_cov / cov, 2) if cov else None,
        }
    versus["random_populated_cells"] = {
        "draws": RANDOM_DRAWS,
        "seed": SEED,
        "newly_within_10km_mean": round(float(rand.mean())),
        "newly_within_10km_p95": round(float(np.quantile(rand, 0.95))),
        "newly_within_10km_max": round(float(rand.max())),
        "greedy_minus_mean": round(greedy_cov - float(rand.mean())),
    }

    # completeness check: drop 10% of OSM hospitals, re-run, compare with the main ten sites
    drops = []
    main_xy = lonlat[cand[chosen]]
    for seed in range(DROP_SEEDS):
        keep = np.random.default_rng(100 + seed).random(len(hospitals)) >= DROP_SHARE
        p = Problem(lonlat, people, district, hospitals[keep], cand, r_main)
        rows, _ = greedy(p.reach, p.gap_people, k_main)
        near = nearest_km(main_xy, lonlat[cand[rows]])
        drops.append(
            {
                "seed": 100 + seed,
                "hospitals_kept": int(keep.sum()),
                "people_beyond_10km_before": round(float(p.gap_people.sum())),
                "greedy_newly_within_10km": round(p.covered(rows)),
                "main_sites_with_a_pick_within_10km": int((near <= r_main).sum()),
            }
        )

    summary = {
        "state": "ka",
        "question": "Which ten 1 km cells, if each had a hospital, would bring the most people "
        "within 10 km (straight line) of a hospital?",
        "status": "Illustrative siting under stated assumptions; not a recommendation.",
        "method": "Greedy maximal coverage over populated S16 cells inside an S17 district "
        "(within 63% of the optimum; not guaranteed optimal). Objective: people newly within "
        "the threshold of a hospital. Secondary: people-weighted mean straight-line km.",
        "inputs": data["inputs"],
        "hospitals": int(len(hospitals)),
        "candidates": int(len(cand)),
        "people": round(float(people.sum())),
        "headline": {
            "sites": k_main,
            "threshold_km": r_main,
            "people_beyond_10km_before": round(float(main.gap_people.sum())),
            "greedy_newly_within_10km": round(greedy_cov),
            "share_of_gap_closed": round(greedy_cov / float(main.gap_people.sum()), 4),
            "mean_km_before": round(before_km, 3),
            "mean_km_after": round(main.mean_km_after(chosen), 3),
        },
        "sites": sites,
        "baselines": versus,
        "baseline_not_run": "District headquarters or town points: no place points in the local "
        "inputs (S18 holds amenities only); the most populous gap cell per worst district "
        "stands in.",
        "sensitivity": table,
        "osm_completeness_check": {"drop_share": DROP_SHARE, "runs": drops},
        "limits": [
            "Straight-line distance from the 1 km cell centre, not road distance or travel time.",
            "OpenStreetMap hospitals are volunteer-mapped and thinner in rural areas; a gap cell "
            "may already have an unmapped hospital, which would change the picks.",
            "No capacity, staffing, hospital size or demand model; every hospital counts the same.",
            "No land, cost, road, terrain or ownership data; a picked cell is a 1 km area, not a "
            "buildable site.",
            "WorldPop 2025 is a modelled 1 km population estimate.",
            "Not an emergency service and no claim that any location is safe or adequate.",
        ],
    }
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(
        json.dumps(summary, indent=1) + "\n", encoding="utf-8", newline="\n"
    )
    curve = {
        "greedy": np.cumsum(runs[r_main][1]),
        **{
            name: [main.covered(main.baselines(k)[name]) for k in range(1, k_max + 1)]
            for name in ("most_populous_gap_cells", "one_per_worst_district")
        },
        "random_mean": [main.random(k).mean() for k in range(1, k_max + 1)],
    }
    return {
        "summary": summary,
        "lonlat": lonlat,
        "people": people,
        "km": main.km,
        "hospitals": hospitals,
        "chosen": lonlat[cand[chosen]],
        "curve": curve,
    }
