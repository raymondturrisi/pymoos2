"""Appcast and realmcast repositories, ordered and counted as uMAC and
pMarineViewer show them.
"""

PROC_PRIORITY = [
    "pHelmIvP", "pNodeReporter", "pContactMgrV20", "uFldNodeBroker", "pObstacleMgr",
    "uTimerScript", "pMarinePIDV22", "uSimMarineV22", "pMissionEval", "uFldMessageHandler",
    "uLoadWatch", "uProcessWatch", "uXMS", "pDeadManPost", "pHostInfo", "pRealm", "uMemWatch",
]

REFRESH_MODES = ("events", "streaming", "paused")


def sort_nodes(names):
    """Shoreside first, then alphabetical."""
    names = sorted(set(names))
    if "shoreside" in names:
        names.remove("shoreside")
        names.insert(0, "shoreside")
    return names


def sort_procs(names):
    names = set(names)
    out = [p for p in PROC_PRIORITY if p in names]
    out += sorted(n for n in names if n not in PROC_PRIORITY)
    return out


class AppCastRepo:
    """Latest appcast per (node, proc) with warning counts and a current selection."""

    def __init__(self):
        self._casts = {}
        self._counts = {}
        self.current_node = ""
        self.current_proc = ""
        self.refresh_mode = "events"
        self._last_proc_by_node = {}

    def add_appcast(self, ac, now=None):
        """Store an AppCast. Returns (new_node, new_proc) flags."""
        node = ac.node or "unknown_node"
        proc = ac.proc or "unknown_proc"
        ac.received_time = now
        new_node = node not in self._casts
        procs = self._casts.setdefault(node, {})
        new_proc = proc not in procs
        procs[proc] = ac
        counts = self._counts.setdefault(node, {})
        counts[proc] = counts.get(proc, 0) + 1
        if not self.current_node:
            self.current_node = node
        if not self.current_proc and node == self.current_node:
            self.current_proc = proc
        return new_node, new_proc

    def remove_node(self, node):
        self._casts.pop(node, None)
        self._counts.pop(node, None)
        if self.current_node == node:
            nodes = self.nodes()
            self.current_node = nodes[0] if nodes else ""
            procs = self.procs(self.current_node)
            self.current_proc = procs[0] if procs else ""

    def set_current_node(self, node):
        if node in self._casts:
            if self.current_node and self.current_proc:
                self._last_proc_by_node[self.current_node] = self.current_proc
            self.current_node = node
            procs = self.procs(node)
            remembered = self._last_proc_by_node.get(node)
            if remembered in procs:
                self.current_proc = remembered
            elif self.current_proc not in procs:
                self.current_proc = procs[0] if procs else ""
            return True
        return False

    def set_current_proc(self, proc):
        if proc in self._casts.get(self.current_node, {}):
            self.current_proc = proc
            return True
        return False

    def set_refresh_mode(self, mode):
        if mode in REFRESH_MODES:
            self.refresh_mode = mode
            return True
        return False

    def nodes(self):
        return sort_nodes(self._casts.keys())

    def procs(self, node=None):
        node = node or self.current_node
        return sort_procs(self._casts.get(node, {}).keys())

    def get(self, node=None, proc=None):
        node = node or self.current_node
        proc = proc or self.current_proc
        return self._casts.get(node, {}).get(proc)

    def current(self):
        return self.get()

    def appcast_count(self, node, proc=None):
        counts = self._counts.get(node, {})
        if proc:
            return counts.get(proc, 0)
        return sum(counts.values())

    def config_warning_count(self, node, proc=None):
        casts = self._casts.get(node, {})
        if proc:
            ac = casts.get(proc)
            return len(ac.config_warnings) if ac else 0
        return sum(len(ac.config_warnings) for ac in casts.values())

    def run_warning_count(self, node, proc=None):
        casts = self._casts.get(node, {})
        if proc:
            ac = casts.get(proc)
            return ac.run_warning_total if ac else 0
        return sum(ac.run_warning_total for ac in casts.values())

    def node_summary(self):
        """Rows for a nodes table: name, appcast count, config and run warning totals."""
        return [{"node": n, "ac": self.appcast_count(n), "cw": self.config_warning_count(n),
                 "rw": self.run_warning_count(n), "procs": len(self._casts[n])}
                for n in self.nodes()]

    def proc_summary(self, node=None):
        node = node or self.current_node
        return [{"proc": p, "ac": self.appcast_count(node, p), "cw": self.config_warning_count(node, p),
                 "rw": self.run_warning_count(node, p)} for p in self.procs(node)]


