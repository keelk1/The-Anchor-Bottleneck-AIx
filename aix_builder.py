
#!/usr/bin/env python3
import csv, pandas as pd, re, argparse, sys
from pathlib import Path

DEFAULT_INPUT  = "OpenVC.csv"
DEFAULT_FULL   = "aix_switzerland_v2.csv"
DEFAULT_AGG    = "aix_tiers_v2.csv"
ACTIVITY_FILE  = "activity_labels.csv"  # optional

# ---------- helpers ----------
def norm(col): 
    return col.replace("\ufeff", "").strip().lower().replace(" ", "_")

def parse_money(txt):
    if not txt: return 0
    s = str(txt).lower().strip()
    # strip currency symbols/codes, spaces
    for tok in ["eur","chf","usd","gbp","€","$","£"]:
        s = s.replace(tok, "")
    s = s.replace(" ", "")
    # unit suffixes
    unit = None
    if s.endswith("m"): unit, s = "m", s[:-1]
    elif s.endswith("k"): unit, s = "k", s[:-1]
    # remove thousand separators, keep decimal
    s = re.sub(r"(?<=\d)[, ](?=\d{3}\b)", "", s)  # 1,000 → 1000
    s = s.replace(",", ".")                       # decimal comma → dot
    try:
        val = float(s)
    except Exception:
        digits = re.sub(r"[^\d.]", "", s)
        val = float(digits or 0)
    if unit == "m": val *= 1_000_000
    if unit == "k": val *= 1_000
    return int(round(val))

def contains_ch(text):
    if not text: 
        return False
    t = str(text).lower()
    return ("switzerland" in t) or ("suisse" in t) or ("schweiz" in t) or ("confederation suisse" in t) or ("lausanne" in t) or ("geneva" in t) or ("zurich" in t) or ("zug" in t) or ("vaud" in t) or ("bern" in t) or ("basel" in t) or ("ch" in t and "swit" in t)

def score_ticket(min_cheque):  # TP 0-20
    if   min_cheque >= 1_000_000: return 20
    elif min_cheque >=   500_000: return 15
    elif min_cheque >=   200_000: return 10
    elif min_cheque >=   100_000: return  5
    return 0

def score_stage(stage):  # SF 0-20
    s = (stage or "").lower()
    if any(k in s for k in ["prototype", "early revenue", "pre-seed", "pre seed", "preseed", "idea", "patent"]):
        return 20
    if "seed" in s: 
        return 10
    return 0

def score_focus(countries, hq):  # FC 0-20
    c = (countries or "").lower()
    h = (hq or "").lower()
    if contains_ch(c) or contains_ch(h) or "dach" in c:
        return 20
    if "europe" in c or "eu" in c:
        return 10
    return 0

def score_anchor_capacity(max_cheque, target_raise):  # AC 0-20
    if not max_cheque or max_cheque <= 0: 
        return 0
    ratio = max_cheque / float(target_raise)
    return 20 if ratio >= 1 else int(round(ratio * 20))

def load_activity_map(path=ACTIVITY_FILE):
    p = Path(path)
    if not p.exists():
        return {}
    try:
        df = pd.read_csv(p)
        # expect columns: name, ep (0/10/20)
        m = {}
        for _, r in df.iterrows():
            name = str(r.get("name") or r.get("fund") or "").strip()
            ep   = int(r.get("ep", 10))
            if name:
                m[name.lower()] = ep
        return m
    except Exception:
        return {}

def score_activity(name, ep_map):  # EP 0/10/20 (V0 default=10)
    ep = ep_map.get((name or "").lower(), None)
    if ep in (0, 10, 20):
        return ep
    return 10

def confidence_flag(has_min, has_max, has_stage, has_countries):
    score = sum([has_min, has_max, has_stage, has_countries])
    if score >= 4: return "high"
    if score >= 2: return "mid"
    return "low"

def assign_tier(aix):
    if aix >= 70: return "A"
    if aix >= 50: return "B"
    return "C"

# ---------- core ----------
def build_scores(path, targets=(300_000, 800_000, 1_500_000), country="CH", types=("vc","corporate vc")):
    rows=[]
    ep_map = load_activity_map()
    with open(path, newline="", encoding="utf-8") as f:
        r=csv.DictReader(f)
        col={norm(c):c for c in r.fieldnames}
        for row in r:
            inv_type = (row.get(col.get("investor_type",""), "") or "").strip().lower()
            if inv_type not in types: 
                continue
            hq = row.get(col.get("global_hq",""), "")
            countries = row.get(col.get("countries_of_investment",""), "")
            # Swiss relevance filter: HQ in CH OR invests in CH
            if country == "CH" and not (contains_ch(hq) or contains_ch(countries)):
                continue

            name = row.get(col.get("investor_name",""), "")
            website = row.get(col.get("website",""), "")
            stage_raw = row.get(col.get("stage_of_investment",""), "")
            min_c = parse_money(row.get(col.get("first_cheque_minimum",""), ""))
            max_c = parse_money(row.get(col.get("first_cheque_maximum",""), ""))

            # components
            tp = score_ticket(min_c)
            sf = score_stage(stage_raw)
            fc = score_focus(countries, hq)
            ep = score_activity(name, ep_map)

            # scenarios
            ac_scores = {t: score_anchor_capacity(max_c, t) for t in targets}
            aix_scores = {t: tp + ac_scores[t] + sf + fc + ep for t in targets}
            tiers = {t: assign_tier(aix_scores[t]) for t in targets}

            # default = 800k
            default_t = 800_000 if 800_000 in targets else list(targets)[0]
            rows.append({
                "name": name,
                "website": website,
                "type": inv_type,
                "hq_raw": hq,
                "countries_raw": countries,
                "stage_raw": stage_raw,
                "cheque_min": min_c,
                "cheque_max": max_c,
                "tp": tp, "sf": sf, "fc": fc, "ep": ep,
                "ac_300k": ac_scores.get(300_000, None),
                "ac_800k": ac_scores.get(800_000, None),
                "ac_1500k": ac_scores.get(1_500_000, None),
                "aix_300k": aix_scores.get(300_000, None),
                "aix_800k": aix_scores.get(800_000, None),
                "aix_1500k": aix_scores.get(1_500_000, None),
                "tier_300k": tiers.get(300_000, None),
                "tier_800k": tiers.get(800_000, None),
                "tier_1500k": tiers.get(1_500_000, None),
                "aix": aix_scores.get(default_t, None),
                "tier": tiers.get(default_t, None),
                "confidence": confidence_flag(min_c>0, max_c>0, bool(stage_raw), bool(countries)),
            })
    return pd.DataFrame(rows)

def aggregate_tiers(df, col_aix="aix", col_tier="tier"):
    g = df.groupby(col_tier).agg(
        count=("name","count"),
        median_min=("cheque_min","median"),
        median_aix=(col_aix,"median")
    ).reset_index()
    # order tiers A,B, C if present
    order = {"A":0,"B":1,"C":2}
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
