"""Local Windows speech. SAPI and documented WinRT voices, no cloud APIs."""
from __future__ import annotations
from queue import Queue, Empty
from threading import Thread
import sys
from .winrt_speech import WinRTSpeechWorker, enumerate_winrt_voices
from .guangrong_tts import GuangrongBridge
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
    def __init__(self, on_error=None, on_event=None):
        self._commands = Queue()
        self._on_error = on_error
        self._on_event = on_event
        self._winrt = None  # lazy WinRT player
        self._guangrong = None  # user-installed external DLL only
        self._guangrong_dir = ""
        self._luna_config_path = ""
        self._luna_natural = None
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
                    if self._guangrong is not None:
                        self._guangrong.close()
                    if self._luna_natural is not None:
                        self._luna_natural.close()
                    break
                try:
                    if command == "stop":
                        voice.Speak("", 3)
                        if self._winrt is not None:
                            self._winrt.send("stop")
                        if self._guangrong is not None:
                            self._guangrong.stop()
                        if self._luna_natural is not None:
                            self._luna_natural.stop()
                    elif command == "luna_config":
                        self._luna_config_path = str(arg or "")
                        if self._luna_natural is not None:
                            self._luna_natural.close()
                            self._luna_natural = None
                    elif command == "guangrong_dir":
                        # Keep only a path to the user's OWN installed binary.
                        if self._guangrong is not None:
                            self._guangrong.close()
                            self._guangrong = None
                        self._guangrong_dir = str(arg or "")
                    elif command == "voice" and arg:
                        voice.Speak("", 3)
                        if self._winrt is not None:
                            self._winrt.send("stop")
                        if self._guangrong is not None:
                            self._guangrong.stop()
                        if self._luna_natural is not None:
                            self._luna_natural.stop()
                        if arg == "luna:original":
                            self._mode = "luna"
                            if self._luna_natural is None:
                                self._luna_natural = LunaNaturalBridge(
                                    self._luna_config_path,
                                    on_error=self._on_error, on_event=self._on_event)
                                self._luna_natural.set_rate(self._rate)
                                self._luna_natural.set_volume(self._volume)
                            if self._on_event:
                                self._on_event("已选择 Luna 原始配置的微软自然语音；尚未验证合成")
                        elif arg.startswith("grtts:"):
                            self._mode = "grtts"
                            if self._guangrong is None:
                                self._guangrong = GuangrongBridge(
                                    self._guangrong_dir,
                                    on_error=self._on_error,
                                    on_event=self._on_event)
                                self._guangrong.set_rate(self._rate)
                                self._guangrong.set_volume(self._volume)
                            self._guangrong.select(int(arg[len("grtts:"):]))
                        elif arg.startswith("winrt:"):
                            self._mode = "winrt"
                            if self._winrt is None:
                                self._winrt = WinRTSpeechWorker(on_error=self._on_error, on_event=self._on_event)
                                self._winrt.send("rate", str(self._rate))
                                self._winrt.send("volume", str(self._volume))
                            self._winrt.send("voice", arg[len("winrt:"):])
                            if self._on_event:
                                self._on_event("已选择 Windows Runtime 音色")
                        else:
                            self._mode = "sapi"
                            items = voice.GetVoices()
                            for i in range(items.Count):
                                item = items.Item(i)
                                if item.Id == arg:
                                    voice.Voice = item
                                    if self._on_event:
                                        self._on_event('已选择 SAPI 音色：' + item.GetDescription())
                                    break
                    elif command == "rate" and arg is not None:
                        voice.Rate = max(-10, min(10, int(arg)))
                        self._rate = int(arg)
                        if self._winrt is not None:
                            self._winrt.send("rate", arg)
                        if self._guangrong is not None:
                            self._guangrong.set_rate(int(arg))
                        if self._luna_natural is not None:
                            self._luna_natural.set_rate(int(arg))
                    elif command == "volume" and arg is not None:
                        voice.Volume = max(0, min(100, int(arg)))
                        self._volume = int(arg)
                        if self._winrt is not None:
                            self._winrt.send("volume", arg)
                        if self._guangrong is not None:
                            self._guangrong.set_volume(int(arg))
                        if self._luna_natural is not None:
                            self._luna_natural.set_volume(int(arg))
                    elif command == "speak" and arg:
                        if self._mode == "luna":
                            if self._luna_natural is None:
                                raise RuntimeError("Luna 自然语音尚未初始化")
                            self._luna_natural.speak(str(arg))
                        elif self._mode == "grtts":
                            if self._guangrong is None:
                                raise RuntimeError("广荣 TTS 尚未完成初始化")
                            self._guangrong.speak(str(arg))
                            if self._on_event:
                                self._on_event(f"广荣已接受 {len(arg)} 字语音请求")
                        elif self._mode == "winrt":
                            if self._winrt is not None:
                                self._winrt.send("speak", arg)
                        else:
                            voice.Speak(arg, 3)
                            if self._on_event:
                                self._on_event(f"SAPI 已提交异步朗读请求：{len(arg)} 字（不证明已出声）")
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

    def set_guangrong_directory(self, directory: str):
        self._commands.put(("guangrong_dir", directory))

    def set_luna_config(self, path: str):
        self._commands.put(("luna_config", path))

    def set_rate(self, rate: int):
        self._commands.put(("rate", str(rate)))

    def set_volume(self, volume: int):
        self._commands.put(("volume", str(volume)))

    def shutdown(self):
        self._commands.put(("exit", None))
