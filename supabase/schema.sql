-- EyeGuard — Supabase schema, Stage 1: the flags pipeline.
-- Run this once in the Supabase SQL Editor (Dashboard -> SQL Editor -> New query).
-- Safe to re-run (idempotent).

create extension if not exists pgcrypto;
create extension if not exists pg_cron;

-- One row per flag the agent uploads.
create table if not exists public.flags (
  id           uuid primary key default gen_random_uuid(),
  created_at   timestamptz not null default now(),
  flagged_at   timestamptz not null,             -- when it was actually flagged
  verdict      text not null check (verdict in ('flagged','alert','clear')),
  is_nudity    boolean not null default false,   -- NudeNet-confirmed exposure
  grade        text,                             -- Likely / Possible / Borderline
  risk         text,                             -- high / neutral / low
  app          text,
  url          text,
  window_title text,
  reason       text,
  score        real,
  image_path   text                              -- path in the 'frames' bucket
);
create index if not exists flags_time_idx on public.flags (flagged_at desc);

-- Row Level Security.
-- The AGENT uploads with the sb_secret key, which BYPASSES RLS entirely — so it
-- can insert without any policy. The PARTNER logs into the dashboard (sb_publish
-- key + auth) and these policies let them only READ. Nobody can insert/delete via
-- the public API — no tampering from the dashboard side.
alter table public.flags enable row level security;
drop policy if exists "partner reads flags" on public.flags;
create policy "partner reads flags" on public.flags
  for select to authenticated using (true);

-- Private bucket for the frame images (blurred reds / clear yellows).
insert into storage.buckets (id, name, public)
  values ('frames', 'frames', false)
  on conflict (id) do nothing;
drop policy if exists "partner reads frames" on storage.objects;
create policy "partner reads frames" on storage.objects
  for select to authenticated using (bucket_id = 'frames');

-- 7-DAY AUTO-WIPE of flag rows (hourly). The images themselves are deleted by
-- the agent via the storage API during its own local retention prune.
select cron.unschedule('eyeguard-retention')
  where exists (select 1 from cron.job where jobname = 'eyeguard-retention');
select cron.schedule('eyeguard-retention', '0 * * * *',
  $$ delete from public.flags where flagged_at < now() - interval '7 days'; $$);
