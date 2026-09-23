# Rapport d'audit — prédicteur de séjour prolongé v1 (MediVox Cliniques)

**Destinataires** : 👩‍💻 **Hélène**, directrice technique · ⚖️ **Marc**, délégué à la protection des données
**Objet audité** : le système désigné en interne « prédicteur DMS », version 1
**Nature du mandat** : observer, mesurer, hiérarchiser, questionner — **pas corriger**

> Les sections sont marquées 👩‍💻 (lecture technique) et ⚖️ (lecture DPO). Le § 1 et le § 6
> s'adressent aux deux. Chaque constat porte une référence **C1 à C17** qui renvoie au tableau
> consolidé du § 6, lui-même adossé aux mesures détaillées des volets d'audit.
---

## 1. Synthèse exécutive

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
d'étiquetage.** *(C3, C4)*

**2. Vous ne pouvez rien prouver, parce que rien n'est écrit.**
Aucune prédiction n'est journalisée : ni l'entrée, ni la sortie, ni la date, ni le modèle utilisé.
MediVox est donc **incapable de répondre** à « quelle décision a été rendue pour ce patient, sur
quelles valeurs ? » — et **incapable de démontrer** qu'un humain tranche réellement, donc de
prouver qu'elle échappe à l'article 22 du RGPD. S'y ajoute un écart de fond : le système est
**présenté** comme un outil de gestion de flux et **fonctionne** comme un profilage individuel de
l'état de santé. Toute la qualification juridique en découle. *(C5, C6)*

**3. Trois failles de sécurité sont à traiter sans attendre la suite.**
Le mot de passe de production (`medivox_prod_2024`) est **en clair dans l'historique Git** depuis
le premier commit — le supprimer ne suffit pas, il faut **révoquer le compte**. Le fichier modèle
est chargé sans aucun contrôle d'intégrité : **quiconque peut l'écrire exécute du code** sur le
serveur. Enfin, les données de santé de 10 000 patients sont **versionnées en clair** et transitent
en arguments de ligne de commande, **lisibles par tout utilisateur du serveur**. *(C1, C2)*

### Ce que l'audit dit aussi — et qui va à contre-courant

- **Le modèle ne coûte rien** : 7 gCO₂e/an, 0,02 € de calcul, **337 ms** pour le réentraîner.
  L'argument « c'est trop lourd pour y toucher » est **factuellement faux**.
- **Le vrai coût est humain** : le geste manuel en SSH représente **96 % de la dépense annuelle**,
  soit ≈ **0,21 ETP**. Optimiser le modèle serait un placebo économique. *(C14)*
- **Ce n'est pas le bon modèle** : une régression logistique **2 722 fois plus petite** est
  **plus performante**. Le RandomForest est surdimensionné pour l'usage — il ne convertit pas sa
  taille en qualité, mais en sur-apprentissage (8,9 points) et en mémorisation de données de
  santé. *(C17)*
- **La performance réelle n'est pas celle annoncée** : **68 %**, et non 77 %. Plus grave que
  l'écart : **le modèle n'a jamais été validé** — il est entraîné sur 100 % des données et évalué
  sur ces mêmes données, donc jamais confronté à un cas qu'il n'avait pas vu. *(C8)*
- **Deux points positifs** : aucun écart par département, et le coût d'une correction de l'équité
  est **mesuré et faible** (retirer le sexe ramène la parité quasi parfaite pour −1,2 point).

### Ce que l'audit ne tranche pas

La qualification **AI Act** reste **indéterminée**, avec une **présomption sérieuse de haut
risque** : elle dépend de **l'usage réel** du score, que le code ne révèle pas. L'exception
« tâche préparatoire » est en revanche **définitivement fermée** (il y a profilage). De même, le
sens du préjudice — qui est lésé : les non-signalés ou les sur-signalés ? — dépend de ce que le
score déclenche concrètement. **Cinq questions bloquent la totalité des qualifications.** *(C7)*

### Ce qui est à faire avant toute évolution

> Sur 17 constats, **6 sont bloquants** : l'accès de production et les données de santé (C1-C2),
> la discrimination (C3-C4), l'absence de journalisation (C5) et l'écart de finalité (C6).
> Cinq autres sont **conditionnels** : ils basculent en bloquant selon vos réponses aux questions
> du § 7.

1. **Révoquer** le compte de base de données — action indépendante de tout le reste.
2. **Répondre** aux questions bloquantes du § 7.1, en particulier : *qui produit l'étiquette et
   selon quelle règle ?* et *que déclenche concrètement le score ?*
