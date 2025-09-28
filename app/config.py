import os
from dotenv import load_dotenv
load_dotenv()
class Config:
     SUPABASE_URL = os.environ['SUPABASE_URL']
     SUPABASE_KEY = os.environ['SUPABASE_SERVICE_KEY']
     TW_SID = os.environ['TWILIO_ACCOUNT_SID']
     TW_TOKEN = os.environ['TWILIO_AUTH_TOKEN']
     TW_FROM = os.environ['TWILIO_FROM_NUMBER']
     BASE_URL = os.environ.get('BASE_URL')
     SHEET_ID = os.environ['GOOGLE_SHEET_ID']
     GOOGLE_SA_JSON = os.environ['GOOGLE_SERVICE_ACCOUNT_JSON_PATH']
     CALL_BATCH_SIZE = int(os.environ.get('CALL_BATCH_SIZE', 5))
     REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
     ATOMS_API_KEY = os.environ.get('ATOMS_API_KEY')
     ATOMS_WS_URL = os.environ.get('ATOMS_WS_URL')