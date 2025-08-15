# AIx — Anchor Investor Index (OpenVC-only)

AIx measures a fund’s ability to anchor a pre-seed/seed round for a given target amount.
It is a transparent, scenario-sensitive scoring framework built OpenVC-only (public CSV), designed for VCs, CVCs and founders who need a defensible, reproducible way to prioritize investor outreach.

**Article:** _The Anchor Bottleneck_ — <ADD MEDIUM LINK>  
**Run scripts:** `aix_builder_sw.py` (Switzerland) · `aix_builder_fr.py` (France)

---

| What it does | Why it matters |
|---|---|
| Reads the **OpenVC** CSV you provide (public, self-reported) | No vendor lock-in, fully reproducible |
| Filters to **VC/CVC** and target **country** (CH or FR) | Focus only on investors that can realistically join your round |
| Computes transparent sub-scores **AC / FS / SF / FC** + a simple confidence penalty | No black box — every point is explainable |
| Produces **AIx** per scenario (e.g. 300k, 800k, 1.5M) and a **Tier** (A/B/C/U) | Gives you an instant outreach order by round size |
| Exports clean **CSVs** (+ optional charts) | Drop straight into your pipeline, memos or IC decks |


---

## Repository structure
	•	aix_builder_sw.py —> CLI to score Switzerland (CH) for one or more target scenarios
	•	aix_builder_fr.py —> CLI to score France (FR) for one or more target scenarios
	•	(You add) OpenVC.csv —> the OpenVC export used as the only data source

---

## Quick start

```bash
# 1) Setup (once)
python3 -m venv venv && source venv/bin/activate
pip install pandas numpy matplotlib

# 2) Put the OpenVC export at the repo root
#    file name: OpenVC.csv  (use your latest export)

# 3) Run Switzerland (CH)
python aix_builder_sw.py --openvc OpenVC.csv --out ./out_ch --scenarios 300k,800k,1500k

# 4) Run France (FR)
python aix_builder_fr.py --openvc OpenVC.csv --out ./out_fr --scenarios 250k,700k,1200k
```
---

## License

This repo is distributed under the MIT License (see LICENSE).
The original OpenVC dataset is MIT‑licensed as well.
