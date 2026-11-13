"""V1.2.1-only changes: wheel clearing and native frame style, no OCR rewrite."""
from __future__ import annotations

from types import SimpleNamespace
import time

from game_reader.app import ReaderApp, DEFAULTS, FRAME_COLORS
from game_reader.hover_modes import (WHEEL_UP, WHEEL_DOWN, HOTKEY_FIELDS,
                                     valid_hotkey, hotkey_label, sanitize_hotkeys)
from game_reader.mouse_input import WheelAccumulator


def test_wheel_partial_deltas_up_and_down():
    accumulator = WheelAccumulator()
    assert accumulator.push(60) is None
    assert accumulator.push(60) == WHEEL_UP
    assert accumulator.push(-60) is None
    assert accumulator.push(-60) == WHEEL_DOWN
    assert accumulator.push(30) is None
    assert accumulator.push(-120) == WHEEL_DOWN
    assert valid_hotkey(WHEEL_UP) and valid_hotkey(WHEEL_DOWN)
    assert hotkey_label(WHEEL_UP) == "滚轮向上"
    assert hotkey_label(WHEEL_DOWN) == "滚轮向下"
    assert not valid_hotkey(1) and not valid_hotkey(2)


def test_preserve_user_shortcuts_and_migrate_old_stock_f6(tmp_path, monkeypatch):
    import json
    import game_reader.app as appmod
    p=tmp_path/"settings.json"
    monkeypatch.setattr(appmod, "CONFIG_PATH", p)
    p.write_text(json.dumps({"clear_vk":117,"clear_hotkey_label":"F6",
        "voice":"natural:old","luna_config":"C:/Voice/user.json"}),encoding="utf-8")
    config=appmod.read_settings()
    assert config["clear_vk"] == WHEEL_DOWN
    assert config["clear_hotkey_label"] == "滚轮向下"
    assert config["voice"] == "natural:old"
    assert config["luna_config"] == "C:/Voice/user.json"
    p.write_text(json.dumps({"clear_vk":WHEEL_UP,"clear_hotkey_label":"滚轮向上"}),encoding="utf-8")
    assert appmod.read_settings()["clear_vk"] == WHEEL_UP
    assert len({config[f] for f in HOTKEY_FIELDS}) == len(HOTKEY_FIELDS)
    assert sanitize_hotkeys(DEFAULTS.copy())["clear_vk"] == WHEEL_DOWN


def _fake_app_for_poll(monkeypatch, selected, events):
    import game_reader.app as appmod
    class FakeWheel:
        def __init__(self): self.calls=0
        def drain(self):
            self.calls+=1
            return events if self.calls==1 else []
    class FakeRoot:
        def __init__(self): self.calls=[]
        def after(self, ms, f): self.calls.append(ms)
        def state(self): return "iconic"
    app=ReaderApp.__new__(ReaderApp)
    app.closed=False
    app._choosing_region=False
    app.setting_hotkey=False
    app.mouse_mode="pointer"
    app.settings={**DEFAULTS,"clear_vk":selected}
    app._hotkey_previous={name:False for name in HOTKEY_FIELDS}
    app.wheel_listener=FakeWheel()
    app.root=FakeRoot()
    app.expires_at=None
    app.lines=[]
    app.busy=False
    app._hover_next_due=float("inf")
    app._last_wheel_action_at=0.0
    hits=[]
    app.clear_results=lambda:hits.append("clear")
    app.capture=lambda:hits.append("capture")
    app.status=lambda _:None
    monkeypatch.setattr(appmod, "is_key_down", lambda key:False)
    return app,hits


def test_wheel_down_clears_only_when_assigned(monkeypatch):
    now=time.monotonic()
    app,hits=_fake_app_for_poll(monkeypatch,WHEEL_DOWN,[
        (WHEEL_UP,now),(WHEEL_DOWN,now+0.01),(WHEEL_DOWN,now+0.02)])
    app.poll_input()
    assert hits==["clear"]
    assert app.root.calls==[20]


def test_wheel_up_can_be_chosen_and_down_does_not_clear(monkeypatch):
    now=time.monotonic()
    app,hits=_fake_app_for_poll(monkeypatch,WHEEL_UP,[
        (WHEEL_DOWN,now),(WHEEL_UP,now+0.02)])
    app.poll_input()
    assert hits==["clear"]


def test_wheel_assignment_does_not_trigger_keyboard_repeat(monkeypatch):
    app=ReaderApp.__new__(ReaderApp)
    app.settings=DEFAULTS.copy()
    app._binding_target="clear_vk"
    app._hotkey_previous={}
    app.mouse_mode="pointer"
    app.status=lambda _:None
    app.persist=lambda:None
    app.finish_hotkey=lambda:setattr(app,"_binding_target",None)
    assert app._apply_hotkey(WHEEL_UP) is True
    assert app.settings["clear_vk"] == WHEEL_UP
    assert app.settings["clear_hotkey_label"] == "滚轮向上"
    assert app._binding_target is None


def test_frame_changes_color_and_thickness_without_touching_ocr(monkeypatch):
    import game_reader.overlay as outlines
    class Var:
        def __init__(self,x):self.value=x
        def get(self):return self.value
        def set(self,x):self.value=x
    class Old:
        def __init__(self):self.closed=0
        def close(self):self.closed+=1
    created=[]
    class FakeFrame:
        def __init__(self,**kwargs):
            created.append(kwargs)
    monkeypatch.setattr(outlines,"ClickThroughOutline",FakeFrame)
    app=ReaderApp.__new__(ReaderApp)
    app.settings={"scan_frame_color":"#5CD537","scan_frame_thickness":2}
    app.scan_color_var=Var("蓝色")
    app.scan_thickness_var=Var("7")
    app.scan_frame=Old()
    old=app.scan_frame
    engine=object()
    app.ocr_worker=engine
    events=[]
    app.persist=lambda:events.append("saved")
    app.update_scan_frame=lambda:events.append("updated")
    app.status=lambda s:events.append(s)
    assert app.save_frame_preferences() is True
    assert created == [{"alpha":92,"padding":3,"thickness":7,"color":"#38A8FF"}]
    assert app.settings["scan_frame_color"] == FRAME_COLORS["蓝色"]
    assert app.settings["scan_frame_thickness"] == 7
    assert old.closed==1
    assert app.ocr_worker is engine
    assert events==["saved","updated"]
    assert app.save_frame_preferences() is True
    assert len(created)==1


def test_invalid_frame_input_does_not_rebuild_overlay():
    app=ReaderApp.__new__(ReaderApp)
    app.scan_color_var=SimpleNamespace(get=lambda:"蓝色")
    app.scan_thickness_var=SimpleNamespace(get=lambda:"unknown")
    app.scan_frame=object()
    app.settings={"scan_frame_color":"#5CD537","scan_frame_thickness":2}
    assert app.save_frame_preferences() is False
    assert app.scan_frame is not None


def test_default_frame_preserves_fastest_v121_original_green_and_two_pixels():
    assert DEFAULTS["scan_frame_color"] == "#5CD537"
    assert DEFAULTS["scan_frame_thickness"] == 2
