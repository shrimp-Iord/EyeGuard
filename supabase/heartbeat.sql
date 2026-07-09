-- Heartbeat / gone-dark: a single-row table the agent pulses while alive.
-- Run once in the Supabase SQL Editor. Safe to re-run.
--
-- The agent upserts last_heartbeat=now every ~60s. A server-side job (added with
-- the alert layer) checks: if now - last_heartbeat > grace AND status='alive'
-- AND not already alerted -> the Mac has gone dark unexpectedly -> email the
-- partners. A clean shutdown/restart sets status='clean_shutdown' so it doesn't
-- false-alarm; each live pulse resets `alerted` so the next outage can fire.

create table if not exists public.device_status (
  id             int primary key default 1,
  last_heartbeat timestamptz,
  status         text default 'unknown',        -- alive | clean_shutdown
  alerted        boolean not null default false, -- gone-dark email already sent?
  updated_at     timestamptz default now(),
  constraint device_single_row check (id = 1)
);
insert into public.device_status (id, status) values (1, 'unknown')
  on conflict (id) do nothing;

alter table public.device_status enable row level security;
drop policy if exists "partner reads status" on public.device_status;
create policy "partner reads status" on public.device_status
  for select to authenticated using (
    auth.uid() in ('0e02aa87-1cd5-4bb6-a263-f51d4e2642b6',   -- partner 1 (father)
                   '1818ac68-7ecf-4e39-a758-8526e496247d')); -- partner 2 (spouse)
