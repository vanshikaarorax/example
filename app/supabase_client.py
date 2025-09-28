from supabase import create_client
from .config import Config
supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
# small helpers
def fetch_new_contacts(limit=None):
    q = supabase.table('contacts_to_call').select('*').eq('status',
   'new').lt('attempts', 3)
    if limit:
       q = q.limit(limit)
    return q.execute().data or []
def mark_queued(ids):
    if not ids:
      return
      supabase.table('contacts_to_call').update({'status':'queued'}).in_('id',ids).execute()
def update_contact(id_, payload):
    return supabase.table('contacts_to_call').update(payload).eq('id',
id_).execute()
def find_contact_by_call_sid(call_sid):
# we created index to query metadata->>call_sid
     resp = supabase.table('contacts_to_call').select('*').filter("metadata->>call_sid","=", call_sid).execute()
     items = resp.data or []
     return items[0] if items else None