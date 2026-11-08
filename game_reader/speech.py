"""Local Windows SAPI voice enumeration / interruptible asynchronous TTS.

No network, no protected Windows Narrator package bypass. Voices appear only if
legitimately exposed to SAPI5 by Windows or an installed SAPI adapter.
"""
from __future__ import annotations
from queue import Queue, Empty
from threading import Thread
import sys


def enumerate_sapi_voices() -> list[tuple[str, str]]:
    if sys.platform != "win32":
        return []
    import pythoncom
    import win32com.client
    pythoncom.CoInitialize()
    try:
        speaker = win32com.client.Dispatch("SAPI.SpVoice")
        voices = speaker.GetVoices()
        return [(voices.Item(i).Id, voices.Item(i).GetDescription())
                for i in range(voices.Count)]
    finally:
        pythoncom.CoUninitialize()


class SpeechWorker:
    def __init__(self, on_error=None):
        self._commands: Queue[tuple[str, str | None]] = Queue()
        self._on_error = on_error
        self._thread = Thread(target=self._loop, daemon=True, name="LocalSAPI")
        self._thread.start()

    def _loop(self):
        import pythoncom
        import win32com.client
        pythoncom.CoInitialize()
        try:
            voice = win32com.client.Dispatch("SAPI.SpVoice")
            while True:
                try:
                    command, arg = self._commands.get(timeout=0.05)
                except Empty:
                    pythoncom.PumpWaitingMessages()
                    continue
                if command == "exit":
                    voice.Speak("", 3)
                    break
                try:
                    if command == "stop":
                        voice.Speak("", 3)  # async | purge previous
                    elif command == "voice" and arg:
                        items = voice.GetVoices()
                        for i in range(items.Count):
                            item = items.Item(i)
                            if item.Id == arg:
                                voice.Voice = item
                                break
                    elif command == "rate" and arg is not None:
                        voice.Rate = max(-10, min(10, int(arg)))
                    elif command == "volume" and arg is not None:
                        voice.Volume = max(0, min(100, int(arg)))
                    elif command == "speak" and arg:
                        voice.Speak(arg, 3)  # SAPI async plus purge, non-blocking
                except Exception as ex:
                    if self._on_error:
                        self._on_error(str(ex))
                pythoncom.PumpWaitingMessages()
        except Exception as ex:
            if self._on_error:
                self._on_error(str(ex))
        finally:
            pythoncom.CoUninitialize()

    def speak(self, text: str):
        self._commands.put(("speak", text))

    def stop(self):
        self._commands.put(("stop", None))

    def set_voice(self, voice_id: str):
        self._commands.put(("voice", voice_id))

    def set_rate(self, rate: int):
        self._commands.put(("rate", str(rate)))

    def set_volume(self, volume: int):
        self._commands.put(("volume", str(volume)))

    def shutdown(self):
        self._commands.put(("exit", None))
