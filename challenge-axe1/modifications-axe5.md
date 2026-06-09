# Modifications — Axe 5 : Guidage de saisie & messages système clairs

> Challenge 1 (UX du chat) — Axe 5 implémenté. Date : 2026-06-08

## Problème traité
Un prompt vague (ex. `aws`) ne produisait aucune action et renvoyait un message opaque
(« Aucune étape détectée pour cette session. Ajoutez des intents puis reconstruisez le plan »).
L'utilisateur ne savait pas quoi taper.

## Solution implémentée
1. **Suggestions cliquables** dans la zone de saisie (`ChatInput`), affichées tant que le champ
   est vide : exemples de demandes exploitables, envoyées en un clic.
2. **Message système clair** : « Aucune étape détectée » est désormais traduit par le service
   d'erreurs (Axe 1) en : *« Aucune action exploitable n'a été détectée — exemple : crée une
   instance ubuntu sur aws »*.

## Fichiers impactés
| Fichier | Nature | Détail |
|---|---|---|
| `frontend/src/components/Chat/ChatInput.tsx` | Modifié | Constante `SUGGESTIONS` + rangée de `Chip` cliquables (envoi direct) ; wrapper `Box` autour du formulaire. |
| `devops_api/app/services/error_translator.py` | (Axe 1) | Règle de traduction du message « Aucune étape détectée » → exemple actionnable. |

## Suggestions proposées
- « crée une instance ubuntu sur aws »
- « configure nginx sur mon serveur »
- « audit de sécurité de mon instance »

## Vérification
Frontend rebuildé avec succès, conteneur `healthy`.

## Critères de réussite — état
- [x] Un prompt non exploitable renvoie un **exemple actionnable**, pas un message technique.
- [x] L'utilisateur a des exemples cliquables sous les yeux.

## Suite possible
- Validation côté backend à la création de l'intent : répondre directement avec un exemple
  si le prompt ne produit aucune spec (au lieu de créer un intent inutile).
