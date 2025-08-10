
#!/usr/bin/env python3
import csv, pandas as pd, re, argparse
from pathlib import Path

DEFAULT_INPUT  = "OpenVC.csv"
DEFAULT_FULL   = "aix_switzerland_v4.csv"
DEFAULT_AGG    = "aix_tiers_sw_v4.csv"

# ---------- helpers ----------
def norm(col):
    return col.replace("\ufeff", "").strip().lower().replace(" ", "_")

def parse_money(txt):
    if not txt: return 0
    s = str(txt).lower().strip()
    for tok in ["eur","chf","usd","gbp","€","$","£"]:
        s = s.replace(tok, "")
    s = s.replace(" ", "")
    unit = None
    if s.endswith("m"): unit, s = "m", s[:-1]
    elif s.endswith("k"): unit, s = "k", s[:-1]
    s = re.sub(r"(?<=\d)[, ](?=\d{3}\b)", "", s)  # thousands
    s = s.replace(",", ".")                       # decimal comma -> dot
    try:
        val = float(s)
    except Exception:
        digits = re.sub(r"[^\d.]", "", s)
        val = float(digits or 0)
    if unit == "m": val *= 1_000_000
    if unit == "k": val *= 1_000
    return int(round(val))

def contains_ch(text):
    if not text: return False
    t = str(text).lower()
    return ("switzerland" in t) or ("suisse" in t) or ("schweiz" in t) or ("confederation suisse" in t) or ("lausanne" in t) or ("geneva" in t) or ("zurich" in t) or ("zug" in t) or ("vaud" in t) or ("bern" in t) or ("basel" in t) or ("ch" in t and "swit" in t)

# ---------- V3.1 logic carried + Tier U ----------
def score_stage(stage):  # SF (0-20)
    s = (stage or "").lower()
    if any(k in s for k in ["prototype","early revenue","pre-seed","pre seed","preseed","idea","patent"]):
        return 20
    if "seed" in s: 
        return 8
    return 0

def score_focus(countries, hq):  # FC (0-15)
    c = (countries or "").lower()
    h = (hq or "").lower()
    if contains_ch(h):  # HQ in CH
        return 15
    if contains_ch(c) or "dach" in c:
        return 10
    if "europe" in c or "eu" in c:
        return 5
    return 0

def score_anchor_capacity(max_cheque, target_raise, sf):  # AC (0-30), cap if SF<20
    if not max_cheque or max_cheque <= 0:
        base = 0
    else:
        ratio = max_cheque / float(target_raise)
        base = 30 if ratio >= 1 else int(round(ratio * 30))
    if sf < 20:
        base = min(base, 15)
    return base

def score_flex(min_cheque, max_cheque, target_raise):  # FS (0-25) overlap with [0.6*target, 1.1*target]
    if not (min_cheque and max_cheque) or max_cheque <= 0 or min_cheque < 0 or max_cheque < min_cheque:
        return 0
    lower, upper = 0.6*target_raise, 1.1*target_raise
    overlap = max(0.0, min(max_cheque, upper) - max(min_cheque, lower))
    band = (upper - lower)
    return int(round(25 * (overlap / band))) if band > 0 else 0

def confidence_flag(has_min, has_max, has_stage, has_countries):
    score = sum([has_min, has_max, has_stage, has_countries])
    if score >= 4: return "high"
    if score >= 2: return "mid"
    return "low"

def malus_from_confidence(flag):
    return {"high": 0, "mid": -5, "low": -10}.get(flag, -5)

def assign_tier(aix):
    if aix >= 75: return "A"
    if aix >= 55: return "B"
    return "C"

def is_unscored(min_c, max_c):
    # "poubelle" / data-gap: BOTH min and max are missing or zero
    return (min_c is None or min_c <= 0) and (max_c is None or max_c <= 0)

