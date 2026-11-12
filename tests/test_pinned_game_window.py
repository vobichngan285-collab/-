"""Current foreground capture only; no sticky HWND, GDI, or guessing."""
from PIL import Image
from game_reader.app import ReaderApp
from game_reader import app as appmod
from game_reader import win_screen


def test_mode_follows_current_foreground(monkeypatch):
    foreground = [111]
    monkeypatch.setattr(appmod, "foreground_window_id", lambda: foreground[0])
    app = ReaderApp.__new__(ReaderApp)
    assert app._game_capture_target() == 111
    foreground[0] = 222
    assert app._game_capture_target() == 222
    assert not app._game_capture_active(111)
    assert app._game_capture_active(222)


def test_current_focus_capture_uses_fresh_desktop_pixels(monkeypatch):
    monkeypatch.setattr(win_screen, "monitor_rect_at_cursor", lambda: (0, 0, 640, 480))
    monkeypatch.setattr(win_screen, "game_client_rect",
                        lambda hwnd: (10, 20, 500, 400) if hwnd == 111 else (35, 40, 270, 230))
    seen = []
    def grab(**kwargs):
        seen.append(kwargs)
        box = kwargs["bbox"]
        return Image.new("RGB", (box[2]-box[0],box[3]-box[1]))
    monkeypatch.setattr(win_screen.ImageGrab, "grab", grab)
    first, a = win_screen.grab_current_monitor(111)
    second, b = win_screen.grab_current_monitor(222)
    assert (a,first.size) == ((10,20),(490,380))
    assert (b,second.size) == ((35,40),(235,190))
    assert seen == [
        {"bbox":(10,20,500,400),"all_screens":True},
        {"bbox":(35,40,270,230),"all_screens":True}
    ]


def test_region_and_hover_never_submit_full_screen_image(monkeypatch):
    box=(200,300,520,470)
    seen=[]
    monkeypatch.setattr(win_screen.ImageGrab,"grab",
                        lambda **kwargs: seen.append(kwargs) or Image.new("RGB",(320,170)))
    result=win_screen.grab_game_rect(box)
    assert result.size == (320,170)
    assert seen == [{"bbox":box,"all_screens":True}]
