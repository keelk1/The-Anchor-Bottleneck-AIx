Here’s a GitHub-friendly README.md in English — clean, minimal, and plug-and-play.

⸻

AIx — Anchor Investor Index (OpenVC-only)

AIx is a small Python tool that ranks venture investors by their ability to anchor a pre-seed/seed round for a given target amount.
It uses only the public OpenVC CSV (min/max check, stage, HQ / countries) to compute interpretable sub-scores (AC / FS / SF / FC), applies a confidence penalty when profiles are incomplete, then outputs an AIx score (/100) and a Tier (A / B / C / U) per scenario to help you sequence outreach.
	•	📄 Article: The Anchor Bottleneck — add your Medium link here
	•	🗂️ Main scripts:
	•	aix_builder_sw.py → Switzerland (CH) runs
	•	aix_builder_fr.py → France (FR) runs
	•	🧾 Dataset expected: OpenVC.csv (export 2025-07) — MD5 8983450fb099e20bc16c91d4a0e8af8f

⸻

1) Prerequisites
	•	Python 3.9+ (3.10/3.11 OK)
	•	pip (or pipx/poetry if you prefer)

Python deps: pandas, numpy, matplotlib (and argparse from stdlib).

If you use a requirements.txt, keep it minimal, e.g.:

pandas>=2.0
numpy>=1.24
matplotlib>=3.7

Install:

pip install -r requirements.txt
# or:
# pip install pandas numpy matplotlib


⸻

2) Quick start

a) Clone & enter the repo

git clone <YOUR_REPO_URL>.git
cd <YOUR_REPO_NAME>

b) (Optional) Create a clean virtual env

python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell
.venv\Scripts\Activate.ps1

c) Install dependencies

pip install -r requirements.txt
# or: pip install pandas numpy matplotlib

d) Add the OpenVC dataset

Place OpenVC.csv (export 2025-07) at the repo root.

Verify the file integrity (optional):

# macOS
md5 OpenVC.csv
# Linux
md5sum OpenVC.csv
# Windows PowerShell
Get-FileHash OpenVC.csv -Algorithm MD5
# → should be: 8983450fb099e20bc16c91d4a0e8af8f


⸻

3) Run the builders

🇨🇭 Switzerland (3 scenarios: 300k / 800k / 1.5M CHF)

python aix_builder_sw.py --openvc OpenVC.csv --out ./out_ch --scenarios 300k,800k,1500k

🇫🇷 France (3 scenarios: ~250k / ~700k / ~1.2M €)

python aix_builder_fr.py --openvc OpenVC.csv --out ./out_fr --scenarios 250k,700k,1200k

Common flags
	•	--openvc : path to OpenVC.csv
	•	--out : output folder (created if missing)
	•	--scenarios : comma-separated target amounts (supports k / M, e.g. 300k,800k,1.5M)

⸻

4) Outputs

Inside your --out folder you’ll typically get:
	•	aix_switzerland_v4.csv / aix_france_v4.csv
Per-fund details: sub-scores AC / FS / SF / FC, malus (confidence penalty), AIx per scenario (aix_300k, aix_800k, …) and tiers (tier_300k, tier_800k, …).
	•	aix_tiers_sw_v4.csv / aix_tiers_fr_v4.csv
Compact A/B/C/U distributions by scenario.
	•	(Optional) a figs/ subfolder if you generate charts from the CSVs.

Quick read of tiers
	•	Tier A (≥ 75): strong anchor candidate at that scenario
	•	Tier B (55–74): partial fit / second wave
	•	Tier C (< 55): misaligned (ticket / stage / country)
	•	Tier U: unscored (missing min & max)

⸻

5) How to use in practice
	1.	Pick the scenario nearest to your raise (e.g. ~800k seed).
	2.	Start outreach with Tier A (wave 1), then Tier B (wave 2), keep Tier C as optional tail.
	3.	Use per-fund sub-scores (AC/FS/SF/FC) to understand why a fund lands in A/B/C and adjust targeting (e.g., switch scenario if tickets are too small/large).
	4.	If you want to favor local HQ only, re-weight FC (15 if HQ local, else 0) and re-tier quickly from the CSV.

⸻

6) Notes & limitations
	•	OpenVC-only → self-reported data (sometimes incomplete). This is surfaced via the confidence penalty and Tier U.
	•	Not a predictor → AIx prioritizes who to call first; it doesn’t guarantee a term sheet.
	•	Fixed cut-offs (A/B/C) for comparability across countries/scenarios over time.

⸻

7) Links & license
	•	📄 Medium article: The Anchor Bottleneck — add link
	•	📜 License: MIT (add a LICENSE file)

⸻

Minimal example (sanity check)

After a CH run, print the tier distribution at ~800k:

import pandas as pd
df = pd.read_csv("out_ch/aix_switzerland_v4.csv")
print(df["tier_800k"].value_counts())