# ---------- core ----------
def build_scores(path, targets=(300_000, 800_000, 1_500_000), country="CH", types=("vc","corporate vc")):
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
            if country == "CH" and not (contains_ch(hq) or contains_ch(countries)):
                continue

            name = row.get(col.get("investor_name",""), "")
            website = row.get(col.get("website",""), "")
            stage_raw = row.get(col.get("stage_of_investment",""), "")
            min_c = parse_money(row.get(col.get("first_cheque_minimum",""), ""))
            max_c = parse_money(row.get(col.get("first_cheque_maximum",""), ""))

            sf = score_stage(stage_raw)             # 0-20
            fc = score_focus(countries, hq)         # 0-15

            conf = confidence_flag(min_c>0, max_c>0, bool(stage_raw), bool(countries))
            malus = malus_from_confidence(conf)

            if is_unscored(min_c, max_c):
                # Put into Tier U (Unscored / Data gap). No AIx computed.
                rows.append({
                    "name": name, "website": website, "type": inv_type,
                    "hq_raw": hq, "countries_raw": countries, "stage_raw": stage_raw,
                    "cheque_min": None if min_c<=0 else min_c,
                    "cheque_max": None if max_c<=0 else max_c,
                    "sf": sf, "fc": fc, "confidence": conf, "malus": malus,
                    "ac_300k": None, "fs_300k": None,
                    "ac_800k": None, "fs_800k": None,
                    "ac_1500k": None, "fs_1500k": None,
                    "aix_300k": None, "tier_300k": "U",
                    "aix_800k": None, "tier_800k": "U",
                    "aix_1500k": None, "tier_1500k": "U",
                    "aix": None, "tier": "U",
                    "status": "unscored:no_min_and_max"
                })
                continue

            ac_scores, fs_scores = {}, {}
            aix_fin, tiers = {}, {}

            for t in targets:
                ac = score_anchor_capacity(max_c, t, sf)      # 0-30
                fs = score_flex(min_c, max_c, t)              # 0-25
                raw90 = ac + fs + sf + fc                     # max 90
                raw100 = int(round(raw90 * (100.0/90.0)))     # rescale
                fin = max(0, min(100, raw100 + malus))
                ac_scores[t] = ac
                fs_scores[t] = fs
                aix_fin[t] = fin
                tiers[t] = assign_tier(fin)

            default_t = 800_000 if 800_000 in targets else list(targets)[0]
            rows.append({
                "name": name, "website": website, "type": inv_type,
                "hq_raw": hq, "countries_raw": countries, "stage_raw": stage_raw,
                "cheque_min": min_c, "cheque_max": max_c,
                "sf": sf, "fc": fc, "confidence": conf, "malus": malus,
                "ac_300k": ac_scores.get(300_000), "fs_300k": fs_scores.get(300_000),
                "ac_800k": ac_scores.get(800_000), "fs_800k": fs_scores.get(800_000),
                "ac_1500k": ac_scores.get(1_500_000), "fs_1500k": fs_scores.get(1_500_000),
                "aix_300k": aix_fin.get(300_000), "tier_300k": tiers.get(300_000),
                "aix_800k": aix_fin.get(800_000), "tier_800k": tiers.get(800_000),
                "aix_1500k": aix_fin.get(1_500_000), "tier_1500k": tiers.get(1_500_000),
                "aix": aix_fin.get(default_t), "tier": tiers.get(default_t),
                "status": "scored"
            })
    return pd.DataFrame(rows)

def aggregate_tiers(df, col_aix="aix", col_tier="tier"):
    g = df.groupby(col_tier).agg(
        count=("name","count"),
        median_min=("cheque_min","median"),
        median_aix=(col_aix,"median")
    ).reset_index()
    order={"A":0,"B":1,"C":2,"U":3}
    g["order"]=g["tier"].map(order).fillna(9)
    return g.sort_values("order").drop(columns=["order"])

def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--input", default=DEFAULT_INPUT)
    p.add_argument("--country", default="CH")
    p.add_argument("--full-out", default=DEFAULT_FULL)
    p.add_argument("--agg-out", default=DEFAULT_AGG)
    args = p.parse_args(argv)

    df = build_scores(args.input, country=args.country)
    df.to_csv(args.full_out, index=False)
    agg = aggregate_tiers(df, col_aix="aix", col_tier="tier")
    agg.to_csv(args.agg_out, index=False)
    print(agg)

if __name__ == "__main__":
    main()
