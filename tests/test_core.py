from game_reader.core import OCRLine, HoverTracker, hit_test, parse_paddle_result


def line(t, x1, y1, x2, y2):
    return OCRLine(t, x1, y1, x2, y2)


def test_ocr_parse_offsets_and_sort():
    result = {'res': {'rec_texts': ['后', '先', '不可信'],
                      'rec_boxes': [[10, 50, 80, 70], [10, 2, 55, 23], [80, 50, 130, 70]],
                      'rec_scores': [.9, .99, .1]}}
    a = parse_paddle_result(result, -100, 300)
    assert [i.text for i in a] == ['先', '后']
    assert (a[0].left, a[0].top, a[0].right, a[0].bottom) == (-90, 302, -45, 323)


def test_ocr_bad_shape_raises():
    try:
        parse_paddle_result({'rec_texts': ['abc'], 'rec_boxes': []})
    except ValueError:
        pass
    else:
        assert False


def test_empty_and_point_polygon():
    assert parse_paddle_result({'rec_texts': [], 'rec_boxes': []}) == []
    a = parse_paddle_result({'rec_texts': ['菜单'], 'rec_boxes': [[[10, 10], [20, 10], [20, 30], [10, 30]]]})
    assert a[0].right == 20


def test_hit_nearest_when_overlapping():
    a = line('第一行', 100, 100, 220, 115)
    b = line('第二行', 100, 125, 220, 145)
    assert hit_test([a, b], 145, 117, margin_y=5) == a
    assert hit_test([a, b], 145, 122, margin_y=5) == b
    assert hit_test([a, b], 250, 120) is None


def test_hover_one_per_entry_and_reset():
    a, b = line('A', 100, 100, 200, 120), line('B', 100, 130, 200, 150)
    tr = HoverTracker(120)
    assert tr.update(a, 0) is None
    assert tr.update(a, 100) is None
    assert tr.update(a, 120) == a
    assert tr.update(a, 300) is None
    assert tr.update(b, 320) is None
    assert tr.update(b, 440) == b
    assert tr.update(None, 450) is None
    assert tr.update(a, 455) is None
    assert tr.update(a, 575) == a
    tr.reset()
    assert tr.update(a, 1000) is None


def test_hover_reenter_same_row_before_other_row_spoken():
    a = line('A', 100, 100, 200, 120)
    b = line('B', 100, 130, 200, 150)
    tr = HoverTracker(100)
    assert tr.update(a, 0) is None
    assert tr.update(a, 100) == a
    assert tr.update(b, 120) is None
    assert tr.update(a, 140) is None
    assert tr.update(a, 240) == a

def test_rapidocr_screen_offset_and_box_filter():
    from types import SimpleNamespace
    import numpy as np
    from game_reader.ocr_backend import rapid_result_lines
    result = SimpleNamespace(
        boxes=np.array([[[12, 20], [88, 20], [88, 42], [12, 42]],
                        [[10, 50], [100, 50], [100, 70], [10, 70]]]),
        txts=("Continue", "Noise"),
        scores=(0.97, 0.1)
    )
    rows = rapid_result_lines(result, (-200, 100))
    assert len(rows) == 1
    assert rows[0].text == "Continue"
    assert (rows[0].left, rows[0].top, rows[0].right, rows[0].bottom) == (-188, 120, -112, 142)


def test_rapidocr_empty_and_mismatch():
    from types import SimpleNamespace
    from game_reader.ocr_backend import rapid_result_lines
    assert rapid_result_lines(SimpleNamespace(boxes=None, txts=None, scores=None), (0,0)) == []
    try:
        rapid_result_lines(SimpleNamespace(boxes=[[[1,1]]], txts=(), scores=()), (0,0))
        assert False, "Expected mismatch failure"
    except ValueError:
        pass


def test_immediate_mouse_target_and_no_duplicate():
    from game_reader.core import HoverTracker
    x = line("打开菜单", 10, 10, 90, 30)
    y = line("退出游戏", 10, 50, 90, 70)
    track = HoverTracker(0)
    assert track.update(x, 100) == x  # no 150ms wait
    assert track.update(x, 101) is None
    assert track.update(y, 120) == y
    assert track.update(None, 121) is None
    assert track.update(x, 122) == x


def test_conservative_region_grouping_matches_spoken_text():
    from game_reader.core import build_reading_regions
    long_line = line("你现在已经到达城市的中央广场", 20, 20, 290, 44)
    next_line = line("继续向东就能找到任务目标。", 21, 48, 275, 72)
    menu_a = line("继续游戏", 20, 130, 155, 152)
    menu_b = line("读取存档", 20, 158, 155, 180)
    regions = build_reading_regions([menu_b, next_line, menu_a, long_line])
    assert len(regions) == 3
    assert "任务目标" in regions[0].text
    assert (regions[0].left, regions[0].top, regions[0].right, regions[0].bottom) == (20, 20, 290, 72)
    assert [region.text for region in regions[1:]] == ["继续游戏", "读取存档"]


def test_small_scene_change_and_two_step_confirmation():
    from PIL import Image
    from game_reader.screen_change import signature_from_image, changed_pixel_fraction, SceneGuard
    blank = Image.new("RGB", (160, 90), "black")
    before = signature_from_image(blank, (0, 0))
    same = signature_from_image(blank.copy(), (0, 0))
    assert changed_pixel_fraction(before, same) == 0
    change = blank.copy()
    from PIL import ImageDraw
    ImageDraw.Draw(change).rectangle((0, 0, 90, 40), fill="white")
    after = signature_from_image(change, (0, 0))
    guard = SceneGuard(before)
    assert guard.changed(after)
    assert changed_pixel_fraction(before, after) >= 0.18


def test_scene_guard_rejects_small_cursor_and_resets():
    from PIL import Image, ImageDraw
    from game_reader.screen_change import signature_from_image, SceneGuard
    im = Image.new("RGB", (160, 90), "black")
    baseline = signature_from_image(im, (-400, 100))
    minor = im.copy()
    ImageDraw.Draw(minor).rectangle((50, 35, 56, 41), fill="white")
    assert not SceneGuard(baseline).changed(signature_from_image(minor, (-400, 100)))
    guard = SceneGuard(baseline)
    moderate = im.copy()
    ImageDraw.Draw(moderate).rectangle((10, 10, 70, 30), fill="white")
    mid = signature_from_image(moderate, (-400, 100))
    assert not guard.changed(mid)
    assert guard.changed(mid)


def test_voice_fallback_prefers_callable_chinese():
    from game_reader.voice_info import preferred_voice_index, voice_diagnostic
    voices = [("eng", "Microsoft Zira"), ("cn", "Microsoft Huihui"),
              ("winrt:abc", "Windows 语音 · Xiaoxiao (zh-CN)")]
    assert preferred_voice_index(voices) == 2
    assert preferred_voice_index(voices, "cn") == 1
    assert preferred_voice_index(voices, "unavailable") == 2
    assert "已安装 ≠" in voice_diagnostic(voices, ["MicrosoftWindows.Voice.zh-CN.Yunxi.1"])


def test_generated_cues_are_short_mono_pcm():
    from io import BytesIO
    import wave
    from game_reader.cues import make_click_wave
    for kind in ("hover", "complete"):
        with wave.open(BytesIO(make_click_wave(kind)), "rb") as wav:
            assert wav.getnchannels() == 1
            assert wav.getsampwidth() == 2
            assert wav.getnframes() < 2000
