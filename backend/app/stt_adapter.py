# backend/app/stt_adapter.py
"""
STT adapter: transcode incoming audio (webm/opus etc.) to WAV using ffmpeg,
then run Whisper transcription.

Provides:
- transcribe_file(path: str) -> str
- transcribe_bytes(data: bytes, src_suffix: str = ".webm") -> str

Notes:
- Requires ffmpeg on PATH.
- Requires 'whisper' python package (openai-whisper).
- Use STT_MODEL env var to pick model (tiny, base, small, medium, large). Default: "tiny".
"""

import os
import subprocess
import tempfile
import shutil
from typing import Optional

# Try to import whisper and lazily load model
_HAS_WHISPER = False
_MODEL = None
_MODEL_NAME = os.environ.get("STT_MODEL", "tiny")  # change to "base" etc if you prefer

try:
    import whisper
    _HAS_WHISPER = True
except Exception as e:
    # Will fall back to placeholder transcript if whisper not available
    print("Warning: whisper import failed:", e)
    _HAS_WHISPER = False
    _MODEL = None


def _get_model():
    global _MODEL, _HAS_WHISPER, _MODEL_NAME
    if not _HAS_WHISPER:
        raise RuntimeError("Whisper not installed. Install `openai-whisper` to enable transcription.")
    if _MODEL is None:
        print(f"Loading Whisper model '{_MODEL_NAME}' (this may take a while)...")
        _MODEL = whisper.load_model(_MODEL_NAME)
    return _MODEL


def _ensure_ffmpeg():
    """Raise an error if ffmpeg is not on PATH."""
    from shutil import which
    if which("ffmpeg") is None:
        raise RuntimeError("ffmpeg not found on PATH. Install ffmpeg (brew install ffmpeg or apt install ffmpeg).")


def _transcode_to_wav(src_path: str, dst_wav_path: str) -> None:
    """
    Use ffmpeg to transcode input audio to a 16k mono WAV suitable for ASR.
    Raises subprocess.CalledProcessError on failure.
    """
    _ensure_ffmpeg()
    # ffmpeg command:
    # -y overwrite, -i input, -ar 16000 sample rate, -ac 1 mono, -vn disable video
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", src_path,
        "-ar", "16000",
        "-ac", "1",
        "-vn",
        dst_wav_path
    ]
    subprocess.run(cmd, check=True)


def transcribe_file(path: str) -> str:
    """
    Transcribe an audio file (webm/opus, wav, etc.) and return transcript string.
    This will transcode to WAV in a temp file and then call Whisper.
    """
    # If whisper not installed, return placeholder so rest of app can proceed
    if not _HAS_WHISPER:
        return "TRANSCRIPT_PLACEHOLDER (whisper not installed)"

    # Create temp dir to hold the intermediate wav
    tempdir = tempfile.mkdtemp(prefix="stt_")
    try:
        base = os.path.basename(path)
        wav_path = os.path.join(tempdir, base + ".wav")
        # Transcode (ffmpeg)
        try:
            _transcode_to_wav(path, wav_path)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"ffmpeg failed to transcode {path}: {e}")

        # Load model and transcribe
        model = _get_model()
        # use model.transcribe which returns dict with 'text'
        result = model.transcribe(wav_path)
        text = result.get("text", "").strip() if isinstance(result, dict) else str(result).strip()
        return text
    finally:
        try:
            shutil.rmtree(tempdir)
        except Exception:
            pass


def transcribe_bytes(data: bytes, src_suffix: str = ".webm") -> str:
    """
    Convenience: write bytes to a temp file (with given suffix) and call transcribe_file.
    """
    tempdir = tempfile.mkdtemp(prefix="stt_bytes_")
    try:
        src_path = os.path.join(tempdir, "input" + src_suffix)
        with open(src_path, "wb") as f:
            f.write(data)
        return transcribe_file(src_path)
    finally:
        try:
            shutil.rmtree(tempdir)
        except Exception:
            pass