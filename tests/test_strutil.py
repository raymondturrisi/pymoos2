from pymoos2.core import strutil as su


def test_strip_comment_basic():
    assert su.strip_comment("rate = 10 // secs") == "rate = 10 "
    assert su.strip_comment("// whole line") == ""
    assert su.strip_comment("no comment here") == "no comment here"


def test_strip_comment_protects_quotes_and_urls():
    assert su.strip_comment('url = "https://a//b" // c') == 'url = "https://a//b" '
    assert su.strip_comment("url = https://a.b/c//d") == "url = https://a.b/c"
    assert su.strip_comment("x=1//y") == "x=1"


def test_parse_string_q_protects_quotes_and_braces():
    s = 'label=A, sval={pts={1,2:3,4}, label=H}, msg="a,b", color=red'
    parts = su.parse_string_q(s)
    assert parts == ['label=A', ' sval={pts={1,2:3,4}, label=H}', ' msg="a,b"', ' color=red']


def test_parse_string_z():
    assert su.parse_string_z("a=1,b={2,3},c=4") == ["a=1", "b={2,3}", "c=4"]


def test_parse_kv_flags_and_pairs():
    pairs = su.parse_kv("client=pmv,duration=3,nosrc,channel=pHelmIvP")
    assert pairs == [("client", "pmv"), ("duration", "3"), ("nosrc", None), ("channel", "pHelmIvP")]


def test_double_to_string_x():
    assert su.double_to_string_x(1.5, 1) == "1.5"
    assert su.double_to_string_x(2.0, 2) == "2"
    assert su.double_to_string_x(-0.001, 2) == "0"
    assert su.double_to_string_x(10.250, 3) == "10.25"
    assert su.double_to_string(2.0, 1) == "2.0"


def test_is_number():
    assert su.is_number("3")
    assert su.is_number("-3.5e2")
    assert su.is_number(" 7 ")
    assert not su.is_number("true")
    assert not su.is_number("1,2")


def test_macro_expand_both_forms():
    assert su.macro_expand("a=$(X),b=$[X]", "X", 5) == "a=5,b=5"
    out = su.macro_expand_all("$(UP_VNAME)_$(VNAME)", {"VNAME": "abe", "UP_VNAME": "ABE"})
    assert out == "ABE_abe"


def test_strip_quotes_and_braces():
    assert su.strip_quotes('"abc"') == "abc"
    assert su.strip_quotes('"abc') == '"abc'
    assert su.strip_braces("{a=1}") == "a=1"
