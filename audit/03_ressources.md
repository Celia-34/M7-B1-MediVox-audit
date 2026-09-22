# Audit — Volet ressources (MediVox Cliniques, prédicteur « DMS » v1)

> Section 4 de `procedure_audit.md`. Périmètre : **mesurer** la consommation réelle (temps, mémoire,
> taille), la **comparer** à des alternatives légères, et en tirer une lecture de sobriété **chiffrée
> et honnête**. Hors périmètre : bilan carbone certifié, chiffrage comptable, optimisation (M7-B2).
>
> **Artefact audité** : `legacy/dms_predictor_v1.joblib` (4 956 361 o) —
> `RandomForestClassifier(n_estimators=60, max_depth=10)`.
> **Mesures reproductibles** : `notebooks/M7-B1_template.ipynb`, sections 2 à 4.
>
> **Banc de mesure** : Windows AMD64 · Python 3.11.15 · scikit-learn 1.5.1 · joblib 1.4.2 ·
> pandas 2.2.2 · 10 cœurs physiques / 12 logiques · 34,0 Go de RAM.
> Unités : **Mo = 10⁶ octets** (et non Mio). Toutes les durées sont des **médianes** (5 runs pour les
> process neufs, 200 itérations pour l'inférence chaude, 3 runs pour les `fit`).

---

## 4.0 Synthèse en 30 secondes (pour Hélène, DT)

| Ce qui a été mesuré | Valeur | Ce que ça veut dire |
|---|---|---|
| Coût mémoire **du modèle lui-même** | **+7,1 Mo** de RSS | **95 % du RSS d'un appel de prod n'est pas le modèle**, c'est le runtime Python |
| Coût **CPU utile** d'une prédiction | **5,2 µs** en lot, **1,51 ms** à chaud | le modèle **n'est pas** le problème de ressources |
| Coût **réel** d'une prédiction en prod | **1 890 ms** | **99,92 % de surcoût** : démarrage d'interpréteur + import sklearn |
| Ré-entraînement complet (10 000 lignes) | **337 ms** | ré-entraîner ce modèle est **gratuit** — l'argument « c'est lourd à réentraîner » ne tient pas |
| Taille de l'artefact | **4,96 Mo** pour **30 846 feuilles** | **2 722×** la taille d'une régression logistique équivalente |
| **Régression logistique** (mêmes données, mêmes features) | **1,8 Ko**, **+1,2 pt d'accuracy**, **+1,6 pt d'AUC** | le modèle **le plus simple est aussi le meilleur** |
| Empreinte carbone annuelle du calcul | **≈ 7 gCO₂e/an** | **≈ 71 m en voiture** — négligeable, et il faut le dire |
| Poste de coût dominant | **geste humain SSH : 96 % du coût annuel** | le coût du système est **humain**, pas informatique |

> 🔴 **Conclusion du volet, en une phrase** : **le modèle ne consomme rien ; c'est l'architecture
> qui consomme, et c'est l'humain qui paie.** Le seul argument de sobriété qui tient n'est donc
> pas énergétique, il est de **complexité injustifiée** : 99,96 % de l'artefact ne sert à rien,
> puisqu'un modèle 2 722 fois plus petit fait **mieux**.

---

## 4.1 Protocole de mesure — et ses limites

Mesurer la consommation d'un modèle depuis un kernel Jupyter donne des chiffres **faux** : le kernel
a déjà importé `sklearn`, `numpy` et `pandas`, et son RSS contient tout l'environnement d'audit.
Le protocole retenu isole donc chaque grandeur :

| Grandeur | Méthode | Pourquoi |
|---|---|---|
| **RSS** | `psutil.Process().memory_info().rss` mesuré dans un **sous-process neuf**, avant / après `joblib.load` | le RSS du kernel est inexploitable |
| **RSS du modèle seul** | même sonde, avec `sklearn` **préchargé** dans le prélude | sinon on mesure l'import de sklearn, pas le modèle |
| **Temps de chargement** | `joblib.load` dans un process neuf, médiane sur **5 runs** | le 1ᵉʳ run paie le cache disque |
| **Désérialisation pure** | même mesure, `sklearn` préchargé | `joblib.load` **déclenche** l'import de sklearn |
| **Latence à chaud** | 200 itérations après warm-up, médiane | la 1ʳᵉ inférence paie l'allocation numpy |
| **Latence de production** | `subprocess.run(["python", "legacy/predict.py", …])`, médiane sur 5 | seule mesure fidèle à l'usage réel |
| **Temps de `fit`** | 3 ré-entraînements, médiane | amortit le bruit d'ordonnancement |

> ⚠️ **Limites à assumer** : ces mesures sont prises sur un **poste d'audit Windows**, pas sur le
> serveur de production de MediVox (non accessible, cf. § 3.13). Les **valeurs absolues** sont donc
> indicatives ; ce sont les **rapports** (× 2 722, × 363 886, 95 %) qui sont robustes — ils sont
> structurels, pas machine-dépendants. Un serveur Linux sans antivirus réduirait probablement le
> temps de démarrage, **sans changer la conclusion**.

### 🔧 Rectification d'une mesure du volet technique

Le § 3.9 de `02_technique.md` annonce « **coût mémoire du modèle seul : +72,1 Mio (≈ 15× la taille
du fichier)** ». **Cette lecture est erronée, et l'audit la corrige ici** : ce delta de RSS mesure
l'import de `scikit-learn` **déclenché** par `joblib.load`, pas le modèle. Une fois sklearn
préchargé, le modèle seul pèse **+7,1 Mo**, soit **1,4× son fichier** — un rapport normal.
La conclusion opérationnelle du § 3.9 reste valable (≈ 148 Mo de RSS repayés à chaque appel),
mais **l'imputation change de responsable** : c'est le runtime, pas le modèle.

---

## 4.2 Mesures psutil — modèle legacy

### 4.2.1 Taille de l'artefact

| Mesure | Valeur |
|---|---|
| Taille du `.joblib` | **4 956 361 o = 4,96 Mo** (4,73 Mio) |
| Taille du CSV d'entraînement | 516 507 o = 0,52 Mo |
| **Rapport modèle / données** | **× 9,6** |
| Feuilles totales (60 arbres) | **30 846** |
| Octets par feuille | ≈ 161 o |
| Feuilles par patient d'entraînement | **3,08** |

### 4.2.2 Mémoire (RSS) — décomposée

| Étape (process neuf, médiane sur 5 runs) | RSS | Delta |
|---|---|---|
| Après les imports de `predict.py` (`pandas`, `joblib`) | **72,7 Mo** | — |
| Après `import sklearn` | **141,5 Mo** | **+68,8 Mo** |
| Après `joblib.load` du modèle | **148,5 Mo** | **+7,1 Mo** |
| **RSS total d'un appel de production** | **148,6 Mo** | — |

> 🟠 **Le modèle représente 4,8 % du RSS qu'il fait payer.** Les 95 % restants sont le prix
> d'entrée du runtime Python scientifique : 72,7 Mo d'interpréteur + pandas + joblib, puis 68,8 Mo
> pour sklearn — importé **uniquement** parce que dépickler un `RandomForestClassifier` exige
> d'importer sa classe.
>
> 🟠 Ce coût est **repayé intégralement à chaque patient**, puisqu'il n'existe aucun service
> résident. 10 appels simultanés = **≈ 1,5 Go de RSS** pour **15 ms** de calcul utile — dont
> 71 Mo seulement sont du modèle. **Le reste est de l'air.**

### 4.2.3 Temps

| Opération | Durée | Débit équivalent |
|---|---|---|
| **Fit complet** (10 000 lignes, 4 features, 60 arbres) | **337 ms** | — |
| `joblib.load` dans un process neuf | **918 ms** | — |
| ├─ dont **import de sklearn** tiré par le `load` | **903 ms** | 98,4 % du `load` |
| └─ dont **désérialisation pure** de la forêt | **15 ms** | 1,6 % du `load` |
| Inférence **1 ligne, modèle déjà chargé** | **1,51 ms** | **664 pred/s** |
| Inférence **lot de 10 000 lignes** | **52,0 ms** | **192 482 pred/s** (**5,2 µs/pred**) |
| **Appel de production complet** (`python legacy/predict.py …`) | **1 890 ms** | **0,53 pred/s** |

> 🟡 **Le ré-entraînement coûte 337 ms.** C'est un point **positif**, et il doit être dit : rien,
> techniquement, n'empêche MediVox de réentraîner ce modèle **plusieurs fois par jour**. L'argument
> « on ne peut pas y toucher, c'est trop lourd » est **factuellement faux** — l'obstacle est
> organisationnel (aucun pipeline, aucun test, cf. § 3.8), pas calculatoire.

### 4.2.4 Décomposition de l'appel de production

| Poste | Durée | Part |
|---|---|---|
| **Total** `python legacy/predict.py 70 3 28.5 1` | **1 890 ms** | **100 %** |
| Démarrage de l'interpréteur + `import pandas`, `import joblib` | ≈ 970 ms | **51,4 %** |
| `joblib.load` (dont 903 ms d'import sklearn, 15 ms de désérialisation) | 918 ms | **48,6 %** |
| **`predict_proba` — le calcul réellement utile** | **1,51 ms** | **0,08 %** |

> 🔴 **Sur 1 890 ms, 1,51 ms servent à quelque chose.** Le rapport entre le coût unitaire payé en
> production et le coût marginal réel en lot est de **× 363 886**.
> Traduit en volume : prédire pour les 10 000 séjours du dataset coûte **52 ms en lot** contre
> **5 h 15 min** dans le mode actuel.
>
> 🔴 Ce n'est **pas** un problème de modèle, et ce n'est même pas un problème de Python : c'est
> l'**absence de processus résident**. Toute la dépense est un coût de démarrage, payé une fois
> par patient au lieu d'une fois par jour.

---

## 4.3 Comparaison à des alternatives — le cœur du volet

Protocole **strictement identique** pour les 4 modèles : mêmes données (`data/dms_dataset.csv`,
10 000 lignes), mêmes features, même sonde RSS, mêmes 200 itérations de latence, même validation
croisée (`StratifiedKFold(5, shuffle=True, random_state=42)`), même mesure d'équité qu'au § 2.4.

- `legacy_rf` — `RandomForestClassifier(n_estimators=60, max_depth=10, random_state=0)` : le modèle audité.
- `logreg` — `StandardScaler` + `LogisticRegression(max_iter=1000)`, **mêmes 4 features** (sexe inclus).
- `histgb` — `HistGradientBoostingClassifier(max_iter=100)` : un boosting moderne, pour vérifier
  qu'on ne perd rien en montant en gamme.
- `logreg_sans_sexe` — même régression logistique, **`sexe_bin` retiré** : contrefactuel du volet
  éthique (§ 2.4).

### Ressources

| Modèle | Taille | RSS modèle seul | Désérialisation | `fit` | Latence 1 ligne | Latence lot 10k |
|---|---|---|---|---|---|---|
| **`legacy_rf`** | **4 959,5 Ko** | **7,05 Mo** | 24,7 ms | 0,338 s | 1,52 ms | 44,5 ms |
| **`logreg`** | **1,8 Ko** | **0,025 Mo** | 1,5 ms | **0,010 s** | 1,26 ms | **3,7 ms** |
| `histgb` | 366,1 Ko | 0,737 Mo | 9,0 ms | 0,508 s | 2,63 ms | 21,8 ms |
| `logreg_sans_sexe` | **1,8 Ko** | 0,029 Mo | 3,3 ms | **0,007 s** | **0,39 ms** | **2,9 ms** |

**Gains relatifs au legacy** (× = « combien de fois moins que le legacy ») :

| Modèle | Taille | `fit` | RSS | Latence lot |
|---|---|---|---|---|
| **`logreg`** | **× 2 722** | **× 33** | **× 287** | **× 12,1** |
| `histgb` | × 14 | × 0,7 *(plus lent)* | × 9,6 | × 2,0 |
| `logreg_sans_sexe` | **× 2 821** | **× 50,6** | × 246 | **× 15,6** |

### Qualité — validation croisée 5 folds stratifiés

| Modèle | Accuracy CV | F1 CV | AUC CV | Δ accuracy vs legacy |
|---|---|---|---|---|
| `legacy_rf` | 0,6835 | 0,5619 | 0,7245 | — |
| **`logreg`** | **0,6953** | **0,5768** | **0,7400** | **+1,2 pt** ✅ |
| `histgb` | 0,6832 | 0,5597 | 0,7242 | −0,0 pt |
| `logreg_sans_sexe` | 0,6715 | 0,5374 | 0,7216 | −1,2 pt |

> 🔴 **Le résultat central du volet ressources : une régression logistique de 1,8 Ko fait MIEUX que
> le RandomForest de 4,96 Mo.** +1,2 point d'accuracy, +1,5 point de F1, **+1,6 point d'AUC** — pour
> **2 722 fois moins d'artefact**, **33 fois moins de temps d'entraînement** et **287 fois moins de
> mémoire**.
>
> Ce n'est pas un hasard : le § 3.7 a mesuré **8,9 points de sur-apprentissage** sur le legacy
> (0,772 en train → 0,684 en CV). Le RandomForest ne convertit pas sa capacité en performance,
> **il la convertit en mémorisation**. La complexité n'achète rien.
>
> 🟠 **`histgb` confirme le diagnostic par l'autre bout** : un boosting moderne, 14 fois plus léger
> que le legacy, obtient **exactement la même performance** (0,6832 vs 0,6835). Autrement dit, le
> plafond atteignable sur ces 4 features est de **≈ 0,69 d'accuracy / 0,73 d'AUC**, quel que soit
> le modèle. **Ce n'est pas le modèle qui limite MediVox, ce sont ses features** — `service` et
> `type_admission`, les deux variables les plus prédictives, sont jetées par `train.py` l.14
> (cf. § 2.2).

### Équité — mesurée sur les mêmes runs

Référence `y_ref = (dms_jours ≥ 5,6)`, identique au § 2.3. Repère conventionnel DI ≥ 0,80.

| Modèle | DI (F/M) | FNR femmes | FNR hommes | Écart FNR | Proba moy. F | Proba moy. M |
|---|---|---|---|---|---|---|
| `legacy_rf` | **0,292** ❌ | 73,7 % | 24,5 % | **49,2 pts** | 0,321 | 0,491 |
| `logreg` | 0,351 ❌ | 72,9 % | 32,8 % | 40,1 pts | 0,321 | 0,491 |
| `histgb` | **0,275** ❌ | 75,7 % | 26,1 % | 49,6 pts | 0,322 | 0,490 |
| **`logreg_sans_sexe`** | **1,001** ✅ | **54,1 %** | 52,0 % | **2,1 pts** | 0,405 | 0,407 |

> 🔴 **Aucune alternative ne corrige le biais tant que `sexe_bin` reste une feature.** `logreg`
> (0,351) et `histgb` (0,275) restent très loin du repère de 0,80, et leurs probabilités moyennes
> par sexe sont **identiques à 0,001 près** à celles du legacy. C'est la démonstration, par le
> benchmark, que **le biais ne vient pas du choix de modèle** : il vient de l'étiquette (§ 2.3) et
> du fait que le sexe soit une entrée.
>
> 🔴 **Retirer `sexe_bin` ramène le disparate impact à 1,001** — parité quasi parfaite — et fait
> chuter l'écart de FNR entre femmes et hommes de **49,2 points à 2,1 points**, pour **−1,2 point
> d'accuracy** et **−0,3 point d'AUC**. **Le prix de l'équité est mesuré, et il est faible.**
>
> 🟠 **À ne pas surinterpréter** : `logreg_sans_sexe` reste à **54,1 % de FNR chez les femmes**.
> Il est *équitable* (il traite les deux groupes pareil) mais toujours **mauvais**, parce qu'il est
> entraîné sur une étiquette biaisée. **Retirer le sexe corrige la discrimination, pas l'erreur.**
> La correction de l'étiquette (Q6) reste le sujet — et elle est hors mandat de cet audit.

---

## 4.4 Coût du modèle — ordre de grandeur

> ⚠️ **Ce n'est pas un chiffrage comptable.** Les hypothèses sont explicites et **paramétrables**
> dans le notebook ; deux d'entre elles (volume annuel, durée du geste humain) sont **inconnues de
> l'audit** et font l'objet de **Q16** et **Q17**. L'objectif est de **hiérarchiser les postes**,
> pas de produire un montant.

### Hypothèses retenues

| Paramètre | Valeur | Source / justification |
|---|---|---|
| Séjours prédits par an | **10 000** | = taille du dataset. **Volume réel inconnu** ❓ **Q16** |
| Geste humain par appel SSH | **2 min** | connexion + saisie des 4 arguments + lecture + report. **Estimation** ❓ **Q17** |
| Coût horaire chargé | **45 €/h** | profil soignant / administratif |
| Puissance d'un cœur serveur sous charge | **25 W** | ordre de grandeur x86 |
| Prix du kWh professionnel | **0,174 €** | tarif France 2025 |
| Intensité carbone du mix FR | **0,056 kgCO₂e/kWh** | ordre de grandeur ADEME / RTE |
| Serveur dédié 24/7 | **600 €/an** | VM ou amortissement ❓ **Q18** |

### Résultat

| Poste | Coût annuel | Part |
|---|---|---|
| **Geste humain SSH** (333 h/an ≈ **0,21 ETP**) | **≈ 15 000 €** | **96,1 %** |
| Serveur dédié 24/7 (coût **fixe**) | ≈ 600 € | 3,9 % |
| Calcul — mode actuel (1 process/patient) | **0,02 €** | **0,0001 %** |
| Calcul — même volume en lot | < 0,00001 € | ≈ 0 |
| Ré-entraînement annuel | **4 × 10⁻⁷ €** | ≈ 0 |

| Indicateur physique | Valeur |
|---|---|
| CPU consommé, mode actuel | **5,25 h/an** |
| CPU consommé, même volume en lot | **1,9 s/an** (**× 9 733** moins) |
| Énergie du calcul | **0,131 kWh/an** |
| **Empreinte carbone du calcul** | **≈ 7 gCO₂e/an** |
| Équivalent | **≈ 71 m parcourus en voiture thermique** |
| Taux d'occupation du serveur | **0,060 % de l'année** |

> 🔴 **Le geste humain coûte ≈ 650 000 fois plus cher que le calcul qu'il déclenche.** Toute
> discussion de sobriété qui porterait sur le modèle — sa taille, son nombre d'arbres, son
> empreinte carbone — se tromperait de **six ordres de grandeur**.
>
> 🟠 **Le serveur est occupé 0,060 % de l'année** pour cette charge. Son coût est **fixe et
> quasi-intégralement gaspillé** : ≈ 600 € pour 5 heures de calcul. C'est le seul poste
> informatique qui mérite une question ❓ **Q18** — est-il dédié, ou mutualisé ?
>
> 🟡 **Honnêteté obligatoire sur le carbone** : **7 gCO₂e par an**. Ce chiffre est **négligeable**,
> et l'audit refuse de le présenter autrement. Passer le modèle en régression logistique ferait
> tomber l'artefact de 4 956 Ko à 1,8 Ko : **gain financier et carbone réel ≈ 0 €**.
> **Le modèle n'a jamais été le coût.** Prétendre le contraire serait du *greenwashing*.

### Ce que la sobriété autorise **vraiment** à dire

| Argument | Tient-il ? | Pourquoi |
|---|---|---|
| « Le modèle consomme trop d'énergie » | ❌ **Non** | 0,131 kWh/an, 7 gCO₂e — sous le seuil du bruit |
| « Le modèle est trop lourd en RAM » | ❌ **Non** | 7,1 Mo ; c'est le runtime (141 Mo) qui pèse |
| « Le modèle est trop coûteux à réentraîner » | ❌ **Non** | 337 ms |
| « **L'architecture** gaspille 99,92 % du calcul » | ✅ **Oui** | 1 890 ms pour 1,51 ms utiles, × 363 886 |
| « **99,96 % de l'artefact est inutile** » | ✅ **Oui** | `logreg` fait **mieux** en 1,8 Ko (× 2 722) |
| « La complexité crée un **risque**, pas de la valeur » | ✅ **Oui** | 30 846 feuilles = 8,9 pts de sur-apprentissage + mémorisation de données de santé |
| « **Le vrai coût est humain** » | ✅ **Oui** | 0,21 ETP, 96 % du coût annuel |

---

## 4.5 Tableau de synthèse du volet ressources

| # | Indicateur | Mesure | Sév. | Conséquence pour MediVox |
|---|---|---|---|---|
| **R1** | Un modèle 2 722× plus petit est **plus performant** | `logreg` 1,8 Ko : **+1,2 pt acc / +1,6 pt AUC** | 🔴 | La complexité du legacy est **injustifiable** ; elle n'achète que du sur-apprentissage |
| **R2** | Surcoût d'exécution en production | **1 890 ms** dont **1,51 ms utiles** (**0,08 %**) | 🔴 | 5 h 15 pour ce qui prend 52 ms ; coût **entièrement** architectural |
| **R3** | Coût dominant = **humain**, pas machine | **0,21 ETP**, ≈ 15 000 €/an, **96 %** du coût | 🔴 | Tout gain sur le modèle est un **placebo** économique |
| **R4** | Aucune alternative ne corrige le biais **avec** `sexe_bin` | DI : legacy 0,292 · logreg 0,351 · histgb 0,275 | 🔴 | Le biais n'est **pas** un défaut de modèle → il ne se corrige pas en changeant de modèle |
| **R5** | Le prix de l'équité est **mesuré et faible** | Sans `sexe_bin` : **DI 1,001**, écart FNR 49,2 → **2,1 pts**, **−1,2 pt d'acc** | 🟠 | Arbitrage documenté disponible pour M7-B2 |
| **R6** | Plafond de performance atteint par **tous** les modèles | `histgb` = `legacy` à 0,0003 près (0,6832 / 0,6835) | 🟠 | Le levier n'est pas le modèle, ce sont les **features jetées** (`service`, `type_admission`) |
| **R7** | RSS repayé intégralement à chaque appel | **148,6 Mo** par process, dont **95 % de runtime** | 🟠 | Aucune élasticité ; 10 appels = 1,5 Go pour 15 ms utiles |
| **R8** | Serveur occupé **0,060 %** de l'année | 5,25 h de CPU sur 8 760 h | 🟠 | ≈ 600 €/an de coût fixe quasi-intégralement gaspillé |
| **R9** | Artefact 9,6× plus gros que ses données | 4,96 Mo / 0,52 Mo — **30 846 feuilles** | 🟠 | Mémorisation de données de santé dans un fichier déplacé par `scp` |
| **R10** | Mesure de RSS du § 3.9 **erronée** | « +72,1 Mio du modèle » → en réalité **+7,1 Mo** | 🟠 | Corrigé ici ; ne pas fonder un argument de sobriété dessus |
| **R11** | Ré-entraînement **gratuit** | **337 ms** | 🟡 | *Point positif* : rien n'empêche techniquement de corriger le modèle |
| **R12** | Empreinte carbone du calcul **négligeable** | **7 gCO₂e/an** ≈ 71 m en voiture | 🟡 | *Point positif* : ne **pas** en faire un argument commercial |
| **R13** | Écart lot / unitaire | **× 363 886** (52 ms vs 5 h 15) | 🟡 | Gain potentiel immédiat, sans toucher au modèle |

---

## 4.6 Questions ouvertes du volet ressources

> Ces questions sont **métier**, pas techniques : aucune ne se répond depuis le repo, et **aucun
> chiffre de coût n'est opposable tant qu'elles restent ouvertes**. Q16 et Q17 conditionnent à
> elles seules **99 %** du chiffrage du § 4.4.

| # | Question | Destinataire | Pourquoi c'est bloquant |
|---|---|---|---|
| **Q16** | **Combien de prédictions sont réellement lancées par an** — et selon quel profil (pic d'admission le lundi ? la nuit ? le week-end ?) | Hélène (DT) + direction des soins | Le chiffrage du § 4.4 suppose 10 000/an **par convention** (taille du dataset). À 100/an, le sujet ressources disparaît ; à 100 000/an, le geste humain devient **2 ETP** |
| **Q17** | **Combien de temps prend le geste complet** : connexion SSH, saisie des 4 arguments, lecture, **report de la réponse** dans le dossier ou l'outil de planification ? | Hélène + les personnes qui l'exécutent | Poste de coût **n°1** (96 %). 2 min est une **estimation d'audit**, à remplacer par un chronométrage réel |
| **Q18** | **Le serveur est-il dédié à ce script ou mutualisé ?** Quel coût lui est réellement imputé ? | Hélène (DT) | Seul poste informatique non négligeable (≈ 600 €/an) ; 0,060 % d'occupation mesurée |
| **Q19** | **Existe-t-il une exigence de délai métier** (« la réponse doit arriver en moins de X ») ? | Direction des soins | Sans SLA, 1 890 ms n'est **pas** un défaut ; avec un SLA à 100 ms, c'est bloquant. Détermine si R2 est 🔴 ou 🟡 |
| **Q20** | **Les prédictions sont-elles faites une par une, ou pourraient-elles l'être par lot quotidien ?** | Hélène + direction des soins | Le passage en lot divise le CPU par **9 733** et supprime 96 % du coût — **sans toucher au modèle**. À valider côté métier, pas techniquement |
| **Q21** | **Combien de personnes exécutent ce geste, et qui prend le relais en congés / arrêt / départ ?** | Hélène (DT) + RH | Chiffre le SPOF #4 du § 3.10 en **jours d'indisponibilité**, pas en ressenti |
| **Q22** | **Le modèle a-t-il été ré-entraîné depuis sa mise en service il y a 2 ans ?** Si non, pourquoi — contrainte technique supposée, ou absence de décision ? | Hélène (DT) | Le `fit` coûte **337 ms** : si le blocage était « c'est trop lourd », la croyance est **mesurément fausse** et doit être levée |
| **Q23** | **MediVox a-t-il un engagement RSE / un reporting CSRD** auquel ce système devrait contribuer ? | Direction + Hélène | Détermine s'il faut **documenter** les 7 gCO₂e (et les mettre en perspective) ou simplement les classer |
| **Q24** | **Quel budget annuel est aujourd'hui attribué à ce système**, et sur quelle ligne ? | Direction | L'audit mesure un coût **≈ 15 600 €/an** dont **0,02 € d'informatique**. Si le budget affiché est « un serveur », il **ne décrit pas** la dépense réelle |

---

## 4.7 Ce que cet audit n'a **pas** pu mesurer

- La consommation **sur le serveur de production** (CPU, RAM, disque réels) — machine non accessible.
- La **puissance électrique réelle** du serveur : 25 W est un ordre de grandeur, pas une mesure
  (un wattmètre ou les compteurs RAPL/IPMI donneraient la vraie valeur).
- Le **coût d'infrastructure partagé** (réseau, sauvegarde, supervision, licences) — hors périmètre.
- Le **temps humain réel** du geste SSH — jamais chronométré, jamais tracé (❓ Q17).
- Le **volume annuel réel** de prédictions — aucun log n'existe (§ 3.6), donc **rien n'est
  reconstituable a posteriori** (❓ Q16).
- L'**empreinte de fabrication** du matériel (*embodied carbon*), qui domine très probablement les
  7 gCO₂e d'usage — hors mandat, et non estimable sans l'inventaire matériel de MediVox.

> **Conséquence méthodologique** : les valeurs de ce volet sont des **ordres de grandeur assumés**,
> et les **rapports** (× 2 722, × 363 886, 96 % du coût) sont les seuls résultats à porter en
> réunion. L'absence totale de journalisation (§ 3.6) fait que **MediVox ne peut, aujourd'hui, ni
> contredire ni confirmer ces chiffres** avec ses propres données — ce qui est, en soi, le constat
> de ressources le plus important du volet.
