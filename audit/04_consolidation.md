# Audit — Consolidation (MediVox Cliniques, prédicteur « DMS » v1)

> Sections 5, 6 et 7 de `procedure_audit.md`. Ce volet **ne produit aucune mesure nouvelle** :
> il reprend, hiérarchise et synthétise les constats de `01_ethique.md`, `02_technique.md` et
> `03_ressources.md`.
> Périmètre inchangé : **observer, mesurer, hiérarchiser, questionner**. Les corrections relèvent
> de M7-B2.
>
> ⚠️ **Numérotation des questions** : chaque volet numérote les siennes de façon indépendante.
> Elles sont donc préfixées ici : **É** (éthique), **T** (technique), **R** (ressources).

---

## 5. Tableau d'indicateurs consolidé

Hiérarchisé : **🔴 bloquant** (à traiter avant toute évolution) → **🟠 sérieux** →
**🟡 à documenter**. Colonne « Source » = volet d'origine du chiffre.

| # | Indicateur | Mesure | Sév. | Conséquence pour MediVox | Source |
|---|---|---|---|---|---|
| **C1** | **Secret de production en clair dans Git** | `DB_PASSWORD = "medivox_prod_2024"`, `train.py` l.9, présent **depuis le commit initial** | 🔴 | **Priorité 0** : compromission présumée. Révocation du compte + purge d'historique ; tous les clones sont à considérer compromis | T1 |
| **C2** | **Exécution de code arbitraire par le modèle** | `joblib.load` d'un pickle **non signé**, déposé par `scp` sans checksum | 🔴 | Qui peut écrire le `.joblib` exécute du code sous l'identité du compte de prod, sans aucun signal | T2 |
| **C3** | **Données de santé exposées** | 10 000 dossiers versionnés en clair dans Git ; 4 valeurs de santé passées en **arguments de processus** (visibles via `ps`, historique shell, logs SSH) | 🔴 | Art. 9 RGPD + secret médical (L1110-4 CSP) ; diffusion incontrôlée par simple clonage | T3, T4 |
| **C4** | **Le biais est dans la donnée, pas dans l'algorithme** | À durée réelle identique (F 5,620 j vs M 5,585 j), **36,3 % des séjours longs de femmes ne sont pas codés** — 917 patientes | 🔴 | Cause racine. **Aucun changement de modèle ne la corrige** : c'est le processus d'étiquetage historique qui est en cause | É §2.3 |
| **C5** | **Le modèle amplifie ce biais ×2,24** | DI F/M : **0,653** (étiquette) → **0,291** (prédictions), repère 0,80. `sexe_bin` = feature active, **9,53 %** d'importance, sans justification clinique | 🔴 | Traitement différencié selon un **critère prohibé** (art. 225-1 CP) ; risque de discrimination caractérisé | É §2.4 |
| **C6** | **Erreurs massivement asymétriques par sexe** | **FNR femmes 73,7 %** vs hommes 24,2 % ; sous-calibration **−18,3 pts** ; **37,05 %** des séjours changent de décision si l'on inverse le seul `sexe_bin` | 🔴 | ≈ 1 860 patientes / 10 000 séjours privées de l'anticipation dont bénéficient les hommes à situation clinique identique | É §2.4, T10 |
| **C7** | **Zéro journalisation** | 0 log d'entraînement, 0 log d'inférence ; ni entrée, ni sortie, ni horodatage, ni version de modèle conservés | 🔴 | **Système inauditable** : aucune décision explicable ni rejouable, et **impossibilité de démontrer** être hors art. 22 (CJUE *SCHUFA*). Accountability (art. 5.2) non démontrable | T6, É §2.5 |
| **C8** | **Écart entre finalité affichée et traitement réel** | « Prédicteur DMS » (durée) = en réalité un **classifieur binaire de risque** → profilage de personnes physiques sur leur état de santé | 🔴 | Requalification complète : limitation des finalités (5.1.b), art. 22, AI Act | É §2.0 |
| **C9** | **AI Act : qualification indéterminée, présomption sérieuse de haut risque** | Bascule si triage urgences (Annexe III 5 d — **40,2 %** d'admissions urgentes), mission de service public (5 a) ou aide à décision clinique (MDR règle 11). Exception art. 6 § 3 **fermée** (profilage) | 🔴 | Obligations art. 8-15 (gestion des risques, qualité des données, documentation, journalisation, supervision humaine) — **aucune n'est satisfaite** | É §2.6 |
| **C10** | **Performance annoncée fausse** | **0,7721** (accuracy *train*, sans split) vs **0,6835** en CV 5 folds ; AUC 0,866 → **0,725** ; gain réel **+8,9 pts** sur la baseline | 🔴 | Si ce chiffre a validé la mise en production, la décision d'origine repose sur une mesure invalide | T9 |
| **C11** | **Artefact de production non reproductible et non versionné** | `random_state` fixé, mais **0,16 %** de désaccord (16 séjours/10 000) et hash différent ; `train.py` écrase toujours le même chemin | 🔴 | **On audite un modèle proche de la prod, pas la prod.** Impossible de savoir quel modèle a décidé quoi ; aucun rollback | T7, T8 |
| **C12** | **Zéro validation d'entrée, zéro test de qualité** | **6 valeurs médicalement impossibles sur 11 acceptées** avec code retour 0 (`age=500`, `imc=900`, `sexe_bin=7`…) ; **0 / 3** tests portent sur la qualité, couverture métier **0 %** | 🔴 | Décisions rendues sur des données aberrantes sans aucun signal ; **aucune évolution déployable avec un filet** | T5, T11 |
| **C13** | **7 points de rupture critiques sur 8** | Pour **25 lignes de code utile** : fichier unique, serveur unique, `cwd` de l'appelant, **la personne** qui tape la commande, environnement non reconstructible (0 manifeste, 0 conteneur), 0 runbook | 🔴 | RTO inconnu, reprise non documentée ; tout incident se résout par rétro-ingénierie | T12 |
| **C14** | **La complexité du modèle est injustifiable** | Une **régression logistique de 1,8 Ko** fait **mieux** : +1,2 pt d'accuracy, +1,6 pt d'AUC, **×2 722** plus petite, ×33 plus rapide à entraîner. `histgb` confirme le plafond (0,6832 vs 0,6835) | 🟠 | 99,96 % de l'artefact n'achète rien — sauf 8,9 pts de sur-apprentissage et un risque de **mémorisation de données de santé** (30 846 feuilles pour 10 000 patients) | R1, R6, T15 |
| **C15** | **Le levier n'est pas le modèle, ce sont les features jetées** | `service` (4,2 j → 7,2 j) et `type_admission` (+19 pts) **écartés** par `train.py` l.14 ; `imc` garde **30,2 %** d'importance pour une corrélation de **0,001** et **−0,5 pt** si retiré | 🟠 | Donnée de santé collectée pour un gain nul → **minimisation (art. 5.1.c)** ; plafond de performance auto-infligé | É §2.2, T14 |
| **C16** | **Architecture : 99,92 % du calcul est du gaspillage** | **1 890 ms** par prédiction dont **1,51 ms** utiles ; 0,53 pred/s vs 192 482/s en lot (**×363 886**) ; 148,6 Mo de RSS repayés à chaque appel, dont **95 % de runtime** | 🟠 | 5 h 15 pour ce qui prend 52 ms, aucune élasticité. **Alléger le modèle ne changerait rien** : le gisement est le mode d'exécution | T16, T17, R2, R7 |
| **C17** | **Le coût réel est humain, pas informatique** | Geste SSH ≈ **0,21 ETP ≈ 15 000 €/an = 96 %** du coût ; calcul : **0,02 €/an** ; serveur occupé **0,060 %** de l'année | 🟠 | Tout gain sur le modèle est un **placebo économique**. Le point de rupture n°1 est une personne | R3, R8 |
| **C18** | **Aucune documentation, aucune métadonnée** | 0 fonction, 0 classe, 0 docstring, 0 carte de modèle, 0 runbook, 0 date d'entraînement ; `class_weight=None` jamais tracé ; 3 commits, 0 tag | 🟠 | Toute modification est une réécriture ; la connaissance du système est orale | T13, T18, É §2.5 |
| **C19** | **Formalités RGPD non vérifiables** | Registre (art. 30), AIPD (art. 35 — **critères apparemment réunis**), base légale art. 9 § 2, durée de conservation, hébergement **HDS** : rien n'est documenté dans le repo | 🟠 | Exposition réglementaire non quantifiable tant que Marc n'a pas répondu | É §2.5 |
| **C20** | **Le prix de l'équité est mesuré, et il est faible** | Sans `sexe_bin` : **DI 1,001**, écart de FNR **49,2 → 2,1 pts**, pour **−1,2 pt** d'accuracy. Ré-entraîner coûte **337 ms** | 🟡 | *Point d'appui* : « on ne peut pas y toucher, c'est trop lourd » est **mesurément faux**. Arbitrage documenté disponible pour M7-B2 | R5, R11 |
| **C21** | **Empreinte carbone négligeable · aucun biais géographique** | **≈ 7 gCO₂e/an** (≈ 71 m en voiture) ; DI par département **0,906** | 🟡 | *Points positifs à assumer* : ne **pas** faire du modèle un argument écologique — ce serait du *greenwashing* | R12, É §2.4 |

---

## 6. Synthèse exécutive

> Lecture : **2 minutes**. Le plus grave d'abord.

### En une phrase

Le « prédicteur DMS » n'est pas un prédicteur de durée mais un **classifieur de risque appliqué à
des patients identifiés** ; il **discrimine selon le sexe**, il **n'enregistre rien**, et il repose
sur un **script de 25 lignes** dont le mot de passe de production est exposé depuis deux ans.

### Les trois constats qui commandent tout le reste

**1. Le système discrimine — et le biais vient de vos données, pas de l'algorithme.**
Les femmes restent **aussi longtemps à l'hôpital que les hommes** (5,620 j contre 5,585 j), mais
**un séjour long de femme sur trois n'a jamais été codé** comme prolongé dans l'historique
(917 patientes sur 10 000). Le modèle a appris cette erreur de codage **et l'a plus que doublée** :
il rate **73,7 %** des séjours longs de femmes contre 24,2 % chez les hommes. Pour **37 % des
séjours**, changer la seule case « sexe » inverse la décision. Changer de modèle ne corrige rien :
les trois alternatives testées reproduisent le même biais. **La cause est en amont, dans la règle
d'étiquetage.**

**2. Vous ne pouvez rien prouver, parce que rien n'est écrit.**
Aucune prédiction n'est journalisée : ni l'entrée, ni la sortie, ni la date, ni le modèle utilisé.
MediVox est donc **incapable de répondre** à « quelle décision a été rendue pour ce patient, sur
quelles valeurs ? » — et **incapable de démontrer** qu'un humain tranche réellement, donc de
prouver qu'elle échappe à l'article 22 du RGPD. S'y ajoute un écart de fond : le système est
**présenté** comme un outil de gestion de flux et **fonctionne** comme un profilage individuel de
l'état de santé. Toute la qualification juridique en découle.

**3. Trois failles de sécurité sont à traiter sans attendre la suite.**
Le mot de passe de production (`medivox_prod_2024`) est **en clair dans l'historique Git** depuis
le premier commit — le supprimer ne suffit pas, il faut **révoquer le compte**. Le fichier modèle
est chargé sans aucun contrôle d'intégrité : **quiconque peut l'écrire exécute du code** sur le
serveur. Enfin, les données de santé de 10 000 patients sont **versionnées en clair** et transitent
en arguments de ligne de commande, **lisibles par tout utilisateur du serveur**.

### Ce que l'audit dit aussi — et qui va à contre-courant

- **Le modèle ne coûte rien** : 7 gCO₂e/an, 0,02 € de calcul, **337 ms** pour le réentraîner.
  L'argument « c'est trop lourd pour y toucher » est **factuellement faux**.
- **Le vrai coût est humain** : le geste manuel en SSH représente **96 % de la dépense annuelle**,
  soit ≈ **0,21 ETP**. Optimiser le modèle serait un placebo économique.
- **La complexité ne sert à rien** : une régression logistique **2 722 fois plus petite** est
  **plus performante**. Le RandomForest ne convertit pas sa taille en qualité, mais en
  sur-apprentissage (8,9 points) et en mémorisation de données de santé.
- **La performance réelle n'est pas celle annoncée** : **68 %**, et non 77 % — le chiffre affiché
  est mesuré sur les données d'entraînement.
- **Deux points positifs** : aucun écart par département, et le coût d'une correction de l'équité
  est **mesuré et faible** (retirer le sexe ramène la parité quasi parfaite pour −1,2 point).

### Ce que l'audit ne tranche pas

La qualification **AI Act** reste **indéterminée**, avec une **présomption sérieuse de haut
risque** : elle dépend de **l'usage réel** du score, que le code ne révèle pas. L'exception
« tâche préparatoire » est en revanche **définitivement fermée** (il y a profilage). De même, le
sens du préjudice — qui est lésé : les non-signalés ou les sur-signalés ? — dépend de ce que le
score déclenche concrètement. **Cinq questions bloquent la totalité des qualifications.**

### Ce qui est à faire avant toute évolution

1. **Révoquer** le compte de base de données — action indépendante de tout le reste.
2. **Répondre** aux questions bloquantes du § 7.1, en particulier : *qui produit l'étiquette et
   selon quelle règle ?* et *que déclenche concrètement le score ?*
3. **Ne pas corriger le modèle avant** : tant que l'étiquette est fausse et l'usage inconnu, tout
   ré-entraînement reproduirait le même biais sous une forme plus difficile à détecter.

---

## 7. Questions ouvertes

### 7.1 Bloquantes — aucune qualification ni correction possible sans réponse

| # | Question | Destinataire | Débloque |
|---|---|---|---|
| **É-Q6** | **Qui produit l'étiquette `sejour_prolonge`, selon quelle règle écrite ?** Pourquoi est-elle déterministe pour les hommes (`dms ≥ 5,6`) et probabiliste pour les femmes (36,3 % de sous-codage) ? | Hélène + métier | **La cause racine du biais** (C4) |
| **É-Q3** | **Que déclenche concrètement le score ?** Planification de lit et coordination de sortie, ou arbitrage d'admission / pilotage T2A ? | Hélène | Sens du préjudice, AI Act, art. 22 (C5, C8, C9) |
| **É-Q4** | Quel est le **taux de désaccord** entre le score et la décision finale, et **où est-il tracé** ? | Hélène | Art. 22 condition 1 (*SCHUFA*) — aujourd'hui **indémontrable** (C7) |
| **É-Q2** | **Quand** le score est-il calculé — à l'arrivée aux urgences, ou après admission ? | Hélène | AI Act Annexe III 5 d) — triage (C9) |
| **É-Q1** | **Qui lit** la sortie de `predict.py`, et sous quelle forme ? | Hélène | Supervision humaine effective |
| **T-Q10** | Quel compte ouvre `medivox_prod_2024`, avec quels droits, et a-t-il été tourné depuis 2024 ? | Hélène + Marc | **Priorité 0**, indépendante du reste de l'audit (C1) |

### 7.2 Qualification juridique

| # | Question | Destinataire | Débloque |
|---|---|---|---|
| **É-Q12** | MediVox exerce-t-elle une **mission de service public hospitalier** (autorisation ARS / ESPIC) ? | Direction | AI Act Annexe III 5 a) |
| **É-Q11** | MediVox est-elle **fournisseur**, **déployeur**, ou les deux au sens de l'AI Act ? | Direction | Répartition des obligations |
| **É-Q7** | Quelle **base légale art. 9 § 2** a été retenue et documentée ? | Marc | Licéité du traitement |
| **É-Q5** | Les patients sont-ils **informés** de ce traitement et de sa logique ? | Marc | Art. 12-15 |
| **É-Q9** | Le traitement figure-t-il au **registre** (art. 30) ? Une **AIPD** (art. 35) a-t-elle été menée ? | Marc | Accountability (C19) |
| **É-Q8** | Quelle **durée de conservation** pour `dms_dataset.csv` et pour les prédictions produites ? | Marc | Art. 5.1.e |
| **É-Q10** | Où sont **hébergés** les données et le modèle ? L'hébergeur est-il **certifié HDS** ? | Hélène + Marc | L1111-8 CSP |
| **É-Q13** | Le dataset constitue-t-il un **entrepôt de données de santé** au sens du référentiel CNIL ? | Marc | Cadre de réutilisation |

