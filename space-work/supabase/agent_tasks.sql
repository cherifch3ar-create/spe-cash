-- Table des tâches d'agents SPE (accord du directeur du 14/11/2026). N'affecte aucune table existante.
create table if not exists public.agent_tasks (
  id          text primary key,
  agent       text not null,
  tache       text not null,
  offre_no    text,
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
drop policy if exists "lecture agent_tasks si autorise" on public.agent_tasks;
create policy "lecture agent_tasks si autorise" on public.agent_tasks for select to authenticated using (prive.est_autorise());
drop policy if exists "ecriture agent_tasks si autorise" on public.agent_tasks;
create policy "ecriture agent_tasks si autorise" on public.agent_tasks for all to authenticated using (prive.est_autorise()) with check (prive.est_autorise());
drop policy if exists "lecture publique agent_tasks" on public.agent_tasks;
create policy "lecture publique agent_tasks" on public.agent_tasks for select to anon using (true);
-- Les robots GitHub Actions écrivent avec la clé service_role (secret GitHub SUPABASE_SERVICE_KEY), jamais avec la clé publique.
