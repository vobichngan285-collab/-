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
        # Media uses the default multimedia endpoint that games normally use.
        player.audio_category = MediaPlayerAudioCategory.MEDIA
        player.volume = 1.0
        player.is_muted = False
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
            ended_token = None
            failed_token = None
            try:
                # Hold the SpeechSynthesisStream until MediaEnded or stop;
                # releasing it as soon as player.play() is called can produce
                # an ended/empty media source on some desktop environments.
                stream = await synth.synthesize_text_to_stream_async(text)
                if expected_generation != generation:
                    return
                loop = asyncio.get_running_loop()
                finished = asyncio.Event()

                def on_ended(_sender, _args):
                    loop.call_soon_threadsafe(finished.set)

                def on_failed(_sender, args):
                    if self._on_error:
                        try:
                            detail = str(args.error_message)
                        except Exception:
                            detail = "未能读取 MediaFailed 错误"
                        self._on_error("WinRT 媒体播放失败：" + detail)
                    loop.call_soon_threadsafe(finished.set)

                ended_token = player.add_media_ended(on_ended)
                failed_token = player.add_media_failed(on_failed)
                player.source = MediaSource.create_from_stream(stream, stream.content_type)
                player.play()
                if self._on_event:
                    self._on_event(f"WinRT 已生成语音并请求播放 {len(text)} 字")
                await asyncio.sleep(0.35)
                if expected_generation == generation and self._on_event:
                    self._on_event(
                        "WinRT 播放器状态：" +
                        str(player.playback_session.playback_state) +
                        "，音量：" + str(player.volume))
                await asyncio.wait_for(finished.wait(), timeout=90)
            except asyncio.CancelledError:
                pass
            except asyncio.TimeoutError:
                if self._on_error:
                    self._on_error("WinRT 播放 90 秒仍未结束，已重置播放器")
            except Exception as exc:
                if self._on_error:
                    self._on_error("WinRT 朗读: " + str(exc))
            finally:
                if ended_token is not None:
                    try:
                        player.remove_media_ended(ended_token)
                    except Exception:
                        pass
                if failed_token is not None:
                    try:
                        player.remove_media_failed(failed_token)
                    except Exception:
                        pass

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
