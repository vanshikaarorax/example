"""
ASGI WebSocket relay that accepts Twilio Media Streams websocket connections
and forwards audio to Atoms websocket.

This is a skeleton and requires filling in details from Atoms docs.

Run with:
    uvicorn app.ws_relay:app --host 0.0.0.0 --port 9000

Flow:
- Twilio -> this WS endpoint (receives base64 pcm frames as JSON)
- Relay audio frames to Atoms websocket using atoms_client.atoms_relay_websocket
- Forward TTS frames from Atoms back to Twilio
- Listen for final event/summary from Atoms and persist to Supabase & Google Sheets
"""
import asyncio
import json
import logging
from websockets import serve
from .config import Config
from .supabase_client import update_contact
from .sheets import append_call_log_row
from .atoms_client import atoms_relay_websocket

logging.basicConfig(level=logging.INFO)

async def handle_twilio_ws(websocket, path):
    """Handle Twilio Media Stream connection.
    Twilio sends JSON messages with event types like 'start','media','stop'.
    Media frames are base64 PCM audio in `media.payload`.
    """
    params = dict()
    # Extract query params from path if present, e.g., /?contact_id=xxx&call_id=yyy
    try:
        qstr = path.split('?', 1)[1]
        for kv in qstr.split('&'):
            k, v = kv.split('=', 1)
            params[k] = v
    except Exception:
        pass

    contact_id = params.get('contact_id')
    call_id = params.get('call_id')

    incoming_queue = asyncio.Queue()
    outgoing_queue = asyncio.Queue()

    # Spawn atoms relay task
    atoms_task = asyncio.create_task(
        atoms_relay_websocket(
            Config.ATOMS_WS_URL,
            incoming_queue,
            outgoing_queue,
            {'contact_id': contact_id, 'call_id': call_id}
        )
    )

    try:
        async for message in websocket:
            # Twilio messages are JSON strings
            obj = json.loads(message)
            event = obj.get('event')

            if event == 'start':
                logging.info('Stream started')
            elif event == 'media':
                # media.payload is base64 audio chunk
                media = obj.get('media', {})
                payload = media.get('payload')
                # push into incoming queue to send to Atoms
                await incoming_queue.put(payload)
            elif event == 'stop':
                logging.info('Stream stopped')
                break

            # Check outgoing queue for atoms responses and send back to Twilio
            while not outgoing_queue.empty():
                out = await outgoing_queue.get()
                await websocket.send(json.dumps(out))

    finally:
        atoms_task.cancel()
        # optionally collect summary from Atoms and persist
        # example: append_call_log_row([...])

async def main():
    async with serve(handle_twilio_ws, '0.0.0.0', 9000):
        await asyncio.Future()  # Run forever

# For running with `python -m app.ws_relay`
if __name__ == '__main__':
    asyncio.run(main())
