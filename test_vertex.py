"""Minimal Vertex AI ADC smoke test. Run from D:\\Red_Hawk\\."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / "gemini-hackathon" / ".env")

print("GOOGLE_GENAI_USE_VERTEXAI =", os.environ.get("GOOGLE_GENAI_USE_VERTEXAI"))
print("GOOGLE_CLOUD_PROJECT      =", os.environ.get("GOOGLE_CLOUD_PROJECT"))
print("GOOGLE_CLOUD_LOCATION     =", os.environ.get("GOOGLE_CLOUD_LOCATION"))
print("GOOGLE_API_KEY present    =", bool(os.environ.get("GOOGLE_API_KEY")))
print()

from google import genai

client = genai.Client()
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Reply with exactly: VERTEX_OK",
)
print("Response:", response.text)
