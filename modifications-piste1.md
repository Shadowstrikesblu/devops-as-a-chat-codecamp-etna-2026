# Modifications — Challenge 2 / Piste 1 : Classification & sécurisation des actions dangereuses

> Date : 2026-06-08

## Problème traité
Aucune notion de **sensibilité** : une lecture (`ls`) et une action destructive (`rm -rf`)
étaient traitées pareil. Rien ne forçait une confirmation pour les actions à risque.

## Solution implémentée
Service `action_safety.py` qui classe une commande en **`safe` / `sensitive` / `dangerous`** via
des motifs regex, et indique si une **confirmation est requise**. Principe de prudence : une
commande non reconnue est considérée `sensitive`.

## Fichiers impactés
| Fichier | Nature | Détail |
|---|---|---|
| `devops_api/app/services/action_safety.py` | **Nouveau** | `classify_command()`, `classify_intent()`, `level_badge()`. |

## Règles (extraits)
- **dangerous** : `rm -rf`, `terraform destroy`, `drop database`, `shutdown/reboot`, `mkfs`, `dd if=`, `terminate-instances`…
- **sensitive** : `systemctl restart/stop/start`, `apt/yum install`, `ufw/iptables`, `chmod/chown`, `docker run/rm`, `terraform apply`…
- **safe** : `systemctl status`, `cat/tail/grep/ls`, `terraform plan`, `echo`…

## Vérification (testée)
| Commande | Niveau | Confirmation |
|---|---|---|
| `systemctl status nginx` | safe | non |
| `sudo systemctl restart nginx` | sensitive | oui |
| `rm -rf /data` | dangerous | oui |
| `ls -la` | safe | non |

## Critères de réussite — état
- [x] Les actions dangereuses sont identifiées et marquées « confirmation requise ».
- [x] Badge de niveau disponible pour l'affichage (`level_badge`).

## Suite
- Brancher `classify_command` comme **garde-fou** systématique dans `ssm_executor` / `ansible_service`
  / `resource_routes` (refus d'exécution directe si `requires_confirmation` et non confirmé).
