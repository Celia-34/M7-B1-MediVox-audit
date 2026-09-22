# M7-B1 — Auditer une architecture IA héritée (MediVox Cliniques)

> **Repo template.** « Use this template » → `M7-B1-medivox-audit-<prenom>`.
> Tu audites le prédicteur hérité — vendu comme « prédicteur DMS », il signale en
> fait les **séjours à risque de prolongation** — et rends un rapport à Hélène (DT)
> et Marc (DPO).

## 🚀 Démarrage

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest -q tests               # l'environnement d'audit fonctionne (3 tests verts)
python legacy/train.py        # le modèle à auditer (déjà fourni, regénérable)
jupyter notebook notebooks/M7-B1_template.ipynb
```

> Variante `uv` : `uv venv .venv && source .venv/bin/activate` puis
> `uv pip install -r requirements.txt`.
> Dépannage : `No module named pip` → vous êtes dans un venv créé par `uv`,
> utilisez `uv pip install …` (pas `pip install`).

**Fourni** : `legacy/` (code héritage à auditer — **ne le modifie pas**),
`data/dms_dataset.csv` (10k séjours), `procedure_audit.md` (template 7 sections).

## 🧭 Ce que tu produis

| # | À faire | Fichier | Mini-cours |
|---|---|---|---|
| 1 | Appliquer la procédure d'audit | `procedure_audit.md` | `01` |
| 2 | Volet éthique (biais + RGPD + AI Act) | `audit/01_ethique.md` | `02`, `03` |
| 3 | Volet technique | `audit/02_technique.md` | `01` |
| 4 | Volet ressources (psutil + alternatives) | `audit/03_ressources.md`, notebook | `04` |
| 5 | Consolidation (tableau risques) | `audit/04_consolidation.md` | — |
| 6 | Rapport 2 lectorats | `rapport_audit_TEMPLATE.md` | `05` |

## ✅ Réussite

- **Disparate impact calculé** sur ≥ 1 variable sensible, **puis investigué** :
  préjudice défini, erreurs (FNR/FPR) par groupe, étiquette confrontée à `dms_jours`.
- **Qualification AI Act raisonnée** (art. 6, usage réel décrit) et art. 22
  examiné sur ses 2 conditions — pas de « santé = haut risque » présumé.
- Mesures psutil **chiffrées** et comparées à ≥ 1 alternative.
- Tableau ≥ 12 lignes en 🔴/🟠/🟡.
- Le rapport **hiérarchise et questionne** (ne propose pas la solution — c'est M7-B2).
- 2 grilles de lecture (Hélène technique / Marc DPO). **Journal de bord** tenu.

## 📚 Ressources

Voir [`./ressources/`](./ressources/) — 5 mini-cours + `liens_officiels.md`.
