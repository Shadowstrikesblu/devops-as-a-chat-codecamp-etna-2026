# app/services/error_translator.py
"""
Traduction des erreurs techniques (Terraform / AWS / réseau) en messages
compréhensibles par l'utilisateur, avec une action corrective concrète.

Utilisé pour l'Axe 1 du Challenge 1 (messages d'erreur compréhensibles).
"""
import re
from typing import Dict

# Préfixes techniques répétés à nettoyer (ex: "500: Erreur exécution : 500: Erreur exécution : ...")
_NOISE_PREFIXES = [
    r"^\s*\d{3}:\s*Erreur ex[ée]cution\s*:\s*",
    r"^\s*Erreur '(?:apply|plan|init)':\s*",
]

# (motif recherché dans l'erreur brute, message clair, action corrective)
_RULES = [
    (
        r"InvalidAMIID\.Malformed|expecting \"ami-",
        "L'image (AMI) demandée est invalide.",
        "Régénère la demande : l'AMI est désormais résolue automatiquement. Si l'erreur persiste, précise l'OS (ex. « instance ubuntu »).",
    ),
    (
        r"InvalidAMIID\.NotFound",
        "L'image (AMI) spécifiée n'existe pas dans cette région.",
        "Change de région ou régénère la demande pour obtenir une AMI valide.",
    ),
    (
        r"not eligible for Free Tier",
        "Le type d'instance choisi n'est pas éligible au Free Tier dans cette région.",
        "Utilise un type éligible (ex. t3.micro en eu-west-1) ou désactive la restriction Free Tier sur ton compte AWS.",
    ),
    (
        r"UnauthorizedOperation|not authorized to perform|AccessDenied",
        "Ton utilisateur AWS n'a pas les permissions nécessaires.",
        "Ajoute la policy IAM adaptée (ex. AmazonEC2FullAccess) à ton utilisateur, puis relance.",
    ),
    (
        r"InvalidKeyPair\.Duplicate",
        "Une paire de clés du même nom existe déjà sur AWS.",
        "Supprime l'ancienne key pair côté AWS, ou relance pour en générer une nouvelle.",
    ),
    (
        r"AuthFailure|InvalidClientTokenId|SignatureDoesNotMatch",
        "Tes identifiants AWS sont invalides ou expirés.",
        "Vérifie/renouvelle ta clé AWS dans les paramètres (onboarding AWS).",
    ),
    (
        r"RequestExpired|ExpiredToken",
        "Tes identifiants AWS ont expiré.",
        "Renouvelle ta clé AWS puis relance la création.",
    ),
    (
        r"VcpuLimitExceeded|InstanceLimitExceeded|exceeded your quota",
        "Tu as atteint une limite de quota AWS.",
        "Supprime des instances existantes ou demande une augmentation de quota à AWS.",
    ),
    (
        r"timeout|timed out|deadline exceeded",
        "L'opération a pris trop de temps.",
        "Réessaie dans un instant. Si le problème persiste, vérifie ta connexion et l'état du backend.",
    ),
    (
        r"Aucune étape détectée|Aucun intent",
        "Aucune action exploitable n'a été détectée dans ta demande.",
        "Formule une demande explicite, par exemple : « crée une instance ubuntu sur aws ».",
    ),
]


def _strip_noise(raw: str) -> str:
    """Supprime les préfixes techniques dupliqués en tête de message."""
    out = (raw or "").strip()
    changed = True
    while changed:
        changed = False
        for pat in _NOISE_PREFIXES:
            new = re.sub(pat, "", out, count=1)
            if new != out:
                out = new.strip()
                changed = True
    return out


def _extract_terraform_error(raw: str) -> str:
    """
    Extrait la (les) ligne(s) 'Error:' d'une sortie Terraform si présentes,
    pour ne pas noyer l'utilisateur sous le plan complet.
    """
    if not raw:
        return raw
    # Bloc encadré Terraform: lignes commençant par 'Error:' (stderr -no-color)
    errors = re.findall(r"^Error:.*$", raw, flags=re.MULTILINE)
    if errors:
        return " ".join(e.strip() for e in errors)
    return raw


def humanize_error(raw: str, max_detail: int = 1500) -> Dict[str, str]:
    """
    Transforme une erreur technique brute en message utilisateur structuré.

    Returns:
        {
            "summary": "<phrase claire>",
            "hint": "<action corrective>",
            "detail": "<extrait technique nettoyé, non tronqué aveuglément>",
        }
    """
    cleaned = _strip_noise(raw or "")
    tech = _extract_terraform_error(cleaned) or cleaned

    summary = "Une erreur est survenue lors de l'opération."
    hint = "Corrige ta demande puis relance. Le détail technique est disponible ci-dessous."

    for pattern, msg, action in _RULES:
        if re.search(pattern, cleaned, flags=re.IGNORECASE):
            summary = msg
            hint = action
            break

    # On garde un détail technique lisible (extrait pertinent), tronqué proprement et signalé.
    detail = tech.strip()
    if len(detail) > max_detail:
        detail = detail[:max_detail].rstrip() + " […]"

    return {"summary": summary, "hint": hint, "detail": detail}


def format_user_error(raw: str, title: str = "Erreur") -> str:
    """
    Construit un message markdown clair (résumé + action + détail technique)
    prêt à être affiché dans le chat.

    Markdown pur uniquement (pas de HTML brut) : le rendu chat (ReactMarkdown
    sans rehype-raw) n'affiche pas les balises HTML.
    """
    h = humanize_error(raw)
    return (
        f"**{title} : {h['summary']}**\n\n"
        f"👉 {h['hint']}\n\n"
        f"_Détail technique :_\n\n"
        f"```\n{h['detail']}\n```"
    )
