# Audit — Volet éthique (MediVox Cliniques, prédicteur « DMS » v1)

> Section 2 de `procedure_audit.md`. Périmètre : **observer, mesurer, hiérarchiser, questionner**.
> Hors périmètre : correction du modèle (M7-B2), AIPD, avis juridique.
> Mesures reproductibles : `notebooks/M7-B1_template.ipynb` — dataset `data/dms_dataset.csv`
> (10 000 séjours), modèle `legacy/dms_predictor_v1.joblib`, code `legacy/train.py` / `legacy/predict.py`.

---

## 2.0 Domaine métier et usage réel

### Le domaine

**Santé — gestion de flux hospitaliers** (établissement de soins privé, MediVox Cliniques).
Le système est vendu en interne comme un « **prédicteur DMS** » (Durée Moyenne de Séjour). Or
`legacy/train.py` entraîne un `RandomForestClassifier` sur la cible **binaire** `sejour_prolonge`,
et `legacy/predict.py` imprime `RISQUE_SEJOUR_PROLONGE` / `SEJOUR_STANDARD`.

> ⚠️ **Premier écart d'audit** : ce n'est **pas** un prédicteur de durée (régression), c'est un
> **classifieur de risque de prolongation** — donc un **profilage de personnes physiques** portant
> sur leur état de santé. Le nom commercial masque la nature réelle du traitement. Tout le volet
> juridique ci-dessous découle de cette requalification.

La DMS n'est pas un indicateur neutre en France : elle est adossée à la **T2A/PMSI**
(GHM/GHS, bornes basses et hautes, suppléments EXH). Un séjour « prolongé » a donc une
**traduction économique** pour l'établissement. C'est précisément ce qui rend l'usage réel du
score critique à qualifier.

### Usage réel du score — ce que l'on sait / ce que l'on ne sait pas

| Question | Constat d'audit | Statut |
|---|---|---|
| Qui calcule le score ? | Script `predict.py` appelé **en prod via SSH**, à la main, 4 arguments positionnels | Observé |
| Qui le lit ? | **Inconnu** — aucun log, aucune interface, aucune trace de destinataire | ❓ **Q1** |
| Quand est-il calculé ? | **Inconnu** — à l'admission ? en cours de séjour ? en préadmission ? | ❓ **Q2** |
| Qu'est-ce qu'il déclenche ? | **Inconnu** — planification de lit ? coordination de sortie ? arbitrage d'admission ? | ❓ **Q3** |
| Un humain peut-il le contredire ? | Aucun mécanisme observable ; `predict.py` **imprime une décision binaire** (seuil 0,5 codé en dur), pas une probabilité motivée | ❓ **Q4** |
| Le patient est-il informé ? | Aucune trace d'information, de mention d'information ni d'explication de la logique | ❓ **Q5** |

**Sans réponse à Q1–Q4, aucune qualification juridique ne peut être fermée.** C'est le point
central à porter à Hélène (DT) et Marc (DPO). L'audit livre donc des qualifications
**conditionnelles**, avec leurs conditions de bascule.

---

## 2.1 Le dataset : features et variables sensibles

`data/dms_dataset.csv` — **10 000 lignes × 10 colonnes**, 0 valeur manquante, 0 doublon,
10 000 `patient_id` distincts (**1 ligne = 1 patient**).

| Colonne | Type | Rôle | Nature au sens RGPD | Utilisée par le modèle ? |
|---|---|---|---|---|
| `patient_id` | str | Identifiant | **Pseudonyme** (donnée personnelle, art. 4-5 RGPD) | Non |
| `age` | int (18–94) | Feature | Quasi-identifiant, **critère protégé** (âge) | ✅ Oui |
| `sexe` | cat (F/M) | Feature | **Variable sensible directe**, critère protégé | ✅ Oui (`sexe_bin`) |
| `departement` | int (35/44/49/56/85) | Contexte | **Quasi-identifiant géographique** (proxy socio-géo) | ❌ Non |
| `service` | cat (5 modalités) | Contexte | **Donnée de santé** (art. 9) — révèle la pathologie | ❌ Non |
| `type_admission` | cat (urgence/programmé) | Contexte | **Donnée de santé** — révèle le contexte de prise en charge | ❌ Non |
| `nb_comorbidites` | int (0–7) | Feature | **Donnée de santé** (art. 9) | ✅ Oui |
| `imc` | float (15,0–44,1) | Feature | **Donnée de santé** (art. 9) | ✅ Oui |
| `dms_jours` | float (1,0–15,3) | Mesure réelle | **Donnée de santé** | ❌ Non (mesure a posteriori) |
| `sejour_prolonge` | int (0/1) | **Cible** | Étiquette dérivée — voir § 2.3 | Cible |

