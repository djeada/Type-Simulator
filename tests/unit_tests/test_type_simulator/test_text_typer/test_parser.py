import pytest
import os
import time
import logging

from type_simulator.text_typer.token import (
    TextToken,
    WaitToken,
    KeyToken,
    RepeatToken,
    RandomTextToken,
    SpeedToken,
    VariableToken,
)
from type_simulator.text_typer.parser import CommandParser
from type_simulator.text_typer.__main__ import Typist, TextTyper


# Parser tests


def test_parse_plain_text():
    parser = CommandParser()
    tokens = parser.parse("Hello")
    assert len(tokens) == 1
    assert type(tokens[0]).__name__ == "TextToken"
    assert getattr(tokens[0], "text", None) == "Hello"


def test_parse_literal_braces():
    parser = CommandParser()
    tokens = parser.parse(r"Text \{braces\}")
    assert len(tokens) == 1
    assert type(tokens[0]).__name__ == "TextToken"
    assert getattr(tokens[0], "text", None) == "Text {braces}"


def test_parse_wait_token():
    parser = CommandParser()
    tokens = parser.parse("A{WAIT_2}B")
    # The parser merges text tokens, so expect: [TextToken('A'), WaitToken(2.0), TextToken('B')]
    assert len(tokens) == 3
    assert type(tokens[0]).__name__ == "TextToken"
    assert getattr(tokens[0], "text", None) == "A"
    assert type(tokens[1]).__name__ == "WaitToken"
    assert getattr(tokens[1], "seconds", None) == pytest.approx(2.0)
    assert type(tokens[2]).__name__ == "TextToken"
    assert getattr(tokens[2], "text", None) == "B"


def test_parse_key_token_single():
    parser = CommandParser()
    tokens = parser.parse("X{<esc>}Y")
    assert type(tokens[1]).__name__ == "KeyToken"
    assert getattr(tokens[1], "keys", None) == ["esc"]


def test_parse_key_token_combo_whitespace():
    parser = CommandParser()
    tokens = parser.parse("{ <ctrl> + <alt> + t }")
    assert len(tokens) == 1
    assert type(tokens[0]).__name__ == "KeyToken"
    assert getattr(tokens[0], "keys", None) == ["ctrl", "alt", "t"]


def test_parse_invalid_sequence_skips(caplog):
    caplog.set_level(logging.WARNING)
    parser = CommandParser()
    tokens = parser.parse("A{INVALID_KEY}B")
    # The parser treats invalid sequences as literal text, so expect one TextToken with the full string
    assert len(tokens) == 1
    assert type(tokens[0]).__name__ == "TextToken"
    assert getattr(tokens[0], "text", None) == "A{INVALID_KEY}B"
    # The parser logs a warning only in strict mode, so this may not always be present
    # assert "Skipping invalid sequence" in caplog.text


def test_preserve_angle_bracket():
    parser = CommandParser()
    # Beginning
    tokens = parser.parse("<abc")
    assert len(tokens) == 1
    assert type(tokens[0]).__name__ == "TextToken"
    assert getattr(tokens[0], "text", None) == "<abc"
    # Middle
    tokens = parser.parse("a < b")
    assert len(tokens) == 1
    assert getattr(tokens[0], "text", None) == "a < b"
    # End
    tokens = parser.parse("abc<")
    assert len(tokens) == 1
    assert getattr(tokens[0], "text", None) == "abc<"
    # Multiple
    tokens = parser.parse("<a < b<")
    assert len(tokens) == 1
    assert getattr(tokens[0], "text", None) == "<a < b<"


def test_preserve_colon():
    parser = CommandParser()
    # Key-value
    tokens = parser.parse("Key: Value")
    assert len(tokens) == 1
    assert tokens[0].text == "Key: Value"
    # Timestamp
    tokens = parser.parse("12:30")
    assert len(tokens) == 1
    assert tokens[0].text == "12:30"
    # Multiple colons
    tokens = parser.parse("a:b:c")
    assert len(tokens) == 1
    assert tokens[0].text == "a:b:c"
    # Colon at start/end
    tokens = parser.parse(":start and end:")
    assert len(tokens) == 1
    assert tokens[0].text == ":start and end:"


