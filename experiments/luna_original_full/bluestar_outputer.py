"""Minimal Blue Star I/O PLUGIN for the untouched official LunaTranslator v12.1.3.9.

THIS FILE IS NOT AN OCR ALGORITHM. The actual work is performed EXCLUSIVELY by
the unmodified upstream imageCutEx(), ocr_run(), ocrtext.getresauto(), and
CVUtils.dll. Control is restricted to 127.0.0.1. No photos or OCR text are saved.
Original full source: HIllya51/LunaTranslator@84677faeaa1e61bd7dd00b820090e9d2fe6c5142.
"""
import json
import socket
import threading
from textio.textoutput.outputerbase import Base

_CONTROL = ("127.0.0.1", 29380)
_TEXT = ("127.0.0.1", 29381)
_MAX_REQUEST = 4096


def _bounded_region(raw):
    if not isinstance(raw, (list, tuple)) or len(raw) != 4:
        raise ValueError("Expected four screen coordinates")
    if not all(isinstance(x, int) and not isinstance(x, bool) for x in raw):
        raise ValueError("Coordinates must be integers")
    left, top, right, bottom = raw
    if right <= left or bottom <= top or (right-left)*(bottom-top) > 40_000_000:
        raise ValueError("Invalid capture region")
    return left, top, right, bottom


class _ChangeRegion:
    """Tiny Qt-thread dispatcher; all actual OCR/region functions remain upstream."""
    def __init__(self):
        from qtsymbols import QObject, pyqtSignal, Qt, QApplication
        class Dispatcher(QObject):
            change = pyqtSignal(object)
            def __init__(self):
                super().__init__()
                self.change.connect(self.apply, Qt.ConnectionType.QueuedConnection)
            def apply(self, payload):
                try:
                    import gobject
                    from qtsymbols import QRect
                    action = payload["action"]
                    if action == "region":
                        # ORIGINAL ocrtext setup, capture, scheduling and OCR.
                        from textio.textsource.ocrtext import ocrtext
                        if not isinstance(gobject.base.textsource, ocrtext):
                            gobject.base.starttextsource("ocr")
                        source = gobject.base.textsource
                        if not isinstance(source, ocrtext):
                            raise RuntimeError("Official Luna OCR source did not start")
                        left, top, right, bottom = payload["box"]
                        source.clearrange()
                        source.newrangeadjustor()
                        source.setrect(QRect(left, top, right-left, bottom-top))
                        payload["ok"] = True
                    elif action == "clear":
                        source = gobject.base.textsource
                        if source is not None and hasattr(source, "clearrange"):
                            source.clearrange()
                        payload["ok"] = True
                    elif action == "pause":
                        source = gobject.base.textsource
                        if source is not None and hasattr(source, "pause_recognition"):
                            source.pause_recognition()
                        payload["ok"] = True
                    elif action == "resume":
                        source = gobject.base.textsource
                        if source is not None and hasattr(source, "resume_recognition"):
                            source.resume_recognition()
                        payload["ok"] = True
                    elif action == "border":
                        source = gobject.base.textsource
                        if source is not None and hasattr(source, "showhiderangeui"):
                            source.showhiderangeui(bool(payload["visible"]))
                        payload["ok"] = True
                    else:
                        raise ValueError("Unknown action")
                except Exception as exc:
                    payload["error"] = type(exc).__name__ + ": " + str(exc)[:260]
                finally:
                    payload["done"].set()

        self._dispatcher = Dispatcher()
        app = QApplication.instance()
        if app is None:
            raise RuntimeError("Luna original Qt app has not started")
        self._dispatcher.moveToThread(app.thread())

    def request(self, action, **kw):
        payload = dict(action=action, done=threading.Event(), **kw)
        self._dispatcher.change.emit(payload)
        if not payload["done"].wait(5.0):
            raise TimeoutError("Luna original Qt UI did not answer")
        if payload.get("error"):
            raise RuntimeError(payload["error"])
        return bool(payload.get("ok"))


class Outputer(Base):
    def init(self):
        self._udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._dispatcher = _ChangeRegion()
        # Original source constructs this Outputer using its unchanged
        # BASEOBJECT.startoutputer() discovery mechanism.
        threading.Thread(target=self._serve, daemon=True,
                         name="BlueStarOriginalLunaIO").start()

    def dispatch(self, text, isorigin):
        if not isorigin or not isinstance(text, str) or not text.strip():
            return
        try:
            message = json.dumps({"kind": "original_ocr_text", "text": text},
                                 ensure_ascii=False).encode("utf-8")
            if len(message) <= 60_000:
                self._udp.sendto(message, _TEXT)
        except OSError:
            pass  # Don't block the ORIGINAL author's recognition loop.

    def _serve(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
                server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                server.bind(_CONTROL)  # loopback ONLY, unlike Luna's HTTP server
                server.listen(2)
                while True:
                    client, _ = server.accept()
                    threading.Thread(target=self._handle, args=(client,),
                                     daemon=True).start()
        except OSError:
            return

    def _handle(self, client):
        with client:
            client.settimeout(12.0)
            try:
                data = bytearray()
                while len(data) <= _MAX_REQUEST:
                    chunk = client.recv(min(4096, _MAX_REQUEST + 1 - len(data)))
                    if not chunk:
                        break
                    data.extend(chunk)
                    if b"\n" in data:
                        break
                if len(data) > _MAX_REQUEST or b"\n" not in data:
                    raise ValueError("Bad request")
                request = json.loads(data.split(b"\n", 1)[0].decode("utf-8"))
                action = request.get("action")
                if action == "ping":
                    result = {"ok": True, "implementation": "LunaTranslator original OCR v12.1.3.9"}
                elif action == "ocr":
                    # CORE IS VERBATIM UPSTREAM. No custom screenshot, OCR model,
                    # image analysis or character filtering lives in this plugin.
                    from textio.textsource.ocrtext import imageCutEx
                    from myutils.ocrutil import ocr_run
                    from qtsymbols import QRect
                    l,t,r,b = _bounded_region(request.get("box"))
                    image = imageCutEx(None, QRect(l,t,r-l,b-t))
                    if image.isNull():
                        raise RuntimeError("Original Luna imageCutEx returned empty image")
                    parsed = ocr_run(image)
                    result = {"ok": not bool(parsed.error), "result": parsed.json}
                elif action in ("region", "clear", "pause", "resume", "border"):
                    if action == "region":
                        kw = {"box": _bounded_region(request.get("box"))}
                    elif action == "border":
                        kw = {"visible": bool(request.get("visible"))}
                    else:
                        kw = {}
                    result = {"ok": self._dispatcher.request(action, **kw)}
                else:
                    raise ValueError("Unsupported control action")
            except Exception as exc:
                result = {"ok": False, "error": type(exc).__name__ + ": " + str(exc)[:300]}
            try:
                client.sendall(json.dumps(result, ensure_ascii=False).encode("utf-8") + b"\n")
            except OSError:
                pass
