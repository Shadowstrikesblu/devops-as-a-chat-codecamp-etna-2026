# Modifications — Axe 4 : Historique des conversations (DÉFÉRÉ)

> Challenge 1 (UX du chat) — Axe 4 **non implémenté** (décision assumée). Date : 2026-06-08

## Problème visé
La `Sidebar` liste les conversations mais sans **statut** (brouillon / déployé / en erreur),
ce qui n'aide pas à retrouver la conversation où une infra a été déployée.

## Pourquoi c'est déféré
- Les données nécessaires ne sont **pas exposées proprement** : `ChatSummary` côté frontend ne
  porte que `id/name/created_at`, et l'endpoint `list_chats` construit un `ChatInfo`
  (`schemas.py`) en **omettant `session_id`** pourtant requis par le schéma — code fragile dont
  la modification risquerait de casser un build/flux qui fonctionne.
- C'est l'axe au **plus faible gain démo** pour le **plus de plomberie** (backend + threading
  frontend `Chat.tsx` → `Sidebar`).
- Priorité donnée à la stabilité des axes 1, 2, 3, 5, 6 déjà livrés et vérifiés.

## Approche recommandée (si repris)
1. **Backend** : fiabiliser `ChatInfo` (rendre `session_id` optionnel ou le passer), puis ajouter
   `mode=c.chat_mode` et un `status` agrégé (dérivé de `session.state` + dernières exécutions)
   dans `list_chats` / `list_all_chats`.
2. **Frontend** : ajouter `mode?` / `status?` (optionnels) à `ChatSummary`, puis afficher un
   petit `Chip` de statut dans `Sidebar.tsx` (ex. « DAC », « Déployé », « Erreur »).
3. Tester le chargement des chats (`Chat.tsx`) pour propager les nouveaux champs.

## État
- [ ] Non implémenté — documenté pour reprise ultérieure.
