# Challenge 2 — Sécurisation : simulation (dry-run) & confirmation avant exécution

> Objectif : éviter qu'une action sensible soit exécutée sans confirmation. DAC doit pouvoir
> **proposer une simulation avant exécution réelle**.
>
> Document de cadrage : pour chaque piste, **problème identifié · solution proposée ·
> fichiers/composants impactés · risques techniques · critères de réussite**.
>
> Projet : DAC (DevOps-as-a-Chat) — CodeCamp ETNA 2026 — Date : 2026-06-08

---

## Constat (existant dans le code)

- Un **début de confirmation existe** : les flux audit / monitoring / create / configure
  affichent un `plan_msg` puis passent dans un état `awaiting_*_confirmation` et attendent
  `ok` / `annuler` (`devops_api/app/routes/chat_creation_routes.py`).
- **Mais** : pas de **dry-run** réel (simulation), pas de **séparation nette** simulation/exécution,
  pas de **journalisation** de la décision utilisateur, et la **confirmation n'est pas systématique**
  pour toutes les actions sensibles (commandes SSM/Ansible sur VM, suppression de ressources).
- L'exécution réelle passe par : Terraform (`terraform_service.py`), SSM
  (`services/ssm_executor.py`), Ansible (`services/ansible_service.py`), suppression de ressources
  (`routes/resource_routes.py`).

L'exemple de l'énoncé (« redémarre nginx sur la VM de test ») correspond au flux **configure → SSM**.

---

## Piste 1 — Classification & sécurisation des actions dangereuses