### Variables sensibles — directes et indirectes

- **Directe** : `sexe`, **utilisé comme feature** (`sexe_bin = (sexe == "M")`, `train.py` l.16).
  Aucune justification clinique n'est documentée nulle part dans le repo. 🔴
- **Directe** : `age` — critère protégé, mais dont la pertinence clinique sur la durée de séjour
  est plausible (corrélation observée 0,346 avec `dms_jours`). À **justifier**, pas à condamner.
- **Indirectes (proxies)** : `service` (proxy de pathologie), `nb_comorbidites` (proxy d'état de
  santé et indirectement d'âge/précarité), `imc` (proxy de morphologie / potentiel stigmate),
  `departement` (proxy socio-géographique).
- **Quasi-identification** : le croisement `age` × `sexe` × `departement` × `service` ×
  `type_admission` sur un dataset de 10 000 lignes produit des **cellules de très faible effectif**
  (ex. dép. 56 = 500 séjours, soit ~100 par service, puis ÷2 par sexe, puis réparti sur 77 âges).
  La pseudonymisation par `patient_id` **ne rend pas le jeu anonyme** : il reste une donnée
  personnelle, pleinement soumise au RGPD. 🟠

---

## 2.2 EDA rapide — ce que disent les données

### Distributions

| Variable | Moyenne | Médiane | Écart-type | Min | Max |
|---|---|---|---|---|---|
| `age` | 55,7 | 56 | 22,1 | 18 | 94 |
| `nb_comorbidites` | 1,51 | 1 | 1,22 | 0 | 7 |
| `imc` | 26,06 | 26,0 | 4,96 | 15,0 | 44,1 |
| `dms_jours` | 5,60 | 5,5 | 2,45 | 1,0 | 15,3 |

| Catégorie | Répartition |
|---|---|
| `sexe` | F **50,11 %** / M **49,89 %** (équilibré) |
| `type_admission` | programmé **59,8 %** / urgence **40,2 %** |
| `service` | cardiologie 20,0 % · chirurgie 20,0 % · gériatrie 20,1 % · médecine 19,7 % · orthopédie 20,2 % |
| `departement` | **44 : 49,2 %** · 49 : 20,2 % · 85 : 15,6 % · 35 : 10,0 % · 56 : 5,0 % |
| `sejour_prolonge` | 0 : **59,4 %** / 1 : **40,6 %** |

### Taux d'étiquetage « séjour prolongé » par groupe

| Découpage | Taux `sejour_prolonge = 1` |
|---|---|
| **sexe** | **F 32,07 %** vs **M 49,15 %** |
| service | médecine 19,5 % · cardiologie 20,9 % · orthopédie 48,9 % · chirurgie 49,7 % · **gériatrie 63,4 %** |
| type_admission | programmé 32,9 % vs **urgence 52,0 %** |
| âge | < 65 ans : 32,8 % vs **≥ 65 ans : 53,1 %** |
| département | 39,5 % → 41,8 % (**aucun écart notable**) |

### Durée réellement observée (`dms_jours`) par groupe

| Découpage | Moyenne | Médiane |
|---|---|---|
| **sexe F** | **5,620 j** | 5,6 |
| **sexe M** | **5,585 j** | 5,5 |
| cardiologie | 4,23 j | 4,1 |
| médecine | 4,17 j | 4,0 |
| orthopédie | 6,15 j | 6,1 |
| chirurgie | 6,22 j | 6,1 |
| gériatrie | 7,20 j | 7,1 |
| départements | 5,55 → 5,75 j | — |

> 🔴 **Le constat le plus lourd de l'EDA** : les femmes restent **aussi longtemps** que les hommes
> (5,620 j vs 5,585 j — écart de **~50 minutes**, non significatif), mais sont étiquetées
> « séjour prolongé » **17 points de moins** (32,1 % vs 49,2 %).
> **L'écart n'est pas dans la réalité, il est dans l'étiquette.**

### Corrélations avec la durée réelle

| Feature | Corrélation avec `dms_jours` | Corrélation avec `sejour_prolonge` |
|---|---|---|
| `nb_comorbidites` | **0,447** | 0,287 |
| `age` | **0,346** | 0,241 |
| `imc` | **0,001** | **−0,006** |

**`imc` n'a strictement aucun pouvoir prédictif** — et se voit pourtant attribuer **30,2 % de
l'importance** du modèle (voir § 2.4). Le modèle **apprend du bruit** sur une donnée de santé
sensible, non minimisée. 🔴

À l'inverse, les variables les plus discriminantes de la durée réelle — `service`
(4,2 j → 7,2 j, soit un facteur **1,7×**) et `type_admission` (urgence : +19 pts d'étiquetage) —
sont **purement et simplement jetées** par `train.py` (l.14, commentaire : « *on jette les
colonnes texte* »). Le modèle ignore le métier et conserve le sexe.

---

## 2.3 L'étiquette est-elle la réalité ? (confrontation `sejour_prolonge` ↔ `dms_jours`)

Un modèle apprend ses **étiquettes**, pas le monde. On reconstruit donc la **règle implicite**
d'étiquetage, par groupe :

| Groupe | min `dms_jours` si label = 1 | max `dms_jours` si label = 0 |
|---|---|---|
| **Hommes** | 5,6 j | **5,5 j** → règle **nette et déterministe** : `dms_jours ≥ 5,6` |
| **Femmes** | 5,6 j | **14,9 j** → **chevauchement massif** : des femmes à **14,9 jours** sont codées « séjour standard » |

**Référence d'audit retenue** : `y_ref = (dms_jours ≥ 5,6)` — c'est **exactement** la règle
appliquée aux hommes, donc une référence non arbitraire, **dérivée des données elles-mêmes**
et non d'un seuil choisi par l'auditeur.

- Taux de référence : **F 50,37 %** vs **M 49,15 %** → les deux groupes font, en réalité,
  **autant** de séjours longs.
- Désaccord global étiquette ↔ référence : **9,17 %** (917 séjours sur 10 000).

**Erreurs de l'étiquette historique elle-même, mesurées contre `y_ref` :**

| Groupe | FNR (séjour long non codé) | FPR |
|---|---|---|
| **Hommes** | **0,0 %** | 0,0 % |
| **Femmes** | **36,33 %** | 0,0 % |

> 🔴 **Un séjour long de femme sur trois (917 patientes) n'a jamais été codé comme prolongé.**
> Le biais n'est pas un artefact du modèle : il est **dans la donnée d'apprentissage**, donc
> dans le **processus d'étiquetage historique** de MediVox (sous-codage, protocole différencié,
> ou règle métier implicite). Le modèle ne fait ensuite que l'hériter — et l'amplifier.
>
> ❓ **Q6 (critique, à poser à MediVox)** : **qui** produit `sejour_prolonge`, **selon quelle
> règle écrite**, et **pourquoi** cette règle est-elle déterministe pour les hommes et
> probabiliste pour les femmes ? C'est la question la plus urgente de tout l'audit.

---

## 2.4 Le modèle amplifie-t-il ? Disparate impact chiffré

### Étape 1 — Définir le préjudice AVANT de lire le chiffre

« Être signalé `RISQUE_SEJOUR_PROLONGE` » est **ambivalent**, et son sens dépend de **Q3** :

| Hypothèse d'usage | Le signalement est… | Qui est lésé |
|---|---|---|
| **(A)** Anticipation de sortie, coordination ville/aval, réservation de lit | un **avantage** (accès à une prise en charge renforcée) | les **non-signalés à tort** (FNR) |
| **(B)** Arbitrage d'admission, priorisation, pilotage de rentabilité T2A | un **désavantage** (patient jugé « coûteux ») | les **signalés à tort** (FPR) |

**L'audit ne peut pas trancher** entre (A) et (B) sans réponse à Q3. Les deux lectures sont donc
instruites ci-dessous. C'est une **condition de bascule du diagnostic**, pas une échappatoire.

### Étape 2 — Disparate impact (signal d'alerte, pas verdict)

Ratio des taux de positifs, repère conventionnel de la « règle des 4/5 » = **0,80**
(origine : droit US de l'emploi — **repère**, pas norme opposable en santé).

| Variable | DI sur **l'étiquette** | DI sur **la prédiction du modèle** | Effet |
|---|---|---|---|
| **sexe (F/M)** | **0,653** ❌ | **0,291** 🔴❌ | **amplification × 2,24** |
| âge (≥65 / <65) | 1,618 | **2,845** | amplification × 1,76 |
| département (min/max) | 0,945 ✅ | 0,906 ✅ | neutre |

Taux bruts : prédiction positive **F 14,15 %** vs **M 48,57 %**, alors que les étiquettes
étaient déjà à 32,07 % / 49,15 % et la **réalité à 50,37 % / 49,15 %**.

> Le modèle **ne se contente pas de reproduire** le biais d'étiquetage : il le **plus que double**.
> Mécanisme identifié : `sexe_bin` est une **feature active**, à laquelle le RandomForest attribue
> **9,53 %** de son importance. Le modèle a appris « être une femme ⇒ moins de risque », alors
> que la donnée réelle dit l'inverse (F 50,37 % vs M 49,15 %).

**Importances du modèle** (`feature_importances_`) :

| Feature | Importance | Corrélation réelle avec `dms_jours` | Lecture |
|---|---|---|---|
| `age` | 35,20 % | 0,346 | plausible |
| `imc` | **30,20 %** | **0,001** | 🔴 **bruit pur appris comme 2ᵉ signal** |
| `nb_comorbidites` | 25,07 % | 0,447 | pertinent mais **sous-pondéré** |
| `sexe_bin` | **9,53 %** | — | 🔴 **variable sensible, sans justification** |

### Étape 3 — Erreurs par groupe (là où se trouve le préjudice réel)

Mesurées contre `y_ref` :

| Groupe | **FNR** (vrai séjour long **non** signalé) | **FPR** (signalé **à tort**) |
|---|---|---|
| **Femmes** | **73,69 %** 🔴 | 1,81 % |
| **Hommes** | 24,23 % | 22,27 % |
| ≥ 65 ans | 35,04 % | 29,14 % |
| < 65 ans | 63,35 % | 5,88 % |

> **Les femmes sont quasi invisibles au modèle : il rate près de 3 séjours longs sur 4.**
> Sous l'**hypothèse (A)** — la plus probable pour un outil de planification de lits — cela
> signifie que **~1 860 patientes** par tranche de 10 000 séjours sont privées de l'anticipation
> de sortie dont bénéficient les hommes dans la même situation clinique.
> Sous l'**hypothèse (B)**, le sens s'inverse et ce sont les hommes (FPR 22,3 % vs 1,8 %) qui
> sont sur-signalés comme « coûteux ».
> **Dans les deux cas, le traitement est différencié selon le sexe, sans justification objective.**

### Étape 4 — Calibration par groupe

| Groupe | Probabilité moyenne prédite | Taux de référence réel | Écart |
|---|---|---|---|
| **Femmes** | **0,321** | **0,504** | **−18,3 pts** 🔴 |
| **Hommes** | 0,491 | 0,492 | −0,1 pt ✅ |
| ≥ 65 ans | 0,532 | 0,646 | −11,4 pts |
| < 65 ans | 0,328 | 0,406 | −7,8 pts |

Le modèle est **correctement calibré pour les hommes et structurellement sous-calibré pour les
femmes**. Ce n'est pas un bruit statistique : c'est un décalage systématique, cohérent en
ampleur avec le biais d'étiquetage documenté au § 2.3.

### Synthèse du volet biais

| Constat | Sévérité |
|---|---|
| Étiquetage historique sous-code 36 % des séjours longs féminins, à durée réelle identique | 🔴 |
| `sexe` utilisé comme feature sans justification clinique documentée | 🔴 |
| DI F/M = 0,291 sur les prédictions (vs repère 0,80), amplification ×2,24 du biais d'étiquette | 🔴 |
| FNR femmes 73,7 % vs hommes 24,2 % | 🔴 |
| Sous-calibration systématique du groupe F (−18,3 pts) | 🔴 |
| `imc` = 30 % de l'importance pour une corrélation de 0,001 (bruit appris) | 🔴 |
| `service` / `type_admission` (les variables réellement prédictives) écartées du modèle | 🟠 |
| DI 65+/<65 = 2,845 — **à ne pas conclure seul** : effet clinique de l'âge plausible (corr. 0,346) ; ce qui interroge, c'est l'**amplification** (1,618 → 2,845) | 🟠 |
| Aucun écart par département | 🟡 (point positif) |

---

## 2.5 RGPD — données de santé

> Le RGPD s'applique **dans tous les cas**, quelle que soit la qualification AI Act.

### Art. 9 — catégories particulières

`nb_comorbidites`, `imc`, `service`, `type_admission`, `dms_jours` sont des **données
concernant la santé** (art. 4-15). Leur traitement est **interdit par principe**, sauf exception.

- **Base légale art. 9 § 2 : non documentée dans le repo.** Les candidates plausibles sont
  le **h)** (médecine préventive, gestion des systèmes et services de soins, sous secret
  professionnel) ou le **i)** (intérêt public dans le domaine de la santé publique).