3. **Ne pas corriger le modèle avant** : tant que l'étiquette est fausse et l'usage inconnu, tout
   ré-entraînement reproduirait le même biais sous une forme plus difficile à détecter.

---

## 2. Contexte et périmètre

### Ce que l'audit a couvert

Le système audité est composé de deux scripts (**25 lignes de code utile**), d'un artefact modèle
et d'un jeu de données de **10 000 séjours**. Trois volets d'analyse ont été conduits — **éthique**,
**technique**, **ressources** — et consolidés ici. Toutes les valeurs citées sont **mesurées** et
reproductibles à partir du notebook d'audit.

### Ce que l'audit **n'a pas** couvert

- le **serveur de production** (OS, versions, droits, sauvegardes, réseau) — non accessible ;
- l'**appelant** de `predict.py` (DPI, ordonnanceur, système amont) — hors du dépôt ;
- la **chaîne de déploiement `scp`** réelle et les **journaux système** (SSH, syslog) ;
- toute **documentation hors dépôt** (wiki, tickets, mails) ;
- le **volume annuel réel** et le **temps humain réel** — aucun log n'existe, donc **rien n'est
  reconstituable a posteriori** ;
- la **consommation réelle** sur le serveur de production : les valeurs absolues du volet
  ressources proviennent d'un poste d'audit Windows ; seuls les **rapports** (×2 722, ×363 886,
  96 %) sont robustes.

> **Deux conséquences à retenir.** D'une part, les conclusions portent sur **l'artefact livré**,
> présumé représentatif de la production **à ±0,16 % près** — présomption à confirmer par la
> question **T-Q8**. D'autre part, ces incertitudes sont **majorantes** : chaque élément non
> vérifié ne peut qu'ajouter du risque, jamais en retirer.

### Ce qui reste hors mandat

Les corrections — ré-étiquetage, retrait du sexe, ajout de `service` / `type_admission`, mise en
service, journalisation, conteneurisation — relèvent de la phase suivante et **ne sont pas
proposées ici**.

---

## 3. Volet éthique ⚖️

### 3.1 Le traitement n'est pas celui qui est annoncé

Le système est présenté comme un « prédicteur DMS », donc un outil de **durée**. Il s'agit en
réalité d'un **classifieur binaire de risque**, appliqué patient par patient : un **profilage de
personnes physiques portant sur leur état de santé**. Cet écart entre la finalité affichée et le
traitement réel emporte des conséquences sur la **limitation des finalités** (art. 5.1.b), sur
l'**article 22** et sur la qualification AI Act. *(C6)*

### 3.2 Une discrimination mesurée, dont la cause est en amont du modèle

| Constat | Mesure |
|---|---|
| Durée réellement observée | F **5,620 j** vs M **5,585 j** — écart non significatif |
| Sous-codage historique des séjours longs de femmes | **36,3 %**, soit **917 patientes** sur 10 000 |
| Disparate impact F/M sur l'étiquette | **0,653** (repère conventionnel : 0,80) |
| Disparate impact F/M sur les prédictions | **0,291** — **amplification ×2,24** |
| Taux de séjours longs non détectés (FNR) | **73,7 %** chez les femmes vs **24,2 %** chez les hommes |
| Sous-calibration du groupe féminin | **−18,3 points** |
| Séjours dont la décision s'inverse si l'on change le seul sexe | **37,05 %** |
| Écart par département | **DI 0,906** — aucun biais géographique |

Le sexe est une **feature active** du modèle (**9,53 %** de l'importance), **sans justification
clinique documentée**. Le traitement est donc différencié selon un **critère prohibé** (art. 225-1
du code pénal). *(C3, C4)*

> ⚠️ Point déterminant pour la suite : **le biais n'est pas un défaut de modèle**. Les trois
> alternatives testées le reproduisent à l'identique. Il provient de la **règle d'étiquetage
> historique** — déterministe pour les hommes, probabiliste pour les femmes. Aucun
> ré-entraînement ne le corrigera tant que cette règle n'aura pas été explicitée (**É-Q6**).

### 3.3 Minimisation : des données de santé traitées pour un gain nul

L'IMC pèse **30,2 %** de l'importance du modèle pour une corrélation de **0,001** avec la durée
réelle, et son retrait ne coûte que **−0,5 point**. À l'inverse, les deux variables réellement
prédictives — `service` (4,2 j → 7,2 j) et `type_admission` (+19 points) — sont **écartées** du
modèle. Une donnée de santé sensible est donc collectée, stockée et transmise pour un bénéfice
nul : c'est une atteinte directe au principe de **minimisation** (art. 5.1.c). *(C12)*

### 3.4 Article 22 : l'impossibilité de démontrer la conformité

Le système produit un **verdict binaire** par patient, sans journalisation d'aucune sorte.
Conséquence : MediVox ne peut **pas prouver** qu'un arbitrage humain existe, ni produire un taux
de désaccord entre le score et la décision finale. Au regard de la jurisprudence **CJUE
*SCHUFA***, l'applicabilité de l'article 22 est **probable mais non fermée** — et, surtout,
**indémontrable en l'état**. L'*accountability* (art. 5.2) n'est pas davantage démontrable. *(C5)*

### 3.5 AI Act : qualification indéterminée, présomption sérieuse de haut risque

La qualification bascule en **haut risque** si l'une de ces conditions est vérifiée :

- le score est calculé **à l'arrivée aux urgences** et influence le triage — Annexe III 5 d)
  (rappel : **40,2 %** des admissions du jeu de données sont des urgences) ;
- MediVox exerce une **mission de service public hospitalier** — Annexe III 5 a) ;
- le score **informe une décision clinique** — logiciel dispositif médical, règle 11.

