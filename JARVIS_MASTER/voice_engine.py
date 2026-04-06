"""Speech recognition + TTS for JARVIS. Degrades gracefully if libs missing."""
from __future__ import annotations
import threading
from typing import Callable
from config import TTS_GENDER, TTS_RATE, TTS_VOLUME, VOICE_ENABLED

try:    import pyttsx3;           _TTS = True
except: _TTS = False
try:    import speech_recognition as sr; _SR = True
except: _SR = False


class VoiceEngine:
    def __init__(self):
        self.enabled = VOICE_ENABLED
        self._engine = None
        self._rec = None
        self._mic = None
        self._lock = threading.Lock()
        if self.enabled:
            self._init_tts()
            self._init_stt()

    def _init_tts(self):
        if not _TTS: return
        try:
            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", TTS_RATE)
            self._engine.setProperty("volume", TTS_VOLUME)
            voices = self._engine.getProperty("voices") or []
            for v in voices:
                n = v.name.lower()
                if TTS_GENDER == "female" and any(k in n for k in ("female","zira","victoria","samantha")):
                    self._engine.setProperty("voice", v.id); return
                if TTS_GENDER == "male" and any(k in n for k in ("male","david","james","alex","fred")):
                    self._engine.setProperty("voice", v.id); return
            if voices: self._engine.setProperty("voice", voices[0].id)
        except Exception as e:
            print(f"  [Voice] TTS init failed: {e}"); self._engine = None

    def _init_stt(self):
        if not _SR: return
        try:
            self._rec = sr.Recognizer()
            self._rec.pause_threshold = 0.8
            self._rec.dynamic_energy_threshold = True
            self._mic = sr.Microphone()
            with self._mic as src:
                self._rec.adjust_for_ambient_noise(src, duration=1)
        except Exception as e:
            print(f"  [Voice] STT init failed: {e}")
            self._rec = self._mic = None

    def speak(self, text: str):
        if not self._engine or not self.enabled: return
        def _run():
            with self._lock:
                try: self._engine.say(text); self._engine.runAndWait()
                except: pass
        threading.Thread(target=_run, daemon=True).start()

    def listen(self):
        if not self._rec or not self._mic or not self.enabled: return None
        try:
            with self._mic as src:
                audio = self._rec.listen(src, timeout=10, phrase_time_limit=15)
            return self._rec.recognize_google(audio).strip()
        except: return None

    def listen_continuous(self, callback: Callable[[str], None]):
        if not self._rec or not self._mic or not self.enabled: return
        def handler(_, audio):
            try:
                t = self._rec.recognize_google(audio)
                if t: callback(t.strip())
            except: pass
        self._stop_fn = self._rec.listen_in_background(self._mic, handler, phrase_time_limit=15)

    def stop_continuous(self):
        fn = getattr(self, "_stop_fn", None)
        if fn: fn(wait_for_stop=False); self._stop_fn = None

    @property
    def stt_available(self): return self._rec is not None
    @property
    def tts_available(self): return self._engine is not None
