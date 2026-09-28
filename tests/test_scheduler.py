import pytest
from app.automation.scheduler import SchedulerManager

def test_scheduler_timer():
    alerts = []
    
    def alert_cb(msg):
        alerts.append(msg)

    sched = SchedulerManager(notify_callback=alert_cb)
    res = sched.set_timer(minutes=1, label="Test Timer")
    assert "Timer set" in res
    sched.shutdown()
