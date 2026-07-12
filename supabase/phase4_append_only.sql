-- Phase 4, Part 1: make the cloud flag record APPEND-ONLY.
--
-- After this, the agent's key (and the partner, and anyone hitting the API) can
-- INSERT and READ flags but can NEVER update or delete them. So the monitored
-- user cannot erase or alter the partner's record — even holding the agent's
-- secret key. Retention still prunes old rows, via a security-definer function
-- that runs as the table owner (postgres), which the revoke doesn't touch.
--
-- Run once in the Supabase SQL Editor. Safe to re-run.

-- 1. Retention as a SECURITY DEFINER function (runs as owner=postgres, so it can
--    still delete after we revoke delete from the API roles below).
create or replace function public.eg_prune_flags() returns void
language sql security definer set search_path = public as $$
  delete from public.flags where flagged_at < now() - interval '7 days';
$$;

select cron.unschedule('eyeguard-retention')
  where exists (select 1 from cron.job where jobname = 'eyeguard-retention');
select cron.schedule('eyeguard-retention', '0 * * * *',
  $$ select public.eg_prune_flags(); $$);

-- 2. Lock the table: no UPDATE or DELETE for any API role (anon = logged-out,
--    authenticated = the partner dashboard, service_role = the agent's key).
--    INSERT stays (agent writes); SELECT stays (RLS still gates partner reads).
revoke update, delete on public.flags from anon, authenticated, service_role;
