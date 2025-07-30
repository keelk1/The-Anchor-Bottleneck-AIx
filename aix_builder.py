#!/usr/bin/env python3
"""
Compute AIx (Anchorability Index) for every Swiss VC/CVC fund
and export two files:
  • aix_switzerland.csv : full per-fund scores (kept private)
  • aix_tiers.csv       : aggregated counts + medians (public)
"""

import csv, pandas as pd, re, pathlib

INPUT_FILE  = "OpenVC.csv"
FULL_OUT    = "aix_switzerland.csv"
AGG_OUT     = "aix_tiers.csv"

# --- helper functions -------------------------------------------------
def norm(col): return col.replace("\ufeff", "").strip().lower().replace(" ", "_")

def parse_money(txt):
    if not txt: return 0
    txt = txt.lower().replace(",", "").strip()
    if "k" in txt: return int(float(txt.replace("k", ""))*1_000)
    if "m" in txt: return int(float(txt.replace("m", ""))*1_000_000)
    digits = re.sub(r"[^\d]", "", txt)
    return int(digits) if digits else 0

def score_ticket(min_cheque):      # TP 0-20
    if   min_cheque >= 1_000_000: return 20
    elif min_cheque >=   500_000: return 15
    elif min_cheque >=   200_000: return 10
    elif min_cheque >=   100_000: return  5
    return 0

def score_stage(stage):            # SF 0-20
    stage = stage.lower() if stage else ""
    if "prototype" in stage or "early revenue" in stage: return 20
    if "seed" in stage: return 10
    return 0

def score_focus(countries):        # FC 0-20
    if not countries: return 0
    c = countries.lower()
    if "switzerland" in c or "dach" in c: return 20
    if "europe" in c: return 10
    return 0

def score_follow(max_cheque):      # FD 0-20
    if   max_cheque >= 2_000_000: return 20
    elif max_cheque >=1_000_000:  return 15
    elif max_cheque >= 500_000:   return 10
    elif max_cheque >= 250_000:   return 5
    return 0

def score_activity():              # EP 10 (placeholder)
    return 10                      # quick static bucket; can refine later
# ----------------------------------------------------------------------

def build_scores(path="OpenVC.csv"):
    rows=[]
    with open(path, newline="", encoding="utf-8") as f:
        r=csv.DictReader(f)
        col={norm(c):c for c in r.fieldnames}
        for row in r:
            if "switzerland" not in (row.get(col["global_hq"],"")).lower(): continue
            if row.get(col["investor_type"],"").strip().lower() not in {"vc","cvc","corporate vc"}: continue

            min_c=parse_money(row.get(col["first_cheque_minimum"],""))
            max_c=parse_money(row.get(col["first_cheque_maximum"],""))

            tp=score_ticket(min_c)
            sf=score_stage(row.get(col["stage_of_investment"],""))
            fc=score_focus(row.get(col["countries_of_investment"],""))
            fd=score_follow(max_c)
            ep=score_activity()

            aix=tp+sf+fc+fd+ep
            tier="A" if aix>=70 else "B" if aix>=50 else "C"

            rows.append({
                "name":row.get(col["investor_name"]),
                "tp":tp,"sf":sf,"fc":fc,"fd":fd,"ep":ep,
                "aix":aix,"tier":tier,
                "cheque_min":min_c,"cheque_max":max_c,
            })
    return pd.DataFrame(rows)

def main():
    df=build_scores(INPUT_FILE)
    df.to_csv(FULL_OUT,index=False)

    tier_stats=df.groupby("tier").agg(
        count=("name","count"),
        median_min=("cheque_min","median"),
        median_aix=("aix","median")
    ).reset_index()
    tier_stats.to_csv(AGG_OUT,index=False)
    print(tier_stats)

if __name__=="__main__":
    main()