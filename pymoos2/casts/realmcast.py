"""Realmcast wire formats and request strings.

REALMCAST           node=V!Q!proc=P!Q!messages=line!Z!line!Z!
REALMCAST_CHANNELS  node=V#channels=MOOSDB_V,pHelmIvP,pNodeReporter,
WATCHCAST           node=V!X!var=DEPLOY!X!src=pHelmIvP!X!comm=V!X!loc_time=12.3!X!utc_time=17e8!X!sval=true
REALMCAST_REQ       client=C,duration=3[,nosrc][,nocom][,nosubs][,wrap][,mask][,trunc][,utc],channel=P
                    client=C,duration=3,vars=A:B:C[,force]
APPCAST_REQ         node=V,app=P,duration=3,key=K,thresh=any|run_warning
"""

from pymoos2.core.strutil import double_to_string_x, to_int


class RealmCast:
    def __init__(self, node="", proc="", messages="", count=0):
        self.node = node
        self.proc = proc
        self.messages = messages
        self.count = count
        self.received_time = None

    def get_formatted_string(self):
        return self.messages

    def to_dict(self):
        return {"node": self.node, "proc": self.proc, "messages": self.messages,
                "count": self.count, "received_time": self.received_time}

    def __repr__(self):
        return f"RealmCast({self.node}:{self.proc}, {len(self.messages)} chars)"


def parse_realmcast(text):
    rc = RealmCast()
    for pair in text.split("!Q!"):
        if "=" not in pair:
            continue
        param, value = pair.split("=", 1)
        param = param.strip()
        if param == "node":
            rc.node = value.strip()
        elif param == "proc":
            rc.proc = value.strip()
        elif param == "count":
            n = to_int(value)
            if n is not None:
                rc.count = n
        elif param == "messages":
            lines = value.split("!Z!")
            if lines and lines[-1] == "":
                lines = lines[:-1]
            rc.messages = "\n".join(lines)
    return rc


class RealmSummary:
    def __init__(self, node="", channels=None):
        self.node = node
        self.channels = list(channels or [])

    def to_dict(self):
        return {"node": self.node, "channels": list(self.channels)}


def parse_realm_summary(text):
    rs = RealmSummary()
    for pair in text.split("#"):
        if "=" not in pair:
            continue
        param, value = pair.split("=", 1)
        param = param.strip()
        if param == "node":
            rs.node = value.strip()
        elif param == "channels":
            rs.channels = [c.strip() for c in value.split(",") if c.strip()]
    return rs


class WatchCast:
    def __init__(self):
        self.node = ""
        self.var = ""
        self.src = ""
        self.comm = ""
        self.loc_time = None
        self.utc_time = None
        self.sval = None
        self.dval = None
        self.received_time = None

    def valid(self):
        return bool(self.node and self.src and self.comm) and (self.sval is None) != (self.dval is None)

    def value_str(self):
        if self.dval is not None:
            return double_to_string_x(self.dval, 6)
        return self.sval if self.sval is not None else ""

    def to_dict(self):
        return {"node": self.node, "var": self.var, "src": self.src, "comm": self.comm,
                "loc_time": self.loc_time, "utc_time": self.utc_time,
                "value": self.value_str(), "is_double": self.dval is not None,
                "received_time": self.received_time}

    def __repr__(self):
        return f"WatchCast({self.node} {self.var}={self.value_str()})"


def parse_watchcast(text):
    wc = WatchCast()
    for pair in text.split("!X!"):
        if "=" not in pair:
            continue
        param, value = pair.split("=", 1)
        param = param.strip()
        value = value.strip()
        if param in ("node", "var", "src", "comm"):
            setattr(wc, param, value)
        elif param in ("loc_time", "utc_time"):
            try:
                setattr(wc, param, float(value))
            except ValueError:
                pass
        elif param == "sval":
            wc.sval = value
        elif param == "dval":
            try:
                wc.dval = float(value)
            except ValueError:
                wc.sval = value
    return wc


def build_appcast_req(node, app, duration, key, thresh="any"):
    """APPCAST_REQ body. Post it as APPCAST_REQ and APPCAST_REQ_<NODE upper>."""
    return f"node={node},app={app},duration={duration:.1f},key={key},thresh={thresh}"


def build_realmcast_req(client, duration, channel=None, variables=None, force=False,
                        show_source=True, show_community=True, show_subscriptions=True,
                        wrap=False, show_masked=True, trunc=False, utc=False):
    """REALMCAST_REQ value. Give exactly one of channel or variables."""
    parts = [f"client={client}", f"duration={duration:g}"]
    if not show_source:
        parts.append("nosrc")
    if not show_community:
        parts.append("nocom")
    if not show_subscriptions:
        parts.append("nosubs")
    if wrap:
        parts.append("wrap")
    if not show_masked:
        parts.append("mask")
    if trunc:
        parts.append("trunc")
    if utc:
        parts.append("utc")
    if variables:
        parts.append("vars=" + ":".join(variables))
        if force:
            parts.append("force")
    elif channel:
        parts.append(f"channel={channel}")
    return ",".join(parts)
