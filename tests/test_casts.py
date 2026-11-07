from pymoos2.casts import (
    parse_appcast, parse_realmcast, parse_realm_summary, parse_watchcast,
    build_appcast_req, build_realmcast_req, AppCastRepo, RealmRepo,
)
from pymoos2.core.AppCastingMOOSApp import AppCastingMOOSApp

SAMPLE = ("proc=pNodeReporter!@#iter=812!@#node=alpha!@#iter=812!@#"
          "messages=line one!@line two!@!@#config_warnings=Unhandled config line: foo=1!@#"
          "events_total=2!@#events=[12.34]: started!@[20.00]: paused!@#"
          "run_warning_total=3!@#run_warnings=2:Waiting for NAV_X!@1:Other Run Warnings")


def test_parse_appcast_fields():
    ac = parse_appcast(SAMPLE)
    assert ac.proc == "pNodeReporter" and ac.node == "alpha" and ac.iteration == 812
    assert ac.messages == "line one\nline two\n"
    assert ac.config_warnings == ["Unhandled config line: foo=1"]
    assert ac.events == ["[12.34]: started", "[20.00]: paused"]
    assert ac.run_warning_total == 3
    assert ac.run_warnings == {"Waiting for NAV_X": 2, "Other Run Warnings": 1}
    text = ac.get_formatted_string()
    assert text.startswith("=" * 62 + "\npNodeReporter alpha")
    assert "1/3(812)" in text.split("\n")[1]
    assert "Runtime Warnings: 3" in text and "[20.00]: paused\n[12.34]: started" in text
    d = ac.to_dict()
    assert d["run_warnings"][0] == {"count": 2, "text": "Waiting for NAV_X"}


def test_parse_appcast_empty_sections():
    ac = parse_appcast("proc=p!@#iter=1!@#node=n!@#iter=1!@#messages=!@#!@#events_total=0!@#!@#run_warning_total=0!@#")
    assert ac.messages == "" and ac.events == [] and ac.run_warnings == {}


def test_producer_output_parses_back():
    app = AppCastingMOOSApp()
    app.m_app_name = "pProbe"
    app.m_community = "shoreside"
    app.m_iteration = 5
    app.m_start_time = 0.0
    app.report("A  B")
    app.report("1  2\n3  4")
    app.report_run_warning("bad thing")
    app.report_config_warning("odd config")
    ac = parse_appcast(app.get_appcast_string())
    assert ac.proc == "pProbe" and ac.node == "shoreside" and ac.iteration == 5
    assert ac.messages == "A  B\n1  2\n3  4\n"
    assert ac.run_warnings == {"bad thing": 1} and ac.run_warning_total == 1
    assert ac.config_warnings == ["odd config"]


def test_realm_parsers():
    rc = parse_realmcast("node=alpha!Q!proc=pHelmIvP!Q!messages=Subscriptions!Z!====!Z!Var  Src!Z!")
    assert rc.node == "alpha" and rc.proc == "pHelmIvP"
    assert rc.messages == "Subscriptions\n====\nVar  Src"
    rs = parse_realm_summary("node=alpha#channels=MOOSDB_alpha,pHelmIvP,pNodeReporter,")
    assert rs.node == "alpha" and rs.channels == ["MOOSDB_alpha", "pHelmIvP", "pNodeReporter"]
    wc = parse_watchcast("node=alpha!X!var=DEPLOY!X!src=pHelmIvP!X!comm=alpha!X!loc_time=123.45!X!utc_time=1700000000.12!X!sval=true")
    assert wc.valid() and wc.value_str() == "true" and wc.loc_time == 123.45
    wd = parse_watchcast("node=alpha!X!var=NAV_X!X!src=uSim!X!comm=alpha!X!loc_time=1!X!utc_time=2!X!dval=3.250")
    assert wd.valid() and wd.dval == 3.25 and wd.value_str() == "3.25"
    never = parse_watchcast("node=alpha!X!var=FOO!X!src=n/a!X!comm=n/a!X!loc_time=-1!X!utc_time=-1!X!sval=n/a")
    assert never.valid() and never.value_str() == "n/a"


