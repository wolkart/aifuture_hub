import thumb_text

OCR = """ocr-cards: собираю бинарник (один раз)…
=== k1DTxuBur-Y.jpg
ПЕРЕСТАНЬ
ИСПОЛЬЗОВАТЬ
CURSOR AI
=== 0Sxf4B-KTvA.jpg
БЕСПЛАТНО
НАВСЕГДА
=== brokenID123.jpg
!! Vision не смог: что-то пошло не так
=== emptyID4567.jpg
"""


def test_parse_ocr_output_splits_blocks():
    blocks = thumb_text.parse_ocr_output(OCR)
    assert blocks["k1DTxuBur-Y"] == ["ПЕРЕСТАНЬ", "ИСПОЛЬЗОВАТЬ", "CURSOR AI"]
    assert blocks["0Sxf4B-KTvA"] == ["БЕСПЛАТНО", "НАВСЕГДА"]


def test_parse_ocr_output_error_block_is_empty():
    # строка с !! — это сообщение об ошибке, а не распознанный текст
    assert thumb_text.parse_ocr_output(OCR)["brokenID123"] == []


def test_parse_ocr_output_empty_block():
    assert thumb_text.parse_ocr_output(OCR)["emptyID4567"] == []


def test_parse_ocr_output_ignores_preamble():
    # строка про сборку бинарника не должна попасть ни в один блок
    blocks = thumb_text.parse_ocr_output(OCR)
    assert all("собираю бинарник" not in " ".join(v) for v in blocks.values())


def test_parse_ocr_output_empty_input():
    assert thumb_text.parse_ocr_output("") == {}


def test_features_free():
    assert thumb_text.features("БЕСПЛАТНО НАВСЕГДА")["бесплатно"] is True
    assert thumb_text.features("Get it FREE now")["бесплатно"] is True
    assert thumb_text.features("СКИДКА 50%")["бесплатно"] is False


def test_features_paid_tool_name():
    f = thumb_text.features("ПЕРЕСТАНЬ ИСПОЛЬЗОВАТЬ CURSOR AI")
    assert f["имя инструмента"] is True
    assert f["запрет"] is True


def test_features_digit():
    assert thumb_text.features("7 ДНЕЙ НЕЙРОСЕТЬ")["цифра"] is True
    assert thumb_text.features("ВЕРНУЛ СЛОВА В МУЗЫКУ")["цифра"] is False


def test_features_on_empty_text():
    f = thumb_text.features("")
    assert all(v is False for v in f.values())


def test_word_count():
    # строки склеиваются пробелом: ПЕРЕСТАНЬ + ИСПОЛЬЗОВАТЬ + CURSOR + AI
    assert thumb_text.word_count(["ПЕРЕСТАНЬ", "ИСПОЛЬЗОВАТЬ CURSOR AI"]) == 4
    assert thumb_text.word_count([]) == 0


def test_slice_by_feature_compares_with_and_without():
    records = {
        "a": {"median_multiple": 4.0},
        "b": {"median_multiple": 3.5},
        "c": {"median_multiple": 1.0},
        "d": {"median_multiple": 0.5},
    }
    blocks = {"a": ["БЕСПЛАТНО"], "b": ["всё БЕСПЛАТНО"],
              "c": ["просто текст"], "d": ["ещё текст"]}
    out = thumb_text.slice_by_feature(records, blocks)
    free = out["бесплатно"]
    assert free["n"] == 2
    assert free["median_multiple"] == 3.75
    assert free["median_without"] == 0.75
    assert free["reliable"] is False  # n=2 < порога 5


def test_slice_marks_reliable_above_threshold():
    records = {str(i): {"median_multiple": 2.0} for i in range(6)}
    records.update({"x%d" % i: {"median_multiple": 1.0} for i in range(6)})
    blocks = {k: (["БЕСПЛАТНО"] if not k.startswith("x") else ["текст"])
              for k in records}
    out = thumb_text.slice_by_feature(records, blocks)
    assert out["бесплатно"]["n"] == 6
    assert out["бесплатно"]["reliable"] is True


def test_slice_ignores_ids_without_metrics():
    records = {"a": {"median_multiple": 2.0}}
    blocks = {"a": ["БЕСПЛАТНО"], "неизвестный": ["БЕСПЛАТНО"]}
    assert thumb_text.slice_by_feature(records, blocks)["бесплатно"]["n"] == 1


def test_length_slice_present():
    records = {str(i): {"median_multiple": 1.0} for i in range(4)}
    blocks = {"0": ["раз два"], "1": ["раз два три четыре пять"],
              "2": ["а"], "3": ["раз два три четыре пять шесть"]}
    out = thumb_text.slice_by_feature(records, blocks)
    assert "текст ≤4 слов" in out
    assert out["текст ≤4 слов"]["n"] == 2
