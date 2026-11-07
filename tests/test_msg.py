from pymoos2.core.constants import (
    MSG_NOTIFY, MSG_NULL, DATA_DOUBLE, DATA_STRING, DATA_BINARY,
)
from pymoos2.core.MOOSMsg import MOOSMsg
from pymoos2.core.MOOSCommPkt import pack, unpack


def roundtrip(msg):
    out, _ = MOOSMsg.deserialize(msg.serialize())
    return out


def test_inferred_types():
    assert MOOSMsg(MSG_NOTIFY, "A", sval="x").is_string()
    assert MOOSMsg(MSG_NOTIFY, "A", sval=b"\x00\x01").is_binary()
    assert MOOSMsg(MSG_NOTIFY, "A", val=1.0).is_double()
    assert MOOSMsg(MSG_NULL, "").is_double()


def test_explicit_empty_string_stays_string():
    m = MOOSMsg(MSG_NOTIFY, "A", sval="", data_type=DATA_STRING)
    assert m.is_string()
    r = roundtrip(m)
    assert r.is_string() and r.string() == ""


def test_roundtrip_values():
    for m in (MOOSMsg(MSG_NOTIFY, "S", sval="hello,world", src="me"),
              MOOSMsg(MSG_NOTIFY, "D", val=3.25),
              MOOSMsg(MSG_NOTIFY, "B", sval=b"\x00\xff\x10")):
        m.community = "shoreside"
        m.src_aux = "pid=A1"
        r = roundtrip(m)
        assert r.key == m.key and r.src == m.src and r.src_aux == "pid=A1"
        assert r.community == "shoreside" and r.data_type == m.data_type
        if m.is_double():
            assert r.double() == 3.25
        elif m.is_binary():
            assert r.binary_data() == b"\x00\xff\x10"
        else:
            assert r.string() == "hello,world"


def test_ids_increase():
    a = MOOSMsg(MSG_NOTIFY, "A", val=1)
    b = MOOSMsg(MSG_NOTIFY, "B", val=2)
    assert b.msg_id > a.msg_id


def test_pack_unpack_many():
    msgs = [MOOSMsg(MSG_NOTIFY, f"K{i}", val=float(i)) for i in range(50)]
    out = unpack(pack(msgs))
    assert [m.key for m in out] == [f"K{i}" for i in range(50)]
    assert out[7].double() == 7.0