### 7.3 Justification des variables

| # | Question | Destinataire | Débloque |
|---|---|---|---|
| **É-Q14** | Quelle **justification clinique documentée** pour l'usage du **sexe** comme variable d'entrée ? | Hélène + médical | Minimisation + non-discrimination (C5). **À défaut : aggravant caractérisé** |
| **É-Q15** | Quelle justification pour l'**`imc`**, dont la corrélation à la durée réelle est de **0,001** et qui ne coûte que **−0,5 pt** s'il est retiré ? | Hélène + médical | Minimisation, art. 5.1.c (C15) |

### 7.4 Technique et exploitation

| # | Question | Destinataire | Débloque |
|---|---|---|---|
| **T-Q8** | `sha256sum` de l'artefact **en production** vs celui du repo ? | Hélène | Détermine si cet audit porte sur le bon modèle (C11) |
| **T-Q13** | Qui a **accès en écriture** au chemin du `.joblib` sur le serveur ? | Hélène | Dimensionne le risque d'exécution de code arbitraire (C2) |
| **T-Q7** | Qui **construit la ligne de commande SSH**, depuis quelle source (DPI, export, saisie) ? | Hélène | Garantie de l'ordre des 4 arguments |
| **T-Q11** | Montrez la ligne exacte qui **assemble et lance** la commande SSH | Hélène | Seul vecteur d'injection possible, hors repo |
| **T-Q14** | Le serveur est-il **sauvegardé** ? Quel RTO/RPO est attendu ? | Hélène | Points de rupture n°1 et n°2, aujourd'hui **inconnus** (C13) |
| **T-Q15** | Le chiffre **« 0,77 »** a-t-il servi à **valider la mise en production** ? | Hélène | Si oui, la décision d'origine repose sur une mesure invalide (C10) |
| **T-Q9** | Une documentation de sélection / d'entraînement existe-t-elle **hors du repo** ? | Hélène | Sinon `RandomForest(60, 10)` est un choix non justifiable (C18) |

