import time
from datetime import datetime, timezone
from twilio.rest import Client as TwilioClient
from twilio.twiml.voice_response import VoiceResponse, Gather

from .config import Config
from .supabase_client import update_contact, supabase
from .sheets import append_call_log_row

# Initialize Twilio client
twilio_client = TwilioClient(Config.TW_SID, Config.TW_TOKEN)


def place_call(contact):
    """
    Place an outbound call via Twilio and update Supabase with call_sid
    and attempts. Wrap in try/except to catch errors on macOS.
    """
    try:
        # Import inside function to avoid fork-related crash on macOS
        from twilio.rest import Client as TwilioClient
        twilio_client = TwilioClient(Config.TW_SID, Config.TW_TOKEN)

        answer_url = f"{Config.BASE_URL}/twiml/answer?contact_id={contact['id']}"
        callback_url = f"{Config.BASE_URL}/webhook/call-status"

        call = twilio_client.calls.create(
            to=contact['phone'],
            from_=Config.TW_FROM,
            url=answer_url,
            status_callback=callback_url,
            status_callback_event=['completed', 'failed', 'no-answer', 'busy'],
            status_callback_method='POST'
        )

        # increment attempts and store call_sid in metadata
        attempts = (contact.get('attempts') or 0) + 1
        md = contact.get('metadata') or {}
        md['call_sid'] = call.sid

        update_contact(contact['id'], {
            'status': 'dialed',
            'attempts': attempts,
            'last_attempt_at': datetime.now(timezone.utc).isoformat(),
            'metadata': md
        })

        print(f"Successfully placed call to {contact['phone']} (SID: {call.sid})")
        return call.sid

    except Exception as e:
        print(f"Error placing call for {contact.get('phone')}: {e}")
        update_contact(contact['id'], {'status': 'failed'})
        return None

def process_call_status(call_sid, call_status, duration, contact):
    """
    Process Twilio call status webhook and append to Google Sheet.
    
    Args:
        call_sid (str): Twilio call SID
        call_status (str): Status returned by Twilio ('completed', 'busy', etc.)
        duration (int/str): Duration of the call in seconds
        contact (dict): Contact dictionary
    """
    # Debug print
    print(f"Processing call_status for {contact.get('phone')}: {call_status}, duration: {duration}")

    disposition = 'no_answer'

    if call_status == 'completed' and int(duration) > 0:
        disposition = 'connected'
    elif call_status in ('busy',):
        disposition = 'busy'
    elif call_status in ('failed', 'no-answer'):
        disposition = 'no_answer'

    # update supabase
    md = contact.get('metadata') or {}
    md['last_status'] = call_status

    update_contact(contact['id'], {
        'status': 'completed' if disposition in ('connected', 'no_answer', 'busy') else 'failed',
        'metadata': md,
        'last_attempt_at': datetime.now(timezone.utc).isoformat()
    })

    # append to Google Sheet
    row = [
        datetime.now(timezone.utc).isoformat(),
        call_sid,
        contact['id'],
        contact.get('name'),
        contact.get('phone'),
        disposition,
        f"Twilio status: {call_status}",
        '',
        duration
    ]
    append_call_log_row(row)
