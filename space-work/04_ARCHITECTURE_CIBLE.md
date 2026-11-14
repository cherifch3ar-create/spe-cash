# 04 — Architecture cible : qui fait quoi, quand, et ce que ça coûte

```
 TUNEPS (public) ──► Robot relevé (2 h) ──► offres (Supabase) ──► Robot pièces (1 h) ──► stockage appels-offres
                                                   │
                                                   ▼
                                     Robot affiches (1 h, Pillow, images métier)
                                                   │ brouillon
                                                   ▼
                          Centre d'approbation (Workspace) ── OK humain ou auto après 2 h
                                                   │
                                                   ▼
                                 file_whatsapp / file_telegram / file_facebook
                                                   │
                 ┌─────────────────────────────────┼──────────────────────────────┐
                 ▼                                 ▼                              ▼
   Robot WhatsApp Web (machine 24 h/24)   Robot Telegram (GitHub Actions)   Robot Facebook (Graph API)
                 └──────────────── events + agent_tasks (journal unique) ◄────────┘
                                                   ▲
                 Superviseur (robot, 1 h) : relance, 3 essais, « bloqué », rapport
                                                   ▲
   Claude (Sonnet, 2×/jour, 15 min) : Bureau d'étude sur les offres nouvelles avec pièces → fiche d'étude
   Claude (1×/jour) : rapport du matin au directeur (push)
```

| Bloc | Type | Où | Fréquence | Coût | État |
|---|---|---|---|---|---|
| Relevé TUNEPS | robot | cloud (déjà) | 2 h | 0 | marche |
| Pièces TUNEPS | robot | GitHub Actions | 1 h | 0 | fusionné 14/11 |
| Veille Google | robot | GitHub Actions | 3 h | 0 | marche |
| Affiches | robot | GitHub Actions | 1 h | 0 | à écrire (OK ?) |
| Superviseur | robot | GitHub Actions | 1 h | 0 | à écrire (OK ?) |
| WhatsApp groupes | robot | machine 24 h/24 | 10 min | 0 (+ SIM dédiée) | à déplacer |
| Telegram | robot | GitHub Actions | 10 min | 0 | à écrire |
| Facebook | robot | GitHub Actions | 1 h | 0 | à écrire (jeton page) |
| Bureau d'étude | agent IA | tâche planifiée Claude (Sonnet) | 07:00, 13:00 | usage Claude, faible | à régler |
| Rapport du matin | agent IA | tâche planifiée Claude | 08:47 | faible | désactivé le 12/11, à réactiver allégé |
| Khalil, Mounir, Ménage | agents IA | tâches planifiées Claude | quotidien | Khalil = cher (Fable 5.2) | à alléger |

Statuts d'une tâche `agent_tasks` : `a_faire` → `en_cours` → `fait` | `erreur` (essais +1, max 3) → `bloque` (le superviseur prévient le directeur).
Règle : les agents ne se parlent pas entre eux ; tout passe par la table et le journal `events`.
