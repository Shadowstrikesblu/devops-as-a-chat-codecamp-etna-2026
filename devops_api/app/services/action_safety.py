# app/services/action_safety.py
"""
Classification de la sensibilité d'une action / commande (Challenge 2, Piste 1).

Niveaux :
- safe       : lecture / diagnostic, aucun effet de bord notable.
- sensitive  : modifie un état (restart service, install paquet, firewall…). Confirmation requise.
- dangerous  : destructif / irréversible (rm -rf, terraform destroy, drop database…). Confirmation requise + avertissement fort.

L'objectif : aucune action sensible/dangereuse ne doit s'exécuter sans confirmation explicite.
"""
import re
from typing import Dict

SAFE = "safe"
SENSITIVE = "sensitive"
DANGEROUS = "dangerous"

# Motifs destructifs / irréversibles
_DANGEROUS_PATTERNS = [
    r"\brm\s+-[rf]", r"\brm\s+-rf\b", r"\bmkfs\b", r"\bdd\s+if=", r"\b:\(\)\s*\{",  # fork bomb
    r"\bterraform\s+destroy\b", r"\bdrop\s+(database|table)\b", r"\btruncate\b",
    r"\bdelete\s+from\b", r"\bshutdown\b", r"\breboot\b", r"\bhalt\b", r"\bpoweroff\b",
    r"\buserdel\b", r"\bchmod\s+-R\s+777\b", r"\b>\s*/dev/sd", r"\bwipefs\b",
    r"\bterminate-instances\b", r"\bdelete-bucket\b", r"\baws\s+s3\s+rb\b",
]

# Motifs modifiant un état (sensibles mais non destructifs)
_SENSITIVE_PATTERNS = [
    r"\bsystemctl\s+(restart|stop|start|reload|enable|disable)\b",
    r"\bservice\s+\w+\s+(restart|stop|start|reload)\b",
    r"\b(apt|apt-get|yum|dnf)\s+(install|remove|purge|upgrade)\b",
    r"\bpip\s+install\b", r"\bnpm\s+install\b",
    r"\b(ufw|firewall-cmd|iptables)\b", r"\bchmod\b", r"\bchown\b",
    r"\bdocker\s+(run|rm|stop|restart|compose)\b",
    r"\buseradd\b", r"\bpasswd\b", r"\bmount\b", r"\bumount\b",
    r"\bgit\s+(push|reset\s+--hard)\b", r"\bkill\b",
    r"\bterraform\s+apply\b",
]

# Motifs typiquement sûrs (lecture / diagnostic)
_SAFE_PATTERNS = [
    r"\b(systemctl\s+status|service\s+\w+\s+status)\b",
    r"\b(cat|less|tail|head|grep|ls|df|free|uptime|whoami|id|uname|ps|top|journalctl)\b",
    r"\bterraform\s+plan\b", r"\becho\b", r"\bcurl\s+-s",
]


def _matches_any(text: str, patterns) -> bool:
    return any(re.search(p, text, flags=re.IGNORECASE) for p in patterns)


def classify_command(command: str) -> Dict[str, object]:
    """
    Classe une commande shell.

    Returns:
        {
            "level": "safe|sensitive|dangerous",
            "requires_confirmation": bool,
            "reason": "<courte explication>",
        }
    """
    cmd = (command or "").strip()
    if not cmd:
        return {"level": SAFE, "requires_confirmation": False, "reason": "Commande vide."}

    if _matches_any(cmd, _DANGEROUS_PATTERNS):
        return {
            "level": DANGEROUS,
            "requires_confirmation": True,
            "reason": "Action destructive ou irréversible détectée.",
        }

    if _matches_any(cmd, _SENSITIVE_PATTERNS):
        return {
            "level": SENSITIVE,
            "requires_confirmation": True,
            "reason": "Action modifiant l'état du système détectée.",
        }

    if _matches_any(cmd, _SAFE_PATTERNS):
        return {"level": SAFE, "requires_confirmation": False, "reason": "Lecture / diagnostic."}

    # Par défaut : on considère sensible si on ne sait pas (principe de prudence).
    return {
        "level": SENSITIVE,
        "requires_confirmation": True,
        "reason": "Commande non reconnue : confirmation requise par prudence.",
    }


def classify_intent(intent_type: str) -> Dict[str, object]:
    """
    Classe une intention DAC de haut niveau (create/configure/audit/...).
    create/configure modifient l'infra → confirmation ; audit/monitoring → sûrs.
    """
    it = (intent_type or "").lower()
    if it in {"create", "configure", "kubernetes"}:
        return {"level": SENSITIVE, "requires_confirmation": True,
                "reason": "Création/modification d'infrastructure."}
    return {"level": SAFE, "requires_confirmation": False, "reason": "Lecture / analyse."}


_LEVEL_BADGE = {
    SAFE: "🟢 Action sûre",
    SENSITIVE: "🟠 Action sensible",
    DANGEROUS: "🔴 Action dangereuse",
}


def level_badge(level: str) -> str:
    return _LEVEL_BADGE.get(level, "🟠 Action sensible")
