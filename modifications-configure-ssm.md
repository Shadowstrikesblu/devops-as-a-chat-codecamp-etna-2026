# Modifications — Intégration end-to-end : confirmation dans le flux configure → SSM

> Challenge 2 — finalisation : l'exemple « redémarre/configure un service » passe désormais par
> une confirmation explicite avant exécution. Date : 2026-06-08

## Problème traité
Dans le flux configure, dès que l'utilisateur **sélectionnait les VM** (`confirm_instances`),
la configuration **s'exécutait immédiatement** (`run_execution_by_id`) — **sans aucune
confirmation**. Cela violait le critère « aucune action sensible exécutée sans confirmation ».

## Solution implémentée
Insertion d'une **étape de confirmation** entre la sélection des VM et l'exécution :

1. À `confirm_instances` : au lieu d'exécuter, DAC **affiche le plan d'action** (action détectée,
   cibles, environnement, badge de sensibilité) et passe en état `awaiting_configure_confirmation`.
   **Aucune commande n'est exécutée.** Le message est de type `proposal` → il reçoit les
   **boutons Confirmer / Annuler** (Piste 3).
2. Nouveau handler `awaiting_configure_confirmation` :
   - **non / annuler** → décision `rejected` **journalisée**, configuration abandonnée.
   - **oui / ok** → décision `confirmed` **journalisée**, puis exécution réelle
     (`run_execution_by_id`) et résumé (success/failed/trace).

## Fichiers impactés
| Fichier | Nature | Détail |
|---|---|---|
| `devops_api/app/routes/chat_creation_routes.py` | Modifié | `confirm_instances` affiche le plan + passe en `awaiting_configure_confirmation` (plus d'exécution directe) ; nouveau handler d'état qui journalise puis exécute. |

Réutilise : `action_safety` (Piste 1), `plan_presenter`/boutons (Piste 3), `decision_log` (Piste 4).

## Parcours utilisateur (exemple type énoncé)
```
Utilisateur : installe/redémarre nginx sur la VM de test
DAC         : (sélection des VM)
Utilisateur : [coche la VM] → Confirmer la sélection
DAC         : Plan d'action — 🟠 Action sensible
              - Action détectée : Installer Nginx (installation)
              - Cible(s) : web-test (i-0123)
              - Environnement : VM sélectionnée(s)
              - Exécution : via SSM/Ansible
              ⚠️ Cette action n'a pas encore été exécutée. Confirmer ? [Confirmer] [Annuler]
Utilisateur : Confirmer
DAC         : ✅ Configuration exécutée : success=1, failed=0. Trace: ...
```
→ décisions `confirmed`/`rejected` tracées dans `action_decisions`.

## Vérification
- Backend rebuildé, `chat_creation_routes` importe sans erreur, conteneur `healthy`.
- Présence du nouvel état confirmée dans le conteneur.

## Critères de réussite (configure) — état
- [x] Aucune configuration exécutée sans confirmation explicite.
- [x] L'utilisateur voit le plan (action, cibles, sensibilité) avant exécution.
- [x] Confirmation 1 clic (boutons) ou texte (oui/non).
- [x] Décisions confirmées et refusées journalisées.

## Limite / suite
- Le **détail des résultats** par instance (ancien formateur riche) reste disponible dans le code
  historique ; le handler de confirmation renvoie un résumé compact. À fusionner si besoin.
- La commande shell exacte (ex. `systemctl restart nginx`) n'est pas affichée car générée à
  l'exécution ; on affiche l'action de catalogue. Possibilité d'exposer la commande via un
  **dry-run** (Piste 2, `execute_command(dry_run=True)`) en amont du plan.
