# Audit — Volet technique (MediVox Cliniques, prédicteur « DMS » v1)

> Section 3 de `procedure_audit.md`. Périmètre : **architecture, sécurité, scalabilité, points de
> rupture** — observer et chiffrer, **pas corriger** (c'est M7-B2). Hors périmètre : pen-test,
> revue de l'infra réseau MediVox (non accessible), refonte.
>
> **Artefacts audités** : `legacy/train.py` (26 lignes), `legacy/predict.py` (20 lignes),
> `legacy/dms_predictor_v1.joblib` (4 956 361 o), `data/dms_dataset.csv` (516 507 o, 10 000 séjours),
> `tests/test_smoke.py`.
>
> **Banc de mesure** : Windows AMD64, Python 3.11.15, scikit-learn 1.5.1, joblib 1.4.2,
> pandas 2.2.2, 10 cœurs physiques / 12 logiques, 34 Go de RAM (venv du repo d'audit,
> `requirements.txt` épinglé). Toutes les valeurs ci-dessous sont **mesurées** et produites par
> les **sections 2 et 5 de `notebooks/M7-B1_template.ipynb`** — la cellule de récapitulatif 5.6
> reprend une à une les valeurs citées ici. Les latences sont des **médianes sur 5 exécutions**
> (200 itérations pour l'inférence chaude) : elles varient de quelques pourcents d'un run à l'autre.

---

## 3.0 Synthèse en 30 secondes (pour Hélène, DT)

| Ce qui a été mesuré | Valeur | Ce que ça veut dire |
|---|---|---|
| Surcoût d'exécution en mode prod | **1 890 ms** par prédiction, dont **1,51 ms** de calcul utile | **99,9 % du temps est de la mise en place** |
| Débit réel | **0,53 prédiction/s** (vs **192 482/s** en batch) | facteur **×363 886** perdu par l'architecture |
| Écart train / validation croisée | accuracy **0,772 → 0,684** ; AUC **0,866 → 0,725** | **sur-apprentissage de 8,9 pts** (14,1 pts en AUC) |
| Gain réel vs « tout le monde = standard » | **+8,9 pts** (68,4 % vs 59,4 %) | le modèle apporte peu au-delà du hasard structuré |
| Taille du modèle / taille des données | **4,96 Mo** pour **517 Ko** de CSV | **×9,6** — 30 846 feuilles pour 10 000 patients |
| Validation d'entrée | **0 ligne** sur 20 dans `predict.py` | `age=500` et `imc=900` acceptés **sans erreur** |
| Gestion d'erreur / logs | **0 `try`**, **0 log**, **0 `logging`** | aucune décision n'est traçable ni rejouable |
| Tests du modèle | **0 / 3** tests portent sur la qualité | couverture métier **0 %** |
| Secrets | **1 mot de passe prod en clair**, `train.py` l.9, **dans l'historique Git** | rotation obligatoire, suppression du fichier insuffisante |
| Reproductibilité du binaire | **0,16 %** de désaccord entre l'artefact livré et un ré-entraînement | l'artefact de prod **n'est pas celui que le repo régénère** |

**Verdict technique** : le système n'est pas un service, c'est un **script** ; il n'a ni frontière,
ni contrat, ni mémoire. Toute évolution (rééquilibrage du modèle, seuil, supervision humaine)
est aujourd'hui **impossible à déployer et à vérifier** dans cet état.

---

## 3.1 Architecture — modularité et couplage

### Constats

| Question | Constat | Chiffre | Sév. |
|---|---|---|---|
| Le code est-il modulaire ? | 2 scripts « top-level », **aucune fonction, aucune classe** | `def` = **0**, `class` = **0** sur **25 lignes de code utile** (13 + 12) | 🔴 |
| Y a-t-il une séparation train / serve ? | Non : aucun artefact partagé autre que le `.joblib` | la préparation des features est **dupliquée à l'identique** dans les 2 scripts (`train.py` l.14-17 ↔ `predict.py` l.11-17) | 🔴 |
| Y a-t-il une frontière (API, CLI structurée) ? | Non : **4 arguments positionnels**, sans nom, sans type, sans schéma | `sys.argv[1..4]`, `predict.py` l.11-14 | 🔴 |
| Y a-t-il plusieurs services ? | Non — un seul dossier `legacy/`, pas de distinction modèle / code / données | 1 dossier, 3 fichiers | 🟠 |
| Est-ce dockerisé ? | Non — **0 `Dockerfile`**, **0 `docker-compose.yml`** dans le repo | — | 🔴 |
| Y a-t-il une CI ? | Non — **0 fichier** `.github/workflows/`, `.gitlab-ci.yml`, `Jenkinsfile` | — | 🔴 |
| Les dépendances de prod sont-elles figées ? | Non — `requirements.txt` est le **venv d'audit**, pas celui de prod ; `legacy/` n'a **aucun** manifeste | 0 fichier de dépendances côté prod | 🔴 |

### Le couplage, mesuré

Le couplage n'est pas une impression de style, il est **vérifiable** :

```
$ cd ~ && python legacy/predict.py 70 3 28.5 1
can't open file 'C:\Users\...\legacy\predict.py': [Errno 2] No such file or directory
→ code retour 2
```

Le script **ne fonctionne que si le répertoire courant est la racine du repo** : `train.py` l.11
lit `data/dms_dataset.csv` et l.25 écrit `legacy/dms_predictor_v1.joblib`, `predict.py` l.8 lit
`legacy/dms_predictor_v1.joblib` — **3 chemins relatifs codés en dur**, zéro variable
d'environnement, zéro fichier de configuration.

> 🔴 **Conséquence opérationnelle** : le comportement du système dépend du `cwd` de l'appelant
> SSH. Un changement d'utilisateur, de répertoire de connexion ou de shell de bascule casse la
> prédiction **silencieusement du point de vue du métier** (code retour 2, message d'erreur envoyé
> sur `stderr`, que personne ne lit puisqu'il n'y a **aucun log**).

### La dette de duplication

Les colonnes sont construites deux fois, dans deux fichiers, dans un **ordre implicite** :
`["age", "nb_comorbidites", "imc", "sexe_bin"]`. Le modèle embarque pourtant bien
`feature_names_in_` (vérifié : les 4 noms sont présents dans l'artefact) — mais **aucun des deux
scripts ne s'en sert pour valider**. Une inversion d'arguments (`imc` et `nb_comorbidites`, par
exemple) passerait **sans aucune erreur** : ce sont deux valeurs numériques plausibles.

Il n'existe donc **aucun mécanisme** permettant de détecter une erreur d'intégration côté appelant.

❓ **Q7** — Qui construit la ligne de commande appelée en SSH, et à partir de quelle source
(DPI, export, saisie manuelle) ? C'est le seul endroit où l'ordre des 4 arguments est garanti,
et il est **hors du repo**.

---

## 3.2 Versionning

| Objet versionné | Constat | Chiffre | Sév. |
|---|---|---|---|
| **Code** | Git présent, mais **3 commits** au total, **0 tag**, 1 branche | `git rev-list --count HEAD` = **3** ; `git tag` = ∅ | 🟠 |
| **Modèle** | Le `.joblib` est **versionné dans Git comme un binaire de 4,73 Mio** ; 1 seul commit le touche (`Initial commit`) | 4 956 361 o = **88,0 % du volume versionné** (23 fichiers suivis, 5,37 Mio) | 🔴 |
| **Données** | `data/dms_dataset.csv` (10 000 dossiers patients) est **suivi par Git**, en clair | 516 507 o versionnés | 🔴 (voir § 3.4) |
| **Nom de version** | `v1` figé **dans le nom de fichier** | 1 occurrence, `train.py` l.25 | 🟠 |

> 🔴 Le versionning du modèle est un **trompe-l'œil** : le suffixe `_v1` est une chaîne de
> caractères, pas une version. `train.py` l.25 écrit **toujours au même chemin** : chaque
> ré-entraînement **écrase l'artefact précédent sans trace**. Il est donc **impossible de savoir
> quel modèle a produit une décision donnée** — et impossible de revenir en arrière.
>
> 🔴 Stocker un binaire de 4,73 Mio dans Git est en outre un anti-pattern coûteux : chaque
> ré-entraînement versionné ajouterait ~4,7 Mio **définitifs** à l'historique (Git ne compresse
> pas les pickles). 10 ré-entraînements = **~47 Mio** d'historique irréversible.

❓ **Q8** — L'en-tête de `train.py` l.3 indique « *tourne depuis 2 ans, déployé par scp* ». L'artefact
en production est-il **bit-à-bit identique** à celui du repo ? Un `sha256sum` sur le serveur de prod
répond en 2 secondes — et c'est **la seule façon** de le savoir aujourd'hui (voir § 3.5).

---

## 3.3 Documentation et métadonnées du modèle

| Question | Constat | Chiffre |
|---|---|---|
| Métadonnées embarquées ? | **Aucune** : pas de date d'entraînement, pas de hash de dataset, pas de version de code, pas de métrique | 0 métadonnée hors hyperparamètres sklearn |
| Version de bibliothèque tracée ? | Seule trace : `_sklearn_version = 1.5.1` **dans le pickle** (champ interne sklearn), identique au runtime d'audit | 1 champ, non documenté |
| Carte de modèle / choix de sélection ? | **Aucune** — aucun comparatif, aucun critère, aucun seuil justifié | 0 fichier |
| Runbook d'astreinte ? | **Aucun** — rien sur « que faire si `predict.py` échoue à 3 h du matin » | 0 fichier |
| Le code se documente-t-il lui-même ? | Non : **0 docstring**, 0 typage, commentaires uniquement narratifs | `def` = 0 donc 0 docstring possible |

Hyperparamètres réellement embarqués dans l'artefact (extraits de `get_params()`) :

```
n_estimators=60, max_depth=10, max_features='sqrt', criterion='gini',
min_samples_leaf=1, min_samples_split=2, class_weight=None, random_state=0
```

> 🟠 **`class_weight=None`** sur une cible déséquilibrée (59,4 % / 40,6 %) et **surtout** sur une
> étiquette dont le volet éthique a montré qu'elle sous-code 36,3 % des séjours longs de femmes :
> le paramètre qui aurait pu atténuer le déséquilibre **n'a jamais été envisagé**, et aucun document
> ne trace ce choix.
>
> 🟠 **`min_samples_leaf=1`** : c'est le réglage le plus permissif possible. Combiné à
> `max_depth=10`, il produit **30 846 feuilles pour 10 000 patients**, soit **3,08 feuilles par
> patient d'entraînement** — le modèle a la place de mémoriser chaque individu (voir § 3.7).

❓ **Q9** — Une documentation de sélection / d'entraînement existe-t-elle **hors du repo**
(wiki, Confluence, mail) ? Si non, le choix `RandomForest(60, 10)` est **non justifié et
non justifiable** en l'état.

---

## 3.4 Sécurité

### 3.4.1 Secrets

```python
# train.py l.8-9
# secret en dur (anti-pattern a reperer en audit securite)
DB_PASSWORD = "medivox_prod_2024"
```

| Élément | Chiffre / constat | Sév. |
|---|---|---|
| Secrets en clair dans le code | **1** (`DB_PASSWORD`, `train.py` l.9) | 🔴 |
| Présent dans l'historique Git ? | **Oui, depuis le commit initial** — `git log --all -S DB_PASSWORD` remonte **2 commits** (`6215242`, `944d01c`) ; la suppression du fichier **ne l'efface pas** | 🔴 |
| Robustesse du secret | `medivox_prod_2024` : 18 caractères, 0 caractère spécial, **devinable** (nom d'entreprise + environnement + millésime) | 🔴 |
| Variable réellement utilisée ? | **Non** — le mot de passe est **mort dans le code** : `train.py` lit un CSV, pas une base | 🟠 |

> 🔴 **Le secret est mort dans le code mais vivant en production.** Un mot de passe nommé
> `..._prod_2024` suggère une **rotation annuelle** ; si elle n'a pas eu lieu, le secret est valide
> depuis ≥ 1 an et connu de **toute personne ayant eu accès au repo** (ou à un clone, ou à un
> fork, ou à une sauvegarde). Corriger `train.py` **ne suffit pas** : il faut **révoquer** le
> compte de base de données, puis purger l'historique (`git filter-repo` / BFG) et
> **considérer tous les clones existants comme compromis**.

❓ **Q10** — Quel compte de base de données ce mot de passe ouvre-t-il, avec quels droits
(lecture ? écriture ? sur quelle base patients ?), et a-t-il été tourné depuis 2024 ?
**Question à traiter en priorité 0, indépendamment de tout le reste de l'audit.**

### 3.4.2 Validation des entrées — 11 cas testés

`predict.py` caste 4 arguments (l.11-14) **sans aucune borne, aucun schéma, aucun `try`**.
Voici les 11 appels réellement exécutés :

| Cas | Commande | Code retour | Sortie | Verdict |
|---|---|---|---|---|
| Nominal | `70 3 28.5 1` | 0 | `RISQUE_SEJOUR_PROLONGE 0.748` | ✅ |
| **Âge négatif** | `-5 0 22 0` | **0** | `SEJOUR_STANDARD 0.097` | 🔴 **accepté** |
| **Âge = 500 ans** | `500 0 22 0` | **0** | `SEJOUR_STANDARD 0.261` | 🔴 **accepté** |
| **IMC = 0** | `70 3 0 1` | **0** | `RISQUE_SEJOUR_PROLONGE 0.837` | 🔴 **accepté** |
| **IMC = 900** | `70 3 900 1` | **0** | `RISQUE_SEJOUR_PROLONGE 0.503` | 🔴 **accepté** |
| **99 comorbidités** | `70 99 28.5 1` | **0** | `RISQUE_SEJOUR_PROLONGE 0.870` | 🔴 **accepté** |
| **`sexe_bin` = 7** | `70 3 28.5 7` | **0** | `RISQUE_SEJOUR_PROLONGE 0.748` | 🔴 **accepté, traité en silence comme « M »** |
| Argument texte | `abc 3 28.5 1` | 1 | `ValueError: invalid literal for int()` | 🟠 crash brut |
| Argument manquant | `70 3 28.5` | 1 | `IndexError: list index out of range` | 🟠 crash brut |
| **Argument en trop** | `70 3 28.5 1 666` | **0** | `RISQUE_SEJOUR_PROLONGE 0.748` | 🟠 **5ᵉ argument ignoré en silence** |
| Aucun argument | *(vide)* | 1 | `IndexError: list index out of range` | 🟠 crash brut |

**Bilan : 6 valeurs médicalement impossibles sur 11 cas produisent une décision d'apparence
normale, avec code retour 0.** Rien ne distingue, pour l'appelant, une prédiction valide d'une
prédiction sur un âge de 500 ans.

> 🔴 Le domaine d'entraînement est pourtant **parfaitement borné** et connu : `age` ∈ [18 ; 94],
> `nb_comorbidites` ∈ [0 ; 7], `imc` ∈ [15,0 ; 44,1], `sexe_bin` ∈ {0, 1}. **Toute valeur hors de
> ces bornes est une extrapolation** : le RandomForest, par construction, la rabat sur la feuille
> la plus proche et rend une probabilité **confiante mais dépourvue de sens**. `imc=900` rend
> 0,503 — soit exactement la frontière de décision, atteinte par pur hasard d'arbre.
>
> 🟠 Les 3 crashs se font en **`stderr` non journalisé**. Combinés à l'absence de log (§ 3.6),
> un échec de prédiction en prod est **invisible** : ni alerte, ni compteur, ni trace.

### 3.4.3 Désérialisation d'un pickle non signé (CWE-502)

```python
# predict.py l.8
model = joblib.load("legacy/dms_predictor_v1.joblib")
```

`joblib.load` **exécute du code Python arbitraire** contenu dans le fichier. Or :

- l'artefact est un **fichier local de 4,73 Mio** sur le disque du serveur de prod ;
- il y est déposé **par `scp`** (`train.py` l.3) — donc **sans checksum, sans signature,
  sans contrôle d'intégrité** ;
- `predict.py` est exécuté **via SSH** sous un compte disposant au minimum des droits de lecture
  sur ce chemin.

> 🔴 **Toute personne capable d'écrire sur ce chemin obtient l'exécution de code arbitraire
> sous l'identité du compte de prod**, sans aucun signal. C'est la vulnérabilité la plus sévère
> du volet technique : elle ne demande ni exploit ni élévation de privilège, juste un accès en
> écriture à un fichier déposé manuellement.

### 3.4.4 Données de santé

| Constat | Chiffre | Sév. |
|---|---|---|
| Données patients **versionnées dans Git**, en clair | 10 000 dossiers, 516 507 o, suivis depuis `6215242` | 🔴 |
| Chiffrement au repos / en transit | **Aucun** ; `.gitignore` couvre `__pycache__/`, `*.pyc`, `.venv/`, `.ipynb_checkpoints/`, `.DS_Store` — **pas les données** | 🔴 |
| Anonymisation | Pseudonymisation par `patient_id` seulement — **pas une anonymisation** (cf. § 2.1 du volet éthique) | 🔴 |
| Contrôle d'accès à la prédiction | **Aucun** : pas d'authentification, pas d'autorisation, pas de quota. Qui a le compte SSH a le modèle | 🔴 |
| Transport | Ligne de commande SSH — les **4 valeurs de santé transitent en arguments de processus**, donc visibles dans `ps`, l'historique shell, et les logs SSH côté serveur | 🔴 |

> 🔴 **Fuite par le canal le plus banal qui soit** : `age`, `nb_comorbidites`, `imc`, `sexe`
> apparaissent en clair dans la **table des processus** du serveur et, très probablement, dans le
> `~/.bash_history` du compte appelant. N'importe quel utilisateur du serveur peut lire des
> données de santé (art. 9 RGPD) avec un simple `ps aux`.

### 3.4.5 Injection

`predict.py` ne construit ni requête SQL ni commande shell : **pas d'injection dans le script
lui-même**. Le risque est **déplacé chez l'appelant** : si la ligne de commande SSH est assemblée
par concaténation de chaînes depuis un système amont (DPI, export), un champ contrôlé par un tiers
peut injecter des arguments ou un opérateur shell. **Non vérifiable dans le périmètre de l'audit.**

❓ **Q11** — Montrez-nous la ligne exacte qui construit et lance la commande SSH. C'est le seul
endroit où une injection est possible, et il est hors du repo.

### 3.4.6 Validation humaine

Aucun mécanisme de validation humaine n'est **observable** : `predict.py` l.20 imprime une
**décision binaire** (`RISQUE_SEJOUR_PROLONGE` / `SEJOUR_STANDARD`) et relègue la probabilité en
second mot, arrondie à 3 décimales. Il n'existe ni champ « avis du soignant », ni possibilité
d'enregistrer une infirmation, ni trace d'un quelconque arbitrage. Point repris en **Q4**
(volet éthique) : c'est la condition d'application de l'art. 22 RGPD.

---

## 3.5 Reproductibilité

### Ce qui est reproductible

| Test | Résultat |
|---|---|
| `random_state=0` fixé dans `train.py` l.21 | ✅ |
| Ré-entraînement deux fois **sur la même machine** → prédictions identiques | ✅ **100 %** |

### Ce qui ne l'est pas

| Test | Résultat | Sév. |
|---|---|---|
| **Artefact livré vs ré-entraînement local** | **0,16 % de prédictions divergentes** (**16 séjours sur 10 000**) ; accuracy train **0,7721** (livré) vs **0,7715** (régénéré) ; écart de probabilité max **0,0233** | 🔴 |
| Hash SHA-256 du `.joblib` après `python legacy/train.py` | **différent** (`33408e6a…` → `0061d7d8…`) | 🔴 |
| Pipeline de preprocessing | **Aucun** : pas de `Pipeline`, pas de `ColumnTransformer`, pas de `scaler` — les 4 features sont assemblées à la main dans **deux fichiers distincts** | 🔴 |
| Split train/test | **Aucun** (`train.py` l.20-22 entraîne sur 100 % des données) | 🔴 |
| Version des dépendances d'entraînement | **Non figée** (aucun manifeste dans `legacy/`) | 🔴 |

> 🔴 **Le constat le plus important de cette section** : bien que `random_state=0` soit fixé,
> **l'artefact livré n'est pas celui que le repo régénère**. 16 patients sur 10 000 changeraient
> de décision si l'on reconstruisait « le même » modèle aujourd'hui. Cela signifie que l'artefact
> de production a été produit avec **une autre version de bibliothèque, une autre plateforme, ou
> un autre jeu de données** — et que **plus personne ne sait lequel**.
>
> Conséquence directe : **on ne peut pas auditer le modèle de production, seulement un modèle
> proche de lui.** Toutes les mesures de ce rapport, y compris le disparate impact du volet
> éthique, portent sur l'artefact du repo et sont **présumées représentatives à ±0,16 %** —
> présomption à confirmer par Q8.

---

## 3.6 Historisation, traçabilité et monitoring

| Question | Constat | Chiffre | Sév. |
|---|---|---|---|
| Les prédictions sont-elles journalisées ? | **Non** — le résultat part sur `stdout` et **disparaît avec le processus** | **0** occurrence de `logging`, d'écriture fichier ou d'insertion en base | 🔴 |
| L'entraînement est-il journalisé ? | **Non** — un `print` d'accuracy **train** (`train.py` l.26) | 1 `print`, non capturé | 🔴 |
| Monitoring / dérive ? | **Aucun** outil, aucune métrique exportée, aucun seuil d'alerte | 0 | 🔴 |
| Rejouabilité d'une décision | **Impossible** : ni entrée, ni sortie, ni version de modèle, ni horodatage conservés | 0/4 éléments | 🔴 |
| Supervision des échecs | **Aucune** : 3 cas sur 11 sortent en code 1 sans que rien ne le compte | 0 alerte | 🔴 |

> 🔴 **Un système qui décide et n'écrit rien est un système inauditable.** Concrètement,
> aujourd'hui, MediVox est **incapable de répondre** à : « quelle décision a été rendue pour le
> patient X le 12 mars, par quel modèle, sur quelles valeurs ? » — question que posera **le
> premier patient, le premier soignant ou le premier contrôleur** qui la posera.
>
> Ce point n'est pas qu'une bonne pratique technique : il conditionne l'**accountability**
> (art. 5.2 RGPD), le droit d'accès et d'explication, et les obligations de journalisation de
> l'AI Act si la qualification haut risque est retenue (cf. volet éthique).
>
> 🟠 Il rend aussi **indétectable toute dérive** : le modèle « tourne depuis 2 ans » (`train.py` l.3)
> sans qu'aucune mesure n'ait jamais été prise sur des données de production. Ni la population,
> ni les pratiques de codage, ni la performance n'ont été surveillées sur cette période.

---

## 3.7 Qualité du modèle — ce que l'artefact vaut réellement

Mesures sur `data/dms_dataset.csv` (10 000 lignes), validation croisée stratifiée 5 folds,
`shuffle=True, random_state=42`.

| Métrique | Valeur | Lecture |
|---|---|---|
| Accuracy **train** (annoncée par `train.py`) | **0,7721** | chiffre **sans valeur** : mesuré sur les données d'entraînement |
| Accuracy **validation croisée 5-fold** | **0,6835** ± 0,0123 | la vraie performance |
| **Écart de sur-apprentissage** | **−8,9 pts** | 🔴 |
| AUC train | 0,8656 | |
| AUC validation croisée | **0,7245** ± 0,0113 | |
| **Écart AUC** | **−14,1 pts** | 🔴 |
| Baseline « tout le monde = séjour standard » | **0,5941** | |
| **Gain réel du modèle** | **+8,9 pts** d'accuracy | 🟠 modeste pour un outil qui décide |

> 🔴 **Le seul chiffre de performance que MediVox possède aujourd'hui (0,7721) est faux d'environ
> 9 points.** Il est imprimé par `train.py` l.26 sur les données d'entraînement, sans split. Si ce
> chiffre a servi à valider la mise en production, la décision de mise en production repose sur
> une mesure invalide.

### Capacité vs données : le modèle mémorise

| Mesure | Valeur |
|---|---|
| Arbres | 60 |
| Nœuds totaux | **61 632** |
| **Feuilles totales** | **30 846** |
| Profondeur (min/max) | 10 / 10 — **tous les arbres saturent la limite** |
| Échantillons d'entraînement | 10 000 |
| **Feuilles par échantillon** | **3,08** |
| Taille artefact / taille données | **4 956 361 o / 516 507 o = ×9,6** |

> 🔴 **Le modèle pèse près de 10 fois ses données d'entraînement et dispose de 3 feuilles par
> patient.** Avec `min_samples_leaf=1` et `max_depth=10` atteint par **les 60 arbres**, la
> structure n'apprend pas une règle, elle **mémorise des individus** — ce qui explique
> mécaniquement l'écart train/CV de 8,9 points, et constitue accessoirement un **risque de
> mémorisation de données de santé** dans un artefact déplacé par `scp`.

### Chaque feature vaut-elle son importance ?

Ablation par validation croisée (mêmes hyperparamètres, mêmes folds) :

| Configuration | Accuracy CV | AUC CV | Δ accuracy | Importance déclarée |
|---|---|---|---|---|
| **4 features (modèle actuel)** | **0,6835** | **0,7245** | — | — |
| **sans `imc`** | 0,6787 | 0,7199 | **−0,5 pt** | `imc` = **30,2 %** |
| **sans `sexe_bin`** | 0,6642 | 0,7056 | −1,9 pt | `sexe_bin` = **9,5 %** |

> 🔴 **`imc` consomme 30,2 % de l'importance du modèle pour −0,5 point de performance.**
> C'est cohérent avec sa corrélation nulle à la durée réelle (0,001, cf. § 2.2). Le modèle
> **dépense un tiers de sa capacité à apprendre du bruit** sur une donnée de santé sensible —
> et c'est aussi une atteinte directe au **principe de minimisation** (art. 5.1.c RGPD) : une
> donnée collectée, stockée et transmise pour un gain nul.
>
> 🟠 **`sexe_bin` apporte +1,9 point** — mais sur une **étiquette dont le volet éthique a démontré
> qu'elle est biaisée** (36,3 % de FNR chez les femmes). Le modèle ne gagne donc pas en qualité :
> il gagne en **fidélité au biais de codage historique**. Cette ligne est à lire **avec le § 2.3**,
> jamais seule.

### Stabilité de la décision

| Test | Résultat | Lecture |
|---|---|---|
| Seuil de décision | **0,5 codé en dur**, `predict.py` l.20 | non paramétrable, non justifié |
| Prédictions dans la bande `[0,45 ; 0,55]` | **12,03 %** (**1 203 séjours**) | décision **retournée par ±0,05** de probabilité |
| Prédictions dans la bande `[0,40 ; 0,60]` | **24,02 %** (**2 402 séjours**) | quasi un quart de la population est « à la frontière » |
| **Inversion du seul `sexe_bin`** (toutes choses égales par ailleurs) | **37,05 %** des séjours **changent de décision** ; Δ probabilité moyen **0,1898** | 🔴 |

> 🔴 **Pour 3 705 séjours sur 10 000, changer une seule variable — le sexe — inverse la décision.**
> C'est la traduction technique, à l'échelle individuelle, du disparate impact de 0,291 mesuré au
> § 2.4. Un patient et une patiente **cliniquement identiques** reçoivent des décisions opposées
> dans plus d'un tiers des cas.
>
> 🟠 Par ailleurs, `predict.py` **imprime une décision binaire** et relègue la probabilité en
> second mot. Sur 1 203 séjours, cette décision tient à 5 centièmes de probabilité — une précision
> que le modèle, avec un AUC de 0,72, **n'a pas**.

---

## 3.8 Tests

| Test existant | Ce qu'il vérifie | Ce qu'il **ne** vérifie **pas** |
|---|---|---|
| `test_dataset_lisible` | le CSV se charge, 3 colonnes présentes | aucune contrainte de domaine, de type, de nullité |
| `test_modele_legacy_chargeable` | `predict_proba` ∈ [0 ; 1] | **tautologie** : une probabilité est toujours dans [0 ; 1] |
| `test_script_legacy_executable` | code retour 0 et `"SEJOUR"` dans la sortie | aucune valeur attendue, aucun cas limite |

| Indicateur | Chiffre |
|---|---|
| Tests présents | **3** |
| Tests portant sur la **qualité du modèle** | **0** |
| Tests portant sur les **valeurs aux limites** | **0** (les 11 cas du § 3.4.2 ont été écrits **par l'audit**) |
| Tests de **non-régression** (seuil de performance) | **0** |
| Tests d'**équité** par groupe | **0** |
| Couverture de la logique métier `legacy/` | **0 %** |
| Assertions non tautologiques | **1 sur 3** (`returncode == 0`) |

> 🟠 Les 3 tests sont **honnêtement étiquetés** comme des tests d'environnement par leur propre
> docstring (« *ces tests vérifient que vous POUVEZ auditer […] pas que le legacy est correct* »).
> Le problème n'est donc pas leur qualité, c'est qu'**ils sont les seuls**. Trois tests verts
> peuvent donner au métier l'illusion d'un système testé : **rien** dans `legacy/` n'est couvert
> par une assertion de comportement.
>
> 🔴 **Conséquence directe** : aucun changement — seuil, features, rééquilibrage — ne peut être
> déployé avec un filet. Un ré-entraînement qui ferait chuter l'AUC de 0,72 à 0,55 **passerait
> les 3 tests au vert**.

---

## 3.9 Scalabilité et coût d'exécution

### Latence décomposée (médiane sur 5 exécutions, processus neuf)

| Étape | Durée | Part |
|---|---|---|
| **Appel complet `python legacy/predict.py …`** | **1 890 ms** | **100 %** |
| démarrage de l'interpréteur + imports `pandas` / `joblib` | **≈ 971 ms** | **51,4 %** |
| `joblib.load` dans un processus neuf | **918 ms** | **48,6 %** |
| ↳ dont **import de `sklearn`, tiré par le `load` lui-même** | **903 ms** | **47,8 %** |
| ↳ dont désérialisation réelle de l'arbre | **15 ms** | 0,8 % |
| inférence réelle (`predict_proba`, 1 ligne, à chaud) | **1,51 ms** | **0,08 %** |

> Le détail compte : la moitié du coût d'un appel est **`joblib.load` qui déclenche l'import de
> scikit-learn**. Désérialiser le modèle ne coûte que **15 ms** — le reste est de la mise en place
> d'environnement, payée intégralement **à chaque patient**.

### Débit

| Mode | Débit | Coût unitaire |
|---|---|---|
| **Mode production actuel** (1 processus par patient) | **0,53 prédiction/s** | 1 890 ms |
| Inférence chaude, 1 ligne, modèle déjà chargé | 664 prédictions/s | 1,51 ms |
| **Batch 10 000 lignes** | **192 482 prédictions/s** | **5,2 µs** |

> 🔴 **Rapport entre le coût unitaire en production et le coût marginal réel : ×363 886.**
> Prédire pour les 10 000 séjours du dataset coûte **0,05 s en batch** contre **5 h 15 min** dans
> le mode actuel (10 000 × 1,890 s). Ce n'est pas un problème de modèle : le modèle est rapide.
> C'est un **problème d'architecture** — il n'y a pas de service, donc tout est payé au
> démarrage, à chaque patient.

### Mémoire (RSS, processus neuf, médiane sur 5 exécutions)

| Étape | RSS | Coût de l'étape |
|---|---|---|
| après les imports de `predict.py` (python + pandas + joblib) | **72,7 Mo** | — |
| + import de `sklearn` (**tiré par `joblib.load`**) | **141,5 Mo** | **+68,8 Mo** |
| + le modèle déplié en mémoire | **148,5 Mo** | **+7,1 Mo** (1,4× son fichier) |
| **RSS total d'un appel de production** | **148,6 Mo** | dont **95 % = runtime, pas le modèle** |

> 🟠 **Contre-intuitif mais décisif : le modèle ne coûte que 7,1 Mo de RAM.** Les 148,6 Mo d'un
> appel sont à **95 % de l'environnement Python** — et ils sont **repayés intégralement à chaque
> patient**, faute de service. 10 appels concurrents = **~1,5 Go de RSS** pour 15 ms de calcul utile.
>
> Conséquence pour M7-B2 : **alléger le modèle ne réglerait rien**. Le gisement est le mode
> d'exécution (un service qui charge une fois), pas l'artefact. Même lecture que la section 4 du
> notebook : *le modèle n'a jamais été le coût*.

### Ce qui ne passe pas à l'échelle

| Dimension | Limite | Sév. |
|---|---|---|
| Concurrence | **Aucune** : 1 processus = 1 patient, pas de file, pas de pool | 🔴 |
| Mise en cache du modèle | **Aucune** : rechargement complet à chaque appel (918 ms, dont 903 ms d'import `sklearn`) | 🟠 |
| Traitement par lot | **Impossible** : l'interface n'accepte **qu'une ligne** (4 `sys.argv`) | 🔴 |
| Montée en charge humaine | **Le facteur limitant n'est pas la machine, c'est la personne** qui tape la commande SSH | 🔴 |
| Élasticité | Nulle : un seul serveur, aucune réplique | 🔴 |

❓ **Q12** — Combien de prédictions par jour, et à quel horaire ? À 27 séjours/jour (10 000/an),
le volume est **trivialement absorbable** — ce qui déplace tout le sujet : le problème de scalabilité
de MediVox **n'est pas le débit, c'est le geste manuel**. À confirmer avec Hélène.

---

## 3.10 Points de rupture (SPOF)

| # | Point de rupture | Chiffré | Impact s'il tombe | Sév. |
|---|---|---|---|---|
| **1** | **Le fichier `.joblib` sur le disque local du serveur** | 1 exemplaire, 4,73 Mio, `predict.py` l.8, aucun réplica, aucun checksum | **Arrêt total** du service. Restauration possible **uniquement** depuis Git — et l'artefact Git **diffère de la prod** (§ 3.5) | 🔴 |
| **2** | **Le serveur unique** | 1 machine, déploiement `scp` | Arrêt total, **RTO inconnu** (aucun runbook, aucune procédure) | 🔴 |
| **3** | **Le répertoire courant de l'appelant** | 3 chemins relatifs en dur | Échec **code 2**, en silence côté métier | 🔴 |
| **4** | **La personne qui lance la commande SSH** | 1 geste manuel, 4 arguments positionnels | Absence / congé / départ = service à l'arrêt ; **aucune doc ne décrit le geste** | 🔴 |
| **5** | **L'environnement Python de prod** | **0 manifeste de dépendances**, 0 conteneur | Toute mise à jour système peut casser le `joblib.load` ; **impossible de reconstruire l'environnement** | 🔴 |
| **6** | **L'accès en écriture au chemin du modèle** | pickle non signé | **Exécution de code arbitraire** (§ 3.4.3) | 🔴 |
| **7** | **L'historique Git** | 3 commits, 0 tag | Aucun point de retour identifié ; le secret y est **définitivement** inscrit | 🟠 |
| **8** | **La connaissance du système** | **0 runbook**, **0 doc**, **0 métadonnée** | Tout incident se résout par **rétro-ingénierie** de 25 lignes de code non documentées | 🔴 |

> 🔴 **Le système compte 8 points de rupture dont 7 critiques, pour 25 lignes de code utile.**
> La densité est révélatrice : ce ne sont pas des défauts de code, c'est **l'absence complète
> d'architecture**. Chaque fonction normalement assurée par une plateforme (artefact versionné,
> service, configuration, observabilité, reprise) est ici assurée par **une convention orale**.

---

## 3.11 Tableau de synthèse du volet technique

| # | Indicateur | Mesure | Sév. | Conséquence pour MediVox |
|---|---|---|---|---|
| T1 | Secret de prod en clair dans Git | `medivox_prod_2024`, depuis le commit initial | 🔴 | Compromission présumée ; **rotation immédiate** obligatoire |
| T2 | Désérialisation pickle non signée | `joblib.load` sur fichier déposé par `scp` | 🔴 | Exécution de code arbitraire sur le serveur de prod |
| T3 | Données de santé versionnées en clair | 10 000 dossiers, 516 Ko suivis par Git | 🔴 | Art. 9 RGPD ; diffusion incontrôlée par clonage |
| T4 | Données de santé en arguments de processus | 4 valeurs visibles dans `ps` / historique shell | 🔴 | Fuite triviale pour tout utilisateur du serveur |
| T5 | Zéro validation d'entrée | 6 valeurs impossibles / 11 acceptées, code retour 0 | 🔴 | Décisions rendues sur des données aberrantes |
| T6 | Zéro journalisation | 0 log entraînement, 0 log inférence | 🔴 | Aucune décision n'est explicable ni rejouable |
| T7 | Artefact de prod non reproductible | 0,16 % de désaccord, hash différent | 🔴 | On audite un modèle **proche** du modèle de prod, pas lui |
| T8 | Aucun versionning de modèle | 1 chemin écrasé à chaque `train.py` | 🔴 | Impossible de savoir quel modèle a décidé quoi ; pas de rollback |
| T9 | Performance annoncée fausse | 0,7721 (train) vs **0,6835** (CV) | 🔴 | La mise en prod a été validée sur un chiffre invalide |
| T10 | Décision inversée par le seul sexe | **37,05 %** des séjours | 🔴 | Traduction individuelle du biais du § 2.4 |
| T11 | Zéro test de qualité / de limite | 0 sur 3 tests | 🔴 | Aucune évolution déployable avec un filet |
| T12 | 7 SPOF critiques | 8 points de rupture recensés | 🔴 | RTO inconnu, reprise non documentée |
| T13 | Aucune modularité | 0 fonction, 0 classe, 25 lignes, features dupliquées | 🟠 | Toute modification est une réécriture |
| T14 | Feature sans valeur (`imc`) | 30,2 % d'importance, **−0,5 pt** si retirée | 🟠 | Donnée sensible collectée pour un gain nul (minimisation) |
| T15 | Sur-dimensionnement / mémorisation | 30 846 feuilles pour 10 000 patients (3,08/patient) | 🟠 | Sur-apprentissage ; risque de mémorisation de données |
| T16 | Coût d'exécution absurde | 1 890 ms/prédiction dont **99,9 % de mise en place** | 🟠 | 5 h 15 pour ce qui prend 0,05 s ; sobriété nulle |
| T17 | Runtime repayé à chaque appel | 148,6 Mo de RSS/appel, dont **95 % ne sont pas le modèle** | 🟠 | Aucune élasticité ; alléger le modèle ne réglerait rien |
| T18 | Dépendances de prod non figées | 0 manifeste, 0 conteneur | 🟠 | Environnement de prod non reconstructible |
| T19 | Seuil 0,5 codé en dur | 12,03 % des séjours dans `[0,45 ; 0,55]` | 🟠 | 1 203 décisions tiennent à 0,05 de probabilité |
| T20 | Binaire de 4,73 Mio dans Git | 88,0 % du volume versionné | 🟡 | Historique alourdi irréversiblement |

---

## 3.12 Questions ouvertes du volet technique

| # | Question | Destinataire | Pourquoi c'est bloquant |
|---|---|---|---|
| **Q7** | Qui construit la ligne de commande SSH, depuis quelle source ? | Hélène (DT) | Seul endroit garantissant l'ordre des 4 arguments — et seul vecteur d'injection |
| **Q8** | `sha256sum` de l'artefact **en production** vs celui du repo ? | Hélène (DT) | Détermine si cet audit porte sur le bon modèle (§ 3.5) |
| **Q9** | Une doc de sélection / d'entraînement existe-t-elle hors repo ? | Hélène (DT) | Sinon `RandomForest(60, 10)` est un choix non justifié |
| **Q10** | Quel compte ouvre `medivox_prod_2024`, avec quels droits, tourné depuis quand ? | Hélène + Marc (DPO) | **Priorité 0** — indépendante du reste de l'audit |
| **Q11** | Montrez la ligne qui assemble et lance la commande SSH | Hélène (DT) | Qualification du risque d'injection |
| **Q12** | Combien de prédictions/jour, à quels horaires ? | Hélène (DT) | Décide si le sujet est le débit ou le geste manuel |
| **Q13** | Qui a accès en écriture au chemin du `.joblib` sur le serveur ? | Hélène (DT) | Dimensionne le risque T2 (exécution de code arbitraire) |
| **Q14** | Le serveur est-il sauvegardé ? Quel RTO/RPO attendu ? | Hélène (DT) | Aujourd'hui **inconnu** — SPOF #1 et #2 |
| **Q15** | Le chiffre « 0,77 » a-t-il servi à valider la mise en production ? | Hélène (DT) | Si oui, la décision d'origine repose sur une mesure invalide (T9) |

---

## 3.13 Ce que cet audit n'a **pas** pu vérifier

Par honnêteté méthodologique, le périmètre réellement couvert s'arrête ici :

- le **serveur de production** (OS, versions, droits, sauvegardes, réseau) — non accessible ;
- l'**appelant** de `predict.py` (système amont, DPI, ordonnanceur) — hors repo ;
- la **chaîne de déploiement** `scp` réelle (qui, quand, depuis quelle machine) ;
- l'existence de **journaux système** (SSH, syslog) qui contiendraient, eux, une trace partielle
  des données de santé passées en arguments ;
- toute **documentation hors repo** (wiki, tickets, mails).

Les conclusions ci-dessus portent donc sur **l'artefact livré**, et sont **majorantes en
incertitude** : chaque élément non vérifié ne peut qu'ajouter du risque, jamais en retirer.
