import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# --------------------------------------------------
# LOAD ENV (CORRECT PATH)
# --------------------------------------------------
ENV_PATH = Path(__file__).resolve().parents[1] / "backend" / ".env"
load_dotenv(dotenv_path=ENV_PATH)

print("🧪 ENV PATH:", ENV_PATH)
print("🧪 OPENAI_API_KEY loaded:", bool(os.getenv("OPENAI_API_KEY")))

# --------------------------------------------------
# CONFIG
# --------------------------------------------------
audio_dir = Path(__file__).resolve().parents[1] / "backend" / "tests" / "audio"
audio_dir.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------
# OPENAI CLIENT (AFTER ENV LOAD)
# --------------------------------------------------
client = OpenAI()

# --------------------------------------------------
# OPENAI TTS (INDIAN-FRIENDLY)
# --------------------------------------------------
def generate_audio(text: str, out_path: Path):
    print(f"🎧 Generating audio for: {text}")

    response = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice="alloy",       # Best neutral/Indian-friendly voice
        input=text,
        speed=0.85           # 🔑 Slow down to avoid kurta → quarter
    )

    response.stream_to_file(out_path)

# --------------------------------------------------
# TEST QUERIES (DEMO FIXTURES)
# --------------------------------------------------
queries = {
    "product_rag.wav": "Show red cotton shirt size medium",
    "ambiguous_query.wav": "I want a shirt",
    "graph_similarity.wav": "Show similar products",
    "low_confidence.wav": "Shirt under five hundred rupees",
    "memory1.wav": "Show me blue cotton shirt",
    "memory2.wav": "What is the price?",
    "faq_query.wav": "How long does delivery take",
    "policy_query.wav": "What is your return policy",
    "order_query.wav": "Where is my order O R D one zero zero two",
    "escalation_query.wav": "I want to talk to a human agent"
}

# --------------------------------------------------
# GENERATE FILES
# --------------------------------------------------
for filename, text in queries.items():
    out_path = audio_dir / filename
    generate_audio(text, out_path)
    print(f"✅ Generated {filename}")