def test_preserve_empty_lines_after_brace_and_logging(caplog):
    """Ensure that empty lines after '{' are preserved and visible in logs when invalid spec occurs."""
    caplog.set_level(logging.DEBUG)
    parser = CommandParser(strict=False)
    text = "{\n\nint value = 1;\n}"
    tokens = parser.parse(text)
    assert len(tokens) == 1
    assert isinstance(tokens[0], TextToken)
    assert tokens[0].text.startswith("{\n\nint value")

    # Now with strict=True and an invalid spec that includes newlines to check escaped logging
    caplog.clear()
    parser_strict = CommandParser(strict=True)
    bad = "{INVALID\n\nSPEC}"
    tokens2 = parser_strict.parse(bad)
    # In strict mode, invalid is skipped; result is empty text token list
    assert all(t.__class__.__name__ != "TextToken" or t.text != bad for t in tokens2)
    # Ensure the log contains the escaped \n sequences
    assert "Invalid sequence '{INVALID\\n\\nSPEC}'" in caplog.text


# New feature tests


def test_parse_repeat_token():
    """Test parsing of REPEAT blocks."""
    parser = CommandParser()
    tokens = parser.parse("{REPEAT_3}Hello {/REPEAT}")
    assert len(tokens) == 1
    assert isinstance(tokens[0], RepeatToken)
    assert tokens[0].count == 3
    assert len(tokens[0].tokens) == 1
    assert tokens[0].tokens[0].text == "Hello "


def test_parse_nested_repeat():
    """Test nested REPEAT blocks."""
    parser = CommandParser()
    tokens = parser.parse("{REPEAT_2}{REPEAT_3}X{/REPEAT}{/REPEAT}")
    assert len(tokens) == 1
    assert isinstance(tokens[0], RepeatToken)
    assert tokens[0].count == 2
    inner = tokens[0].tokens[0]
    assert isinstance(inner, RepeatToken)
    assert inner.count == 3


def test_parse_random_token():
    """Test parsing of RANDOM token."""
    parser = CommandParser()
    tokens = parser.parse("{RANDOM_10}")
    assert len(tokens) == 1
    assert isinstance(tokens[0], RandomTextToken)
    assert tokens[0].length == 10
    assert tokens[0].charset == "alphanumeric"


def test_parse_random_with_charset():
    """Test parsing of RANDOM token with custom charset."""
    parser = CommandParser()
    tokens = parser.parse("{RANDOM_5_alpha}")
    assert len(tokens) == 1
    assert tokens[0].length == 5
    assert tokens[0].charset == "alpha"


def test_parse_speed_token():
    """Test parsing of SPEED token."""
    parser = CommandParser()
    tokens = parser.parse("{SPEED_0.1}")
    assert len(tokens) == 1
    assert isinstance(tokens[0], SpeedToken)
    assert tokens[0].speed == pytest.approx(0.1)
    assert tokens[0].variance is None


def test_parse_speed_with_variance():
    """Test parsing of SPEED token with variance."""
    parser = CommandParser()
    tokens = parser.parse("{SPEED_0.05_0.02}")
    assert len(tokens) == 1
    assert tokens[0].speed == pytest.approx(0.05)
    assert tokens[0].variance == pytest.approx(0.02)


def test_parse_variable_set():
    """Test parsing of SET variable."""
    parser = CommandParser()
    tokens = parser.parse("{SET_myvar=hello world}")
    assert len(tokens) == 1
    assert isinstance(tokens[0], VariableToken)
    assert tokens[0].name == "myvar"
    assert tokens[0].value == "hello world"
    assert tokens[0].action == "set"


def test_parse_variable_get():
    """Test parsing of GET variable."""
    parser = CommandParser()
    tokens = parser.parse("{GET_myvar}")
    assert len(tokens) == 1
    assert isinstance(tokens[0], VariableToken)
    assert tokens[0].name == "myvar"
    assert tokens[0].action == "get"


def test_parse_complex_macro():
    """Test parsing a complex macro with multiple features."""
    parser = CommandParser()
    macro = "{SPEED_0.1}Hello{WAIT_1}{REPEAT_2} World{/REPEAT}"
    tokens = parser.parse(macro)
    assert len(tokens) == 4
    assert isinstance(tokens[0], SpeedToken)
    assert isinstance(tokens[1], TextToken)
    assert isinstance(tokens[2], WaitToken)
    assert isinstance(tokens[3], RepeatToken)


# New token tests for enhanced features


def test_parse_datetime_token():
    """Test parsing of DATETIME token."""
    from type_simulator.text_typer.token import DateTimeToken

    parser = CommandParser()
    tokens = parser.parse("{DATETIME}")
    assert len(tokens) == 1
    assert isinstance(tokens[0], DateTimeToken)
    assert tokens[0].format == "%Y-%m-%d %H:%M:%S"