### Problème identifié
Aucune notion de **niveau de sensibilité** : une commande anodine (`echo`) et une commande
dangereuse (`systemctl restart`, `rm`, `terraform destroy`, suppression d'instance) sont traitées
pareil. Rien ne force une confirmation pour les actions à risque.

### Solution proposée
- Créer un **classifieur de sensibilité** (`safe` / `sensitive` / `dangerous`) basé sur des
  motifs (restart/stop/reboot, rm, destroy, drop, delete, chmod 777, firewall…).
- Toute action `sensitive`/`dangerous` **exige une confirmation** (et n'est jamais auto-exécutée).

### Fichiers / composants impactés
- Nouveau : `devops_api/app/services/action_safety.py` (classification + règles).
- `devops_api/app/services/ssm_executor.py`, `ansible_service.py`, `terraform_service.py`
  (point de contrôle avant exécution).
- `devops_api/app/routes/resource_routes.py` (suppression de ressources).

### Risques techniques
- Faux négatifs (commande dangereuse non détectée) → liste de motifs conservatrice + « par défaut sensible si doute ».
- Faux positifs (trop de confirmations) → garder `safe` pour les lectures/diagnostics.

### Critères de réussite
- Une commande dangereuse ne part jamais sans confirmation.
- La catégorie est visible dans le message (badge « action sensible »).

---

## Piste 2 — Mode dry-run (simulation) & séparation simulation / exécution

### Problème identifié
Il n'existe pas de **simulation** : on ne peut pas voir ce qui *serait* fait sans le faire.
Terraform a pourtant un `plan` natif, et SSM/Ansible peuvent être simulés.

### Solution proposée
- Introduire un **flag `dry_run`** porté par l'exécution.
- **Terraform** : `terraform plan` seul = simulation (déjà exécuté avant l'apply → l'exposer comme
  résultat de simulation, sans apply).
- **SSM / Ansible** : mode simulation = **n'exécute pas** la commande, renvoie la commande exacte
  qui *serait* lancée (+ cible + environnement). Ansible dispose nativement de `--check`.
- **Séparation** : une exécution `dry_run=true` produit un **plan**; l'exécution réelle est un
  acte distinct, déclenché seulement après confirmation.

### Fichiers / composants impactés
- `devops_api/app/services/ssm_executor.py`, `ansible_service.py`, `terraform_service.py`
  (branche `if dry_run: return simulation`).
- `devops_api/app/schemas/execution_plan.py` / modèle `Execution` (champ `dry_run` / `mode`).
- `devops_api/app/routes/chat_creation_routes.py` (orchestration simulation → confirmation → exécution).

### Risques techniques
- Divergence simulation/réel (la simu doit refléter exactement la commande réelle) → générer la
  commande **une seule fois** et la réutiliser pour les deux modes.
- `terraform plan` peut nécessiter des credentials valides (déjà le cas).

### Critères de réussite
- Le mode simulation est **démontrable** : l'utilisateur voit la commande/plan sans aucun effet réel.
- Aucune ressource modifiée pendant une simulation.

---

## Piste 3 — Plan d'exécution clair + demande de confirmation systématique

### Problème identifié
La confirmation existe mais est **hétérogène** et le plan affiché n'a pas le format clair de
l'énoncé (action détectée / cible / environnement / commande proposée / « non exécutée »).

### Solution proposée
- Standardiser un **bloc de plan** unique réutilisé par tous les flux :
  ```
  Action détectée : redémarrage de service
  Cible : nginx
  Environnement : VM de test
  Commande proposée : sudo systemctl restart nginx

  ⚠️ Cette action n'a pas encore été exécutée. Confirmer ? (oui / non)
  ```
- Message de type `proposal` (cf. Challenge 1, Axe 2) avec **boutons Confirmer / Annuler**.

### Fichiers / composants impactés
- Nouveau : `devops_api/app/services/plan_presenter.py` (formatage du bloc de plan).
- `devops_api/app/routes/chat_creation_routes.py` (utilise le presenter ; états `awaiting_*_confirmation`).
- `frontend/src/components/Chat/MessageBubble.tsx` (boutons sur les messages `proposal`).

### Risques techniques
- Cohérence des états de session (ne pas exécuter si l'utilisateur change de sujet entre-temps).

### Critères de réussite
- L'utilisateur voit **clairement ce qui va être fait** avant toute exécution.
- Aucune action sensible exécutée sans `oui` explicite.

---

## Piste 4 — Journalisation de la décision utilisateur (audit trail)

### Problème identifié
Les décisions (confirmé / refusé) ne sont **pas tracées** : impossible de savoir qui a validé/refusé
quoi, ni de prouver qu'une action a été confirmée.

### Solution proposée
- Nouvelle table **`action_decisions`** : `user_id`, `session_id`, `execution_id`, `action_summary`,
  `command`, `safety_level`, `decision` (`confirmed`/`rejected`), `created_at`.
- Écriture systématique au moment du `oui`/`non`. Endpoint de consultation (historique).

### Fichiers / composants impactés
- Nouveau : `devops_api/app/models/action_decision.py` + migration.
- Nouveau : `devops_api/app/services/decision_log.py` (helper d'écriture).
- `devops_api/app/routes/chat_creation_routes.py` (log au point de décision).
- (Option) `frontend` : affichage de l'historique des décisions.

### Risques techniques
- Création de table / migration en environnement étudiant → fournir un script idempotent.
- Ne pas logguer de secrets dans `command`.

### Critères de réussite
- Les actions **confirmées et refusées sont tracées** (horodatées, attribuées à l'utilisateur).

---

## Critères de réussite globaux (mapping avec l'énoncé)

| Critère de l'énoncé | Pistes couvrantes |
|---|---|
| Aucune action sensible exécutée sans confirmation | Piste 1 (classification) + Piste 3 (confirmation systématique) |
| L'utilisateur voit clairement ce qui va être fait | Piste 3 (bloc de plan standardisé) + Piste 2 (simulation) |
| Le mode simulation est démontrable | Piste 2 (dry-run Terraform/SSM/Ansible) |
| Actions confirmées et refusées tracées | Piste 4 (journalisation) |

## Priorisation recommandée (effort/impact démo)

1. **Piste 3** (plan clair + confirmation + boutons) — réutilise l'Axe 2 déjà livré, effet démo immédiat.
2. **Piste 1** (classification dangereuses) — garantit le critère central « rien sans confirmation ».
3. **Piste 2** (dry-run) — le « waouh » : simulation réelle sans effet.
4. **Piste 4** (journalisation) — coche le dernier critère, table simple.

## Lien avec le Challenge 1 (déjà implémenté)
- Le type de message **`proposal`** (Axe 2) et le **récapitulatif de plan** (Axe 3) servent de base
  directe aux Pistes 3 et 2 ci-dessus.
