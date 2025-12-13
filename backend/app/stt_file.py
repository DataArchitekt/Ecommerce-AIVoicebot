# backend/app/stt_file.py
import tempfile
from fastapi import APIRouter, UploadFile, File
import subprocess

router = APIRouter(prefix="/stt", tags=["stt"])

@router.post("/file")
async def stt_file(file: UploadFile = File(...)):
    """
    Accepts uploaded audio file (webm/wav),
    converts to wav if needed,
    runs Whisper (or dummy STT),
    returns transcript
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=file.filename) as tmp:
        tmp.write(await file.read())
        input_path = tmp.name

    wav_path = input_path
    if not input_path.endswith(".wav"):
        wav_path = input_path + ".wav"
        subprocess.run(
            ["ffmpeg", "-y", "-i", input_path, wav_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )

    # ---- TEMP: dummy STT (replace with Whisper call if you already have one)
    transcript = "dummy transcript from audio"

    return {
        "text": transcript,
        "audio_path": wav_path
    }