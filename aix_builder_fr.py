#!/usr/bin/env python3
# AIx — France only (V4, EP neutralized, Tier U, FR keywords)
# Usage:
#   python aix_builder_fr_only.py --input OpenVC.csv \
#     --targets "250000,700000,1200000" \
#     --full-out aix_france_v4.csv --agg-out aix_tiers_fr_v4.csv

import csv, pandas as pd, re, argparse
from pathlib import Path

DEFAULT_INPUT  = "OpenVC.csv"
DEFAULT_FULL   = "aix_france_v4.csv"
DEFAULT_AGG    = "aix_tiers_fr_v4.csv"

# ---------- helpers ----------
def norm(col: str) -> str:
    return col.replace("\ufeff", "").strip().lower().replace(" ", "_")

def parse_money(txt) -> int:
    """Parse '€250k', '1.2m', 'CHF 300 000' -> int (in units)"""
    if not txt: return 0
    s = str(txt).lower().strip()
    for tok in ["eur","chf","usd","gbp","€","$","£"]:
        s = s.replace(tok, "")
    s = s.replace(" ", "")
    unit = None
    if s.endswith("m"): unit, s = "m", s[:-1]
    elif s.endswith("k"): unit, s = "k", s[:-1]
    # remove thousands sep, keep decimal
    s = re.sub(r"(?<=\d)[, ](?=\d{3}\b)", "", s)
    s = s.replace(",", ".")
    try:
        val = float(s)
    except Exception:
        digits = re.sub(r"[^\d.]", "", s)
        val = float(digits or 0)
    if unit == "m": val *= 1_000_000
    if unit == "k": val *= 1_000
    return int(round(val))

def contains_fr(text) -> bool:
    if not text: return False
    t = str(text).lower()
    # HQ or investment footprint in France (common cities/regions)
    return (
        "france" in t or "paris" in t or "ile-de-france" in t or "île-de-france" in t or
        "idf" in t or "lyon" in t or "marseille" in t or "toulouse" in t or "lille" in t or
        "nantes" in t or "bordeaux" in t or "rennes" in t or "strasbourg" in t or
        "grenoble" in t or "nice" in t or "sophia antipolis" in t or "sophia-antipolis" in t
    )

def in_fr(hq: str, countries: str) -> bool:
    return contains_fr(hq) or contains_fr(countries)

# ---------- Scoring (FR, EP neutralized) ----------
def score_stage(stage: str) -> int:
    """SF (0–20) — valorise explicitement le pré-amorçage / prototype"""
    s = (stage or "").lower()
    preseed_keys = [
        "prototype","early revenue","pre-seed","pre seed","preseed",
        "pré-amorçage","pre-amorcage","pre-amorçage","pre amorcage","pre amorçage",
        "idea","idéation","ideation"
    ]
    if any(k in s for k in preseed_keys):
        return 20
    if ("seed" in s) or ("amorçage" in s) or ("amorcage" in s) or ("amorçage" in s):
        return 8
    return 0

def score_focus_fr(countries: str, hq: str) -> int:
    """FC (0–15) — ancrage FR"""
    c = (countries or "").lower()
    h = (hq or "").lower()
    if contains_fr(h): return 15         # HQ France
    if contains_fr(c): return 10         # Invest FR
    if "europe" in c or "eu" in c: return 5
    return 0

def score_anchor_capacity(max_cheque: int, target_raise: int, sf: int) -> int:
    """AC (0–30) — capacité à fermer l’écart; cap si pas explicitement pré-seed"""
    if not max_cheque or max_cheque <= 0:
        base = 0
    else:
        ratio = max_cheque / float(target_raise)
        base = 30 if ratio >= 1 else int(round(ratio * 30))
    if sf < 20:
        base = min(base, 15)  # si pas explicitement pré-seed
    return base

def score_flex(min_cheque: int, max_cheque: int, target_raise: int) -> int:
    """FS (0–25) — overlap du range du fonds avec la bande [0.6×target ; 1.1×target]"""
    if not (min_cheque and max_cheque) or max_cheque <= 0 or min_cheque < 0 or max_cheque < min_cheque:
        return 0
    lower, upper = 0.6*target_raise, 1.1*target_raise
    overlap = max(0.0, min(max_cheque, upper) - max(min_cheque, lower))
    band = (upper - lower)
    return int(round(25 * (overlap / band))) if band > 0 else 0

def confidence_flag(has_min: bool, has_max: bool, has_stage: bool, has_countries: bool) -> str:
    score = sum([has_min, has_max, has_stage, has_countries])
    if score >= 4: return "high"
    if score >= 2: return "mid"
    return "low"

def malus_from_confidence(flag: str) -> int:
    return {"high": 0, "mid": -5, "low": -10}.get(flag, -5)

def assign_tier(aix):
    if aix is None: return "U"   # Unscored
    if aix >= 75: return "A"
    if aix >= 55: return "B"
    return "C"

def is_unscored(min_c: int, max_c: int) -> bool:
    """Tier U si min ET max manquants/0 (vrai trou de data)"""
    return (min_c is None or min_c <= 0) and (max_c is None or max_c <= 0)

def parse_targets(s: str):
    parts = [p.strip() for p in str(s).split(",") if p.strip()]
    vals = []
    for p in parts:
        try:
            vals.append(int(float(p)))
        except:
            pass
    return tuple(vals) if vals else (250_000, 700_000, 1_200_000)

