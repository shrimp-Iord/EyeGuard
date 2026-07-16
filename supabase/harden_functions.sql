-- Lock down the alert helper functions (run once in the SQL Editor).
--
-- These are only ever called INTERNALLY — by the eg_on_red trigger and the
-- pg_cron jobs, which run as the function owner and are unaffected by these
-- revokes. But they default to PUBLIC EXECUTE, which means anyone holding the
-- public key can invoke them over the REST API. The dangerous one is
-- eg_send_email: it would let a public-key holder send ARBITRARY email from the
-- EyeGuard sender to the partners (spoofed "all clear", phishing, harassment).
-- eg_daily_digest / eg_check_gone_dark are less severe (spam / no-op) but there's
-- no reason for anyone to call them directly either.

revoke execute on function public.eg_send_email(text, text)
  from public, anon, authenticated, service_role;
revoke execute on function public.eg_check_gone_dark()
  from public, anon, authenticated, service_role;
revoke execute on function public.eg_daily_digest()
  from public, anon, authenticated, service_role;

-- Verify (optional): each should show no execute for anon/authenticated.
--   select proname, proacl from pg_proc
--   where proname in ('eg_send_email','eg_check_gone_dark','eg_daily_digest');