L'exception de l'**art. 6 § 3** (tâche préparatoire) est **définitivement fermée**, puisqu'il y a
profilage. Si la bascule est confirmée, les obligations des **articles 8 à 15** s'appliquent —
gestion des risques, qualité des données et examen des biais, documentation technique,
journalisation, supervision humaine, robustesse : **aucune n'est satisfaite aujourd'hui**. *(C7)*

### 3.6 Formalités RGPD : non vérifiables depuis le dépôt

Registre (art. 30), **AIPD** (art. 35 — les critères d'obligation semblent réunis), **base légale
art. 9 § 2**, durée de conservation, **certification HDS** de l'hébergeur : aucun de ces éléments
n'est documenté dans le périmètre audité. L'exposition réglementaire **n'est donc pas
quantifiable** tant que ces points ne sont pas confirmés. *(C15, § 7.2)*

---

## 4. Volet technique 👩‍💻

### 4.1 Sécurité — trois points à traiter sans attendre

| Constat | Mesure | Conséquence |
|---|---|---|
| **Secret de production en clair dans Git** | `DB_PASSWORD = "medivox_prod_2024"`, présent **depuis le commit initial** | **Priorité 0** : révocation du compte **puis** purge d'historique. Tous les clones sont à considérer compromis *(C1)* |
| **Modèle chargé sans contrôle d'intégrité** | pickle **non signé**, déposé par `scp` sans checksum | Qui peut écrire le fichier modèle **exécute du code** sous l'identité du compte de production, sans aucun signal *(C1)* |
| **Données de santé exposées** | 10 000 dossiers versionnés en clair ; 4 valeurs de santé passées en **arguments de processus** | Lisibles via `ps`, l'historique shell et les logs SSH par **tout utilisateur du serveur**. Art. 9 RGPD + secret médical *(C2)* |

> Les deux premiers sont regroupés sous un même item **C1** : ce sont deux chemins d'accès au
> **même compte de production**, à traiter ensemble.

### 4.2 Fiabilité — ce que le système ne garantit pas

- **Aucune validation d'entrée** : **6 valeurs médicalement impossibles sur 11 testées** sont
  acceptées avec un code retour 0 (`age=500`, `imc=900`, `sexe_bin=7`…). Rien ne distingue, pour
  l'appelant, une prédiction valide d'une prédiction aberrante. *(C10)*
- **Aucun test de qualité** : **0 des 3 tests** existants porte sur le modèle ; couverture métier
  **0 %**. Aucune évolution ne peut être déployée avec un filet. *(C16)*
- **Le modèle n'a jamais été validé** : il n'existe **aucune séparation entre données
  d'entraînement et données de test**. L'entraînement porte sur 100 % du jeu de données, et la
  performance est mesurée sur ces mêmes données — un modèle qui récite ce qu'il a appris obtient
  ainsi une bonne note sans rien prouver. C'est l'origine du **0,7721** affiché : en validation
  croisée, la performance réelle tombe à **0,6835**, et l'AUC de 0,866 à **0,725**. Si ce chiffre
  a servi à valider la mise en production, la décision d'origine repose sur une mesure invalide.
  *(C8)*

### 4.3 Traçabilité — le système est inauditable

Ni l'entraînement ni l'inférence ne produisent de journal : aucune entrée, aucune sortie, aucun
horodatage, aucune version de modèle conservés. Aucune décision n'est **explicable** ni
**rejouable**. C'est le constat technique qui bloque le volet juridique (§ 3.4). *(C5)*

S'y ajoute une **absence de versionnage** : le script d'entraînement écrit toujours au même
chemin, donc écrase l'artefact précédent. Il est impossible de savoir **quel modèle a rendu quelle
décision**, et aucun retour arrière n'est possible. *(C9)*

### 4.4 Reproductibilité — l'artefact de production n'est pas celui du dépôt

Bien que la graine aléatoire soit fixée, l'artefact livré et un ré-entraînement local divergent sur
**0,16 % des prédictions** (16 séjours sur 10 000) et n'ont pas le même hash. **L'audit porte donc
sur un modèle proche de la production, pas sur la production elle-même** — présomption à lever par
un simple `sha256sum` côté serveur (**T-Q8**). *(C9)*

### 4.5 Architecture et continuité de service

- **7 points de rupture critiques sur 8**, pour 25 lignes de code, à commencer par le
  **déploiement mono-machine** : un seul serveur, un seul exemplaire du fichier modèle sur son
  disque local, déposé par `scp`. **Si cette machine tombe, le service, l'artefact et son
  environnement disparaissent ensemble.** S'y ajoutent la dépendance au répertoire courant de
  l'appelant, **à la personne** qui tape la commande, un environnement non reconstructible (aucun
  manifeste de dépendances, aucun conteneur) et aucun runbook. **RTO inconnu**, reprise non
  documentée. *(C11)*