- ⚠️ **L'audit ne présume pas** que le h) s'applique : il est **à vérifier** avec Marc. Un usage
  de **pilotage économique/logistique** (hypothèse B) s'éloigne du h) et fragiliserait la base.
- Le pendant art. 6 (licéité générale) et l'articulation avec le **secret médical**
  (art. L1110-4 CSP) sont également à confirmer. ❓ **Q7**

### Art. 5 — minimisation, exactitude, limitation de conservation

| Principe | Constat |
|---|---|
| **Minimisation (5.1.c)** | `imc` est collecté et utilisé alors que sa corrélation à la durée est **0,001** → donnée de santé traitée **sans finalité démontrée**. `sexe` utilisé sans justification. 🔴 |
| **Exactitude (5.1.d)** | L'étiquette `sejour_prolonge` est **démontrée inexacte** pour 36 % des séjours longs féminins (§ 2.3). Une donnée inexacte doit être rectifiée. 🔴 |
| **Limitation de conservation (5.1.e)** | Aucune durée de conservation définie ni dans le code ni dans le repo ; le CSV de 10 000 séjours est versionné en clair dans le dépôt. ❓ **Q8** 🟠 |
| **Limitation des finalités (5.1.b)** | Finalité affichée (« prédicteur DMS ») ≠ traitement réel (classification de risque individuel) → **écart de finalité** à documenter. 🔴 |
| **Responsabilité (5.2)** | Aucune documentation, aucun versionnage, aucune metadata modèle (`train.py` l.25) → **accountability non démontrable**. 🔴 |

