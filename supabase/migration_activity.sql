-- Migration: allow GREEN activity records (verdict = 'clear', no image).
-- Run once in the Supabase SQL Editor. Safe to re-run.
alter table public.flags drop constraint if exists flags_verdict_check;
alter table public.flags add constraint flags_verdict_check
  check (verdict in ('flagged', 'alert', 'clear'));
