Excellente idée. Voici un README.md prêt à copier-coller dans ton repo GitHub. Tu pourras ensuite simplement mettre un lien vers le repo dans la section “Reproducing the analysis” de l’article.

⸻

AIx — Anchor Investor Index (OpenVC-only)

AIx is a transparent, scenario-sensitive scoring model that ranks venture investors by their ability to anchor a pre-seed/seed round.
It uses only public OpenVC data and outputs per-fund sub-scores (AC/FS/SF/FC), a confidence penalty, an overall AIx score (0–100), and a Tier (A/B/C/U) to guide outreach sequencing.
	•	Paper: The Anchor Bottleneck (link to Medium)
	•	Dataset: OpenVC export 2025-07 — MD5 8983450fb099e20bc16c91d4a0e8af8f
	•	Status: Open-source (MIT)

⸻

1) What AIx measures

AIx = anchoring capacity, not “generic alignment.”
For a given target round size, AIx answers: which investors are most likely to anchor this round quickly?

Components (interpretable)
	•	AC — Anchor Capacity (0–30): max check vs. target (capped if not early-stage).
	•	FS — FlexScore (0–25): ticket compatibility = overlap between the fund’s [min,max] and the window [0.6×; 1.1×] of the target round (proxy for a ~60–70% lead).
	•	SF — Stage Fit (0–20): pre-seed/very-early = 20; seed-only = partial; growth-oriented = 0 (for a seed scenario).
	•	FC — Focus Country (0–15): 15 if HQ in target country; 10 if active investor in that country; 0 otherwise.
(Optional toggle later: “HQ-strict” = 15 if HQ local, else 0.)

Confidence penalty (malus): −5 or −10 if OpenVC fields (min, max, stage, country) are incomplete.

Final score & tiers (fixed cut-offs):
\textbf{AIx} = \big(AC + FS + SF + FC + \text{malus}\big)\times \frac{100}{90}
Tier A ≥ 75, B 55–74, C < 55, U = unscored (no min/max).

⸻

2) Data requirements
	•	Input: single CSV from OpenVC (OpenVC.csv, export 2025-07).
	•	Fields used:
	•	first_cheque_minimum, first_cheque_maximum → AC, FS
	•	stage_of_investment → SF
	•	global_hq, countries_of_investment → FC
	•	investor_type → filter (VC/CVC only)

✅ We provide the MD5 above to guarantee reproducibility of the published results.

⸻

3) Quick start

git clone <YOUR_REPO_URL>.git
cd <YOUR_REPO_NAME>

# 0) Put the OpenVC export in the repo root (exact file name: OpenVC.csv)
#    Verify integrity (on macOS/Linux):
md5 OpenVC.csv   # should print: 8983450fb099e20bc16c91d4a0e8af8f

# 1) Install dependencies
pip install -r requirements.txt

# 2) Run Switzerland (3 scenarios)
python aix_builder_sw.py --openvc OpenVC.csv --out ./out_ch --scenarios 300k,800k,1500k

# 3) Run France (3 scenarios)
python aix_builder_fr.py --openvc OpenVC.csv --out ./out_fr --scenarios 250k,700k,1200k

Outputs (examples):

out_ch/
  aix_switzerland_v4.csv         # per-fund details: AC/FS/SF/FC/malus, AIx by scenario, Tier by scenario
  aix_tiers_sw_v4.csv            # compact Tier distributions
  figs/                          # PNG charts (tier distribution, sensitivity, ablation, HQ toggle)

out_fr/
  aix_france_v4.csv
  aix_tiers_fr_v4.csv
  figs/


⸻

4) Columns you can expect

Typical columns in the per-fund file:
	•	Identity & filters: fund_name, investor_type, global_hq, countries_of_investment, stage_of_investment, first_cheque_minimum, first_cheque_maximum, raw fields (e.g., hq_raw).
	•	Sub-scores: ac_300k, fs_300k, ac_800k, fs_800k, ac_1500k, fs_1500k, sf, fc, malus.
	•	AIx & tiers: aix_300k, tier_300k, aix_800k, tier_800k, aix_1500k, tier_1500k.

⸻

5) Reproducing article figures

The repo includes minimal scripts/notebooks to recreate the figures from The Anchor Bottleneck.
If you prefer a one-file example, drop the snippet below in figs_make.py and run it.

# figs_make.py — minimal reproduction of 5 key charts
import pandas as pd, numpy as np, matplotlib.pyplot as plt
ch = pd.read_csv("out_ch/aix_switzerland_v4.csv")
fr = pd.read_csv("out_fr/aix_france_v4.csv")
T=['A','B','C','U']
def dist(s): c=s.value_counts().reindex(T).fillna(0); p=(c/c.sum()*100).round(1); return c,p

# 1) Switzerland tier distribution @ ~800k CHF
c,p = dist(ch['tier_800k'])
plt.figure(); plt.bar(range(4), c.values); plt.xticks(range(4), T); plt.title("CH — Tier @ 800k CHF"); plt.ylabel("Funds"); plt.tight_layout(); plt.savefig("out_ch/figs/ch_800k_tiers.png")

# 2) Sensitivity (CH): 300k / 800k / 1.5M, stacked %
sc = [('300k','tier_300k'),('800k','tier_800k'),('1.5M','tier_1500k')]
P = np.array([dist(ch[col])[1].values for _,col in sc])
plt.figure(); b=np.zeros(3); 
for j,t in enumerate(T): plt.bar(range(3), P[:,j], bottom=b, label=t); b+=P[:,j]
plt.xticks(range(3), [s for s,_ in sc]); plt.ylabel("% of funds"); plt.title("CH — Tier by target (stacked %)"); plt.legend(); plt.tight_layout(); plt.savefig("out_ch/figs/ch_sensitivity.png")

