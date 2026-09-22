"""Tests de démarrage — l'environnement d'audit fonctionne.

⚠️ Ces tests vérifient que vous POUVEZ auditer (données lisibles, modèle
chargeable, script legacy exécutable) — pas que le legacy est correct.
Le legacy est volontairement fragile : le corriger n'est PAS l'objet du
brief, l'auditer si.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import joblib
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def test_dataset_lisible():
    """Le dataset d'audit se charge avec les colonnes attendues."""
    df = pd.read_csv(ROOT / "data" / "dms_dataset.csv")
    assert len(df) > 0
    for col in ("age", "nb_comorbidites", "imc"):
        assert col in df.columns, f"colonne {col} absente"


def test_modele_legacy_chargeable():
    """Le modèle hérité se charge et prédit — sinon vérifiez la version scikit-learn."""
    model = joblib.load(ROOT / "legacy" / "dms_predictor_v1.joblib")
    X = pd.DataFrame(
        [[70, 3, 28.5, 1]], columns=["age", "nb_comorbidites", "imc", "sexe_bin"]
    )
    proba = model.predict_proba(X)[0, 1]
    assert 0.0 <= proba <= 1.0


def test_script_legacy_executable():
    """`python legacy/predict.py 70 3 28.5 1` tourne depuis la racine du repo.

    (Oui, il ne tourne QUE depuis la racine — notez-le, c'est déjà un
    constat d'audit.)
    """
    r = subprocess.run(
        [sys.executable, "legacy/predict.py", "70", "3", "28.5", "1"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    assert "SEJOUR" in r.stdout
