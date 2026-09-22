# Audit ressources avec psutil — Mini-cours

> Brief associé : M7-B1
> Durée de lecture : ~20 min
> Pré-requis : Python, un modèle entraîné

## Pourquoi cette techno ?

La sobriété est un critère d'audit (et un argument métier). Mais « ce modèle
consomme beaucoup » ne vaut rien : il faut **chiffrer** — temps, mémoire, taille —
et **comparer** à une alternative. `psutil` mesure la consommation réelle du
process Python ; quelques lignes suffisent pour transformer une impression en
fait opposable.

## Concepts clés

- **RSS (Resident Set Size)** : mémoire physique réellement utilisée par le
  process. `psutil.Process().memory_info().rss` (en octets).
- **Temps d'entraînement / d'inférence** : `time.perf_counter()` autour du `fit`
  / `predict`, à plusieurs volumes (100 / 1k / 10k) pour voir l'échelle.
- **Taille du modèle** : `Path(...).stat().st_size` du `.joblib`.
- **Comparer, toujours** : mesurer le modèle audité **et** 1-2 alternatives
  légères (LogReg, HistGB) sur les mêmes données → met la consommation en
  perspective.
- **Honnêteté** : ordres de grandeur, pas faux chiffres précis. Et distinguer
  coût **compute** (souvent faible) du coût **opérationnel** (souvent le vrai sujet).

## Exemple minimal qui tourne

```python
import os, time, psutil, joblib
from pathlib import Path
proc = psutil.Process(os.getpid())
rss0 = proc.memory_info().rss / 1e6
model = joblib.load("legacy/dms_predictor_v1.joblib")
t0 = time.perf_counter(); model.predict(X); t = (time.perf_counter()-t0)*1000
print(f"RSS={proc.memory_info().rss/1e6:.0f} Mo | inférence={t:.1f} ms "
      f"| modèle={Path('legacy/dms_predictor_v1.joblib').stat().st_size/1e6:.1f} Mo")
```

## Exercice guidé

1. Mesure RSS, temps d'inférence (100/1k/10k) et taille du modèle legacy.
2. Entraîne une **régression logistique** sur les mêmes features.
3. Compare F1, temps et taille dans un tableau. Quel argument de sobriété ?

## Pièges fréquents

| Piège | Conséquence |
|---|---|
| Mesurer sans comparer | « ça consomme » sans référence = inutile |
| Confondre RSS et taille du modèle | Deux choses différentes |
| Une seule mesure (bruit) | Faire plusieurs volumes / runs |
| Surinterpréter le compute | Le vrai coût est souvent opérationnel |
| Inventer un CO₂eq précis | Hors mandat — ordre de grandeur suffit |

| Symptôme | Cause probable |
|---|---|
| Temps d'inférence instable | mesurer sur plus de volume / moyenner |
| RSS énorme | modèle non borné (arbres profonds) |
| Argument sobriété faible | pas d'alternative comparée |

## Pour aller plus loin

- psutil : https://psutil.readthedocs.io/en/latest/
- scikit-learn — HistGradientBoosting : https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.HistGradientBoostingClassifier.html

## Vérification (checklist apprenant)

- [ ] Je mesure RSS + temps + taille (chiffrés).
- [ ] Je compare à ≥ 1 alternative légère.
- [ ] Mes mesures sont à plusieurs volumes.
- [ ] Je distingue coût compute et coût opérationnel.
- [ ] Mon argument de sobriété est appuyé sur des chiffres.

> 💡 **Récap** : **chiffrer** (RSS, temps, taille) et **comparer** à ≥ 1 alternative
> légère — « ça consomme » ne vaut rien. Mesurer à plusieurs volumes, et distinguer
> coût **compute** (souvent faible) du coût **opérationnel** (souvent le vrai sujet).
> Pas de CO₂eq précis : ordre de grandeur suffit.

*Réflexe : la vraie question de sobriété n'est pas « combien de Mo » mais « un modèle plus simple ferait-il aussi bien ? » — d'où la comparaison.*
