from flask import Flask, request, Response, jsonify
from twilio.twiml.voice_response import VoiceResponse, Gather
from .config import Config
from .supabase_client import fetch_new_contacts, mark_queued, supabase, find_contact_by_call_sid
from .jobs import place_call, process_call_status
from rq import Queue
from redis import Redis
import json

app = Flask(__name__)

# Redis / RQ setup
redis_conn = Redis.from_url(Config.REDIS_URL)
q = Queue(connection=redis_conn)


@app.route('/start-batch', methods=['POST'])
def start_batch():
    """Fetch new contacts and enqueue outbound calls via RQ."""
    contacts = fetch_new_contacts(limit=Config.CALL_BATCH_SIZE)
    ids = [c['id'] for c in contacts]
    mark_queued(ids)

    for c in contacts:
        q.enqueue(place_call, c)

    return jsonify({'queued': len(contacts)})


@app.route('/twiml/answer', methods=['POST', 'GET'])
def twiml_answer():
    """Initial TwiML response for a contact."""
    contact_id = request.values.get('contact_id')
    resp = supabase.table('contacts_to_call').select('*').eq('id', contact_id).single().execute()
    contact = resp.data

    vr = VoiceResponse()
    vr.say('Hello. This is a short call from Example Company.', voice='alice', language='en-US')
    vr.pause(length=0.4)
    vr.say(f"Am I speaking with {contact.get('name')}? Press 1 for yes, 2 for no.")

    g = Gather(
        num_digits=1,
        action=f"{Config.BASE_URL}/twiml/gather_verify?contact_id={contact_id}",
        method='POST',
        timeout=5
    )
    vr.append(g)
    vr.say('We did not receive an answer. Goodbye.')
    vr.hangup()
    return Response(str(vr), mimetype='application/xml')


@app.route('/twiml/gather_verify', methods=['POST'])
def gather_verify():
    """Handle user input after initial prompt."""
    digit = request.values.get('Digits')
    contact_id = request.values.get('contact_id')

    vr = VoiceResponse()
    if digit == '1':
        vr.say('Great, thank you. I have two quick questions.', voice='alice')
        vr.say('Where do you work? You can record your answer after the beep. Press # when done.')
        vr.record(
            max_length=12,
            finish_on_key='#',
            action=f"{Config.BASE_URL}/twiml/record1?contact_id={contact_id}"
        )
    else:
        vr.say('Sorry we reached the wrong person. Thank you. Goodbye.', voice='alice')
        vr.hangup()

    return Response(str(vr), mimetype='application/xml')


@app.route('/twiml/record1', methods=['POST'])
def record1():
    """Handle first recorded answer and prompt second question."""
    recording_url = request.values.get('RecordingUrl')
    contact_id = request.values.get('contact_id')

    # store recording url into metadata
    resp = supabase.table('contacts_to_call').select('*').eq('id', contact_id).single().execute()
    contact = resp.data
    md = contact.get('metadata') or {}
    md['recording_1'] = recording_url
    supabase.table('contacts_to_call').update({'metadata': md}).eq('id', contact_id).execute()

    vr = VoiceResponse()
    vr.say('Thank you. One last question: what do you do? Please record after the beep and press # when done.')
    vr.record(
        max_length=12,
        finish_on_key='#',
        action=f"{Config.BASE_URL}/twiml/record2?contact_id={contact_id}"
    )

    return Response(str(vr), mimetype='application/xml')


@app.route('/twiml/record2', methods=['POST'])
def record2():
    """Handle second recorded answer and end call."""
    recording_url = request.values.get('RecordingUrl')
    contact_id = request.values.get('contact_id')

    resp = supabase.table('contacts_to_call').select('*').eq('id', contact_id).single().execute()
    contact = resp.data
    md = contact.get('metadata') or {}
    md['recording_2'] = recording_url
    supabase.table('contacts_to_call').update({'metadata': md}).eq('id', contact_id).execute()

    vr = VoiceResponse()
    vr.say('Thanks for your time. Good bye.', voice='alice')
    vr.hangup()

    return Response(str(vr), mimetype='application/xml')


@app.route('/webhook/call-status', methods=['POST'])
def call_status():
    """Twilio webhook to handle call status updates."""
    call_sid = request.values.get('CallSid')
    call_status = request.values.get('CallStatus')
    duration = request.values.get('CallDuration') or '0'

    contact = find_contact_by_call_sid(call_sid)
    if contact:
        q.enqueue(process_call_status, call_sid, call_status, duration, contact)
        return '', 204
    else:
        # fallback: search by phone or ignore
        return '', 204


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
