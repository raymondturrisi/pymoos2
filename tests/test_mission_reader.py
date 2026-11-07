from pymoos2.core.MissionReader import MissionReader


def test_globals_first_wins_and_case_insensitive(sample_mission):
    mr = MissionReader(sample_mission, "pViewer")
    assert mr.get_value("LatOrigin", type=float) == 42.358456
    assert mr.get_value("latorigin", type=float) == 42.358456
    assert mr.get_value("LongOrigin", type=float) == -71.087589
    assert mr.get_value("MOOSTimeWarp", type=float) == 10.0
    assert mr.get_value("Community") == "shoreside"
    assert mr.get_value("Missing", default="d") == "d"


def test_block_names_and_apptick(sample_mission):
    mr = MissionReader(sample_mission, "pViewer")
    assert mr.block_names() == ["ANTLER", "pViewer", "uFldDelve"]
    assert mr.get_config("apptick", type=float) == 10.0
    assert mr.get_config("CommsTick", type=int) == 20
    assert mr.has_block()
    assert MissionReader(sample_mission, "pviewer").has_block()
    assert not MissionReader(sample_mission, "pNope").has_block()


def test_repeated_keys_kept_in_order(sample_mission):
    mr = MissionReader(sample_mission, "pViewer")
    buttons = mr.get_config_values("button_1")
    assert buttons == ["DEPLOY # DEPLOY_ALL=true # color=light_green",
                       "MOOS_MANUAL_OVERRIDE_ALL=false"]
    keys = [k for k, _ in mr.get_config_lines()]
    assert keys.count("basemap") == 2
    assert "right_context[Return_Point]" in keys


def test_quoted_url_survives_comment_stripping(sample_mission):
    mr = MissionReader(sample_mission, "pViewer")
    urls = mr.get_config_values("basemap")
    assert urls[0] == '"https://tile.example.com/{z}/{x}/{y}.png//x"'
    assert urls[1] == "https://tile.example.org/{z}/{x}/{y}.png"


def test_braced_values_do_not_end_block(sample_mission):
    mr = MissionReader(sample_mission, "pViewer")
    cmds = mr.get_config_values("cmd")
    assert len(cmds) == 2
    assert cmds[0] == "label=POLY, var=SURVEY_UPDATE, sval={pts={30,-30:-25,-30}, label=H}, receivers=all"
    assert mr.get_config("rate_frame", type=int) == 10
    assert mr.get_config("empty_value") == ""
    assert MissionReader(sample_mission, "uFldDelve").get_config("apptick", type=int) == 4


def test_duplicate_scalar_last_wins_unless_first(sample_mission):
    mr = MissionReader(sample_mission, "pViewer")
    assert mr.get_config("vehicles_name_mode") == "names+depth"
    assert mr.get_config("vehicles_name_mode", first=True) == "names"
    assert mr.get_config_values("vehicles_name_mode") == ["names", "names+depth"]


def test_real_pmarineviewer_plug(pmv_plug):
    mr = MissionReader(pmv_plug, "pMarineViewer")
    lines = mr.get_config_lines()
    keys = [k for k, _ in lines]
    assert keys.count("button_1") == 4
    assert keys.count("scope") == 3
    assert keys.count("watch_cluster") == 4
    assert keys.count("cmd") == 9
    assert keys.count("action") == 9
    assert keys.count("right_context[return_point]") == 2
    assert keys.count("right_context[station]") == 1
    assert mr.get_config("tiff_file") == "MIT_SP.tif"
    assert mr.get_config("vehicles_name_mode") == "names+depth"
    assert mr.get_config("vehicles_name_mode", first=True) == "names"
    assert MissionReader(pmv_plug, "uFldDelve").get_config("rate_frame") == "10"
    assert mr.warnings == []


def test_missing_file_fails_fast():
    import pytest
    with pytest.raises(FileNotFoundError):
        MissionReader("/nonexistent/file.moos", "x")