# ---------- core ----------
def build_scores(path, targets=(250_000, 700_000, 1_200_000), types=("vc","corporate vc","cvc")) -> pd.DataFrame:
    rows=[]
    with open(path, newline="", encoding="utf-8") as f:
        r=csv.DictReader(f)
        col={norm(c):c for c in r.fieldnames}

        for row in r:
            inv_type = (row.get(col.get("investor_type",""), "") or "").strip().lower()
            if inv_type not in types:
                continue

            hq = row.get(col.get("global_hq",""), "")
            countries = row.get(col.get("countries_of_investment",""), "")
            if not in_fr(hq, countries):
                continue

            name = row.get(col.get("investor_name",""), "")
            website = row.get(col.get("website",""), "")
            stage_raw = row.get(col.get("stage_of_investment",""), "")
            min_c = parse_money(row.get(col.get("first_cheque_minimum",""), ""))
            max_c = parse_money(row.get(col.get("first_cheque_maximum",""), ""))

            sf = score_stage(stage_raw)                # 0–20
            fc = score_focus_fr(countries, hq)         # 0–15
            conf = confidence_flag(min_c>0, max_c>0, bool(stage_raw), bool(countries))
            malus = malus_from_confidence(conf)

            # Tier U si pas de min ET pas de max
            if is_unscored(min_c, max_c):
                rows.append({
                    "name": name, "website": website, "type": inv_type,
                    "hq_raw": hq, "countries_raw": countries, "stage_raw": stage_raw,
                    "cheque_min": None, "cheque_max": None,
                    "sf": sf, "fc": fc, "confidence": conf, "malus": malus,
                    "ac_250k": None, "fs_250k": None,
                    "ac_700k": None, "fs_700k": None,
                    "ac_1200k": None, "fs_1200k": None,
                    "aix_250k": None, "tier_250k": "U",
                    "aix_700k": None, "tier_700k": "U",
                    "aix_1200k": None, "tier_1200k": "U",
                    "aix": None, "tier": "U",
                    "status": "unscored:no_min_and_max"
                })
                continue

            ac_scores, fs_scores, aix_fin, tiers = {}, {}, {}, {}
            # EP est neutralisé : score = (AC+FS+SF+FC) rescalé /100 + malus
            for t in targets:
                ac = score_anchor_capacity(max_c, t, sf)   # 0–30
                fs = score_flex(min_c, max_c, t)           # 0–25
                raw90 = ac + fs + sf + fc                  # max 90
                raw100 = int(round(raw90 * (100.0/90.0)))  # /100
                fin = max(0, min(100, raw100 + malus))

                ac_scores[t] = ac
                fs_scores[t] = fs
                aix_fin[t] = fin
                tiers[t] = assign_tier(fin)

            # défaut = scénario médian (700k)
            default_t = 700_000 if 700_000 in targets else list(targets)[0]
            rows.append({
                "name": name, "website": website, "type": inv_type,
                "hq_raw": hq, "countries_raw": countries, "stage_raw": stage_raw,
                "cheque_min": min_c, "cheque_max": max_c,
                "sf": sf, "fc": fc, "confidence": conf, "malus": malus,
                f"ac_{targets[0]//1000}k": ac_scores.get(targets[0]), f"fs_{targets[0]//1000}k": fs_scores.get(targets[0]),
                f"ac_{targets[1]//1000}k": ac_scores.get(targets[1]), f"fs_{targets[1]//1000}k": fs_scores.get(targets[1]),
                f"ac_{targets[2]//1000}k": ac_scores.get(targets[2]), f"fs_{targets[2]//1000}k": fs_scores.get(targets[2]),
                f"aix_{targets[0]//1000}k": aix_fin.get(targets[0]), f"tier_{targets[0]//1000}k": tiers.get(targets[0]),
                f"aix_{targets[1]//1000}k": aix_fin.get(targets[1]), f"tier_{targets[1]//1000}k": tiers.get(targets[1]),
                f"aix_{targets[2]//1000}k": aix_fin.get(targets[2]), f"tier_{targets[2]//1000}k": tiers.get(targets[2]),
                "aix": aix_fin.get(default_t), "tier": tiers.get(default_t),
                "status": "scored"
            })
    return pd.DataFrame(rows)

def aggregate_tiers(df: pd.DataFrame, col_aix="aix", col_tier="tier") -> pd.DataFrame:
    g = df.groupby(col_tier).agg(
        count=("name","count"),
        median_min=("cheque_min","median"),
        median_aix=(col_aix,"median")
    ).reset_index()
    order={"A":0,"B":1,"C":2,"U":3}
    g["order"]=g["tier"].map(order).fillna(9)
    return g.sort_values("order").drop(columns=["order"])

# ---------- CLI ----------
def main(argv=None):
    p = argparse.ArgumentParser(description="AIx France-only (V4, EP neutralized, Tier U)")
    p.add_argument("--input", default=DEFAULT_INPUT, help="Chemin du CSV OpenVC")
    p.add_argument("--targets", default="250000,700000,1200000",
                   help="Montants cibles (comma-separated), ex: '250000,700000,1200000'")
    p.add_argument("--full-out", default=DEFAULT_FULL, help="CSV de sortie détaillé")
    p.add_argument("--agg-out", default=DEFAULT_AGG, help="CSV agrégat tiers")
    args = p.parse_args(argv)

    targets = parse_targets(args.targets)
    df = build_scores(args.input, targets=targets)
    df.to_csv(args.full_out, index=False)

    agg = aggregate_tiers(df, col_aix="aix", col_tier="tier")
    agg.to_csv(args.agg_out, index=False)
    print(agg)

if __name__ == "__main__":
    main()