- **Aucune documentation, aucune métadonnée** : 0 fonction, 0 classe, 0 carte de modèle, 0 date
  d'entraînement, 3 commits, 0 tag. La connaissance du système est **orale** ; toute modification
  est une réécriture. *(C9)*
- **99,92 % du temps d'exécution est du gaspillage** : **1 890 ms** par prédiction dont **1,51 ms**
  de calcul utile ; 0,53 prédiction/s en production contre 192 482/s en lot (**×363 886**). Chaque
  appel repaie **148,6 Mo** de mémoire, dont **95 % de runtime** — le modèle étant **rechargé en
  synchrone à chaque prédiction**. Point important : **alléger le modèle ne changerait
  rien** — le gisement est le mode d'exécution. *(C13)*

---

## 5. Volet ressources

### 5.1 Ce n'est pas le bon modèle

Une **régression logistique de 1,8 Ko**, entraînée sur les mêmes données et les mêmes variables,
obtient **+1,2 point d'accuracy** et **+1,6 point d'AUC** que le modèle en place — pour un artefact
**2 722 fois plus petit** et un entraînement **33 fois plus rapide**. Un modèle de *boosting*
moderne confirme le plafond (0,6832 contre 0,6835). **99,96 % de l'artefact actuel n'achète rien**,
sauf 8,9 points de sur-apprentissage et un risque de **mémorisation de données de santé**
(30 846 feuilles pour 10 000 patients). *(C17)*

> Corollaire pour la suite : le levier de performance n'est pas le modèle, ce sont les **variables
> écartées** (§ 3.3). *(C12)*

### 5.2 Le coût réel est humain, pas informatique

| Poste | Valeur | Part |
|---|---|---|
| Geste manuel en SSH | ≈ **0,21 ETP** ≈ **15 000 €/an** | **96 %** |
| Calcul | **0,02 €/an** | ≈ 0 |
| Taux d'occupation du serveur | **0,060 %** de l'année | — |

Toute optimisation portant sur le modèle serait un **placebo économique**. Le point de rupture
n°1 du système est **une personne**. *(C14)*

### 5.3 Sobriété — ce que l'audit autorise à dire, et ce qu'il interdit

- **À ne pas dire** : que le modèle consomme trop. Son empreinte est de **≈ 7 gCO₂e/an**,
  soit l'équivalent de **71 mètres en voiture** — un chiffre négligeable, qu'il serait malhonnête
  de présenter autrement.
- **À dire** : que la complexité crée un **risque** (sur-apprentissage, mémorisation de données de
  santé), pas de la valeur ; et que l'architecture gaspille **99,92 %** du calcul. *(C17, C13)*

### 5.4 Deux points d'appui pour la suite

- **Réentraîner le modèle coûte 337 ms.** L'argument « on ne peut pas y toucher, c'est trop
  lourd » est **mesurément faux** : l'obstacle est organisationnel, pas calculatoire.
- **Le prix de l'équité est mesuré, et il est faible.** Retirer le sexe des variables d'entrée
  ramène le disparate impact à **1,001** et réduit l'écart de FNR entre femmes et hommes de
  **49,2 à 2,1 points**, pour **−1,2 point d'accuracy**.

---

## 6. Tableau consolidé des risques