### 7.5 Ressources et organisation

| # | Question | Destinataire | Débloque |
|---|---|---|---|
| **R-Q16** | **Combien de prédictions par an**, selon quel profil horaire ? | Hélène + direction des soins | Conditionne **99 %** du chiffrage de coût (C17) |
| **R-Q17** | **Combien de temps prend le geste complet** (connexion, saisie, lecture, report) ? | Hélène + exécutants | Poste de coût **n°1** (96 %) — estimé à 2 min, jamais chronométré |
| **R-Q21** | **Combien de personnes** exécutent ce geste, et **qui prend le relais** en congés / départ ? | Hélène + RH | Chiffre le point de rupture « humain » en jours d'indisponibilité |
| **R-Q20** | Les prédictions **pourraient-elles être faites par lot quotidien** ? | Hélène + direction des soins | Diviserait le CPU par **9 733** et supprimerait l'essentiel du coût, **sans toucher au modèle** |
| **R-Q19** | Existe-t-il une **exigence de délai métier** (SLA) ? | Direction des soins | Détermine si les 1 890 ms sont 🔴 ou 🟡 |
| **R-Q22** | Le modèle a-t-il été **ré-entraîné depuis 2 ans** ? Si non, pourquoi ? | Hélène | Le `fit` coûte **337 ms** : la croyance « c'est trop lourd » est mesurément fausse (C20) |
| **R-Q18** | Le serveur est-il **dédié** à ce script ou mutualisé ? | Hélène | Seul poste informatique non négligeable (≈ 600 €/an, **0,060 %** d'occupation) |
| **R-Q24** | Quel **budget annuel** est attribué à ce système, et sur quelle ligne ? | Direction | L'audit mesure ≈ 15 600 €/an dont **0,02 €** d'informatique |
| **R-Q23** | MediVox a-t-il un **engagement RSE / reporting CSRD** auquel ce système devrait contribuer ? | Direction + Hélène | Détermine s'il faut documenter les 7 gCO₂e ou simplement les classer |

---

## 8. Limites de l'audit

Ce que l'audit **n'a pas pu vérifier** :

- le **serveur de production** (OS, versions, droits, sauvegardes, réseau) — non accessible ;
- l'**appelant** de `predict.py` (DPI, ordonnanceur, système amont) — hors repo ;
- la **chaîne de déploiement `scp`** réelle et les **journaux système** (SSH, syslog) ;
- toute **documentation hors repo** (wiki, tickets, mails) ;
- le **volume annuel réel** et le **temps humain réel** — aucun log n'existe, donc **rien n'est
  reconstituable a posteriori** ;
- la **consommation réelle** sur le serveur de production : les valeurs absolues du volet ressources
  proviennent d'un poste d'audit Windows ; seuls les **rapports** (×2 722, ×363 886, 96 %) sont
  robustes.

> Deux conséquences. D'une part, les conclusions portent sur **l'artefact livré**, présumé
> représentatif de la production **à ±0,16 % près** — présomption à confirmer par **T-Q8**.
> D'autre part, ces incertitudes sont **majorantes** : chaque élément non vérifié ne peut
> qu'ajouter du risque, jamais en retirer.
>
> 📌 Ce volet **consolide et hiérarchise**. Les corrections (ré-étiquetage, retrait de `sexe`,
> ajout de `service` / `type_admission`, mise en service, journalisation, conteneurisation)
> relèvent de **M7-B2** et ne sont **pas** proposées ici.
