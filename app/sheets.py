from google.oauth2 import service_account
from googleapiclient.discovery import build
from .config import Config

def sheets_service():
    creds = service_account.Credentials.from_service_account_file(
        Config.GOOGLE_SA_JSON,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    return build('sheets', 'v4', credentials=creds)

def append_call_log_row(row_values):
    svc = sheets_service()
    body = {'values': [row_values]}
    svc.spreadsheets().values().append(
        spreadsheetId=Config.SHEET_ID,
        range='call_log!A1',
        valueInputOption='USER_ENTERED',
        body=body
    ).execute()
