-- Harden the pause-password check (run once in the SQL Editor).
--   1. Only the SECRET key may call it — the public key can no longer be used
--      to brute-force the password.
--   2. A failed-attempt lockout throttles guessing to a crawl.
-- Pair this with a long, random pause password.

-- Lockout state on the single settings row.
alter table public.settings add column if not exists pause_fails int not null default 0;
alter table public.settings add column if not exists pause_locked_until timestamptz;

create or replace function public.eg_check_pause(pw text) returns boolean
language plpgsql security definer set search_path = public, extensions as $$
declare s public.settings; ok boolean;
begin
  select * into s from public.settings where id = 1;

  -- an expired lockout clears itself
  if s.pause_locked_until is not null and now() >= s.pause_locked_until then
    update public.settings set pause_fails = 0, pause_locked_until = null where id = 1;
    s.pause_fails := 0; s.pause_locked_until := null;
  end if;

  -- currently locked out -> refuse without even checking
  if s.pause_locked_until is not null and now() < s.pause_locked_until then
    return false;
  end if;

  ok := s.pause_password_hash is not null
        and s.pause_password_hash = encode(digest(pw, 'sha256'), 'hex');

  if ok then
    update public.settings set pause_fails = 0, pause_locked_until = null where id = 1;
    return true;
  end if;

  -- wrong guess: count it; lock for 15 min after 5 in a row
  update public.settings
    set pause_fails = pause_fails + 1,
        pause_locked_until = case when pause_fails + 1 >= 5
                                  then now() + interval '15 minutes' else null end
    where id = 1;
  return false;
end $$;

-- Only the secret key (service_role) may call it now — not the public key.
revoke execute on function public.eg_check_pause(text) from public, anon, authenticated;
grant  execute on function public.eg_check_pause(text) to service_role;