### Art. 12–15 — information et transparence

Aucune trace de mention d'information aux patients, ni de communication d'« **informations
utiles concernant la logique sous-jacente** » (art. 15 § 1 h, applicable dès lors qu'il y a
décision automatisée au sens de l'art. 22). ❓ **Q5** 🟠

### Art. 25 / 30 / 32 / 35

| Article | Constat |
|---|---|
| **Art. 32 — sécurité** | `DB_PASSWORD = "medivox_prod_2024"` en **clair dans `train.py` (l.9)**, versionné. Déploiement **par `scp` manuel**. Aucune trace d'authentification ni de chiffrement applicatif. 🔴 *(détaillé dans `02_technique.md`)* |
| **Art. 25 — protection dès la conception** | Variable sensible en entrée, aucun garde-fou, seuil 0,5 en dur, aucune validation d'input (`predict.py` l.11-14). 🔴 |
| **Art. 30 — registre** | Existence du traitement au registre : **non vérifiable** depuis le repo. ❓ **Q9** 🟠 |
| **Art. 35 — AIPD** | Profilage systématique + données de santé + grande échelle → **les critères d'obligation d'AIPD semblent réunis** (lignes directrices WP248). L'audit **signale l'obligation probable** ; **rédiger l'AIPD est hors mandat**. 🟠 → Marc |
| **Hébergement** | Données de santé → **certification HDS** (art. L1111-8 CSP) requise pour l'hébergeur. Le modèle et les données résident sur le **disque local d'un serveur** (`train.py` l.25). ❓ **Q10** 🟠 |

### Art. 22 — décision individuelle automatisée : les **deux** conditions

> Rappel : les conditions sont **cumulatives**. Une prédiction n'est pas une décision.

**Condition 1 — décision fondée *exclusivement* sur un traitement automatisé ?**

- `predict.py` **n'émet pas une probabilité, il émet un verdict** (`RISQUE_SEJOUR_PROLONGE`),
  seuil 0,5 codé en dur, **sans log, sans traçabilité, sans champ de motivation**.
- **Aucun mécanisme d'intervention humaine n'est observable dans le code.**
- Mais rien ne prouve non plus qu'un humain ne décide pas en aval → **en droit, indéterminé**.
- ⚠️ **CJUE, C-634/21 *SCHUFA Holding* (7 déc. 2023)** : un **score** peut relever de l'art. 22
  s'il joue un **rôle déterminant** dans la décision prise par un tiers. Une validation humaine
  « pour la forme » ne suffit pas.
- **Point bloquant** : l'**absence totale de journalisation** rend **impossible de démontrer**
  un taux de désaccord humain/score. MediVox ne peut donc **pas prouver** qu'il est hors art. 22.
  ❓ **Q4** → *quel est le taux de désaccord entre le score et la décision finale, et où est-il tracé ?*

**Condition 2 — effet juridique ou *similairement significatif* ?**

- Sous **hypothèse (B)** (arbitrage d'admission, priorisation, pilotage T2A) : **oui**, un effet
  sur l'accès ou le délai de prise en charge est un effet significatif.
- Sous **hypothèse (A)** (coordination de sortie, réservation de lit d'aval) : l'effet reste
  **significatif** (date de sortie, accès à un dispositif d'aval), quoique moins tranché.
- Sous une hypothèse **purement agrégée** (prévision de charge, capacitaire, sans effet individuel
  identifiable) : **non**. Mais le code produit un verdict **par patient**, ce qui rend cette
  troisième hypothèse peu compatible avec l'implémentation observée.

**➡️ Conclusion art. 22 : applicabilité *probable*, non fermée faute de réponse à Q3 et Q4.**
Si l'art. 22 s'applique, s'ajoutent : information spécifique (art. 13-14 § 2 f), droit d'obtenir
une **intervention humaine**, d'exprimer son point de vue et de **contester** (art. 22 § 3), et —
pour des données de santé — l'art. 22 § 4 qui n'autorise le traitement **que** sur la base du
consentement explicite ou d'un motif d'intérêt public, **avec** mesures de sauvegarde. 🔴

---

## 2.6 AI Act (règlement UE 2024/1689) — qualification raisonnée

> ⚠️ **On ne présume pas que « santé = haut risque ».** On parcourt les cas de l'**art. 6**.
> Les **dates d'application** des obligations « haut risque » ayant fait l'objet d'ajustements,
> toute date citée devra être revérifiée sur le texte consolidé EUR-Lex au jour de l'audit.

### Préalable : est-ce un « système d'IA » au sens de l'art. 3 ?

Oui. RandomForest supervisé, inférence à partir d'entrées produisant une sortie (classification)
influençant un environnement. MediVox en est vraisemblablement **fournisseur ET déployeur**
(système développé en interne et mis en service pour son propre usage) — à confirmer. ❓ **Q11**

### Cas 1 — Annexe I : composant de sécurité / produit réglementé (dispositif médical, MDR 2017/745)

- Si le score n'alimente **que** de la logistique de lits → **probablement pas** un DM : pas de
  finalité médicale de diagnostic, prévention, pronostic ou traitement d'une pathologie.
- **Mais** s'il **informe une décision clinique** (ex. arbitrage d'une date de sortie, orientation
  vers un dispositif d'aval), la **règle 11 de l'Annexe VIII MDR** (cf. MDCG 2019-11) pourrait
  s'appliquer → logiciel DM, classe IIa ou supérieure, avec évaluation par organisme notifié,
  et donc **haut risque AI Act par le cas 1**.
- **➡️ Statut : à instruire. Condition de bascule = Q3.** 🟠

### Cas 2 — Annexe III

| Point Annexe III | Applicable ? | Raisonnement |
|---|---|---|
| **5 a)** — évaluation, **par ou pour une autorité publique**, de l'éligibilité aux services essentiels de soins | **à instruire** | MediVox est une clinique **privée**. Mais si elle exerce une **mission de service public hospitalier** (autorisation ARS, statut ESPIC, activité conventionnée), le « **ou pour** » peut être rempli. ❓ **Q12** |
| **5 d)** — systèmes de **triage des patients en urgence** | **à instruire** | **40,2 % du dataset sont des admissions en urgence**, et `type_admission` figure dans les données. Si le score est calculé **à l'arrivée aux urgences** et influence l'ordre/l'orientation → **cas explicite, haut risque**. S'il tourne **après** admission pour planifier un lit → non. ❓ **Q2 + Q3** |
| Autres points (emploi, crédit, justice…) | Non | Hors sujet |

### Cas 3 — Exception de l'art. 6 § 3 (tâche préparatoire / étroite)

**Fermée.** L'exception ne s'applique **pas** lorsque le système effectue un **profilage de
personnes physiques**. Or ce système **évalue l'état de santé individuel** de patients
identifiés — c'est un profilage au sens de l'art. 4-4 RGPD.
➡️ **Si l'Annexe III s'applique, l'exception ne pourra pas être invoquée.**

### Conclusion de qualification

> **Qualification : INDÉTERMINÉE en l'état, avec une présomption sérieuse de haut risque.**
>
> - Elle **bascule en haut risque** si l'une de ces conditions est vraie :
>   (a) le score est calculé à l'arrivée aux urgences et influence le triage → Annexe III 5 d) ;
>   (b) MediVox exerce une mission de service public hospitalier et le score conditionne l'accès
>   aux soins → Annexe III 5 a) ;
>   (c) le score informe une décision clinique → logiciel DM (MDR règle 11) → Annexe I.
> - Elle **reste hors haut risque** uniquement si le score sert exclusivement à une planification
>   capacitaire **sans effet individuel** — hypothèse **peu compatible** avec un `predict.py`
>   qui émet un verdict patient par patient.
> - Dans **tous** les cas, l'exception 6 § 3 est inutilisable (profilage).

**Si la bascule est confirmée**, les obligations à instruire (art. 8-15) incluent notamment :
système de **gestion des risques** (art. 9) ; **gouvernance et qualité des données**, incluant
l'**examen des biais** (art. 10) — *l'audit démontre ici qu'il n'a pas été fait* ;
**documentation technique** (art. 11) — *absente* ; **journalisation** (art. 12) — *absente* ;
**transparence** vers les utilisateurs (art. 13) ; **supervision humaine effective** (art. 14) —
*non observable* ; **exactitude, robustesse, cybersécurité** (art. 15) — *pas de split
train/test, `accuracy` mesurée sur le train, mot de passe en dur*.

**Indépendamment de la qualification** : l'**art. 4** (maîtrise de l'IA / *AI literacy* des
personnels concernés) et, le cas échéant, les obligations de **transparence de l'art. 50**
restent à examiner.

