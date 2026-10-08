"""
Regner ut tallene til Task 1 (EDA) på HELE datasettet og lagrer figurer.
Kjøres med:  python eda_stats.py
Leser CSV-en i biter, så den går fint på en vanlig laptop.
Resultatet skrives ut og lagres i output/eda_stats.txt, figurene i figures/.
"""

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from haversine import Unit, haversine_vector

CSV_PATH = "data/porto.csv"
CHUNK_SIZE = 50_000
JUMP_KM = 1.0
LOCAL_TZ = "Europe/Lisbon"
# Grov boks rundt fastlands-Portugal, for å finne helt umulige koordinater.
LON_RANGE = (-9.6, -6.1)
LAT_RANGE = (36.9, 42.2)
OUTPUT_DIR = Path("output")
FIG_DIR = Path("figures")


def per_trip(polylines):
    """n_points, distance_km (uten hopp), gps_jumps, punkter utenfor boksen."""
    n = np.array([len(p) for p in polylines], dtype=np.int64)
    dist = np.zeros(len(polylines))
    jumps = np.zeros(len(polylines), dtype=np.int64)
    outside = np.zeros(len(polylines), dtype=np.int64)
    if n.sum() == 0:
        return n, dist, jumps, outside
    coords = np.array([pt for p in polylines for pt in p], dtype=float)
    owner = np.repeat(np.arange(len(polylines)), n)
    out = ((coords[:, 0] < LON_RANGE[0]) | (coords[:, 0] > LON_RANGE[1]) |
           (coords[:, 1] < LAT_RANGE[0]) | (coords[:, 1] > LAT_RANGE[1]))
    np.add.at(outside, owner[out], 1)
    if len(coords) > 1:
        steps = haversine_vector(coords[:-1, ::-1], coords[1:, ::-1], Unit.KILOMETERS)
        same = owner[:-1] == owner[1:]
        jump = same & (steps > JUMP_KM)
        ok = same & ~jump
        np.add.at(dist, owner[:-1][ok], steps[ok])
        np.add.at(jumps, owner[:-1][jump], 1)
    return n, dist, jumps, outside


def summarize_chunk(chunk):
    """Én rad per tur med det som trengs videre (ikke selve polylinjen)."""
    polylines = [json.loads(p) for p in chunk["POLYLINE"]]
    n, dist, jumps, outside = per_trip(polylines)
    return pd.DataFrame({
        "row": chunk.index,
        "trip_id": chunk["TRIP_ID"].to_numpy(),
        "call_type": chunk["CALL_TYPE"].to_numpy(),
        "origin_call_set": chunk["ORIGIN_CALL"].notna().to_numpy(),
        "origin_stand_set": chunk["ORIGIN_STAND"].notna().to_numpy(),
        "taxi_id": chunk["TAXI_ID"].to_numpy(),
        "timestamp": chunk["TIMESTAMP"].to_numpy(),
        "day_type": chunk["DAY_TYPE"].to_numpy(),
        "missing": chunk["MISSING_DATA"].astype(str).str.lower().eq("true").to_numpy(),
        # hash i stedet for selve teksten, så minnebruken holder seg nede
        "polyline_hash": pd.util.hash_array(chunk["POLYLINE"].to_numpy(dtype=object)),
        "n_points": n, "distance_km": dist, "gps_jumps": jumps, "outside": outside,
    })


def main():
    parts = []
    nan_counts = None
    n_columns = None
    for chunk in pd.read_csv(CSV_PATH, chunksize=CHUNK_SIZE):
        n_columns = chunk.shape[1]
        nan_counts = chunk.isna().sum() if nan_counts is None else nan_counts + chunk.isna().sum()
        parts.append(summarize_chunk(chunk))
        print(f"  lest {parts[-1]['row'].iloc[-1] + 1:,} rader")
    report(pd.concat(parts, ignore_index=True), nan_counts, n_columns)