class WatchCluster:
    """A named set of variables watched across all nodes via WATCHCAST."""

    def __init__(self, key, variables=None):
        self.key = key
        self.variables = []
        self._data = {}
        self.update_count = 0
        if variables:
            self.add_vars(variables)

    def add_vars(self, variables):
        for v in variables:
            v = v.strip()
            if v and v not in self.variables:
                self.variables.append(v)

    def has_var(self, var):
        return var in self.variables

    def add_watchcast(self, wc):
        if wc.var not in self.variables:
            return False
        self._data.setdefault(wc.node, {})[wc.var] = wc
        self.update_count += 1
        return True

    def nodes(self):
        return sort_nodes(self._data.keys())

    def get(self, node, var):
        return self._data.get(node, {}).get(var)

    def var_update_count(self, var):
        return sum(1 for node in self._data.values() if var in node)

    def rows(self, var=None):
        """Table rows: one per node for var, or one per node with a column per
        variable when var is None.
        """
        out = []
        if var:
            for node in self.nodes():
                wc = self.get(node, var)
                if wc is None:
                    continue
                out.append({"node": node, "var": var, "time": wc.loc_time, "utc": wc.utc_time,
                            "src": wc.src, "comm": wc.comm, "value": wc.value_str()})
        else:
            for node in self.nodes():
                row = {"node": node}
                for v in self.variables:
                    wc = self.get(node, v)
                    row[v] = wc.value_str() if wc else ""
                out.append(row)
        return out

    def to_dict(self):
        return {"key": self.key, "vars": list(self.variables), "updates": self.update_count,
                "nodes": self.nodes()}


class RealmRepo:
    """Channels per node, latest realmcast per (node, proc), watch clusters, selection."""

    def __init__(self):
        self._channels = {}
        self._casts = {}
        self._counts = {}
        self.clusters = {}
        self.current_node = ""
        self.current_proc = ""
        self.current_cluster = ""
        self.current_cluster_var = ""
        self.refresh_mode = "events"
        self._pending_node = ""
        self._pending_proc = ""

    def add_watch_cluster(self, key, variables):
        cluster = self.clusters.get(key)
        if cluster is None:
            cluster = WatchCluster(key)
            self.clusters[key] = cluster
        cluster.add_vars(variables)
        return cluster

    def set_on_start_preferences(self, spec):
        """realmcast_channel = node:proc or cluster[:var]; applied as data arrives."""
        a, _, b = spec.partition(":")
        a, b = a.strip(), b.strip()
        if a in self.clusters:
            self.current_cluster = a
            self.current_cluster_var = b if b in self.clusters[a].variables else ""
            return True
        self._pending_node, self._pending_proc = a, b
        return True

    def add_realm_summary(self, rs):
        """Returns True if the node or channel set changed."""
        node = rs.node or "unknown_node"
        before = self._channels.get(node)
        self._channels[node] = list(rs.channels)
        changed = before != self._channels[node]
        self._casts.setdefault(node, {})
        self._apply_pending()
        if not self.current_node and not self.current_cluster:
            self.current_node = node
            if rs.channels and not self.current_proc:
                self.current_proc = rs.channels[0]
        return changed

    def add_realmcast(self, rc, now=None):
        node = rc.node or "unknown_node"
        proc = rc.proc or "unknown_proc"
        rc.received_time = now
        self._casts.setdefault(node, {})[proc] = rc
        counts = self._counts.setdefault(node, {})
        counts[proc] = counts.get(proc, 0) + 1
        if proc not in self._channels.setdefault(node, []):
            self._channels[node].append(proc)
        self._apply_pending()
        if not self.current_node and not self.current_cluster:
            self.current_node, self.current_proc = node, proc

    def add_watchcast(self, wc, now=None):
        wc.received_time = now
        hit = False
        for cluster in self.clusters.values():
            if cluster.add_watchcast(wc):
                hit = True
        return hit

    def _apply_pending(self):
        if self._pending_node and self._pending_node in self._channels:
            self.current_node = self._pending_node
            if self._pending_proc in self._channels[self._pending_node]:
                self.current_proc = self._pending_proc
            self._pending_node = self._pending_proc = ""

    def set_current_node(self, node):
        if node in self._channels:
            self.current_cluster = ""
            self.current_node = node
            if self.current_proc not in self._channels[node]:
                chans = self.channels(node)
                self.current_proc = chans[0] if chans else ""
            return True
        return False

    def set_current_proc(self, proc):
        if proc in self._channels.get(self.current_node, []):
            self.current_proc = proc
            return True
        return False

    def set_current_cluster(self, key, var=""):
        if key in self.clusters:
            self.current_cluster = key
            self.current_cluster_var = var if var in self.clusters[key].variables else ""
            return True
        return False

    def set_refresh_mode(self, mode):
        if mode in REFRESH_MODES:
            self.refresh_mode = mode
            return True
        return False

    def nodes(self):
        return sort_nodes(self._channels.keys())

    def channels(self, node=None):
        node = node or self.current_node
        return list(self._channels.get(node, []))

    def get(self, node=None, proc=None):
        node = node or self.current_node
        proc = proc or self.current_proc
        return self._casts.get(node, {}).get(proc)

    def realmcast_count(self, node, proc=None):
        counts = self._counts.get(node, {})
        if proc:
            return counts.get(proc, 0)
        return sum(counts.values())

    def node_summary(self):
        return [{"node": n, "rc": self.realmcast_count(n), "channels": len(self._channels[n])}
                for n in self.nodes()]

    def channel_summary(self, node=None):
        node = node or self.current_node
        return [{"proc": p, "rc": self.realmcast_count(node, p)} for p in self.channels(node)]

    def cluster_summary(self):
        return [c.to_dict() for c in self.clusters.values()]

    def request_vars(self):
        """Variables to put in REALMCAST_REQ_ALL for the current cluster view."""
        cluster = self.clusters.get(self.current_cluster)
        if cluster is None:
            return []
        if self.current_cluster_var:
            return [self.current_cluster_var]
        return list(cluster.variables)
