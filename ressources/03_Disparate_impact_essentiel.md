# Disparate impact et équité (en audit) — Mini-cours

> Brief associé : M7-B1
> Durée de lecture : ~25 min
> Pré-requis : pandas, notion de variable sensible (revu de M2-B2), matrice de confusion

## Pourquoi cette techno ?

En audit éthique, « il y a peut-être un biais » ne suffit pas : il faut le
**mesurer**. Le **disparate impact** (DI) est l'indicateur le plus simple :
il compare le **taux de décision positive** entre groupes. C'est un
**signal d'alerte**, pas un verdict : un DI bas peut refléter une
discrimination… ou une différence réelle entre les groupes. Il **déclenche
une investigation**, il ne la conclut pas.

L'investigation se fait avec d'autres outils : **qui est lésé** par une
prédiction, **quelles erreurs** le modèle commet par groupe, et **ses
probabilités** sont-elles justes pour chaque groupe. Ici on l'applique à un
modèle **déjà en prod** (audit), pas à un dataset à nettoyer (M2).

## Concepts clés

- **DI = taux(groupe A) / taux(groupe B)** sur une issue (ici : prédiction
  « séjour prolongé »). Le seuil **0,80** (« règle des 4/5 ») vient du droit
  américain de l'emploi : c'est un **repère d'alerte conventionnel**, pas un
  seuil universel ni une norme opposable en santé.
- **Définir le préjudice d'abord** : être signalé « séjour prolongé »,
  est-ce un avantage (anticipation, coordination de sortie, lit réservé) ou un
  désavantage (patient jugé « coûteux », refus ou report) ? **Le sens du biais
  dépend de l'usage.** Sans cette réponse, « biais défavorable à X » n'a pas
  de sens.
- **Taux d'erreur par groupe** : **FNR** (vrais séjours longs non signalés) et
  **FPR** (signalés à tort) calculés séparément pour chaque groupe. Deux
  groupes au même DI peuvent subir des erreurs très différentes — et c'est
  l'erreur qui fait le préjudice.
- **Calibration par groupe** : parmi les patients à qui le modèle donne ~40 %,
  ~40 % font-ils vraiment un séjour long — **dans chaque groupe** ? Un modèle
  qui sous-estime un groupe le prive systématiquement de l'anticipation.
- **Étiquette vs réalité** : un modèle apprend ses **étiquettes**. Si
  l'étiquetage historique est lui-même biaisé (sous-codage d'un groupe), le
  modèle reproduit et souvent **amplifie** ce biais. Quand une mesure plus
  proche de la réalité existe dans les données, **confronte-lui** l'étiquette.
- **Variable sensible en feature** : si le modèle utilise `sexe` directement,
  on doit pouvoir le **justifier cliniquement** ; sinon c'est un aggravant.

## Exemple minimal qui tourne

```python
import pandas as pd, joblib  # pandas 2.x, scikit-learn 1.5.x
df = pd.read_csv("data/dms_dataset.csv")
model = joblib.load("legacy/dms_predictor_v1.joblib")
X = df[["age", "nb_comorbidites", "imc"]].assign(sexe_bin=(df["sexe"] == "M").astype(int))
df["pred"] = model.predict(X)
rate = df.groupby("sexe")["pred"].mean()
print("DI F/M (prédictions) =", round(rate["F"] / rate["M"], 3))  # signal, pas verdict
```

Et le réflexe « erreurs par groupe », une fois qu'on a une **référence** `y_ref` :

```python
def error_rates(g: pd.DataFrame) -> pd.Series:
    pos, neg = g[g["y_ref"] == 1], g[g["y_ref"] == 0]
    return pd.Series({"FNR": 1 - pos["pred"].mean(), "FPR": neg["pred"].mean()})

# df["y_ref"] = ...  ← à toi de construire une référence défendable
# print(df.groupby("sexe").apply(error_rates).round(3))
```

## Exercice guidé

Sur le prédicteur MediVox :
1. Calcule le DI F/M **sur les prédictions**, puis **sur les étiquettes**
   `sejour_prolonge`. Le modèle amplifie-t-il ?
2. Le dataset contient aussi `dms_jours` (durée réellement observée).
   Compare-la entre les groupes. La différence d'étiquetage s'explique-t-elle
   par une différence de durée réelle ?
3. Construis une **référence** à partir de `dms_jours` (indice : regarde à
   partir de quelle durée un séjour est étiqueté « prolongé » dans chaque
   groupe) et calcule **FNR/FPR par groupe**, pour l'étiquette **et** pour le
   modèle.
4. Compare la **probabilité moyenne prédite** au taux de référence, par groupe.
5. Écris en 3 lignes **qui est lésé**, par quelle erreur, **sous quelle
   hypothèse d'usage** — et la question à poser à MediVox pour trancher.

## Pièges fréquents

| Piège | Conséquence |
|---|---|
| « DI < 0,80 donc discrimination » | Verdict sur un signal ; ignore une différence réelle possible |
| Sens du préjudice non défini | « Défavorable » à un groupe… qui est peut-être avantagé |
| DI calculé sur le dataset seulement | On rate l'amplification par le modèle |
| Étiquette prise pour la vérité | On mesure l'écart au biais historique, pas à la réalité |
| Un seul indicateur (DI) | Erreurs et calibration par groupe invisibles |
| Conclure sur l'âge sans contexte médical | Faux positif (effet clinique légitime) |

| Symptôme | Cause probable |
|---|---|
| DI bas sur les étiquettes, durées réelles identiques entre groupes | étiquetage historique biaisé |
| DI plus bas sur le modèle que sur les étiquettes | le modèle amplifie (souvent via la variable sensible) |
| Même DI, FNR très différents | les erreurs ne tombent pas sur les mêmes patients |
| Proba moyenne d'un groupe << taux de référence | modèle mal calibré pour ce groupe |

## Pour aller plus loin

- Fairlearn — métriques par groupe et guide conceptuel : https://fairlearn.org/main/user_guide/assessment/index.html
- scikit-learn — calibration : https://scikit-learn.org/stable/modules/calibration.html
- EEOC — origine de la règle des 4/5 (emploi, droit US) : https://www.eeoc.gov/laws/guidance/employment-tests-and-selection-procedures
- Défenseur des droits & CNIL — *Algorithmes : prévenir l'automatisation des discriminations* (2020)

## Vérification (checklist apprenant)

- [ ] J'ai calculé le DI sur les prédictions **et** sur les étiquettes.
- [ ] J'ai écrit **qui est lésé** et sous quelle hypothèse d'usage.
- [ ] J'ai calculé FNR/FPR **par groupe** contre une référence que je justifie.
- [ ] J'ai comparé probabilité moyenne et taux de référence par groupe.
- [ ] Mon rapport présente le DI comme un **signal**, et l'investigation comme la preuve.

> 💡 **Récap** : le DI **alerte**, il ne conclut pas ; 0,80 est un repère
> conventionnel, pas une norme. L'investigation : **définir le préjudice**,
> mesurer **FNR/FPR** et **calibration par groupe**, confronter l'**étiquette** à la
> réalité mesurée. Aggravant si la variable sensible est une feature sans
> justification clinique.

*Réflexe : avant de dire « biais défavorable », écris ce que le signalement fait au patient.*