---

## 2.7 Autres textes applicables

| Texte | Point d'accroche |
|---|---|
| **RGPD** (UE 2016/679) | art. 4-15, 5, 6, 9, 12-15, 22, 25, 30, 32, 35 — cf. § 2.5 |
| **Loi Informatique et Libertés** (78-17 modifiée), **titre III** | traitements de données de santé ; formalités et référentiels CNIL |
| **Référentiel CNIL « entrepôts de données de santé »** | si le CSV de 10 000 séjours constitue un entrepôt réutilisé à des fins secondaires → cadre dédié. ❓ **Q13** |
| **Code de la santé publique** | **L1110-4** (secret médical) ; **L1111-8** (hébergement de données de santé → **certification HDS**) ; **L1111-2** (information du patient) |
| **AI Act** (UE 2024/1689) | art. 3, 4, 6, Annexe I, Annexe III 5 a) et 5 d), art. 8-15, art. 50 — cf. § 2.6 |
| **Règlement Dispositifs Médicaux** (UE 2017/745) | qualification logiciel DM, **règle 11** Annexe VIII / MDCG 2019-11 |
| **Code pénal art. 225-1 et 225-2 / loi 2008-496** | **le sexe est un critère de discrimination prohibé** ; refus/subordination de la fourniture d'un **bien ou service** — à instruire si hypothèse (B) |
| **Code pénal art. 226-13** | violation du secret professionnel (mot de passe prod en clair, CSV patients versionné) |
| **CJUE C-634/21 *SCHUFA*** (7 déc. 2023) | un score déterminant relève de l'art. 22 même si la décision est formellement prise par un tiers |
| **Défenseur des droits / CNIL, *Algorithmes : prévenir l'automatisation des discriminations* (2020)** | cadre de référence pour le volet biais |
| **Code de la sécurité sociale — T2A/PMSI** (GHM/GHS, bornes, EXH) | traduction économique d'un « séjour prolongé » → motive l'hypothèse (B) |

