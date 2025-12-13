import subprocess
import uuid
import os
import pyttsx3

class TTSAdapter:
    def synthesize(self, text: str) -> str:
        base = f"/tmp/tts_{uuid.uuid4()}"
        raw_path = base + ".aiff"   # pyttsx3 produces AIFF reliably
        wav_path = base + ".wav"

        engine = pyttsx3.init()
        engine.save_to_file(text, raw_path)
        engine.runAndWait()

        # 🔁 Convert to REAL WAV (RIFF PCM)
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", raw_path,
                "-ac", "1",
                "-ar", "16000",
                wav_path
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )

        return wav_path
