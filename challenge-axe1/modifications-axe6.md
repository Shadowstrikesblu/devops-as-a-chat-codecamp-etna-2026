# Modifications — Axe 6 : Robustesse réseau & feedback d'erreur

> Challenge 1 (UX du chat) — Axe 6 implémenté. Date : 2026-06-08

## Problème traité
Les erreurs réseau s'affichaient en anglais brut, ex. lors d'un changement de mode :
`Impossible de changer de mode: timeout of 30000ms exceeded` — incompréhensible et anxiogène
(le backend était simplement en train de redémarrer).

## Solution implémentée
- Util de **traduction des erreurs axios/réseau** en français, distinguant :
  timeout, serveur injoignable, 401/403/404, erreurs 5xx, détail backend.
- Branchement dans `ChatModeToggle` (bascule DAC ↔ libre) : messages clairs + cas dédié
  pour les credentials AWS manquantes (400).

## Fichiers impactés
| Fichier | Nature | Détail |
|---|---|---|
| `frontend/src/utils/errorMessage.ts` | **Nouveau** | `friendlyNetworkError(error)` → message FR clair. |
| `frontend/src/components/Chat/ChatModeToggle.tsx` | Modifié | Les 2 `alert(...)` (free & dac) utilisent `friendlyNetworkError` ; message dédié 400 (credentials). |

## Exemples de traduction
| Cas | Message affiché |
|---|---|
| timeout / `ECONNABORTED` | « Le serveur met trop de temps à répondre. Il est peut-être en cours de redémarrage — réessaie dans quelques secondes. » |
| pas de réponse | « Impossible de joindre le serveur. Vérifie ta connexion et que le backend est démarré… » |
| 400 (DAC) | « Active d'abord tes identifiants AWS pour passer en mode DAC. » |

## Vérification
Frontend rebuildé avec succès, conteneur `healthy`.

## Critères de réussite — état
- [x] Plus d'alerte technique en anglais ; message clair en français.
- [x] Cause probable suggérée (redémarrage backend) + invitation à réessayer.

## Suite possible
- Intercepteur axios global pour traduire toutes les erreurs au même endroit.
- Remplacer les `alert()` par des toasts (un `ToastContext` existe déjà dans le projet).