> Hors périmètre de cet audit : NIS2, marchés publics, droit du travail.

---

## 2.8 Questions ouvertes à MediVox (volet éthique)

Par ordre de **blocage décroissant** — sans réponse à Q1–Q4, aucune qualification n'est fermable.

| # | Question | Pour qui | Débloque |
|---|---|---|---|
| **Q6** | Qui produit l'étiquette `sejour_prolonge`, selon quelle **règle écrite** ? Pourquoi est-elle déterministe pour les hommes (`dms ≥ 5,6`) et probabiliste pour les femmes (36 % de sous-codage) ? | Hélène + métier | La cause racine du biais |
| **Q3** | **Que déclenche concrètement le score ?** Planification de lit, coordination de sortie, ou arbitrage d'admission / pilotage T2A ? | Hélène | Sens du préjudice, AI Act, art. 22 |
| **Q4** | Quel est le **taux de désaccord** entre le score et la décision finale, et **où est-il tracé** ? (aucun log n'existe aujourd'hui) | Hélène | Art. 22, condition 1 (SCHUFA) |
| **Q2** | **Quand** le score est-il calculé — à l'arrivée aux urgences, ou après admission ? | Hélène | AI Act Annexe III 5 d) |
| **Q1** | **Qui lit** la sortie de `predict.py` et sous quelle forme ? | Hélène | Supervision humaine |
| **Q12** | MediVox exerce-t-elle une **mission de service public hospitalier** (autorisation ARS / ESPIC) ? | Direction | AI Act Annexe III 5 a) |
| **Q7** | Quelle **base légale art. 9 § 2** a été retenue et documentée ? | Marc | Licéité du traitement |
| **Q14** | Quelle **justification clinique** documentée pour l'usage du **sexe** comme variable d'entrée ? (à défaut : aggravant caractérisé) | Hélène + médical | Minimisation, non-discrimination |
| **Q15** | Quelle **justification** pour l'`imc`, dont la corrélation à la durée réelle est de **0,001** ? | Hélène + médical | Minimisation (art. 5.1.c) |
| **Q5** | Les patients sont-ils **informés** de l'existence de ce traitement et de sa logique ? | Marc | Art. 12-15 |
| **Q10** | Où sont **hébergés** les données et le modèle ? L'hébergeur est-il **certifié HDS** ? | Hélène + Marc | L1111-8 CSP |
| **Q9** | Le traitement figure-t-il au **registre** (art. 30) ? Une **AIPD** (art. 35) a-t-elle été menée ? | Marc | Accountability |
| **Q8** | Quelle **durée de conservation** pour `dms_dataset.csv` et les prédictions produites ? | Marc | Art. 5.1.e |
| **Q11** | MediVox est-elle **fournisseur**, **déployeur**, ou les deux au sens de l'AI Act ? | Direction | Répartition des obligations |
| **Q13** | Le dataset constitue-t-il un **entrepôt de données de santé** au sens du référentiel CNIL ? | Marc | Cadre de réutilisation |

