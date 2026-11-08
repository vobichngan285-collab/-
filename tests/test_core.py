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
