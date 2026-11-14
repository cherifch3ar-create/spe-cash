-- Table des tâches d'agents SPE (à appliquer SEULEMENT après l'accord du directeur).
-- Ne touche à aucune table existante. Lecture ouverte, écriture réservée aux robots (clé service) et aux comptes autorisés.
create table if not exists public.agent_tasks (
  id          text primary key,                 -- ex. AT-20261114-0001
  agent       text not null,                    -- bureau_etude | affiches | whatsapp | telegram | facebook | superviseur
  tache       text not null,                    -- description courte
  offre_no    text,                             -- numéro TUNEPS si lié à une offre
  statut      text not null default 'a_faire' check (statut in ('a_faire','en_cours','fait','erreur','bloque','annule')),
  priorite    int  not null default 2,
  essais      int  not null default 0,
  resultat    jsonb,
  erreur      text,
  cree_le     timestamptz not null default now(),
  maj         timestamptz not null default now(),
  cree_par    text not null default 'superviseur'
);
create index if not exists agent_tasks_statut_idx on public.agent_tasks (statut, priorite, cree_le);
alter table public.agent_tasks enable row level security;
create policy "lecture agent_tasks si autorise" on public.agent_tasks for select to authenticated using (prive.est_autorise());
create policy "ecriture agent_tasks si autorise" on public.agent_tasks for all to authenticated using (prive.est_autorise()) with check (prive.est_autorise());
-- Les robots GitHub Actions écrivent avec la clé service_role (secret GitHub), jamais avec la clé publique.