---

## 2.9 À retenir pour la consolidation (`04_consolidation.md`)

1. 🔴 **Le biais est d'abord dans la donnée, pas dans l'algorithme** : à durée réelle identique
   (5,620 j vs 5,585 j), **36 % des séjours longs de femmes ne sont pas codés**. 917 patientes.
2. 🔴 **Le modèle amplifie ce biais ×2,24** (DI 0,653 → **0,291**) en utilisant `sexe` comme
   feature (9,53 % d'importance) sans justification clinique.
3. 🔴 **FNR femmes = 73,7 %** contre 24,2 % pour les hommes ; sous-calibration de **−18,3 points**.
4. 🔴 **`imc` = 30,2 % de l'importance pour une corrélation de 0,001** : donnée de santé traitée
   sans finalité démontrée, et bruit appris comme signal.
5. 🟠 **Le modèle ignore les variables réellement prédictives** (`service` : 4,2 j → 7,2 j ;
   `type_admission` : +19 pts) jetées par `train.py`.
6. 🔴 **Écart entre la finalité affichée et le traitement réel** : « prédicteur DMS » ≠ classifieur
   de risque individuel → limitation des finalités, et toute la qualification juridique.
7. 🔴 **L'absence de journalisation empêche MediVox de démontrer sa conformité** à l'art. 22 —
   l'établissement ne peut pas prouver qu'il en est hors champ.
8. 🟠 **Qualification AI Act indéterminée mais présomption sérieuse de haut risque** ;
   l'exception de l'art. 6 § 3 est **fermée** (profilage).

> 📌 Ce volet **hiérarchise et questionne**. Les corrections (ré-étiquetage, retrait de `sexe`,
> ajout de `service`/`type_admission`, calibration par groupe, journalisation) relèvent de **M7-B2**
> et ne sont **pas** proposées ici.
