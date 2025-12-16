# backend/app/stt_file.py
import tempfile
from fastapi import APIRouter, UploadFile, File
import subprocess

router = APIRouter(prefix="/stt", tags=["stt"])

import whisper

model = whisper.load_model("base")  # load once at module level

@router.post("/file")
async def stt_file(file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=file.filename) as tmp:
        tmp.write(await file.read())
        input_path = tmp.name

    wav_path = input_path
    if not input_path.endswith(".wav"):
        wav_path = input_path + ".wav"
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i", input_path,
                "-ar", "16000",   # 🔑 force 16 kHz (Whisper expects this)
                "-ac", "1",       # 🔑 force mono
                "-vn",            # 🔑 no video
                wav_path
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )


    # ✅ REAL STT
    result = model.transcribe(
        wav_path,
        language="en",
        temperature=0.0,
        no_speech_threshold=0.2
    )
    
    transcript = result["text"].strip()
    
    if not transcript:
        return {
            "text": "",
            "audio_path": wav_path,
            "error": "No speech detected"
    }
    
    return {
        "text": transcript,
        "audio_path": wav_path
    }
