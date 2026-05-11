from lyrics_editor.align.text import lyric_line_tokens, normalize_text


def test_normalize_text_removes_common_punctuation():
    assert normalize_text("Hello, 世界！") == "hello世界"


def test_latin_tokenization_keeps_word_boundaries():
    assert lyric_line_tokens("Hello, world!") == ["hello", "world"]


def test_cjk_tokenization_is_character_based():
    assert lyric_line_tokens("你好世界") == ["你", "好", "世", "界"]
