AIx — Anchor Investor Index (OpenVC-only)

But du projet
AIx est un petit outil Python qui classe les investisseurs capables d’ancrer (lead/anchor) un tour pre-seed/seed pour un montant cible donné.
Il s’appuie uniquement sur le CSV public OpenVC (tickets min/max, stage, HQ/pays d’investissement), calcule des sous-scores interprétables (AC/FS/SF/FC), applique un malus de confiance si la fiche est incomplète, et produit un score AIx /100 ainsi qu’un Tier (A/B/C/U) par scénario de montant.

	•	📄 Article associé (Medium) : The Anchor Bottleneck — <INSÈRE ICI LE LIEN MEDIUM>
	•	🗂️ Fichiers principaux à utiliser :
	•	aix_builder_sw.py → exécutions Suisse (CH)
	•	aix_builder_fr.py → exécutions France (FR)
	•	🧾 Dataset attendu : OpenVC.csv (export 2025-07) — MD5 8983450fb099e20bc16c91d4a0e8af8f

⸻

1) Prérequis
	•	Python 3.9+ (3.10/3.11 OK)
	•	pip (ou pipx/poetry si tu préfères)
	•	Système : macOS, Linux, ou Windows (PowerShell)

Dépendances Python : pandas, numpy, matplotlib (et argparse natif).
Si le repo contient requirements.txt, installe-le directement (voir Quick start). Sinon :

pip install pandas numpy matplotlib


⸻

2) Installation rapide (Quick start)

a) Cloner & se placer dans le dossier

git clone <TON_REPO_GITHUB>.git
cd <TON_REPO_GITHUB>

b) (Optionnel) Créer un venv propre

python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell
.venv\Scripts\Activate.ps1

c) Installer les dépendances

# si requirements.txt est présent
pip install -r requirements.txt
# sinon :
# pip install pandas numpy matplotlib

d) Placer le dataset OpenVC

Copie OpenVC.csv (export 2025-07) à la racine du repo.

(Optionnel) Vérifier l’intégrité :

# macOS
md5 OpenVC.csv
# Linux
md5sum OpenVC.csv
# Windows PowerShell
Get-FileHash OpenVC.csv -Algorithm MD5
# → doit renvoyer : 8983450fb099e20bc16c91d4a0e8af8f


⸻

3) Lancer le scoring

🇨🇭 Suisse (3 scénarios : 300k / 800k / 1.5M CHF)

python aix_builder_sw.py --openvc OpenVC.csv --out ./out_ch --scenarios 300k,800k,1500k

🇫🇷 France (3 scénarios : ~250k / ~700k / ~1.2M €)

python aix_builder_fr.py --openvc OpenVC.csv --out ./out_fr --scenarios 250k,700k,1200k

Paramètres communs
	•	--openvc : chemin vers le fichier OpenVC.csv
	•	--out : dossier de sortie (sera créé si absent)
	•	--scenarios : liste séparée par des virgules des montants cibles (suffixes autorisés : k / M, ex. 300k,800k,1.5M)

⸻

4) Résultats générés

Dans --out, tu obtiendras (noms indicatifs) :
	•	aix_switzerland_v4.csv / aix_france_v4.csv
→ détail par fonds : sous-scores AC/FS/SF/FC, malus, AIx par scénario (aix_300k, aix_800k, …) et tiers (tier_300k, tier_800k, …).
	•	aix_tiers_sw_v4.csv / aix_tiers_fr_v4.csv
→ distributions A/B/C/U par scénario (résumé).
	•	(éventuellement) un sous-dossier figs/ si tu génères des graphes à partir des CSV.

Lecture rapide des Tiers
	•	Tier A (≥75) : très bon candidat anchor au palier donné
	•	Tier B (55–74) : fit partiel / second rideau
	•	Tier C (<55)  : misaligné (ticket/stage/pays)
	•	Tier U        : non scoré (min & max manquants)

⸻

5) Conseils d’usage
	•	Choisis ton scénario (ex. seed ~800k) et utilise la liste Tier A en vague 1 d’intros, Tier B en vague 2, Tier C en backup.
	•	Transparence : les sous-scores par fonds (AC/FS/SF/FC) expliquent pourquoi un fonds est A/B/C — utile en entretien.
	•	Toggle local : si tu veux privilégier un HQ strict local, tu peux réajuster FC (15 si HQ local, sinon 0) et recalculer rapidement les Tiers à partir du CSV.

⸻

6) Limitations (à connaître)
	•	OpenVC-only : données déclaratives (parfois incomplètes). Le malus et le Tier U rendent cette qualité visible.
	•	Pas une prédiction : AIx priorise l’ordre de tir (qui appeler d’abord), mais ne garantit pas un term sheet.
	•	Seuils fixes : les cut-offs (A/B/C) sont fixes pour comparer pays/scénarios dans le temps.

⸻

7) Référence article & licence
	•	📄 Medium : The Anchor Bottleneck — <INSÈRE ICI LE LIEN MEDIUM>
	•	📜 Licence : MIT

⸻

Besoin d’un exemple minimal ?

Une fois out_ch/aix_switzerland_v4.csv généré, tu peux facilement tracer la répartition des Tiers à 800k :

import pandas as pd
ch = pd.read_csv("out_ch/aix_switzerland_v4.csv")
print(ch['tier_800k'].value_counts())
