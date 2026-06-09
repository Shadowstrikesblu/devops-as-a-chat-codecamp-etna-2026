# Modifications — Axe 2 : Distinction info / proposition / exécution / erreur

> Challenge 1 (UX du chat) — Axe 2 implémenté. Date : 2026-06-08

## Problème traité
Tous les messages du bot avaient le même rendu : impossible de distinguer une **information**,
une **action proposée** et une **action exécutée** (ni une **erreur**).

## Solution implémentée
- Introduction d'un **type de message** : `info` | `proposal` | `execution` | `error`.
- Le type est porté par `extra.type` (source backend) ; à défaut il est **inféré** du contenu
  côté frontend (mots-clés : erreur, déployé/créé/IP, confirme/plan…).
- Rendu visuel par type dans `MessageBubble` : **badge** (icône + libellé) et **couleur de bordure**
  de la bulle.

## Fichiers impactés
| Fichier | Nature | Détail |
|---|---|---|
| `frontend/src/components/Chat/MessageBubble.tsx` | Modifié | `resolveBotType()` + `BOT_TYPE_META` ; badge `Chip` + bordure colorée selon le type ; `extra` ajouté à l'interface `Message`. |
| `devops_api/app/routes/chat_creation_routes.py` | Modifié | `extra.type = "error"` sur la notification d'échec (Axe 1) et `extra.type = "execution"` sur le lancement de création (Axe 3). |

## Mapping type → rendu
| Type | Libellé badge | Couleur | Icône |
|---|---|---|---|
| `info` | Information | vert | Info |
| `proposal` | Action proposée | orange | Lightbulb |
| `execution` | Action exécutée | bleu | CheckCircle |
| `error` | Erreur | rouge | ErrorOutline |

## Vérification
Frontend rebuildé avec succès (`✓ built`), conteneur `healthy`.

## Critères de réussite — état
- [x] Info / proposition / exécution / erreur visuellement distinctes.
- [x] Fonctionne même sur les messages historiques (inférence de secours).

## Suite possible
- Ajouter `extra.type` explicite sur davantage de messages backend (succès final, confirmations)
  pour ne plus dépendre de l'inférence.
- Boutons d'action (Confirmer/Annuler) sur les messages `proposal`.
