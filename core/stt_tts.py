import os, io, tempfile
import streamlit as st
from gtts import gTTS
import soundfile as sf
import numpy as np
from faster_whisper import WhisperModel

_model = None
def _load_whisper():
    global _model
    if _model is None:
        _model = WhisperModel("small", compute_type="int8")  # ajuste se necessário
    return _model

def transcribe_bytes(b: bytes) -> str:
    """Transcreve áudio usando Whisper local."""
    try:
        # Carrega o áudio em memória -> PCM 16k mono
        with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
            tmp.write(b); tmp.flush()
            audio, sr = sf.read(tmp.name)
        
        if sr != 16000:
            # resample
            duration = len(audio)/sr
            t = np.linspace(0, duration, int(16000*duration), endpoint=False)
            audio = np.interp(t, np.linspace(0, duration, len(audio), endpoint=False), audio)
            sr = 16000
        
        model = _load_whisper()
        segments, _ = model.transcribe(audio, language="pt")
        text = " ".join([s.text for s in segments])
        return text.strip()
    except Exception as e:
        st.error(f"Erro na transcrição: {e}")
        return "Erro na transcrição do áudio"

def tts_bytes(text: str, use_openai: bool=False, use_azure: bool=False) -> bytes:
    """Converte texto em áudio usando OpenAI TTS, Azure TTS ou gTTS como fallback."""
    
    # 1. Tenta OpenAI TTS primeiro (mais confiável)
    if use_openai:
        try:
            openai_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
            if openai_key:
                from openai import OpenAI
                client = OpenAI(api_key=openai_key)
                
                response = client.audio.speech.create(
                    model="tts-1",
                    voice="nova",  # Voz feminina natural
                    input=text,
                    speed=1.0
                )
                
                return response.content
                
        except Exception as e:
            st.warning(f"OpenAI TTS falhou: {e}, tentando próxima opção")
    
    # 2. Tenta Azure TTS se habilitado  
    if use_azure:
        try:
            azure_key = st.secrets.get("AZURE_SPEECH_KEY", os.getenv("AZURE_SPEECH_KEY"))
            azure_region = st.secrets.get("AZURE_SPEECH_REGION", os.getenv("AZURE_SPEECH_REGION", "brazilsouth"))
            
            if azure_key:
                import azure.cognitiveservices.speech as speechsdk
                
                speech_config = speechsdk.SpeechConfig(
                    subscription=azure_key,
                    region=azure_region
                )
                speech_config.speech_synthesis_voice_name = "pt-BR-FranciscaNeural"
                
                stream = speechsdk.audio.PushAudioOutputStream()
                audio_config = speechsdk.audio.AudioOutputConfig(stream=stream)
                synthesizer = speechsdk.SpeechSynthesizer(speech_config, audio_config)
                
                result = synthesizer.speak_text_async(text).get()
                
                if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                    return result.audio_data
                    
        except Exception as e:
            st.warning(f"Azure TTS falhou: {e}, usando fallback")
    
    # 3. Fallback para gTTS (sempre funciona)
    try:
        fp = io.BytesIO()
        tts = gTTS(text=text, lang="pt", slow=False)
        tts.write_to_fp(fp)
        fp.seek(0)
        return fp.read()
    except Exception as e:
        st.error(f"Erro no gTTS: {e}")
        return b""
