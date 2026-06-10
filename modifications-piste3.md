# Modifications — Challenge 2 / Piste 3 : Plan d'exécution clair + confirmation

> Date : 2026-06-08

## Problème traité
La confirmation existait mais de façon hétérogène, et le plan n'avait pas le format clair de
l'énoncé. Surtout : il fallait **taper** « oui »/« non » sans bouton.

## Solution implémentée
1. **Presenter de plan** (`plan_presenter.py`) produisant exactement le bloc de l'énoncé
   (action détectée / cible / environnement / commande proposée + avertissement « non exécutée »),
   avec **badge de sensibilité** (via Piste 1) et sortie de simulation optionnelle (via Piste 2).
2. **Boutons Confirmer / Annuler** dans le chat, affichés sous la dernière proposition d'action
   (message de type `proposal` ou état `awaiting_*_confirmation`). Ils envoient « oui » / « non ».

## Fichiers impactés
| Fichier | Nature | Détail |
|---|---|---|
| `devops_api/app/services/plan_presenter.py` | **Nouveau** | `format_action_plan(action, command, target, environment, simulated_output)`. |
| `frontend/src/components/Chat/ChatWindow.tsx` | Modifié | Prop `onSend` ; boutons **Confirmer/Annuler** sous la dernière proposition. |
| `frontend/src/pages/Chat.tsx` | Modifié | Passe `onSend={wrappedSendMessage}` à `ChatWindow`. |

## Rendu du plan (exemple)
```
Plan d'action — 🟠 Action sensible

- Action détectée : redémarrage de service
- Cible : nginx
- Environnement : VM de test
- Commande proposée :
  sudo systemctl restart nginx

⚠️ Cette action n'a pas encore été exécutée.
Voulez-vous confirmer ? Répondez oui pour exécuter, non pour annuler.
```
+ boutons **[Confirmer] [Annuler]** sous le message.

## Vérification
Frontend rebuildé (`✓ built`), presenter testé (format conforme), conteneurs `healthy`.

## Critères de réussite — état
- [x] L'utilisateur voit clairement ce qui va être fait avant exécution.
- [x] Confirmation en 1 clic (boutons) ou par texte (« oui »/« non »).

## Suite
- Utiliser `format_action_plan` dans le flux configure/SSM pour afficher la commande exacte
  (`sudo systemctl restart nginx`) avant exécution.
