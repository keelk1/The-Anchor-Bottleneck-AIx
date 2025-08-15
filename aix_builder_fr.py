#!/usr/bin/env python3
# AIx — France (Top-20 Tier A simple table + summary)
# Usage:
#   python aix_builder_fr_only.py --input OpenVC.csv \
#     --targets "250k,700k,1.2M" \
#     --full-out aix_france_v4.csv \
#     --agg-out aix_tiers_fr_v4.csv \
#     --summary-out aix_tiers_fr_summary_v4.csv \
#     --topn 20

import csv, pandas as pd, re, argparse
from pathlib import Path

DEFAULT_INPUT    = "OpenVC.csv"
DEFAULT_FULL     = "aix_france_v4.csv"
DEFAULT_AGG      = "aix_tiers_fr_v4.csv"            # -> Top-20 Tier A (simple)
DEFAULT_SUMMARY  = "aix_tiers_fr_summary_v4.csv"    # -> counts/% per scenario

# ---------- helpers ----------
def norm(col: str) -> str:
    return col.replace("\ufeff", "").strip().lower().replace(" ", "_")

def parse_money(txt) -> int:
    """Parse '€250k', '1.2m', 'CHF 300 000' -> int (units)."""
    if not txt: return 0
    s = str(txt).lower().strip()
    for tok in ["eur","chf","usd","gbp","€","$","£"]:
        s = s.replace(tok, "")
    s = s.replace(" ", "")
    unit = None
    if s.endswith("m"): unit, s = "m", s[:-1]
    elif s.endswith("k"): unit, s = "k", s[:-1]
    s = re.sub(r"(?<=\d)[, ](?=\d{3}\b)", "", s)  # thousands sep
    s = s.replace(",", ".")                       # decimal comma -> dot
    try:
        val = float(s)
    except Exception:
        digits = re.sub(r"[^\d.]", "", s)
        val = float(digits or 0)
    if unit == "m": val *= 1_000_000
    if unit == "k": val *= 1_000
    return int(round(val))

def parse_targets(txt: str):
    """Supports '250000,700000,1200000' or '250k,700k,1.2M'."""
    out=[]
    for tok in str(txt).split(","):
        t = tok.strip().lower()
        if not t: 
            continue
        mult = 1
        if t.endswith("m"): mult, t = 1_000_000, t[:-1]
        elif t.endswith("k"): mult, t = 1_000, t[:-1]
        t = t.replace(" ", "").replace(",", ".")
        try:
            out.append(int(round(float(t) * mult)))
        except:
            pass
    return tuple(out) if out else (250_000, 700_000, 1_200_000)

def label_for(target: int) -> str:
    """300000 -> '300k', 1500000 -> '1500k'."""
    return f"{int(round(target/1000))}k"

def contains_fr(text) -> bool:
    if not text: return False
    t = str(text).lower()
    return ("france" in t or "paris" in t or "ile-de-france" in t or "île-de-france" in t or
            "idf" in t or "lyon" in t or "marseille" in t or "toulouse" in t or "lille" in t or
            "nantes" in t or "bordeaux" in t or "rennes" in t or "strasbourg" in t or
            "grenoble" in t or "nice" in t or "sophia antipolis" in t or "sophia-antipolis" in t)

def in_fr(hq: str, countries: str) -> bool:
    return contains_fr(hq) or contains_fr(countries)

# ---------- scoring (FR) ----------
def score_stage(stage: str) -> int:
    """SF (0–20) — bonus explicite pré-amorçage/early."""
    s = (stage or "").lower()
    preseed_keys = [
        "prototype","early revenue","pre-seed","pre seed","preseed",
        "pré-amorçage","pre-amorcage","pre-amorçage","pre amorcage","pre amorçage",
        "idea","idéation","ideation"
    ]
    if any(k in s for k in preseed_keys):
        return 20
    if ("seed" in s) or ("amorçage" in s) or ("amorcage" in s):
        return 8
    return 0

def score_focus_fr(countries: str, hq: str) -> int:
    """FC (0–15) — ancrage FR."""
    c = (countries or "").lower()
    h = (hq or "").lower()
    if contains_fr(h): return 15         # HQ France
    if contains_fr(c): return 10         # Invest FR
    if "europe" in c or "eu" in c: return 5
    return 0

def score_anchor_capacity(max_cheque: int, target_raise: int, sf: int) -> int:
    """AC (0–30) — capacité à couvrir le target; cap si pas explicitement early."""
    if not max_cheque or max_cheque <= 0:
        base = 0
    else:
        ratio = max_cheque / float(target_raise)
        base = 30 if ratio >= 1 else int(round(ratio * 30))
    if sf < 20:
        base = min(base, 15)
    return base

