# Modifications — Axe 3 : Affichage structuré du plan / des actions

> Challenge 1 (UX du chat) — Axe 3 implémenté. Date : 2026-06-08

## Problème traité
Au lancement d'une création, l'utilisateur ne voyait pas **ce qui allait être créé**
(type d'instance, OS, région, réseau, sécurité) — juste « Création Terraform lancée en arrière-plan ».

## Solution implémentée
Enrichissement du message de lancement avec un **récapitulatif structuré en markdown**
(tableau de ressources), rendu par le markdown déjà supporté dans le chat — pas de nouveau
composant React (approche volontairement légère et sans risque pour la démo).

Le récapitulatif est construit à partir des specs de l'intent (`_extract_create_specs`) :
provider, OS, nombre d'instances, et région (depuis les credentials AWS).

## Fichiers impactés
| Fichier | Nature | Détail |
|---|---|---|
| `devops_api/app/routes/chat_creation_routes.py` | Modifié | Génère `plan_md` (tableau ressources) à la place du message brut ; `extra.type="execution"`. |

## Exemple de rendu

```
Plan de déploiement (AWS)

| Ressource    | Détail                                   |
|--------------|------------------------------------------|
| Instance EC2 | t3.micro × 1                             |
| OS           | ubuntu                                   |
| Région       | eu-west-1                                |
| Réseau       | VPC par défaut                           |
| Sécurité     | Security group SSH (port 22) + key pair  |

🚀 Création lancée en arrière-plan…
```

## Vérification
Backend rebuildé, imports OK, conteneur `healthy`.

## Critères de réussite — état
- [x] Avant exécution, l'utilisateur voit les ressources et leurs paramètres clés.
- [ ] Outputs (IP/instance_id) en tableau après exécution — *non fait* (voir suite).

## Suite possible
- Carte React dédiée `PlanSummary.tsx` (rendu plus riche, boutons copier).
- Afficher les **outputs** Terraform (IP publique, instance_id) après succès, en tableau.
