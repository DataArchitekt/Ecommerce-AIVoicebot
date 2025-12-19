# Reads raw PCM frames from WAV file and streams them over WebSocket.
# WAV header is handled by the frontend audio context.
import wave
from fastapi import WebSocket

async def stream_wav_over_ws(ws: WebSocket, wav_path: str):
    with open(wav_path, "rb") as f:
        wav_bytes = f.read()
        await ws.send_bytes(wav_bytes)
        # Send metadata first
        await ws.send_json({"type": "audio_end"})
        
        with wave.open(wav_path, "rb") as wf:
            while True:
                chunk = wf.readframes(1024)
                if not chunk:
                    break
                await ws.send_bytes(chunk)

    await ws.send_json({"type": "audio_end"})
    

