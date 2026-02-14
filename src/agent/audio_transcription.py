import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def audio_transcription(audio_base64: str) -> str:
    import base64
    
    # Decodifica audio
    audio_data = base64.b64decode(audio_base64)
    
    # Transcreve direto (sem salvar arquivo)
    response = client.audio.transcriptions.create(
        model="whisper-1",
        file=("audio.mp3", audio_data),
        language="pt"
    )
    
    return response.text
