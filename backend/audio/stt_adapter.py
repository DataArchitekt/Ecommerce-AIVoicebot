
"""
STT adapter: transcode incoming audio (webm/opus etc.) to WAV using ffmpeg,
then run Whisper transcription.
"""

import os
import subprocess
import tempfile
import shutil


_HAS_WHISPER = False
_MODEL = None
_MODEL_NAME = os.environ.get("STT_MODEL", "tiny") 

try:
    import whisper
    _HAS_WHISPER = True
except Exception as e:

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

    from shutil import which
    if which("ffmpeg") is None:
        raise RuntimeError("ffmpeg not found on PATH. Install ffmpeg (brew install ffmpeg or apt install ffmpeg).")


def _transcode_to_wav(src_path: str, dst_wav_path: str) -> None:
    """
    Use ffmpeg to transcode input audio to a 16k mono WAV suitable for ASR.
    """
    _ensure_ffmpeg()

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
    Write bytes to a temp file (with given suffix) and call transcribe_file.
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