def report(df, nan_counts, n_columns):
    OUTPUT_DIR.mkdir(exist_ok=True)
    FIG_DIR.mkdir(exist_ok=True)
    df["duration_min"] = np.maximum(df["n_points"] - 1, 0) * 15 / 60
    df["local"] = (pd.to_datetime(df["timestamp"], unit="s", utc=True)
                   .dt.tz_convert(LOCAL_TZ).dt.tz_localize(None))

    out = []
    def line(text=""):
        out.append(text)

    # --- Oversikt
    line("OVERSIKT")
    line(f"  Rader: {len(df):,}   Kolonner: {n_columns}")
    line(f"  Unike TRIP_ID: {df['trip_id'].nunique():,}   Unike taxier: {df['taxi_id'].nunique():,}")
    line(f"  GPS-punkter totalt: {int(df['n_points'].sum()):,}")
    line(f"  Første start (lokal): {df['local'].min()}   Siste start: {df['local'].max()}")

    # --- NaN
    line("\nNaN PER KOLONNE")
    for col, count in nan_counts.items():
        line(f"  {col}: {int(count):,}")

    # --- CALL_TYPE og ORIGIN_*
    line("\nCALL_TYPE")
    for ct, share in df["call_type"].value_counts(normalize=True).sort_index().items():
        line(f"  {ct}: {(df['call_type'] == ct).sum():,} ({100 * share:.1f} %)")
    a, b = df["call_type"] == "A", df["call_type"] == "B"
    line(f"  ORIGIN_CALL satt for A: {df.loc[a, 'origin_call_set'].mean() * 100:.1f} %, "
         f"satt utenfor A: {int(df.loc[~a, 'origin_call_set'].sum()):,} turer")
    line(f"  ORIGIN_STAND satt for B: {df.loc[b, 'origin_stand_set'].mean() * 100:.1f} %, "
         f"satt utenfor B: {int(df.loc[~b, 'origin_stand_set'].sum()):,} turer, "
         f"B-turer uten stand: {int((b & ~df['origin_stand_set']).sum()):,}")

    # --- DAY_TYPE og MISSING_DATA
    line("\nDAY_TYPE")
    for dt, count in df["day_type"].value_counts().items():
        line(f"  {dt}: {count:,}")
    line(f"\nMISSING_DATA = True: {int(df['missing'].sum())} turer "
         f"(på {df.loc[df['missing'], 'taxi_id'].nunique()} taxier), "
         f"av dem med under 3 punkter: {int((df['missing'] & (df['n_points'] < 3)).sum())}")

    # --- Duplikater
    dup_mask = df["trip_id"].duplicated(keep=False)
    dups = df[dup_mask]
    line("\nDUPLIKATER I TRIP_ID")
    line(f"  TRIP_ID som forekommer mer enn én gang: {dups['trip_id'].nunique()}")
    line(f"  Rader involvert: {len(dups)}   Overskytende rader: {len(dups) - dups['trip_id'].nunique()}")
    exact = df.drop(columns=["row", "local"]).duplicated(keep="first").sum()
    line(f"  Helt identiske rader (overskytende): {int(exact)}")
    g = dups.sort_values("row").groupby("trip_id")
    same_taxi_ts = int((g["taxi_id"].nunique().eq(1) & g["timestamp"].nunique().eq(1)).sum())
    first_shorter = int((g["n_points"].first() < g["n_points"].max()).sum())
    line(f"  Duplikat-ID-er med samme taxi og tidsstempel: {same_taxi_ts} av {dups['trip_id'].nunique()}")
    line(f"  Duplikat-ID-er der første kopi har færre punkter enn den lengste: {first_shorter}")

    # --- Punkter per tur
    line("\nGPS-PUNKTER PER TUR")
    for k in (0, 1, 2):
        line(f"  {k} punkter: {int((df['n_points'] == k).sum()):,}")
    invalid = int((df["n_points"] < 3).sum())
    line(f"  Under 3 punkter (ugyldige): {invalid:,} ({100 * invalid / len(df):.2f} %)")
    valid = df[df["n_points"] >= 3]
    for col, unit in (("n_points", "punkter"), ("duration_min", "min"), ("distance_km", "km")):
        q = valid[col].quantile([0.5, 0.95, 0.99])
        line(f"  Gyldige turer, {col}: median {q[0.5]:.1f}, 95 % {q[0.95]:.1f}, "
             f"99 % {q[0.99]:.1f}, maks {valid[col].max():.1f} {unit}")

    # --- Datakvalitet i polylinjene
    line("\nDATAKVALITET I POLYLINJENE")
    line(f"  Turer med minst ett GPS-hopp (> {JUMP_KM} km på 15 s): "
         f"{int((df['gps_jumps'] > 0).sum()):,}")
    line(f"  Turer med punkter utenfor Portugal-boksen: {int((df['outside'] > 0).sum()):,}")
    speed = valid["distance_km"] / (valid["duration_min"] / 60)
    line(f"  Gyldige turer med snittfart > 120 km/t (etter at hopp er fjernet): "
         f"{int((speed > 120).sum()):,}")
    line(f"  Gyldige turer lenger enn 3 timer: {int((valid['duration_min'] > 180).sum()):,}")

    # --- Taxier og tid
    per_taxi = df["taxi_id"].value_counts()
    line("\nTURER PER TAXI")
    line(f"  snitt {per_taxi.mean():.1f}, median {per_taxi.median():.0f}, "
         f"min {per_taxi.min()}, maks {per_taxi.max()}")
    line(f"  Taxier med under 100 turer: {int((per_taxi < 100).sum())}")

    text = "\n".join(out)
    print(text)
    (OUTPUT_DIR / "eda_stats.txt").write_text(text + "\n", encoding="utf-8")

    make_figures(df, valid, per_taxi)


