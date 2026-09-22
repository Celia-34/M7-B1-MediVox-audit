# MediVox - prediction DMS (script appele en prod via SSH, NON-MODULAIRE)
# >>> Volontairement fragile pour l'audit M7-B1 <<<
import sys
import joblib
import pandas as pd

# chemin absolu en dur vers le modele local (point de rupture si la machine tombe)
model = joblib.load("legacy/dms_predictor_v1.joblib")

# pas de validation d'input, pas de schema, pas de gestion d'erreur
age = int(sys.argv[1])
comorbidites = int(sys.argv[2])
imc = float(sys.argv[3])
sexe_bin = int(sys.argv[4])

X = pd.DataFrame([[age, comorbidites, imc, sexe_bin]],
                 columns=["age", "nb_comorbidites", "imc", "sexe_bin"])
proba = model.predict_proba(X)[0, 1]
# decision automatique sans supervision humaine, sans log, sans tracabilite
print("RISQUE_SEJOUR_PROLONGE" if proba >= 0.5 else "SEJOUR_STANDARD", round(float(proba), 3))