**Critère de sévérité**, appliqué uniformément — pour que le rouge garde sa valeur :

| Niveau | Critère retenu | Ce qu'il implique |
|---|---|---|
| 🔴 **Bloquant** | préjudice **avéré et en cours**, ou **impossibilité démontrée** de justifier la conformité | à traiter **avant toute évolution** — **6 lignes** |
| 🟠 **Sérieux** | risque réel mais **conditionnel, différé, ou sans préjudice individuel constaté** | à traiter **dans** la phase de correction — **9 lignes**, dont 5 portent une **condition de bascule en 🔴** |
| 🟡 **Mineur** | défaut de conception ou de méthode, sans risque immédiat ; à reprendre dans la phase suivante | **2 lignes** |

> Les cinq lignes **conditionnelles** dépendent d'une réponse de votre part : leur sévérité sera
> arrêtée définitivement une fois les questions du § 7 traitées.

| # | Indicateur | Mesure | Sév. | Conséquence pour MediVox |
|---|---|---|---|---|
| **C1** | **Accès de production compromis : identifiant exposé et code exécuté sans contrôle** | (a) `DB_PASSWORD = "medivox_prod_2024"` en clair, **depuis le commit initial** ; (b) modèle chargé depuis un fichier **non signé**, déposé par `scp` sans checksum | 🔴 | **Priorité 0** — deux chemins d'accès au compte de production. Le secret est à **révoquer** (supprimer le fichier ne suffit pas ; tous les clones sont à considérer compromis), et quiconque peut écrire le fichier modèle **exécute du code** sous l'identité de production, sans aucun signal |
| **C2** | **Données de santé exposées** | 10 000 dossiers versionnés en clair ; 4 valeurs de santé en **arguments de processus** (`ps`, historique shell, logs SSH) | 🔴 | Art. 9 RGPD + secret médical (L1110-4 CSP) ; diffusion incontrôlée par simple clonage |
| **C3** | **Le biais est dans la donnée, pas dans l'algorithme** | À durée réelle identique (F 5,620 j vs M 5,585 j), **36,3 % des séjours longs de femmes ne sont pas codés** — 917 patientes | 🔴 | Cause racine. **Aucun changement de modèle ne la corrige** : c'est le processus d'étiquetage historique qui est en cause |
| **C4** | **Le modèle amplifie ce biais ×2,24 et le rend massivement asymétrique** | DI F/M : **0,653** (étiquette) → **0,291** (prédictions), repère 0,80 ; sexe = variable active à **9,53 %** d'importance, sans justification clinique. Conséquences mesurées : **FNR femmes 73,7 %** vs hommes 24,2 %, sous-calibration **−18,3 pts**, **37,05 %** des séjours changent de décision si l'on inverse le seul sexe | 🔴 | Traitement différencié selon un **critère prohibé** (art. 225-1 CP). Concrètement : ≈ **1 860 patientes / 10 000 séjours** privées de l'anticipation dont bénéficient les hommes à situation clinique identique |
| **C5** | **Zéro journalisation** | 0 log d'entraînement, 0 log d'inférence ; ni entrée, ni sortie, ni horodatage, ni version de modèle conservés | 🔴 | **Système inauditable** : aucune décision explicable ni rejouable, et **impossibilité de démontrer** être hors art. 22 (CJUE *SCHUFA*). Accountability (art. 5.2) non démontrable |
| **C6** | **Écart entre finalité affichée et traitement réel** | « Prédicteur DMS » (durée) = en réalité un **classifieur binaire de risque** → profilage de personnes physiques sur leur état de santé | 🔴 | Requalification complète : limitation des finalités (5.1.b), art. 22, AI Act |
| **C7** | **AI Act : qualification indéterminée, présomption sérieuse de haut risque** | Bascule si triage urgences (Annexe III 5 d — **40,2 %** d'admissions urgentes), mission de service public (5 a) ou aide à décision clinique (règle 11). Exception art. 6 § 3 **fermée** (profilage) | 🟠 | Obligations art. 8-15 (gestion des risques, qualité des données, documentation, journalisation, supervision humaine) — **aucune n'est satisfaite**. ⚠️ **Bascule en 🔴** dès qu'**É-Q2**, **É-Q3** ou **É-Q12** confirme l'un des trois cas |
| **C8** | **Le modèle n'a jamais été validé** | **Aucun split train/test** : l'entraînement porte sur **100 % des données** et l'accuracy est mesurée sur ces mêmes données. **0,7721** annoncé vs **0,6835** en validation croisée ; AUC 0,866 → **0,725** ; gain réel **+8,9 pts** sur la baseline | 🟠 | Le modèle est en production depuis 2 ans **sans avoir jamais été évalué sur des données qu'il n'avait pas vues** ; le seul chiffre de performance que MediVox possède est **faux d'environ 9 points**. ⚠️ **Bascule en 🔴** si **T-Q15** confirme que ce chiffre a servi à **valider la mise en production** |
| **C9** | **Aucune traçabilité du modèle : ni version, ni métadonnée, ni documentation** | L'entraînement écrit **toujours au même chemin** (3 commits, 0 tag) ; 0 date d'entraînement, 0 carte de modèle, 0 runbook, 0 fonction, 0 classe ; et malgré une graine fixée, **0,16 %** de désaccord (16 séjours/10 000) et un hash différent entre l'artefact livré et un ré-entraînement | 🟠 | Impossible de savoir **quel modèle a décidé quoi**, ni de revenir en arrière ; la connaissance du système est **orale** et toute modification est une réécriture. ⚠️ **Bascule en 🔴** si **T-Q8** révèle un artefact de production **réellement différent** |
| **C10** | **Zéro validation d'entrée** | **6 valeurs médicalement impossibles sur 11 acceptées** avec code retour 0 (`age=500`, `imc=900`…), alors que le domaine d'entraînement est **connu et borné** | 🟠 | Rien ne distingue, pour l'appelant, une prédiction valide d'une prédiction rendue sur un âge de 500 ans. Risque **conditionné à la source des 4 arguments**, inconnue de l'audit. ⚠️ **Bascule en 🔴** si **T-Q7** révèle une **saisie humaine** des arguments |
| **C11** | **Déploiement mono-machine : un seul serveur, aucun réplica** | 1 machine, déploiement manuel par `scp` ; **un seul exemplaire** du fichier modèle sur son disque local, sans checksum ; 7 autres points de rupture recensés (répertoire courant de l'appelant, la personne qui tape la commande, environnement non reconstructible, 0 runbook) | 🟠 | **Si la machine tombe, tout est perdu d'un coup** : le service, l'artefact et l'environnement qui le fait tourner. La seule copie restante est celle du dépôt — qui **diffère de la production** (cf. C9). RTO inconnu, aucune procédure de reprise. ⚠️ **Bascule en 🔴** si **T-Q14** confirme l'absence de sauvegarde, ou **R-Q19** un délai métier contraignant |
| **C12** | **Le levier n'est pas le modèle, ce sont les variables écartées** | `service` (4,2 j → 7,2 j) et `type_admission` (+19 pts) **écartés** ; l'IMC garde **30,2 %** d'importance pour une corrélation de **0,001** et **−0,5 pt** si retiré | 🟠 | Donnée de santé collectée pour un gain nul → **minimisation (art. 5.1.c)** ; plafond de performance auto-infligé |
| **C13** | **Architecture : 99,92 % du calcul est du gaspillage, et le modèle est rechargé à chaque appel** | **1 890 ms** par prédiction dont **1,51 ms** utiles ; 0,53 pred/s vs 192 482/s en lot (**×363 886**) ; à chaque appel, **918 ms** de rechargement synchrone du modèle (dont 903 ms d'import de bibliothèque) et **148,6 Mo** de mémoire repayés, dont **95 % de runtime** ; aucun cache, aucun processus résident | 🟠 | Aucune élasticité, toute montée en charge impossible. **Alléger le modèle ne changerait rien** : le gisement est le mode d'exécution |
| **C14** | **Le coût réel est humain, pas informatique** | Geste SSH ≈ **0,21 ETP ≈ 15 000 €/an = 96 %** du coût ; calcul : **0,02 €/an** ; serveur occupé **0,060 %** de l'année | 🟠 | Tout gain sur le modèle est un **placebo économique**. Le point de rupture n°1 est une personne |
| **C15** | **Formalités RGPD non vérifiables** | Registre (art. 30), **AIPD** (art. 35 — critères apparemment réunis), base légale art. 9 § 2, durée de conservation, **HDS** : rien n'est documenté dans le périmètre audité | 🟠 | Exposition réglementaire non quantifiable tant que ces points ne sont pas confirmés |
| **C16** | **Aucun test du modèle** | **3 tests** au total, **0** portant sur la qualité, les valeurs limites, la non-régression ou l'équité ; couverture métier **0 %** ; **1 seule assertion non tautologique** sur 3 | 🟡 | Trois tests au vert donnent l'**illusion d'un système testé**. Aucune évolution — seuil, variables, rééquilibrage — ne peut être déployée avec un filet : un ré-entraînement qui ferait chuter l'AUC de 0,72 à 0,55 **passerait les 3 tests** |
| **C17** | **Ce n'est pas le bon modèle : un RandomForest surdimensionné pour l'usage** | Une **régression logistique de 1,8 Ko** fait **mieux** : +1,2 pt d'accuracy, +1,6 pt d'AUC, **×2 722** plus petite, ×33 plus rapide à entraîner. Un *boosting* moderne confirme le plafond (0,6832 vs 0,6835) | 🟡 | 30 846 feuilles pour 10 000 patients (3,08 par patient) : le modèle **n'apprend pas une règle, il mémorise des individus** — d'où les 8,9 pts de sur-apprentissage, et un risque de **mémorisation de données de santé** dans un fichier déplacé par `scp`. La complexité ne crée pas de valeur, seulement du risque |

> **Hors tableau — deux résultats qui ne sont pas des risques**, mais qu'il serait malhonnête
> d'omettre :
>
> - **Le prix de l'équité est mesuré, et il est faible.** Sans le sexe : **DI 1,001**, écart de
>   FNR **49,2 → 2,1 pts**, pour **−1,2 pt** d'accuracy — et ré-entraîner coûte **337 ms**.
>   *Point d'appui* : « on ne peut pas y toucher, c'est trop lourd » est **mesurément faux**.
> - **Empreinte carbone négligeable · aucun biais géographique** : **≈ 7 gCO₂e/an** (≈ 71 m en
>   voiture) ; écart par département **0,906**. *Points positifs à assumer* : ne **pas** faire du
>   modèle un argument écologique.

---

## 7. Questions ouvertes pour le client

### 7.1 Bloquantes — aucune qualification ni correction possible sans réponse

| # | Question | Destinataire | Débloque |
|---|---|---|---|
| **É-Q6** | **Qui produit l'étiquette « séjour prolongé », selon quelle règle écrite ?** Pourquoi est-elle déterministe pour les hommes (durée ≥ 5,6 j) et probabiliste pour les femmes (36,3 % de sous-codage) ? | 👩‍💻 Hélène + métier | **La cause racine du biais** (C3) |
| **É-Q3** | **Que déclenche concrètement le score ?** Planification de lit et coordination de sortie, ou arbitrage d'admission / pilotage T2A ? | 👩‍💻 Hélène | Sens du préjudice, AI Act, art. 22 (C4, C6, C7) |
| **É-Q4** | Quel est le **taux de désaccord** entre le score et la décision finale, et **où est-il tracé** ? | 👩‍💻 Hélène | Art. 22, première condition (*SCHUFA*) — aujourd'hui **indémontrable** (C5) |
| **É-Q2** | **Quand** le score est-il calculé — à l'arrivée aux urgences, ou après admission ? | 👩‍💻 Hélène | AI Act Annexe III 5 d) — triage (C7) |
| **É-Q1** | **Qui lit** la sortie du script de prédiction, et sous quelle forme ? | 👩‍💻 Hélène | Supervision humaine effective |
| **T-Q10** | Quel compte ouvre `medivox_prod_2024`, avec quels droits, et a-t-il été tourné depuis 2024 ? | 👩‍💻 Hélène + ⚖️ Marc | **Priorité 0**, indépendante du reste de l'audit (C1) |

### 7.2 Qualification juridique ⚖️

| # | Question | Destinataire | Débloque |
|---|---|---|---|
| **É-Q12** | MediVox exerce-t-elle une **mission de service public hospitalier** (autorisation ARS / ESPIC) ? | Direction | AI Act Annexe III 5 a) |
| **É-Q11** | MediVox est-elle **fournisseur**, **déployeur**, ou les deux au sens de l'AI Act ? | Direction | Répartition des obligations |
| **É-Q7** | Quelle **base légale art. 9 § 2** a été retenue et documentée ? | ⚖️ Marc | Licéité du traitement |
| **É-Q5** | Les patients sont-ils **informés** de ce traitement et de sa logique ? | ⚖️ Marc | Art. 12-15 |
| **É-Q9** | Le traitement figure-t-il au **registre** (art. 30) ? Une **AIPD** (art. 35) a-t-elle été menée ? | ⚖️ Marc | Accountability (C15) |
| **É-Q8** | Quelle **durée de conservation** pour le jeu de données et pour les prédictions produites ? | ⚖️ Marc | Art. 5.1.e |
| **É-Q10** | Où sont **hébergés** les données et le modèle ? L'hébergeur est-il **certifié HDS** ? | 👩‍💻 Hélène + ⚖️ Marc | L1111-8 CSP |
| **É-Q13** | Le jeu de données constitue-t-il un **entrepôt de données de santé** au sens du référentiel CNIL ? | ⚖️ Marc | Cadre de réutilisation |

### 7.3 Justification des variables ⚖️ 👩‍💻

| # | Question | Destinataire | Débloque |
|---|---|---|---|
| **É-Q14** | Quelle **justification clinique documentée** pour l'usage du **sexe** comme variable d'entrée ? | 👩‍💻 Hélène + médical | Minimisation + non-discrimination (C4). **À défaut : aggravant caractérisé** |
| **É-Q15** | Quelle justification pour l'**IMC**, dont la corrélation à la durée réelle est de **0,001** et qui ne coûte que **−0,5 pt** s'il est retiré ? | 👩‍💻 Hélène + médical | Minimisation, art. 5.1.c (C12) |

### 7.4 Technique et exploitation 👩‍💻

| # | Question | Destinataire | Débloque |
|---|---|---|---|
| **T-Q8** | `sha256sum` de l'artefact **en production** vs celui du dépôt ? | 👩‍💻 Hélène | Détermine si cet audit porte sur le bon modèle (C9) |
| **T-Q13** | Qui a **accès en écriture** au chemin du fichier modèle sur le serveur ? | 👩‍💻 Hélène | Dimensionne le risque d'exécution de code arbitraire (C1) |
| **T-Q7** | Qui **construit la ligne de commande SSH**, depuis quelle source (DPI, export, saisie) ? | 👩‍💻 Hélène | Garantie de l'ordre des 4 arguments |
| **T-Q11** | Montrez la ligne exacte qui **assemble et lance** la commande SSH | 👩‍💻 Hélène | Seul vecteur d'injection possible, hors du dépôt |
| **T-Q14** | Le serveur est-il **sauvegardé** ? Quel RTO/RPO est attendu ? | 👩‍💻 Hélène | Points de rupture n°1 et n°2, aujourd'hui **inconnus** (C11) — **si la machine tombe, tout est perdu** |
| **T-Q15** | Le chiffre **« 0,77 »** a-t-il servi à **valider la mise en production** ? | 👩‍💻 Hélène | Si oui, la décision d'origine repose sur une mesure invalide (C8) |
| **T-Q9** | Une documentation de sélection / d'entraînement existe-t-elle **hors du dépôt** ? | 👩‍💻 Hélène | Sinon le choix du modèle n'est pas justifiable (C9) |

### 7.5 Ressources et organisation

| # | Question | Destinataire | Débloque |
|---|---|---|---|
| **R-Q16** | **Combien de prédictions par an**, selon quel profil horaire ? | 👩‍💻 Hélène + direction des soins | Conditionne **99 %** du chiffrage de coût (C14) |
| **R-Q17** | **Combien de temps prend le geste complet** (connexion, saisie, lecture, report) ? | 👩‍💻 Hélène + exécutants | Poste de coût **n°1** (96 %) — estimé à 2 min, jamais chronométré |
| **R-Q21** | **Combien de personnes** exécutent ce geste, et **qui prend le relais** en congés / départ ? | 👩‍💻 Hélène + RH | Chiffre le point de rupture « humain » en jours d'indisponibilité |
| **R-Q20** | Les prédictions **pourraient-elles être faites par lot quotidien** ? | 👩‍💻 Hélène + direction des soins | Diviserait le CPU par **9 733** et supprimerait l'essentiel du coût, **sans toucher au modèle** |
| **R-Q19** | Existe-t-il une **exigence de délai métier** (SLA) ? | Direction des soins | Détermine si les 1 890 ms sont 🔴 ou 🟡 |
| **R-Q22** | Le modèle a-t-il été **ré-entraîné depuis 2 ans** ? Si non, pourquoi ? | 👩‍💻 Hélène | L'entraînement coûte **337 ms** : la croyance « c'est trop lourd » est mesurément fausse (point d'appui, sous le tableau § 6) |
| **R-Q18** | Le serveur est-il **dédié** à ce script ou mutualisé ? | 👩‍💻 Hélène | Seul poste informatique non négligeable (≈ 600 €/an, **0,060 %** d'occupation) |
| **R-Q24** | Quel **budget annuel** est attribué à ce système, et sur quelle ligne ? | Direction | L'audit mesure ≈ 15 600 €/an dont **0,02 €** d'informatique |
| **R-Q23** | MediVox a-t-il un **engagement RSE / reporting CSRD** auquel ce système devrait contribuer ? | Direction + 👩‍💻 Hélène | Détermine s'il faut documenter les 7 gCO₂e ou simplement les classer |
