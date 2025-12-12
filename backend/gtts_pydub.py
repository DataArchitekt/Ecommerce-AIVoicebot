# create files
from gtts import gTTS
from pydub import AudioSegment
texts = [
    ("order_query.wav", "Where is my order one two three four five"),
    ("product_search.wav", "Find blue running shoes size eight"),
    ("order_status.wav", "What is the status of order 12345")
]
import os
os.makedirs("backend/tests/audio", exist_ok=True)
for fn, txt in texts:
    t = gTTS(txt)
    tmp = "backend/tests/audio/"+fn+".mp3"
    t.save(tmp)
    # convert to 16k mono wav
    wav_out = "backend/tests/audio/"+fn
    AudioSegment.from_file(tmp).set_frame_rate(16000).set_channels(1).export(wav_out, format="wav")
    os.remove(tmp)
print("Created:", os.listdir("backend/tests/audio"))