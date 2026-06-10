# app/services/plan_presenter.py
"""
Formatage du plan d'action avant exécution (Challenge 2, Piste 3).

Produit le bloc lisible décrit dans l'énoncé :

    Action détectée : redémarrage de service
    Cible : nginx
    Environnement : VM de test
    Commande proposée : sudo systemctl restart nginx

    ⚠️ Cette action n'a pas encore été exécutée. Confirmer ? (oui / non)
"""
from typing import Optional
from app.services.action_safety import classify_command, level_badge


def format_action_plan(
    action: str,
    command: str,
    target: Optional[str] = None,
    environment: Optional[str] = None,
    simulated_output: Optional[str] = None,
) -> str:
    """
    Construit le message markdown de plan d'action (type `proposal`).

    Args:
        action: description courte de l'action (« redémarrage de service »).
        command: commande exacte qui serait exécutée.
        target: cible (ex. « nginx », « i-0123 »).
        environment: environnement (ex. « VM de test »).
        simulated_output: sortie de simulation (dry-run) éventuelle à afficher.
    """
    safety = classify_command(command)
    badge = level_badge(str(safety["level"]))

    lines = [
        f"**Plan d'action** — {badge}",
        "",
        f"- **Action détectée** : {action}",
    ]
    if target:
        lines.append(f"- **Cible** : {target}")
    if environment:
        lines.append(f"- **Environnement** : {environment}")
    lines.append(f"- **Commande proposée** :")
    lines.append("")
    lines.append(f"```bash\n{command}\n```")

    if simulated_output:
        lines.append("")
        lines.append("_Résultat simulé (dry-run, aucune exécution réelle) :_")
        lines.append("")
        lines.append(f"```\n{simulated_output}\n```")

    lines.append("")
    lines.append("⚠️ **Cette action n'a pas encore été exécutée.**")
    lines.append("Voulez-vous confirmer ? Répondez **oui** pour exécuter, **non** pour annuler.")

    return "\n".join(lines)