# 3) CH vs FR comparison (seed-sized)
pc = dist(ch['tier_800k'])[1]; pf = dist(fr['tier_700k'])[1]
idx=np.arange(4); w=0.35
plt.figure(); plt.bar(idx-w/2, pc.values, w, label="CH ~800k CHF"); plt.bar(idx+w/2, pf.values, w, label="FR ~700–800k €")
plt.xticks(idx, T); plt.ylabel("% of funds"); plt.title("Tier — CH vs FR"); plt.legend(); plt.tight_layout(); plt.savefig("out_ch/figs/ch_fr_compare.png")

# 4) Ablation (CH, 800k): AC → AC+FS → +SF → +FC (renormalized 30/55/75/90)
def tiers(score): 
  def t(x): return 'U' if pd.isna(x) else ('A' if x>=75 else 'B' if x>=55 else 'C')
  return score.apply(t)
def pcts(ac,fs,sf,fc,malus,maxp): 
  s=(ac+fs+sf+fc+malus)*(100.0/maxp); return dist(tiers(s))[1]
ac,fs,sf,fc,malus = [ch['ac_800k'], ch['fs_800k'], ch['sf'], ch['fc'], ch['malus']]
steps=[("AC only", pcts(ac,0*fs,0*sf,0*fc,malus,30)),
       ("AC+FS",   pcts(ac,fs,0*sf,0*fc,malus,55)),
       ("AC+FS+SF",pcts(ac,fs,sf,0*fc,malus,75)),
       ("Full",    pcts(ac,fs,sf,fc,malus,90))]
plt.figure(); b=np.zeros(len(steps))
for j,t in enumerate(T): plt.bar(range(len(steps)), np.array([p.values for _,p in steps])[:,j], bottom=b, label=t); b+=np.array([p.values for _,p in steps])[:,j]
plt.xticks(range(len(steps)), [name for name,_ in steps]); plt.ylabel("% of funds"); plt.title("Ablation (CH, 800k)"); plt.legend(); plt.tight_layout(); plt.savefig("out_ch/figs/ch_ablation.png")

# 5) HQ-strict toggle (CH, 800k): recompute FC strictly (15 if HQ in CH else 0)
def hq_ch(s): 
  if pd.isna(s): return False
  s=str(s).lower(); return any(t in s for t in ['switzerland','suisse','schweiz','svizzera',' ch']) or any(c in s for c in ['zurich','geneva','genève','lausanne','basel','zug','bern'])
fc_strict = ch['hq_raw'].apply(lambda x: 15 if hq_ch(x) else 0)
score_perm  = (ch['ac_800k'] + ch['fs_800k'] + ch['sf'] + ch['fc']        + ch['malus'])*(100.0/90.0)
score_strict= (ch['ac_800k'] + ch['fs_800k'] + ch['sf'] + fc_strict       + ch['malus'])*(100.0/90.0)
def tier_of(x): return 'U' if pd.isna(x) else ('A' if x>=75 else 'B' if x>=55 else 'C')
pc_perm  = dist(score_perm.apply(tier_of))[1]; pc_strict = dist(score_strict.apply(tier_of))[1]
idx=np.arange(4); w=0.35
plt.figure(); plt.bar(idx-w/2, pc_perm.values, w, label="Default (HQ or active)"); plt.bar(idx+w/2, pc_strict.values, w, label="HQ-strict (HQ only)")
plt.xticks(idx, T); plt.ylabel("% of funds"); plt.title("Local HQ toggle (CH, 800k)"); plt.legend(); plt.tight_layout(); plt.savefig("out_ch/figs/ch_hq_toggle.png")

Run:

python figs_make.py


⸻

6) Interpreting the outputs
	•	Tier A (≥ 75): highly aligned to anchor the scenario round.
	•	Tier B (55–74): partial fit (e.g., stage/local OK but ticket not ideal, or vice-versa).
	•	Tier C (< 55): misaligned on one or more dimensions.
	•	Tier U: unscored due to missing min/max check info.

We also keep sub-scores and a confidence flag per fund so you can see why a fund is Tier A/B/C and adjust outreach accordingly.

⸻

7) Reproducing the article’s Swiss & France numbers (sanity check)

With the dataset above and default settings:
	•	Switzerland (~800k CHF): ~50% A, ~27% B, ~17% C, ~6% U (tier medians ≈ A 94 / B 67 / C 38).
	•	France (~700–800k €): ~45% A, ~24% B, ~22% C, ~10% U (tier medians ≈ A 94 / B 67 / C 34).

Exact counts may differ minutely if OpenVC updates profiles between exports. Fix your CSV to the MD5 above for identical replication.

⸻

8) Notes & limitations
	•	OpenVC-only: self-reported and sometimes stale; we expose this via Confidence Score and Tier U.
	•	Not a predictor: AIx prioritizes who to call first; it doesn’t guarantee a term sheet.
	•	Fixed thresholds: using fixed tier cut-offs (not quantiles) ensures comparability across countries and time.

⸻

9) License & citation
	•	License: MIT (see LICENSE)
	•	Citation:
Tissot, E. (2025). The Anchor Bottleneck — AIx (Anchor Investor Index) for pre-seed/seed anchoring using OpenVC data.
GitHub:

⸻

10) FAQ

Q. Can I change the round size?
Yes — pass scenario amounts via --scenarios (e.g., 300k,800k,1500k). The scripts compute AC/FS accordingly and emit per-scenario AIx & Tiers.

Q. Can I force “HQ-strict”?
The per-fund CSV includes sub-scores; you can re-compute FC and tiers with the snippet in §5 to emulate HQ-strict vs permissive.

Q. Where do the charts come from?
From the generated CSVs (see out_*/figs). The minimal script in §5 reproduces the key figures used in the article.
