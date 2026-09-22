# Rapport d'audit pour 2 lectorats — Mini-cours

> Brief associé : M7-B1
> Durée de lecture : ~20 min
> Pré-requis : les 3 volets d'audit réalisés

## Pourquoi cette techno ?

Votre rapport sera lu par **Hélène** (directrice technique) **et Marc** (DPO,
juriste). Un document trop technique perd Marc ; trop juridique perd Hélène. Le
geste pro : **un seul document, deux grilles de lecture** — chaque section
signale qui doit en tirer quoi. C'est exactement la compétence de communication
(C2/CT6) que le jury de certif évalue, et le quotidien du consultant.

## Concepts clés

- **Synthèse exécutive** : ½ page lisible en 5 min par les deux, le « plus grave »
  d'abord. C'est souvent la seule partie lue par un décideur pressé.
- **Sections fléchées** : marquer 👩‍💻 (technique) / ⚖️ (DPO) pour orienter la
  lecture. Le volet éthique parle surtout à Marc, le technique à Hélène.
- **Traduire le jargon** : « calibration dégradée » → « les probabilités ne sont
  plus fiables ». Définir une fois, réutiliser.
- **Structure 7 sections** : synthèse / contexte / éthique / technique /
  ressources / tableau consolidé / questions ouvertes.
- **Hiérarchiser visuellement** : 🔴/🟠/🟡 pour que le décideur voie l'urgence.
- **Ne pas proposer la solution** : le rapport hiérarchise et questionne (la
  proposition d'architecture, c'est M7-B2).

## Exemple minimal qui tourne

```markdown
## 1. Synthèse exécutive (5 min)
Le modèle fonctionne mais expose MediVox à un risque juridique :
⚖️ <écart mesuré entre groupes + qui en subit l'erreur>, sans traçabilité
   — à confirmer par <la question ouverte qui tranche>.
👩‍💻 tout repose sur une seule machine, sans CI/CD.

## 3. Volet éthique ⚖️ (pour Marc)
...
```

## Exercice guidé

À partir de tes 4 volets d'audit :
1. Rédige la **synthèse exécutive** (½ page, le plus grave d'abord).
2. Flèche chaque section (👩‍💻 / ⚖️).
3. Fais relire par un binôme : « Hélène comprend-elle le volet éthique en 2 min ? ».

## Pièges fréquents

| Piège | Conséquence |
|---|---|
| Un seul jargon mélangé | Un des 2 lecteurs décroche |
| Pas de synthèse exec | Le décideur ne lit rien d'actionnable |
| Sections non fléchées | On ne sait pas à qui chaque partie s'adresse |
| Proposer la solution | Hors mandat (c'est M7-B2) |
| Rapport de 15 pages | Illisible — viser 5-10 pages |

| Symptôme | Cause probable |
|---|---|
| Marc conteste / ne suit pas | volet éthique trop technique |
| Hélène trouve le rapport « flou » | pas de chiffres / hiérarchie |
| Le client redemande la priorité | tableau consolidé absent ou plat |

## Pour aller plus loin

- Pyramide de Minto (structurer) : https://en.wikipedia.org/wiki/Barbara_Minto
- Cf. `rapport_audit.md` du correctif (2 grilles de lecture).

## Vérification (checklist apprenant)

- [ ] Synthèse exécutive ½ page, le plus grave d'abord.
- [ ] Sections fléchées 👩‍💻 / ⚖️.
- [ ] Jargon traduit, défini une fois.
- [ ] Tableau consolidé hiérarchisé inclus.
- [ ] Le rapport **questionne** sans proposer l'architecture cible.

> 💡 **Récap** : **un document, deux grilles** — flécher 👩‍💻 (Hélène) / ⚖️ (Marc),
> traduire le jargon, ouvrir par une **synthèse exécutive** (le plus grave d'abord).
> Hiérarchiser en 🔴/🟠/🟡, **questionner sans proposer** l'architecture cible (M7-B2).

*Réflexe : si un décideur ne lit que la synthèse exécutive, doit-il pouvoir décider ? Si non, elle est à retravailler.*
