# RGPD santé + AI Act — Mini-cours

> Brief associé : M7-B1
> Durée de lecture : ~30 min
> Pré-requis : notions RGPD de base (M2)

## Pourquoi cette techno ?

En santé, la conformité n'est pas optionnelle : les données sont **sensibles**
(RGPD art. 9). Mais « santé » ne veut pas dire automatiquement « haut risque »
au sens de l'AI Act, ni « décision automatisée » au sens du RGPD. Ces deux
qualifications **dépendent de l'usage réel** du système : à quoi sert la
prédiction, qui la lit, qu'est-ce qu'elle déclenche. Le travail de l'auditeur
est de **qualifier et documenter son raisonnement**, pas de présumer.
Vous n'êtes pas juriste — vous **posez la qualification probable, ses
conditions, et les questions à trancher** avec le DPO, sans rédiger d'AIPD.

## Concepts clés

- **RGPD art. 9** : les données de santé sont une **catégorie particulière** →
  traitement interdit par défaut, sauf exception (ex. gestion des systèmes de
  soins, intérêt public en santé publique, consentement). La base retenue est
  à **vérifier**, pas à présumer. Minimisation (art. 5) : une variable
  sensible sans justification métier doit être questionnée.
- **RGPD art. 22 — conditions cumulatives** : il vise une décision fondée
  **exclusivement** sur un traitement automatisé **et** produisant un effet
  **juridique ou similairement significatif** sur la personne. Une prédiction
  n'est pas une décision. La question d'audit : **que pilote réellement ce
  score** (admission, sortie, soins, allocation de lits) et **un humain
  peut-il le contredire** ? La CJUE (arrêt *SCHUFA*, C-634/21, 2023) a jugé
  qu'un score peut relever de l'art. 22 s'il **joue un rôle déterminant**
  dans la décision prise par un tiers — un humain qui valide « pour la
  forme » ne suffit pas.
- **AI Act — qualification (art. 6)** : un système est « à haut risque » s'il
  entre dans **l'un de ces cas**, pas parce qu'il touche à la santé :
  1. **composant de sécurité ou produit** couvert par la législation de
     l'Annexe I (ex. **dispositif médical** au sens du règlement 2017/745)
     soumis à évaluation par un tiers ;
  2. **cas listé en Annexe III** — en santé, notamment l'évaluation, **par ou
     pour une autorité publique**, de l'éligibilité à des services essentiels
     dont les soins (5 a), ou les **systèmes de triage des patients en
     urgence** (5 d) ;
  3. **exception de l'art. 6(3)** : un système de l'Annexe III peut ne pas être
     haut risque s'il ne fait qu'une tâche préparatoire ou étroite sans
     influencer substantiellement la décision — exception **fermée** dès
     qu'il y a **profilage** de personnes (évaluer leur santé en est un).
  Sinon : obligations de transparence éventuelles, bonnes pratiques, et
  RGPD — qui s'applique **dans tous les cas**.
- **Obligations si haut risque** : notamment **gestion des risques**,
  **qualité/gouvernance des données** (dont examen des biais),
  **journalisation**, **transparence** envers les utilisateurs,
  **supervision humaine**, exactitude/robustesse. Les citer n'a de sens
  qu'**après** la qualification.
- **Deux cadres, deux objets** : le RGPD encadre le **traitement de données
  personnelles** ; l'AI Act encadre le **système d'IA mis sur le marché ou en
  service**. Un système peut être hors haut risque AI Act et poser quand même
  de sérieux problèmes RGPD.

> ⚠️ Les **dates d'application** des obligations « haut risque » ont fait
> l'objet d'ajustements. Si vous en citez une, vérifiez-la sur le texte
> consolidé (EUR-Lex) le jour de l'audit.

## Exemple minimal qui tourne

La trame d'une qualification — ici sur **un autre cas** (un score de priorité
affiché à l'accueil des urgences d'un hôpital) :