def test_request_builders():
    assert build_appcast_req("alpha", "pHelmIvP", 3, "viewer:shoreside", "any") == \
        "node=alpha,app=pHelmIvP,duration=3.0,key=viewer:shoreside,thresh=any"
    assert build_realmcast_req("viewer", 3, channel="pHelmIvP") == "client=viewer,duration=3,channel=pHelmIvP"
    assert build_realmcast_req("viewer", 3, channel="x", show_source=False, show_community=False,
                               show_subscriptions=False, wrap=True, show_masked=False, trunc=True, utc=True) == \
        "client=viewer,duration=3,nosrc,nocom,nosubs,wrap,mask,trunc,utc,channel=x"
    assert build_realmcast_req("viewer", 3, variables=["A", "B"], force=True) == \
        "client=viewer,duration=3,vars=A:B,force"


def test_appcast_repo_ordering_and_counts():
    repo = AppCastRepo()
    for node, proc, rw, cw in (("abe", "uProcessWatch", 0, 0), ("shoreside", "pMarineViewer", 1, 0),
                               ("abe", "pHelmIvP", 2, 1), ("abe", "aZeta", 0, 0)):
        ac = parse_appcast(f"proc={proc}!@#iter=1!@#node={node}!@#iter=1!@#messages=!@#"
                           + ("config_warnings=c" if cw else "") + f"!@#events_total=0!@#!@#run_warning_total={rw}!@#")
        repo.add_appcast(ac, now=1.0)
    assert repo.nodes() == ["shoreside", "abe"]
    assert repo.procs("abe") == ["pHelmIvP", "uProcessWatch", "aZeta"]
    assert repo.current_node == "abe" and repo.current_proc == "uProcessWatch"
    assert repo.run_warning_count("abe") == 2 and repo.config_warning_count("abe") == 1
    assert repo.appcast_count("abe") == 3
    assert repo.set_current_node("shoreside") and repo.current_proc == "pMarineViewer"
    assert repo.set_current_node("abe") and repo.current_proc == "uProcessWatch"
    assert repo.set_current_proc("pHelmIvP") and repo.current().proc == "pHelmIvP"
    assert not repo.set_current_proc("nope")
    rows = repo.node_summary()
    assert rows[0]["node"] == "shoreside" and rows[1]["rw"] == 2
    repo.remove_node("abe")
    assert repo.nodes() == ["shoreside"] and repo.current_node == "shoreside"


def test_realm_repo_and_clusters():
    repo = RealmRepo()
    repo.add_watch_cluster("mission", ["DEPLOY", "RETURN"])
    repo.add_watch_cluster("mission", ["RETURN", "STATION"])
    assert repo.clusters["mission"].variables == ["DEPLOY", "RETURN", "STATION"]
    repo.set_on_start_preferences("abe:pHelmIvP")
    repo.add_realm_summary(parse_realm_summary("node=shoreside#channels=MOOSDB_shoreside,pRealm,"))
    assert repo.current_node == "shoreside"
    repo.add_realm_summary(parse_realm_summary("node=abe#channels=MOOSDB_abe,pHelmIvP,pNodeReporter,"))
    assert repo.current_node == "abe" and repo.current_proc == "pHelmIvP"
    repo.add_realmcast(parse_realmcast("node=abe!Q!proc=pHelmIvP!Q!messages=hello!Z!"), now=5.0)
    assert repo.get().messages == "hello" and repo.realmcast_count("abe") == 1
    assert repo.nodes() == ["shoreside", "abe"]
    wc = parse_watchcast("node=abe!X!var=DEPLOY!X!src=pHelmIvP!X!comm=abe!X!loc_time=1!X!utc_time=2!X!sval=true")
    assert repo.add_watchcast(wc)
    assert not repo.add_watchcast(parse_watchcast("node=abe!X!var=NOPE!X!src=a!X!comm=abe!X!loc_time=1!X!utc_time=2!X!sval=x"))
    cluster = repo.clusters["mission"]
    assert cluster.rows("DEPLOY") == [{"node": "abe", "var": "DEPLOY", "time": 1.0, "utc": 2.0,
                                      "src": "pHelmIvP", "comm": "abe", "value": "true"}]
    assert cluster.rows() == [{"node": "abe", "DEPLOY": "true", "RETURN": "", "STATION": ""}]
    assert repo.set_current_cluster("mission", "RETURN") and repo.request_vars() == ["RETURN"]
    assert repo.set_current_cluster("mission") and repo.request_vars() == ["DEPLOY", "RETURN", "STATION"]
    assert repo.set_current_node("shoreside") and repo.current_cluster == ""
