"""Use Windows' *documented* local WinRT speech API (no Narrator license bypass).

The Windows Runtime voice list is different from legacy SAPI. Narrator-only
voices not exposed by WinRT cannot be forcibly enabled by this adapter.
"""
from __future__ import annotations
import asyncio
from queue import Empty, Queue
from threading import Thread

def enumerate_winrt_voices() -> list[tuple[str, str]]:
    try:
        from winrt.windows.media.speechsynthesis import SpeechSynthesizer
        return [("winrt:" + v.id, f"Windows 语音 · {v.display_name} ({v.language})")
                for v in SpeechSynthesizer.all_voices]
    except Exception:
        return []


class WinRTSpeechWorker:
    def __init__(self, on_error=None, on_event=None):
        self._q = Queue()
        self._on_error = on_error
        self._on_event = on_event
        self._thread = Thread(target=self._run, daemon=True, name="LocalWinRTSpeech")
        self._thread.start()

    def _run(self):
        try:
            asyncio.run(self._main())
        except Exception as exc:
            if self._on_error:
                self._on_error("WinRT: " + str(exc))

    async def _main(self):
        from winrt.windows.media.speechsynthesis import SpeechSynthesizer
        from winrt.windows.media.core import MediaSource
        from winrt.windows.media.playback import MediaPlayer, MediaPlayerAudioCategory

        synth = SpeechSynthesizer()
        player = MediaPlayer()
        player.audio_category = MediaPlayerAudioCategory.SPEECH
        task = None
        generation = 0

        def cancel_playback():
            nonlocal task, generation
            generation += 1
            if task is not None and not task.done():
                task.cancel()
            task = None
            try:
                player.pause()
                player.source = None
            except Exception:
                pass

        async def synth_and_play(text, expected_generation):
            try:
                stream = await synth.synthesize_text_to_stream_async(text)
                if expected_generation != generation:
                    return
                player.source = MediaSource.create_from_stream(stream, stream.content_type)
                player.play()
                if self._on_event:
                    self._on_event(f"WinRT 已合成并向播放器提交 {len(text)} 字（不证明扬声器已出声）")
                # Speech synthesis succeeding does not prove the output device
                # is playing. Query the WinRT playback state as a separate link.
                await asyncio.sleep(0.28)
                if expected_generation == generation and self._on_event:
                    try:
                        state = str(player.playback_session.playback_state)
                        self._on_event("WinRT 播放器状态：" + state +
                                       "；如仍无声，请检查系统音量混合器和输出设备")
                    except Exception as exc:
                        self._on_event(f"WinRT 无法查询播放状态：{exc}")
            except asyncio.CancelledError:
                pass
            except Exception as exc:
                if self._on_error:
                    self._on_error("WinRT 朗读: " + str(exc))

        while True:
            try:
                command, arg = self._q.get_nowait()
            except Empty:
                await asyncio.sleep(0.035)
                continue
            if command == "exit":
                cancel_playback()
                break
            try:
                if command == "stop":
                    cancel_playback()
                elif command == "voice":
                    cancel_playback()
                    found = next((v for v in SpeechSynthesizer.all_voices if v.id == arg), None)
                    if found is None:
                        raise RuntimeError("已选择的 Windows 语音已不存在，请重新扫描。")
                    synth.voice = found
                elif command == "rate":
                    synth.options.speaking_rate = min(2.5, max(0.5, 1.0 + int(arg) * 0.1))
                elif command == "volume":
                    synth.options.audio_volume = min(1.0, max(0.0, int(arg) / 100))
                elif command == "speak" and arg:
                    cancel_playback()
                    task = asyncio.create_task(synth_and_play(arg, generation))
            except Exception as exc:
                if self._on_error:
                    self._on_error("WinRT: " + str(exc))

    def send(self, command, argument=None):
        self._q.put((command, argument))