```markdown
Usage réel : score calculé à l'arrivée depuis constantes + motif ; l'IAO
(infirmière d'accueil) le voit et fixe l'ordre de passage. En pratique,
elle suit le score dans 95 % des cas (à vérifier dans les logs).
- AI Act : dispositif médical ? à instruire (aide à une décision clinique).
  Annexe III 5 d (triage des patients en urgence) ? OUI, cas explicite.
  6(3) ? non : profilage (état de santé) + influence directe sur l'ordre.
  → Qualification : haut risque. Obligations : risques, données, logs,
  transparence, supervision humaine effective.
- RGPD art. 22 : exclusivement automatisé ? non en droit (l'IAO décide),
  mais si le score est suivi sans examen → rôle déterminant (SCHUFA) → à
  instruire. Effet significatif ? délai de prise en charge → oui.
- Questions au client : taux de désaccord IAO/score ? désaccord tracé ?
```

La structure se réutilise ; **les réponses se re-dérivent de votre cas**.

## Exercice guidé

Pour le prédicteur MediVox :
1. Écris **l'usage réel** en 3 lignes : qui lit le score, quand, et qu'est-ce
   qu'il déclenche. Ce que tu ne sais pas → **question ouverte** au client.
2. Parcours les 3 cas de l'art. 6 et conclus : haut risque / probablement
   pas / **indéterminé faute d'information** — avec la condition qui ferait
   basculer.
3. Art. 22 : vérifie les **deux** conditions (exclusivement automatisé ? effet
   significatif ?) à partir de ce que fait `legacy/predict.py` **et** de ce que
   tu ne sais pas de son usage.
4. Liste 2 points RGPD à vérifier **quelle que soit** la qualification AI Act.

## Pièges fréquents

| Piège | Conséquence |
|---|---|
| « Santé = haut risque » | Qualification fausse, obligations plaquées hors-sol |
| « Il y a une prédiction, donc art. 22 » | Confond score et décision ; ignore la condition d'effet significatif |
| Qualifier sans décrire l'usage réel | Conclusion invérifiable par le DPO |
| Présumer la base légale art. 9 | On valide à tort une non-conformité |
| Citer les obligations avant la qualification | Liste récitée, pas un raisonnement |
| Rédiger une AIPD complète | Hors mandat d'audit |

| Symptôme | Cause probable |
|---|---|
| Marc (DPO) conteste la qualification | usage réel non décrit, ou cas de l'art. 6 non parcourus |
| « Le système est conforme » trop vite | base légale art. 9 non vérifiée |
| Toutes les obligations « haut risque » listées, aucune question au client | présomption au lieu de qualification |
| Art. 22 écarté parce qu'« un humain valide » | rôle déterminant du score non examiné (SCHUFA) |

## Pour aller plus loin

- AI Act — texte consolidé (EUR-Lex), art. 6 et Annexe III : https://eur-lex.europa.eu/eli/reg/2024/1689/oj
- RGPD — art. 9 et 22 (EUR-Lex) : https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX%3A32016R0679
- CNIL — IA et RGPD : https://www.cnil.fr/fr/intelligence-artificielle/ia-comment-etre-en-conformite-avec-le-rgpd
- CJUE, C-634/21 *SCHUFA Holding* (7 décembre 2023) — score et décision automatisée

## Vérification (checklist apprenant)

- [ ] J'ai décrit l'**usage réel** du score avant toute qualification.
- [ ] J'ai parcouru les 3 cas de l'art. 6 et conclu, avec la condition de bascule.
- [ ] J'ai vérifié les **deux** conditions de l'art. 22.
- [ ] Je cite l'art. 9 et la base légale **à vérifier**.
- [ ] Ce que je ne sais pas est devenu une **question ouverte** au client.

> 💡 **Récap** : RGPD **art. 9** s'applique toujours (données de santé). L'**art.
> 22** ne s'applique que si la décision est **exclusivement** automatisée **et** a
> un effet **significatif** — un score déterminant peut suffire. L'**AI Act**
> classe « haut risque » selon l'**art. 6** (dispositif médical, cas de l'Annexe
> III, exception 6(3)), pas selon le secteur. L'auditeur **qualifie, conditionne,
> questionne** — il ne présume pas.

*Réflexe : avant de citer un article, écris ce que le score déclenche dans la vraie vie.*
