-- Phase 4b — three hardenings that shrink the "silent bypass" surface.
--   1. blind alert  — device_status carries screen health; alert if it goes blind
--   2. storage lockdown — agent key can no longer delete/overwrite review frames;
--      image retention moves server-side
--   (3. truncation detection is agent-side only — no SQL)
-- Run once in the SQL Editor.

-- ===== 1. Blind detection =====
alter table public.device_status add column if not exists screen_ok       boolean;
alter table public.device_status add column if not exists frames_analyzed bigint;
alter table public.device_status add column if not exists blind_alerted    boolean
  not null default false;

-- gone-dark check now ALSO fires when the agent is alive + reporting recently
-- but says it can't see the screen (Screen Recording revoked / capture frozen).
create or replace function public.eg_check_gone_dark() returns void
language plpgsql security definer set search_path = public as $$
declare d public.device_status;
begin
  select * into d from public.device_status where id = 1;
  if d.last_heartbeat is null then return; end if;

  -- (a) went dark: no heartbeat for 3+ minutes
  if d.status = 'alive' and not d.alerted
     and now() - d.last_heartbeat > interval '3 minutes' then
    perform public.eg_send_email(
      '⚫ EyeGuard — monitoring went dark',
      format('<p><b>EyeGuard stopped reporting.</b></p><p>Last seen %s ago. The Mac '
          || 'may be off, offline, or the monitor was stopped. If unexpected, '
          || 'check in.</p>', age(now(), d.last_heartbeat)));
    update public.device_status set alerted = true where id = 1;
  end if;

  -- (b) went blind: alive + fresh heartbeat, but no view of the screen
  if d.status = 'alive' and now() - d.last_heartbeat <= interval '3 minutes' then
    if d.screen_ok is false and not d.blind_alerted then
      perform public.eg_send_email(
        '🚨 EyeGuard — lost view of the screen',
        '<p><b>EyeGuard is running but can no longer see the screen.</b></p>'
        || '<p>Screen Recording may have been revoked, the display switched, or '
        || 'capture frozen. Detection is NOT working until this is resolved.</p>');
      update public.device_status set blind_alerted = true where id = 1;
    elsif d.screen_ok is not false and d.blind_alerted then
      update public.device_status set blind_alerted = false where id = 1;  -- recovered
    end if;
  end if;
end $$;

-- ===== 2. Storage lockdown =====
-- The agent uploads (INSERT) review frames but must not be able to DELETE or
-- OVERWRITE them, so it can't silently blank the evidence.
revoke delete, update on storage.objects from anon, authenticated, service_role;

-- Image retention now runs server-side (agent can no longer prune). Deletes the
-- object records older than 7 days, hourly, as postgres.
create extension if not exists pg_cron;
select cron.unschedule('eyeguard-image-retention')
  where exists (select 1 from cron.job where jobname = 'eyeguard-image-retention');
select cron.schedule('eyeguard-image-retention', '7 * * * *',
  $$ delete from storage.objects
     where bucket_id = 'frames' and created_at < now() - interval '7 days'; $$);
