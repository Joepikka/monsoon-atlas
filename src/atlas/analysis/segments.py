"""Karnataka district segmentation (T285, plan item 4): which districts are alike?

Six per-district features, all committed and licence-safe: ERA5 southwest-season rain level,
year-to-year variability and northeast-season share (S02, CC BY 4.0, 2001-2025), the IMD rain
trend as a Sen slope in percent per decade (an index, no mm), hospital distance (D195) and
log population. n = 30, so this is a typology, not a discovery; stability decides whether it is
published.

Rules fixed before the results were looked at:
- features are robust-scaled (median, IQR); one of any pair with |r| > 0.9 is dropped (the later
  one in FEATURES);
- k-means for k = 2..6 (20 starts, seed 285); k = the highest silhouette among values where every
  segment has at least 3 districts; a tie goes to the smaller k;
- stability: 1000 bootstrap resamples of districts, k-means refit, all 30 districts assigned to
  the nearest centroid, adjusted Rand index against the full-data labels;
- median bootstrap ARI >= 0.6 -> "descriptive typology"; otherwise "exploratory" (no stable
  clusters claimed).
"""

from __future__ import annotations

import csv
import hashlib
import json
import statistics
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
NORMALS = ROOT / "configs/static/ka/monsoon-normals.json"
CLIMATE = ROOT / "reports/eda/08_climate_product/climate.json"
ACCESS = ROOT / "reports/eda/11_ka_hospital_access/district_access.csv"
SEED, K_RANGE, MIN_SIZE, BOOT, ARI_BAR, CORR_BAR = 285, range(2, 7), 3, 1000, 0.6, 0.9

FEATURES = ["sw_rain_level", "sw_rain_cv", "ne_share", "rain_trend", "hospital_km", "log_people"]
# (low wording, high wording) used to name a segment from its centroid
WORDS = {
    "sw_rain_level": ("dry", "wet"),
    "sw_rain_cv": ("steady rain", "erratic rain"),
    "ne_share": ("little autumn rain", "much autumn rain"),
    "rain_trend": ("drying trend", "wetting trend"),
    "hospital_km": ("close to hospitals", "far from hospitals"),
    "log_people": ("sparsely populated", "populous"),
}


def season_total(table: dict) -> list[float]:
    """The 25 reference-year season totals sit at the last checkpoint (sorted, order is lost)."""
    return table[max(table, key=int)]


def load_features() -> tuple[list[str], np.ndarray, dict]:
    """(districts, raw feature matrix, input hashes) from committed files only."""
    normals = json.loads(NORMALS.read_text("utf-8"))["districts"]
    trend = {
        r["area"].removesuffix(" (Karnataka district)"): r["sen_slope_pct_per_decade"]
        for r in json.loads(CLIMATE.read_text("utf-8"))["trend"]
        if r["area"].endswith("(Karnataka district)")
    }
    with ACCESS.open(encoding="utf-8") as f:
        access = {r["district"]: r for r in csv.DictReader(f)}
    names = sorted(normals)
    if not set(names) == set(trend) == set(access):
        raise ValueError("district lists differ between the normals, trend and access files")
    rows = []
    for d in names:
        sw = season_total(normals[d]["southwest"])
        ne = statistics.median(season_total(normals[d]["northeast"]))
        sw_med = statistics.median(sw)
        rows.append(
            [
                sw_med,
                statistics.pstdev(sw) / statistics.mean(sw),
                ne / (ne + sw_med),
                trend[d],
                float(access[d]["mean_km"]),
                float(np.log10(float(access[d]["people"]))),
            ]
        )
    hashes = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()[:16] for p in (NORMALS, CLIMATE, ACCESS)
    }
    return names, np.array(rows), hashes


def robust_scale(x: np.ndarray) -> np.ndarray:
    q1, med, q3 = np.percentile(x, [25, 50, 75], axis=0)
    return (x - med) / np.where(q3 - q1 == 0, 1.0, q3 - q1)


def drop_collinear(x: np.ndarray, names: list[str], bar: float = CORR_BAR):
    """Keep columns; drop the later of any pair with |r| > bar. Returns (kept, dropped pairs)."""
    corr = np.corrcoef(x, rowvar=False)
    kept: list[int] = []
    dropped: list[dict] = []
    for j in range(x.shape[1]):
        hit = next((i for i in kept if abs(corr[i, j]) > bar), None)
        if hit is None:
            kept.append(j)
        else:
            r = round(float(corr[hit, j]), 3)
            dropped.append({"dropped": names[j], "kept": names[hit], "r": r})
    return kept, dropped


def kmeans(x: np.ndarray, k: int, seed: int = SEED, n_init: int = 20):
    from sklearn.cluster import KMeans

    return KMeans(n_clusters=k, n_init=n_init, random_state=seed).fit(x)


def choose_k(x: np.ndarray) -> tuple[int, list[dict]]:
    """Highest silhouette among k whose smallest segment has >= MIN_SIZE; tie -> smaller k."""
    from sklearn.metrics import silhouette_score

    table = []
    for k in K_RANGE:
        labels = kmeans(x, k).labels_
        table.append(
            {
                "k": k,
                "silhouette": round(float(silhouette_score(x, labels)), 4),
                "smallest_segment": int(np.bincount(labels).min()),
            }
        )
    ok = [t for t in table if t["smallest_segment"] >= MIN_SIZE]
    if not ok:
        raise ValueError("no k gives segments of at least 3 districts")
    best = max(ok, key=lambda t: (t["silhouette"], -t["k"]))
    return best["k"], table


