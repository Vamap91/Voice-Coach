import os, io, tempfile
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

def tts_bytes(text: str, use_azure: bool=False) -> bytes:
    if use_azure and os.getenv("AZURE_SPEECH_KEY"):
        try:
            import azure.cognitiveservices.speech as speechsdk
            speech_config = speechsdk.SpeechConfig(
                subscription=os.getenv("AZURE_SPEECH_KEY"),
                region=os.getenv("AZURE_SPEECH_REGION","brazilsouth"))
            speech_config.speech_synthesis_voice_name = "pt-BR-FranciscaNeural"
            stream = speechsdk.audio.PushAudioOutputStream()
            audio_config = speechsdk.audio.AudioOutputConfig(stream=stream)
            synthesizer = speechsdk.SpeechSynthesizer(speech_config, audio_config)
            result = synthesizer.speak_text_async(text).get()
            # Azure SDK já envia para stream; para simplificar no MVP usamos gTTS como retorno direto
        except Exception:
            pass
    # Fallback gTTS
    fp = io.BytesIO()
    gTTS(text=text, lang="pt").write_to_fp(fp)
    fp.seek(0)
    return fp.read()
