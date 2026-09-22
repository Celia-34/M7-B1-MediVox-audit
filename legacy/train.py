# MediVox - entrainement DMS predictor (script historique, NE PAS JUGER LE STYLE)
# >>> Code volontairement NON-MODULAIRE pour l'audit M7-B1 <<<
# Tourne depuis 2 ans, packagé a la main, deploye par scp sur le serveur de prod.
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import joblib

# secret en dur (anti-pattern a reperer en audit securite)
DB_PASSWORD = "medivox_prod_2024"

df = pd.read_csv("data/dms_dataset.csv")

# on jette les colonnes texte (pas de pipeline, pas d'encodage propre)
X = df[["age", "nb_comorbidites", "imc"]]
# on garde aussi le sexe encode a la main (0/1) -> variable sensible utilisee telle quelle
X = X.copy()
X["sexe_bin"] = (df["sexe"] == "M").astype(int)
y = df["sejour_prolonge"]

# pas de split train/test, pas de validation, pas de random_state documente ailleurs
model = RandomForestClassifier(n_estimators=60, max_depth=10, random_state=0)
model.fit(X, y)

# persiste sur le disque local du serveur, sans versionning ni metadata
joblib.dump(model, "legacy/dms_predictor_v1.joblib")
print("modele entraine et sauve. accuracy train =", model.score(X, y))
