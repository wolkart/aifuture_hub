import transcript as tr


def W(*toks):
    return [{"text": t, "start": i * 0.5, "end": i * 0.5 + 0.4} for i, t in enumerate(toks)]


def test_dictionary_keeps_trailing_punctuation():
    out, n = tr.apply_dictionary(W("Напиши", "лего,", "в"), {"лего": "СЛОВО"})
    assert [w["text"] for w in out] == ["Напиши", "СЛОВО,", "в"] and n == 1


def test_dictionary_multiword_key_merges_tokens():
    out, n = tr.apply_dictionary(W("а", "РРС", "ленты", "сайтов"), {"РРС ленты": "RSS-ленты", "РРС": "RSS"})
    assert [w["text"] for w in out] == ["а", "RSS-ленты", "сайтов"]
    assert out[1]["start"] == 0.5 and out[1]["end"] == 1.4 and n == 1


def test_dictionary_case_insensitive():
    out, _ = tr.apply_dictionary(W("Lego"), {"лего": "X", "lego": "Y"})
    assert out[0]["text"] == "Y"


def test_merge_split_on_hyphen():
    out = tr.merge_split(W("телеграм", "-канал,", "который"))
    assert [w["text"] for w in out] == ["телеграм-канал,", "который"]
    assert out[0]["start"] == 0.0 and out[0]["end"] == 0.9


def test_trim_hallucination_after_script():
    words = W("раз", "два", "три", "Продолжение", "следует")
    assert [w["text"] for w in tr.trim_to_script(words, "Раз, два, три.")] == ["раз", "два", "три"]


def test_trim_keeps_last_word_misheard():
    words = W("раз", "два", "тли", "спасибо")
    assert [w["text"] for w in tr.trim_to_script(words, "раз два три")] == ["раз", "два", "тли"]


def test_diff_script_reports_mismatch_with_time():
    d = tr.diff_script(W("раз", "два", "тли"), "Раз, два, три.")
    assert len(d) == 1 and "«тли» ≠ сценарий «три.»" in d[0] and d[0].strip().startswith("1.00")


def test_diff_script_equal():
    assert tr.diff_script(W("Сейчас", "покажу,"), "Сейчас покажу") == []


def test_parse_replace():
    assert tr.parse_replace(["перепост=перепост —", "bad"]) == {"перепост": "перепост —"}
