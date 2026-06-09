# Challenge 1 — Amélioration de l'expérience utilisateur du chat

> Document de cadrage : pour chaque axe d'amélioration, on précise **le problème identifié**,
> **la solution proposée**, **les fichiers/composants impactés**, **les risques techniques**
> et **les critères de réussite**.
>
> Projet : DAC (DevOps-as-a-Chat) — CodeCamp ETNA 2026
> Date : 2026-06-08

---

## Contexte & constat global

Le mode DAC permet de créer/configurer de l'infrastructure AWS via un chat. Aujourd'hui,
l'expérience souffre de plusieurs limites concrètes observées en utilisation réelle :

- Tous les messages du bot ont **le même rendu visuel**, qu'il s'agisse d'une information,
  d'une action proposée ou d'une action exécutée.
- Les **messages d'erreur** sont des traces techniques brutes, **tronquées**, souvent avec
  des préfixes dupliqués (`500: Erreur exécution : 500: Erreur exécution : Erreur 'apply': …`).
- Le **plan Terraform** (ressources créées) n'est pas présenté de façon structurée.
- Certains messages systèmes sont **opaques** (« Aucune étape détectée pour cette session »).
- Les erreurs réseau frontend s'affichent en anglais brut (`timeout of 30000ms exceeded`).

Les axes ci-dessous découpent le challenge en chantiers livrables indépendamment.

---

## Axe 1 — Messages d'erreur compréhensibles

### Problème identifié
Les erreurs renvoyées à l'utilisateur sont des `str(Exception)` bruts, **tronqués à 300 caractères**,
ce qui coupe souvent la vraie cause. Exemple réel :
`Erreur création Terraform: 500: Erreur exécution : 500: Erreur exécution : Erreur 'apply': data.aws_vpc.default: Reading...`
→ le message s'arrête avant la ligne `Error:` utile (la cause réelle, ex. `InvalidAMIID.Malformed`
ou `not eligible for Free Tier`, est dans **stderr** qui n'est même pas capturé).

### Solution proposée
- Créer une couche de **traduction d'erreurs** : mapper les erreurs techniques fréquentes
  (AWS `UnauthorizedOperation`, `InvalidAMIID.*`, `not eligible for Free Tier`,
  `InvalidKeyPair.Duplicate`, timeouts) vers un message clair + une **action corrective**.