def make_figures(df, valid, per_taxi):
    """Én figur per tema, lagret i figures/ for bruk i rapporten."""
    plt.rcParams.update({"figure.dpi": 150, "axes.spines.top": False,
                         "axes.spines.right": False, "axes.grid": True,
                         "grid.alpha": 0.3, "axes.axisbelow": True})
    color = "#3b6ea5"

    def save(fig, name):
        fig.tight_layout()
        fig.savefig(FIG_DIR / name, bbox_inches="tight")
        plt.close(fig)
        print(f"  lagret {FIG_DIR / name}")

    # 1. CALL_TYPE
    counts = df["call_type"].value_counts().sort_index()
    labels = {"A": "A: sentral", "B": "B: holdeplass", "C": "C: på gaten"}
    fig, ax = plt.subplots(figsize=(5.5, 3.5))
    bars = ax.bar([labels.get(c, c) for c in counts.index], counts.values, color=color)
    for bar, v in zip(bars, counts.values):
        ax.annotate(f"{v:,}\n({100 * v / counts.sum():.1f} %)".replace(",", " "),
                    (bar.get_x() + bar.get_width() / 2, v), ha="center", va="bottom", fontsize=8)
    ax.set_ylabel("Antall turer")
    ax.set_ylim(0, counts.max() * 1.2)
    ax.set_title("Turer per CALL_TYPE")
    save(fig, "fig1_call_type.png")

    # 2. Antall punkter: ugyldige vs. gyldige
    buckets = pd.Series({
        "0": (df["n_points"] == 0).sum(), "1": (df["n_points"] == 1).sum(),
        "2": (df["n_points"] == 2).sum(), "3 eller flere": (df["n_points"] >= 3).sum()})
    fig, ax = plt.subplots(figsize=(5.5, 3.5))
    bars = ax.bar(buckets.index, buckets.values,
                  color=["#c0504d", "#c0504d", "#c0504d", color])
    for bar, v in zip(bars, buckets.values):
        ax.annotate(f"{v:,}".replace(",", " "), (bar.get_x() + bar.get_width() / 2, v),
                    ha="center", va="bottom", fontsize=8)
    ax.set_yscale("log")
    ax.set_xlabel("GPS-punkter i turen")
    ax.set_ylabel("Antall turer (log-skala)")
    ax.set_title("Ugyldige turer (rødt) har færre enn 3 punkter")
    save(fig, "fig2_invalid_trips.png")

    # 3. Fordeling av punkter, varighet og distanse for gyldige turer
    fig, ax = plt.subplots(1, 3, figsize=(12, 3.4))
    specs = [("n_points", 300, "GPS-punkter", "Punkter per tur"),
             ("duration_min", 90, "minutter", "Varighet"),
             ("distance_km", 40, "km", "Distanse (uten GPS-hopp)")]
    for a, (col, cap, unit, title) in zip(ax, specs):
        a.hist(valid[col].clip(upper=cap), bins=60, color=color)
        med = valid[col].median()
        a.axvline(med, color="black", linestyle="--", linewidth=1)
        a.annotate(f"median {med:.1f}", (med, a.get_ylim()[1] * 0.9),
                   xytext=(5, 0), textcoords="offset points", fontsize=8)
        a.set_xlabel(f"{unit} (kuttet ved {cap})")
        a.set_title(title)
    ax[0].set_ylabel("Antall turer")
    save(fig, "fig3_trip_distributions.png")

    # 4. Tid: per måned og per time på døgnet (lokal tid)
    fig, ax = plt.subplots(1, 2, figsize=(12, 3.4))
    # Måned etter UTC, siden datasettet er avgrenset til juli 2013 - juni 2014 i UTC.
    utc_month = pd.to_datetime(df["timestamp"], unit="s").dt.to_period("M")
    per_month = utc_month.value_counts().sort_index()
    ax[0].bar(per_month.index.astype(str), per_month.values, color=color)
    ax[0].tick_params(axis="x", rotation=90, labelsize=8)
    ax[0].set_title("Turer per måned")
    ax[0].set_ylabel("Antall turer")
    per_hour = df["local"].dt.hour.value_counts().sort_index()
    ax[1].bar(per_hour.index, per_hour.values, color=color)
    for edge in (6, 12, 18):
        ax[1].axvline(edge - 0.5, color="black", linestyle=":", linewidth=1)
    ax[1].set_xticks(range(0, 24, 2))
    ax[1].set_xlabel("Starttime (lokal tid, stiplet = tidsintervallene i oppgave 4b)")
    ax[1].set_title("Turer per time på døgnet")
    save(fig, "fig4_time.png")

    # 5. Turer per taxi
    fig, ax = plt.subplots(figsize=(5.5, 3.5))
    ax.hist(per_taxi, bins=40, color=color)
    ax.axvline(per_taxi.mean(), color="black", linestyle="--", linewidth=1)
    ax.annotate(f"snitt {per_taxi.mean():.0f}", (per_taxi.mean(), ax.get_ylim()[1] * 0.9),
                xytext=(5, 0), textcoords="offset points", fontsize=8)
    ax.set_xlabel("Antall turer i perioden")
    ax.set_ylabel("Antall taxier")
    ax.set_title(f"Turer per taxi ({len(per_taxi)} taxier)")
    save(fig, "fig5_trips_per_taxi.png")

    # 6. Datakvalitet: snittfart for gyldige turer, med og uten GPS-hopp
    fig, ax = plt.subplots(figsize=(6, 3.5))
    hours = valid["duration_min"] / 60
    speed = (valid["distance_km"] / hours).clip(upper=150)
    ax.hist(speed, bins=75, color=color)
    ax.axvline(120, color="#c0504d", linestyle="--", linewidth=1)
    ax.annotate(f"{int((valid['distance_km'] / hours > 120).sum())} turer > 120 km/t",
                (120, ax.get_ylim()[1] * 0.85), xytext=(-5, 0), textcoords="offset points",
                ha="right", fontsize=8, color="#c0504d")
    ax.set_xlabel("Gjennomsnittsfart, km/t (GPS-hopp fjernet, kuttet ved 150)")
    ax.set_ylabel("Antall turer")
    jumps = int((df["gps_jumps"] > 0).sum())
    ax.set_title(f"Snittfart per tur  ({jumps:,} turer hadde GPS-hopp > 1 km)".replace(",", " "))
    save(fig, "fig6_speed_quality.png")

    print(f"\nFigurer lagret i {FIG_DIR}/")


if __name__ == "__main__":
    main()
