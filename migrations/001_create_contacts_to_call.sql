CREATE TABLE IF NOT EXISTS public.contacts_to_call (
id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
name text,
phone text,
status text DEFAULT 'new',
attempts integer DEFAULT 0,
last_attempt_at timestamptz,
metadata jsonb DEFAULT '{}'::jsonb
);
-- Index on metadata->call_sid would be helpful if you store call SID there
CREATE INDEX IF NOT EXISTS idx_contacts_metadata_call_sid ON
public.contacts_to_call((metadata->>'call_sid'));