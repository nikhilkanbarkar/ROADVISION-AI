"""
ROADVISION AI - Test Suite for Historical Condition Progress Monitoring
Tests temporal condition comparison (Worsened, Stable, Repaired).
"""
from types import SimpleNamespace
from datetime import datetime, timedelta
from backend.progress_monitor import compare_inspections

def test_progress_monitoring_repaired():
    t1 = datetime(2026, 1, 1)
    t2 = datetime(2026, 2, 1)

    insp1 = SimpleNamespace(id=1, upload_time=t1, severe_count=1, annotated_path=None)
    insp2 = SimpleNamespace(id=2, upload_time=t2, severe_count=0, annotated_path=None)

    defects1 = [SimpleNamespace(relative_area=0.04)]
    defects2 = [] # Repaired!

    res = compare_inspections(insp1, insp2, defects1, defects2)
    assert "Repaired" in res["condition_trend"]
    assert res["earlier_defect_count"] == 1
    assert res["later_defect_count"] == 0
    assert res["days_elapsed"] == 31

def test_progress_monitoring_worsened():
    t1 = datetime(2026, 1, 1)
    t2 = datetime(2026, 2, 1)

    insp1 = SimpleNamespace(id=1, upload_time=t1, severe_count=0, annotated_path=None)
    insp2 = SimpleNamespace(id=2, upload_time=t2, severe_count=2, annotated_path=None)

    defects1 = [SimpleNamespace(relative_area=0.02)]
    defects2 = [SimpleNamespace(relative_area=0.05), SimpleNamespace(relative_area=0.04)]

    res = compare_inspections(insp1, insp2, defects1, defects2)
    assert res["condition_trend"] == "Worsened"
    assert res["count_delta"] == 1
    assert res["area_delta_pct"] > 50.0

def test_progress_monitoring_stable():
    t1 = datetime(2026, 1, 1)
    t2 = datetime(2026, 1, 15)

    insp1 = SimpleNamespace(id=1, upload_time=t1, severe_count=0, annotated_path=None)
    insp2 = SimpleNamespace(id=2, upload_time=t2, severe_count=0, annotated_path=None)

    defects1 = [SimpleNamespace(relative_area=0.02)]
    defects2 = [SimpleNamespace(relative_area=0.021)]

    res = compare_inspections(insp1, insp2, defects1, defects2)
    assert res["condition_trend"] == "Stable"
