-- Lock all reads to the two partner accounts ONLY (father + spouse).
-- Even if another account ever authenticates, it sees nothing. The agent still
-- writes with the sb_secret key (bypasses RLS); nobody can insert/delete/update
-- via the public API. Run once in the Supabase SQL Editor. Safe to re-run.

drop policy if exists "partner reads flags" on public.flags;
create policy "partner reads flags" on public.flags
  for select to authenticated using (
    auth.uid() in (
      '0e02aa87-1cd5-4bb6-a263-f51d4e2642b6',  -- partner1@example.com
      '1818ac68-7ecf-4e39-a758-8526e496247d'   -- partner2@example.com
    ));

drop policy if exists "partner reads frames" on storage.objects;
create policy "partner reads frames" on storage.objects
  for select to authenticated using (
    bucket_id = 'frames' and auth.uid() in (
      '0e02aa87-1cd5-4bb6-a263-f51d4e2642b6',  -- partner1@example.com
      '1818ac68-7ecf-4e39-a758-8526e496247d'   -- partner2@example.com
    ));