def score_flex(min_cheque: int, max_cheque: int, target_raise: int) -> int:
    """FS (0–25) — overlap du range avec la bande [0.6×target ; 1.1×target]."""
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
    """Tier U si min ET max manquants/0."""
    return (min_c is None or min_c <= 0) and (max_c is None or max_c <= 0)

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

            sf = score_stage(stage_raw)               # 0–20
            fc = score_focus_fr(countries, hq)        # 0–15
            conf = confidence_flag(min_c>0, max_c>0, bool(stage_raw), bool(countries))
            malus = malus_from_confidence(conf)

            # Tier U : pas de min ET pas de max
            if is_unscored(min_c, max_c):
                # prépare des colonnes scenario-based vides
                row_dict = {
                    "name": name, "website": website, "type": inv_type,
                    "hq_raw": hq, "countries_raw": countries, "stage_raw": stage_raw,
                    "cheque_min": None, "cheque_max": None,
                    "sf": sf, "fc": fc, "confidence": conf, "malus": malus,
                    "aix": None, "tier": "U",
                    "status": "unscored:no_min_and_max"
                }
                for t in targets:
                    lab = label_for(t)
                    row_dict[f"ac_{lab}"] = None; row_dict[f"fs_{lab}"] = None
                    row_dict[f"aix_{lab}"] = None; row_dict[f"tier_{lab}"] = "U"
                rows.append(row_dict)
                continue

            ac_scores, fs_scores, aix_fin, tiers = {}, {}, {}, {}
            for t in targets:
                ac = score_anchor_capacity(max_c, t, sf)
                fs = score_flex(min_c, max_c, t)
                raw90 = ac + fs + sf + fc
                raw100 = int(round(raw90 * (100.0/90.0)))
                fin = max(0, min(100, raw100 + malus))

                ac_scores[t] = ac; fs_scores[t] = fs
                aix_fin[t] = fin; tiers[t] = assign_tier(fin)

            default_t = 700_000 if 700_000 in targets else list(targets)[0]
            row_dict = {
                "name": name, "website": website, "type": inv_type,
                "hq_raw": hq, "countries_raw": countries, "stage_raw": stage_raw,
                "cheque_min": min_c, "cheque_max": max_c,
                "sf": sf, "fc": fc, "confidence": conf, "malus": malus,
                "aix": aix_fin.get(default_t), "tier": tiers.get(default_t),
                "status": "scored"
            }
            # ajoute colonnes par scénario avec labels '250k' / '700k' / '1200k'
            for t in targets:
                lab = label_for(t)
                row_dict[f"ac_{lab}"]  = ac_scores.get(t)
                row_dict[f"fs_{lab}"]  = fs_scores.get(t)
                row_dict[f"aix_{lab}"] = aix_fin.get(t)
                row_dict[f"tier_{lab}"]= tiers.get(t)

            rows.append(row_dict)
    return pd.DataFrame(rows)

# ---------- Top-20 simple & summary ----------
def topA_simple(df: pd.DataFrame, targets, topn=20) -> pd.DataFrame:
    """Top-N A per scenario with only fund info + rank_20 + AIx."""
    blocks=[]
    for t in targets:
        lab = label_for(t)
        tier_col = f"tier_{lab}"
        aix_col  = f"aix_{lab}"

        subset = df[df[tier_col] == "A"].copy()
        if subset.empty:
            continue

        # tri: AIx desc, puis cheque_max, puis SF/FC
        subset = subset.sort_values(
            by=[aix_col, "cheque_max", "sf", "fc"],
            ascending=[False, False, False, False]
        ).head(topn)

        out = subset[[
            "name","website","type","hq_raw","countries_raw","stage_raw",
            "cheque_min","cheque_max",aix_col
        ]].rename(columns={
            "name":"fund_name","website":"website","type":"type",
            "hq_raw":"hq","countries_raw":"countries","stage_raw":"stage",
            "cheque_min":"min_check","cheque_max":"max_check",
            aix_col:"aix"
        })

        out.insert(0, "scenario", lab)
        out.insert(1, "rank_20", range(1, len(out)+1))
        blocks.append(out)

    return pd.concat(blocks, ignore_index=True) if blocks else pd.DataFrame(
        columns=["scenario","rank_20","fund_name","website","type","hq","countries","stage","min_check","max_check","aix"]
    )

def tiers_summary_by_scenario(df: pd.DataFrame, targets) -> pd.DataFrame:
    rows=[]; order=["A","B","C","U"]
    for t in targets:
        lab = label_for(t); col = f"tier_{lab}"
        vc = df[col].value_counts(); total = int(vc.sum())
        for tier in order:
            cnt = int(vc.get(tier, 0))
            pct = round((cnt/total*100.0), 1) if total>0 else 0.0
            rows.append({"scenario":lab, "tier":tier, "count":cnt, "percent":pct})
    return pd.DataFrame(rows)

# ---------- CLI ----------
def main(argv=None):
    p = argparse.ArgumentParser(description="AIx France (Top-20 Tier A per scenario + summary)")
    p.add_argument("--input", default=DEFAULT_INPUT, help="Chemin du CSV OpenVC")
    p.add_argument("--targets", default="250k,700k,1200k",
                   help="Montants cibles (comma-separated), ex: '250k,700k,1200k'")
    p.add_argument("--full-out", default=DEFAULT_FULL, help="CSV détaillé par fonds")
    p.add_argument("--agg-out", default=DEFAULT_AGG, help="Top-20 Tier A (simple) par scénario")
    p.add_argument("--summary-out", default=DEFAULT_SUMMARY, help="Résumé A/B/C/U par scénario")
    p.add_argument("--topn", type=int, default=20, help="Taille du Top-N")
    args = p.parse_args(argv)

    targets = parse_targets(args.targets)

    df = build_scores(args.input, targets=targets)
    df.to_csv(args.full_out, index=False)

    topA = topA_simple(df, targets, topn=args.topn)
    topA.to_csv(args.agg_out, index=False)
    print(f"[Top-20] wrote {len(topA)} rows -> {args.agg_out}")

    summary = tiers_summary_by_scenario(df, targets)
    summary.to_csv(args.summary_out, index=False)
    print(f"[Summary] wrote {len(summary)} rows -> {args.summary_out}")

if __name__ == "__main__":
    main()
