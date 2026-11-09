"""Local Windows speech. SAPI and documented WinRT voices, no cloud APIs."""
from __future__ import annotations
from queue import Queue, Empty
from threading import Thread
import sys
from .winrt_speech import WinRTSpeechWorker, enumerate_winrt_voices
from .luna_bridge import LunaNaturalBridge


def enumerate_sapi_voices() -> list[tuple[str, str]]:
    """Expose only genuine, installed and callable SAPI + WinRT voices."""
    if sys.platform != "win32":
        return []
    voices = []
    import pythoncom
    import win32com.client
    pythoncom.CoInitialize()
    try:
        speaker = win32com.client.Dispatch("SAPI.SpVoice")
        items = speaker.GetVoices()
        voices.extend((items.Item(i).Id, items.Item(i).GetDescription())
                      for i in range(items.Count))
    finally:
        pythoncom.CoUninitialize()
    ids = {id_ for id_, _ in voices}
    for entry in enumerate_winrt_voices():
        if entry[0] not in ids:
            voices.append(entry)
    return voices


class SpeechWorker:
    def __init__(self, on_error=None):
        self._commands = Queue()
        self._on_error = on_error
        self._winrt = None  # create WinRT media player only if WinRT voice is selected
        self._luna_natural = None
        self._luna_config_path = ""
        self._rate = 0
        self._volume = 100
        self._mode = "sapi"
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
                    if self._winrt is not None:
                        self._winrt.send("exit")
                    if self._luna_natural is not None:
                        self._luna_natural.close()
                    break
                try:
                    if command == "stop":
                        voice.Speak("", 3)
                        if self._winrt is not None:
                            self._winrt.send("stop")
                        if self._luna_natural is not None:
                            self._luna_natural.stop()
                    elif command == "luna_config":
                        self._luna_config_path = str(arg or "")
                        if self._luna_natural is not None:
                            self._luna_natural.close()
                            self._luna_natural = None
                    elif command == "voice" and arg:
                        voice.Speak("", 3)
                        if self._winrt is not None:
                            self._winrt.send("stop")
                        if self._luna_natural is not None:
                            self._luna_natural.stop()
                        if arg.startswith("natural:"):
                            self._mode = "natural"
                            if self._luna_natural is not None:
                                self._luna_natural.close()
                            self._luna_natural = LunaNaturalBridge(
                                self._luna_config_path, arg, on_error=self._on_error)
                            self._luna_natural.set_rate(self._rate)
                            self._luna_natural.set_volume(self._volume)
                        elif arg.startswith("winrt:"):
                            self._mode = "winrt"
                            if self._winrt is None:
                                self._winrt = WinRTSpeechWorker(on_error=self._on_error)
                                self._winrt.send("rate", str(self._rate))
                                self._winrt.send("volume", str(self._volume))
                            self._winrt.send("voice", arg[len("winrt:"):])
                        else:
                            self._mode = "sapi"
                            items = voice.GetVoices()
                            for i in range(items.Count):
                                item = items.Item(i)
                                if item.Id == arg:
                                    voice.Voice = item
                                    break
                    elif command == "rate" and arg is not None:
                        voice.Rate = max(-10, min(10, int(arg)))
                        self._rate = int(arg)
                        if self._winrt is not None:
                            self._winrt.send("rate", arg)
                        if self._luna_natural is not None:
                            self._luna_natural.set_rate(int(arg))
                    elif command == "volume" and arg is not None:
                        voice.Volume = max(0, min(100, int(arg)))
                        self._volume = int(arg)
                        if self._winrt is not None:
                            self._winrt.send("volume", arg)
                        if self._luna_natural is not None:
                            self._luna_natural.set_volume(self._volume)
                    elif command == "speak" and arg:
                        if self._mode == "natural":
                            if self._luna_natural is None:
                                raise RuntimeError("尚未初始化系统自然语音")
                            self._luna_natural.speak(str(arg))
                        elif self._mode == "winrt":
                            if self._winrt is not None:
                                self._winrt.send("speak", arg)
                        else:
                            voice.Speak(arg, 3)
                except Exception as exc:
                    if self._on_error:
                        self._on_error(str(exc))
                pythoncom.PumpWaitingMessages()
        except Exception as exc:
            if self._on_error:
                self._on_error(str(exc))
        finally:
            pythoncom.CoUninitialize()

    def speak(self, text: str):
        self._commands.put(("speak", text))

    def stop(self):
        self._commands.put(("stop", None))

    def set_voice(self, voice_id: str):
        self._commands.put(("voice", voice_id))

    def set_luna_config(self, config_path: str):
        self._commands.put(("luna_config", config_path))

    def set_rate(self, rate: int):
        self._commands.put(("rate", str(rate)))

    def set_volume(self, volume: int):
        self._commands.put(("volume", str(volume)))

    def shutdown(self):
        self._commands.put(("exit", None))
