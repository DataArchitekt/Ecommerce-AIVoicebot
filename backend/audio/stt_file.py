
import tempfile
from fastapi import APIRouter, UploadFile, File
import subprocess
from backend.observability.metrics import STT_CALL_COUNT

router = APIRouter(prefix="/stt", tags=["stt"])

import whisper

model = whisper.load_model("base") 

def transcribe_audio(wav_path: str):
    STT_CALL_COUNT.inc()   

    result = model.transcribe(
        wav_path,
        language="en",
        temperature=0.0,
        no_speech_threshold=0.2
    )
    return result

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
                "-ar", "16000",  
                "-ac", "1",       
                "-vn",            
                wav_path
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )


    # REAL STT
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