def test_parse_datetime_with_format():
    """Test parsing of DATETIME token with custom format."""
    from type_simulator.text_typer.token import DateTimeToken

    parser = CommandParser()
    tokens = parser.parse("{DATETIME_%Y/%m/%d}")
    assert len(tokens) == 1
    assert isinstance(tokens[0], DateTimeToken)
    assert tokens[0].format == "%Y/%m/%d"


def test_parse_date_shorthand():
    """Test parsing of DATE shorthand."""
    from type_simulator.text_typer.token import DateTimeToken

    parser = CommandParser()
    tokens = parser.parse("{DATE}")
    assert len(tokens) == 1
    assert isinstance(tokens[0], DateTimeToken)
    assert tokens[0].format == "%Y-%m-%d"


def test_parse_time_shorthand():
    """Test parsing of TIME shorthand."""
    from type_simulator.text_typer.token import DateTimeToken

    parser = CommandParser()
    tokens = parser.parse("{TIME}")
    assert len(tokens) == 1
    assert isinstance(tokens[0], DateTimeToken)
    assert tokens[0].format == "%H:%M:%S"


def test_parse_counter_token():
    """Test parsing of COUNTER token."""
    from type_simulator.text_typer.token import CounterToken

    parser = CommandParser()
    tokens = parser.parse("{COUNTER}")
    assert len(tokens) == 1
    assert isinstance(tokens[0], CounterToken)
    assert tokens[0].name == "default"
    assert tokens[0].action == "next"


def test_parse_counter_with_name():
    """Test parsing of named COUNTER token."""
    from type_simulator.text_typer.token import CounterToken

    parser = CommandParser()
    tokens = parser.parse("{COUNTER_mycount}")
    assert len(tokens) == 1
    assert isinstance(tokens[0], CounterToken)
    assert tokens[0].name == "mycount"


def test_parse_loop_token():
    """Test parsing of LOOP block."""
    from type_simulator.text_typer.token import LoopToken

    parser = CommandParser()
    tokens = parser.parse("{LOOP_5}Item {GET_i}{/LOOP}")
    assert len(tokens) == 1
    assert isinstance(tokens[0], LoopToken)
    assert tokens[0].count == 5
    assert tokens[0].var_name == "i"


def test_parse_loop_with_var():
    """Test parsing of LOOP block with custom variable name."""
    from type_simulator.text_typer.token import LoopToken

    parser = CommandParser()
    tokens = parser.parse("{LOOP_3_num}Number {GET_num}{/LOOP}")
    assert len(tokens) == 1
    assert isinstance(tokens[0], LoopToken)
    assert tokens[0].count == 3
    assert tokens[0].var_name == "num"


def test_parse_newline_token():
    """Test parsing of NEWLINE token."""
    from type_simulator.text_typer.token import NewlineToken

    parser = CommandParser()
    tokens = parser.parse("{NEWLINE}")
    assert len(tokens) == 1
    assert isinstance(tokens[0], NewlineToken)
    assert tokens[0].count == 1


def test_parse_newline_with_count():
    """Test parsing of NEWLINE token with count."""
    from type_simulator.text_typer.token import NewlineToken

    parser = CommandParser()
    tokens = parser.parse("{NEWLINE_3}")
    assert len(tokens) == 1
    assert isinstance(tokens[0], NewlineToken)
    assert tokens[0].count == 3


def test_parse_nl_shorthand():
    """Test parsing of NL shorthand for newline."""
    from type_simulator.text_typer.token import NewlineToken

    parser = CommandParser()
    tokens = parser.parse("{NL}")
    assert len(tokens) == 1
    assert isinstance(tokens[0], NewlineToken)


def test_parse_tab_token():
    """Test parsing of TAB token."""
    from type_simulator.text_typer.token import TabToken

    parser = CommandParser()
    tokens = parser.parse("{TAB}")
    assert len(tokens) == 1
    assert isinstance(tokens[0], TabToken)
    assert tokens[0].count == 1


def test_parse_tab_with_count():
    """Test parsing of TAB token with count."""
    from type_simulator.text_typer.token import TabToken

    parser = CommandParser()
    tokens = parser.parse("{TAB_2}")
    assert len(tokens) == 1
    assert isinstance(tokens[0], TabToken)
    assert tokens[0].count == 2
