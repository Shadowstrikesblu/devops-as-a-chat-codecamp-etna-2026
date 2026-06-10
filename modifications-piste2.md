# Modifications — Challenge 2 / Piste 2 : Mode dry-run (simulation)

> Date : 2026-06-08

## Problème traité
Impossible de **voir ce qui serait fait sans le faire**. Aucune séparation simulation / exécution.

## Solution implémentée
Ajout d'un paramètre **`dry_run`** à l'exécuteur SSM : en mode simulation, **aucune commande
n'est envoyée** aux instances ; on retourne la commande qui *serait* lancée (statut `simulated`).
Le presenter de plan (Piste 3) sait afficher cette sortie simulée.

> Côté Terraform, la simulation correspond au `terraform plan` déjà exécuté avant l'`apply`
> (récapitulatif structuré ajouté au Challenge 1, Axe 3).

## Fichiers impactés
| Fichier | Nature | Détail |
|---|---|---|
| `devops_api/app/services/ssm_executor.py` | Modifié | `execute_command(..., dry_run=False)` : court-circuit retournant un résultat `simulated` sans `send_command`. |
| `devops_api/app/services/plan_presenter.py` | (Piste 3) | Paramètre `simulated_output` pour afficher le résultat de simulation. |

## Comportement
```python
execute_command(["i-0123"], "sudo systemctl restart nginx", dry_run=True)
# -> {"i-0123": {"status": "simulated",
#                "stdout": "[DRY-RUN] La commande suivante serait exécutée ... sudo systemctl restart nginx",
#                ...}}
```
Aucune modification réelle sur les instances en mode `dry_run`.

## Critères de réussite — état
- [x] Le mode simulation est démontrable (SSM) : commande affichée, aucun effet réel.
- [x] Séparation simulation (`dry_run=True`) vs exécution réelle (`dry_run=False`).

## Suite
- Exposer un toggle « Simuler / Exécuter » dans l'UI et le propager jusqu'à `execute_command`.
- Mode `--check` natif d'Ansible pour la simulation côté playbooks.
