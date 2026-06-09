# Modifications — Axe 1 : Messages d'erreur compréhensibles

> Challenge 1 (UX du chat) — Axe 1 implémenté.
> Date : 2026-06-08

---

## Problème traité

Les erreurs affichées dans le chat étaient des traces techniques brutes :

- **tronquées à 300 caractères** (`str(e)[:300]`), ce qui coupait souvent la vraie cause ;
- avec des **préfixes dupliqués** (`500: Erreur exécution : 500: Erreur exécution : Erreur 'apply': …`) ;
- la **vraie cause** Terraform/AWS (ligne `Error:`) part dans **stderr**, qui n'était même pas
  capturé (seul `stdout` l'était) → le message s'arrêtait sur `Terraform used the selected p…`.

Exemples réels rencontrés et désormais traduits :
`InvalidAMIID.Malformed`, `not eligible for Free Tier`, `UnauthorizedOperation`,
`Aucune étape détectée`.

---

## Solution implémentée

1. **Capture de stderr** dans l'apply Terraform : on privilégie `stderr` (où se trouve la
   ligne `Error:`) plutôt que `stdout` tronqué.
2. **Service de traduction d'erreurs** (`error_translator.py`) :
   - nettoie les préfixes techniques dupliqués ;
   - extrait la/les ligne(s) `Error:` de la sortie Terraform ;
   - mappe les erreurs fréquentes vers **un résumé clair + une action corrective** ;
   - produit un message **markdown** (résumé + action + détail technique en bloc de code),
     sans HTML brut (le rendu chat n'affiche pas le HTML).
3. **Branchement** dans la notification d'erreur du chat : remplacement du message brut tronqué
   par le message traduit. Ajout d'un `type: "error"` dans `extra` (préparé pour l'Axe 2).

---

## Fichiers impactés

| Fichier | Nature | Détail |
|---|---|---|
| `devops_api/app/services/error_translator.py` | **Nouveau** | Traduction technique → message utilisateur (`humanize_error`, `format_user_error`). |
| `devops_api/app/services/terraform_service.py` | Modifié | L'échec d'`apply` remonte désormais **stderr** (vraie cause) et non plus seulement stdout tronqué. |
| `devops_api/app/routes/chat_creation_routes.py` | Modifié | La notification d'erreur de création utilise `format_user_error(...)` ; `extra.type="error"` ; détail porté à 1000 car. |

> Couverture : les erreurs `empty` / `partial` / `apply` du flux de création remontent toutes
> via le même `except` de `execute_infrastructure_creation`, donc toutes passent par le
> traducteur.

---

## Détail des changements

### 1. `error_translator.py` (nouveau)

Fonctions principales :
- `humanize_error(raw) -> {summary, hint, detail}` : nettoyage + extraction + mapping.
- `format_user_error(raw, title) -> str` : message markdown prêt pour le chat.

Règles de mapping couvertes : AMI invalide/introuvable, Free Tier, permissions IAM,
key pair dupliquée, credentials invalides/expirés, quotas, timeouts, « aucune étape détectée ».

### 2. `terraform_service.py`

```python
if apply_result.returncode != 0:
    apply_err = (getattr(apply_result, "stderr", "") or "").strip()
    detail = apply_err or apply_output
    raise Exception(f"Erreur 'apply': {detail}")
```

### 3. `chat_creation_routes.py`

```python
from app.services.error_translator import format_user_error
friendly = format_user_error(str(e), title="Création Terraform échouée")
db.add(models.Message(
    ..., sender="bot", text=friendly,
    extra={"state": "awaiting_intent", "type": "error", "error": str(e)[:1000]},
))
```

---

## Vérification

Backend rebuildé (`docker compose up -d --build backend`, conteneur `healthy`).
Test unitaire du traducteur sur 3 erreurs réelles :

| Entrée (brute) | Résumé affiché |
|---|---|
| `… not eligible for Free Tier` | « Le type d'instance choisi n'est pas éligible au Free Tier dans cette région. » |
| `… UnauthorizedOperation … ec2:DescribeVpcs` | « Ton utilisateur AWS n'a pas les permissions nécessaires. » |
| `Aucune étape détectée …` | « Aucune action exploitable n'a été détectée dans ta demande. » |

Chaque résumé est accompagné d'une **action corrective** et du **détail technique** (non tronqué aveuglément).

---

## Critères de réussite (Axe 1) — état

- [x] Pour les erreurs fréquentes, l'utilisateur voit **quoi faire** sans lire de stacktrace.
- [x] La vraie cause (stderr) n'est plus coupée par la troncature à 300 caractères.
- [x] Plus de préfixe dupliqué `500: … 500: …` (nettoyé par le traducteur).

## Limites / suite

- Le rendu visuel distinctif des messages d'erreur (badge, couleur) relève de l'**Axe 2**
  (déjà préparé via `extra.type="error"`).
- D'autres messages d'erreur secondaires (audit/monitoring/configure) utilisent encore
  `str(e)[:200]` et pourront être branchés sur le traducteur ultérieurement.