- **Capturer stderr** de Terraform (aujourd'hui seul stdout est remonté) pour extraire la
  vraie ligne `Error:`, et ne plus tronquer aveuglément à 300 caractères (afficher un résumé
  clair + détail technique repliable).
- Nettoyer les **préfixes dupliqués** `500: Erreur exécution :`.

### Fichiers / composants impactés
- `devops_api/app/services/terraform_service.py` — capturer/retourner `stderr` en plus de `stdout`.
- `devops_api/app/routes/chat_creation_routes.py` (ligne ~233, `str(e)[:300]`) — formatage du message d'erreur.
- Nouveau : `devops_api/app/services/error_translator.py` — table technique → message utilisateur.
- `frontend/src/components/Chat/MessageBubble.tsx` — rendu d'un message d'erreur (résumé + détail repliable).

### Risques techniques
- Sur/filtrage : masquer une info utile en « traduisant » trop agressivement → garder le détail brut accessible (accordéon).
- stderr Terraform volumineux → tronquer **intelligemment** (garder le bloc `│ Error:`).
- Régression sur les autres flux qui consomment le message d'erreur.

### Critères de réussite
- Pour les 5 erreurs les plus fréquentes, l'utilisateur voit **quoi faire** sans lire de stacktrace.
- La cause réelle (issue de stderr) n'est plus jamais coupée.
- Plus aucun préfixe dupliqué `500: … 500: …`.

---

## Axe 2 — Distinction information / action proposée / action exécutée

### Problème identifié
Dans `MessageBubble`, un message bot n'a que `sender` + `text` + `timestamp`. Impossible de
distinguer visuellement « je t'explique », « je te **propose** de créer une instance » et
« l'instance **a été** créée ». L'utilisateur ne sait pas si quelque chose a réellement été exécuté.

### Solution proposée
- Ajouter un **type de message** (`info` | `proposal` | `execution` | `error`), porté par le
  champ `extra` déjà existant des messages (déjà utilisé pour `state`/`error`).
- Décliner le rendu dans `MessageBubble` : couleur/icône/badge par type
  (ex. badge « Action proposée », « ✅ Exécuté », « ⚠️ Erreur »).
- Pour une action proposée, afficher des **boutons d'action** (Confirmer / Annuler) plutôt
  qu'attendre une saisie texte ambiguë.

### Fichiers / composants impactés
- `frontend/src/components/Chat/MessageBubble.tsx` — variant visuel par `type`.
- `frontend/src/components/Chat/ChatWindow.tsx` — passage du `type` au composant.
- `devops_api/app/routes/chat_creation_routes.py` — `send_bot_message(...)` enrichi d'un `type` dans `extra`.
- `devops_api/app/models/` (table `messages`, colonne `extra` JSON déjà présente) — pas de migration si on réutilise `extra`.

### Risques techniques
- Messages historiques sans `type` → prévoir un **fallback** (`info` par défaut).
- Cohérence backend/frontend du vocabulaire des types (contrat partagé).

### Critères de réussite
- À l'écran, on distingue instantanément une info, une proposition et une exécution.
- Une action proposée est confirmable en 1 clic.

---

## Axe 3 — Affichage structuré du plan / des actions Terraform

### Problème identifié
Quand DAC génère de l'infra, l'utilisateur ne voit pas clairement **ce qui va être créé**
(instance, security group, key pair, AMI, type, région). Le plan Terraform existe côté backend
(`build_plan`) mais n'est pas présenté de façon lisible.

### Solution proposée
- Afficher une **carte récapitulative** avant exécution : ressources, type d'instance, région,
  OS/AMI, nombre — issue du plan (`plan_resp`) et du `.tf` généré.
- Après exécution, afficher les **outputs** (IP publique, instance_id) sous forme de tableau,
  avec bouton copier.

### Fichiers / composants impactés
- Nouveau : `frontend/src/components/Chat/PlanSummary.tsx` (carte de plan).
- `frontend/src/components/Chat/ChatWindow.tsx` — insertion de la carte.
- `devops_api/app/routes/generate_routes.py` / `app/services/plan_builder.py` — exposer un résumé
  structuré (déjà calculé : `domain`, `meta.vms`, `provider`).
- `devops_api/app/services/terraform_service.py` — remonter les `outputs` Terraform.

### Risques techniques
- Parsing fragile du `.tf` si on s'y appuie → préférer les **métadonnées du plan** déjà structurées.
- Outputs absents si l'apply échoue → gérer l'état partiel.

### Critères de réussite
- Avant d'exécuter, l'utilisateur voit la liste exacte des ressources et leurs paramètres clés.
- Après exécution, l'IP/instance_id sont affichés et copiables.

---

## Axe 4 — Historique des conversations plus utile

### Problème identifié
La `Sidebar` liste les chats mais l'historique n'aide pas à **reprendre** une création
(pas de statut visible : en cours / réussi / échoué), et les sessions polluées par des essais
ratés ne sont pas distinguables.

### Solution proposée
- Afficher un **statut** par conversation (badge : brouillon / déployé / en erreur) dérivé de
  l'état de session et des exécutions.
- Permettre **renommer / supprimer** une conversation, et un aperçu du dernier message.

### Fichiers / composants impactés
- `frontend/src/components/Chat/Sidebar.tsx` — badges de statut + actions.
- `devops_api/app/routes/chat_metadata_routes.py` — exposer le statut agrégé (session.state + exécutions).

### Risques techniques
- Coût des requêtes si on agrège le statut pour chaque chat → prévoir un champ agrégé ou un endpoint dédié.

### Critères de réussite
- D'un coup d'œil, l'utilisateur retrouve la conversation où son infra a été déployée.
- Suppression/renommage fonctionnels.

---

## Axe 5 — Guidage de saisie & messages système clairs

### Problème identifié
Un prompt vague comme `aws` ne produit **aucune** action et renvoie un message opaque
(« Aucune étape détectée pour cette session. Ajoutez des intents puis reconstruisez le plan »).
L'utilisateur ne sait pas quoi taper.

### Solution proposée
- **Valider/guider** la saisie : si l'intent n'est pas exploitable, répondre avec un exemple concret
  (« Essaie : *crée une instance ubuntu sur aws* ») au lieu d'un message technique.
- Proposer des **suggestions cliquables** (chips) d'exemples de demandes dans `ChatInput`/`EmptyState`.

### Fichiers / composants impactés
- `frontend/src/components/Chat/ChatInput.tsx`, `frontend/src/components/Chat/EmptyState.tsx` — suggestions.
- `devops_api/app/routes/generate_routes.py` (msg « Aucune étape détectée ») et
  `app/services/plan_builder.py` (`_extract_create_specs`) — message d'aide contextuel.

### Risques techniques
- Faux négatifs du parser d'intent (`parse_intent`) → bien tester les formulations FR/EN courantes.

### Critères de réussite
- Un prompt non exploitable renvoie un **exemple actionnable**, pas un message technique.
- Le taux de demandes comprises du premier coup augmente lors de la démo.

---

## Axe 6 — Robustesse réseau & feedback de chargement

### Problème identifié
Les appels axios ont un timeout global de 30 s (`axiosClient.ts`). Une indisponibilité brève
(ou une opération longue) affiche une alerte brute : `Impossible de changer de mode: timeout of 30000ms exceeded`.

### Solution proposée
- Afficher des **états de chargement explicites** (spinner + « Bascule en cours… ») et des
  messages d'erreur réseau traduits/réessayables.
- Distinguer « backend indisponible » de « opération longue » ; bouton **Réessayer**.

### Fichiers / composants impactés
- `frontend/src/components/Chat/ChatModeToggle.tsx` (alertes brutes lignes ~102/164).
- `frontend/src/api/axiosClient.ts` (timeout, intercepteur d'erreurs).
- `frontend/src/components/Chat/ErrorState.tsx`.

### Risques techniques
- Augmenter le timeout sans feedback dégraderait l'UX → coupler avec indicateur de progression.

### Critères de réussite
- Plus d'alerte technique en anglais ; message clair + action « Réessayer ».

---

## Critères de réussite globaux (mapping avec l'énoncé)

| Critère de l'énoncé | Comment on le mesure |
|---|---|
| L'utilisateur comprend mieux ce que DAC propose | Axe 2 (types de message) + Axe 3 (plan structuré) : info / proposition / exécution distinctes et plan lisible avant action. |
| Les réponses sont plus lisibles | Axe 2 + Axe 3 : badges, cartes récapitulatives, outputs en tableau. |
| Les erreurs sont mieux expliquées | Axe 1 : traduction des erreurs + vraie cause (stderr) non tronquée + action corrective. |
| La démonstration montre un vrai gain d'usage | Scénario de démo : créer une instance Ubuntu de bout en bout, montrer plan → exécution → IP, et provoquer une erreur (ex. type non Free Tier) pour montrer le message clair. |

## Priorisation recommandée (effort/impact pour la démo)

1. **Axe 1** (erreurs claires) — impact démo fort, périmètre maîtrisé.
2. **Axe 2** (types de message) — gain de lisibilité immédiat.
3. **Axe 3** (plan structuré) — effet « waouh » en démo.
4. Axes 5, 6, 4 — selon le temps restant.