def bootstrap_ari(x: np.ndarray, k: int, reference: np.ndarray, runs: int = BOOT) -> np.ndarray:
    """ARI of full-data labels vs labels from a k-means fitted on a district bootstrap sample."""
    from sklearn.metrics import adjusted_rand_score

    rng = np.random.default_rng(SEED)
    out = []
    for _ in range(runs):
        idx = rng.integers(0, len(x), len(x))
        seed = int(rng.integers(1 << 31))
        if len(np.unique(idx)) <= k:
            continue
        labels = kmeans(x[idx], k, seed=seed, n_init=5).predict(x)
        out.append(adjusted_rand_score(reference, labels))
    return np.array(out)


def name_segments(raw, scaled, labels, kept) -> list[dict]:
    """Plain names from each centroid's two largest robust-scaled gaps (|z| >= 0.5); centroids are
    reported in original units. Nothing is named that the numbers do not show."""
    out = []
    for s in sorted(set(labels.tolist())):
        z = scaled[labels == s].mean(axis=0)
        order = sorted(range(len(kept)), key=lambda i: -abs(z[i]))
        phrases = [WORDS[FEATURES[kept[i]]][int(z[i] > 0)] for i in order if abs(z[i]) >= 0.5]
        out.append(
            {
                "segment": s + 1,
                "name": ", ".join(phrases[:2]) or "close to the state middle on every feature",
                "centroid": {
                    FEATURES[j]: round(float(raw[labels == s, j].mean()), 2)
                    for j in range(raw.shape[1])
                },
            }
        )
    return out


def run() -> dict:
    """Everything the notebook publishes, as plain Python objects and arrays."""
    from sklearn.cluster import AgglomerativeClustering
    from sklearn.metrics import adjusted_rand_score, silhouette_score

    districts, raw, hashes = load_features()
    kept, dropped = drop_collinear(raw, FEATURES)
    scaled = robust_scale(raw[:, kept])
    k, table = choose_k(scaled)
    labels = kmeans(scaled, k).labels_
    ari = bootstrap_ari(scaled, k, labels)
    median = float(np.median(ari))
    ward = AgglomerativeClustering(n_clusters=k, linkage="ward").fit_predict(scaled)
    # same analysis without Bangalore (the one big-city outlier), kept openly as a sensitivity run
    keep = np.array([d != "Bangalore" for d in districts])
    no_blr = kmeans(robust_scale(raw[keep][:, kept]), k).labels_
    stable = median >= ARI_BAR
    segs = name_segments(raw, scaled, labels, kept)
    summary = {
        "task": "T285",
        "n_districts": len(districts),
        "features_used": [FEATURES[j] for j in kept],
        "features_dropped_collinear": dropped,
        "scaling": "robust (median, IQR); population as log10",
        "k_rule": "highest silhouette over k=2..6 among k whose smallest segment has >= 3 "
        "districts; tie goes to the smaller k (fixed before results were seen)",
        "silhouette_by_k": table,
        "k_excluded_small_segment": [t["k"] for t in table if t["smallest_segment"] < MIN_SIZE],
        "k": k,
        "silhouette": next(t["silhouette"] for t in table if t["k"] == k),
        "bootstrap": {
            "runs": int(len(ari)),
            "median_ari": round(median, 3),
            "p10_ari": round(float(np.percentile(ari, 10)), 3),
            "p90_ari": round(float(np.percentile(ari, 90)), 3),
            "bar": ARI_BAR,
        },
        "ward_comparison": {
            "silhouette": round(float(silhouette_score(scaled, ward)), 4),
            "ari_vs_kmeans": round(float(adjusted_rand_score(labels, ward)), 3),
        },
        "without_bangalore_ari_vs_kmeans": round(
            float(adjusted_rand_score(labels[keep], no_blr)), 3
        ),
        "segments": [{**s, "districts": int((labels == s["segment"] - 1).sum())} for s in segs],
        "publish_decision": "descriptive typology" if stable else "exploratory",
        "decision_rule": f"median bootstrap ARI >= {ARI_BAR} -> descriptive typology; otherwise "
        "exploratory, no stable clusters claimed",
        "input_sha256_16": hashes,
        "limits": [
            "n = 30 districts: a typology for orientation, not a discovery or a forecast.",
            "Rain level, variability and autumn share are ERA5 reanalysis at one grid point per "
            "district (2001-2025), not gauge counts; the trend is the IMD-based Sen slope index "
            "(1981-2025). No IMD mm value is published.",
            "Hospital distance is straight-line to the nearest OSM hospital (D195); OSM is "
            "thinner in rural areas.",
            "Segment names describe each centroid against the state middle; they are not causes.",
        ],
    }
    return {
        "districts": districts,
        "labels": labels,
        "scaled": scaled,
        "ari": ari,
        "segs": segs,
        "summary": summary,
    }


def write_segments_csv(path: Path, result: dict) -> None:
    names = {s["segment"]: s["name"] for s in result["segs"]}
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["district", "segment", "segment_name"])
        for d, lab in zip(result["districts"], result["labels"], strict=True):
            w.writerow([d, int(lab) + 1, names[int(lab) + 1]])


def write_summary(path: Path, summary: dict) -> None:
    path.write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
