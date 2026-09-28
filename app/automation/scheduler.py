import datetime
from typing import Callable, Optional
from apscheduler.schedulers.background import BackgroundScheduler
from app.memory.memory_manager import MemoryManager
from app.core.logging_config import logger

class SchedulerManager:
    """APScheduler background manager for timers and scheduled reminders."""

    def __init__(self, memory_manager: Optional[MemoryManager] = None, notify_callback: Optional[Callable[[str], None]] = None):
        self.scheduler = BackgroundScheduler()
        self.memory_manager = memory_manager
        self.notify_callback = notify_callback
        self.scheduler.start()
        logger.info("APScheduler BackgroundScheduler started.")

    def set_timer(self, minutes: int, label: str = "Timer") -> str:
        """Schedule a countdown timer."""
        trigger_time = datetime.datetime.now() + datetime.timedelta(minutes=minutes)
        job_id = f"timer_{int(datetime.datetime.now().timestamp())}"

        def timer_fired():
            msg = f"Timer Alert: {label} ({minutes} minutes completed!)"
            logger.info(msg)
            if self.notify_callback:
                self.notify_callback(msg)

        self.scheduler.add_job(
            timer_fired,
            "date",
            run_date=trigger_time,
            id=job_id
        )

        if self.memory_manager:
            self.memory_manager.save_reminder(f"Timer: {label}", trigger_time.isoformat())

        time_str = trigger_time.strftime("%I:%M %p")
        return f"Timer set for {minutes} minutes (will trigger at {time_str})."

    def set_reminder(self, time_str: str, message: str) -> str:
        """
        Set a reminder for a specific time string e.g. '20:00' or '8 PM' or 'in 15 minutes'.
        """
        now = datetime.datetime.now()
        target_time = None

        # Parse simple HH:MM format e.g. '20:00' or '8 PM'
        try:
            if ":" in time_str:
                parts = time_str.split(":")
                hh = int(parts[0])
                mm = int(parts[1][:2])
                target_time = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
                if target_time < now:
                    target_time += datetime.timedelta(days=1)
            elif "pm" in time_str.lower() or "am" in time_str.lower():
                time_clean = time_str.lower().replace("pm", "").replace("am", "").strip()
                hh = int(time_clean)
                if "pm" in time_str.lower() and hh < 12:
                    hh += 12
                target_time = now.replace(hour=hh, minute=0, second=0, microsecond=0)
                if target_time < now:
                    target_time += datetime.timedelta(days=1)
        except Exception:
            pass

        if not target_time:
            # Default to 30 minutes from now if unparseable
            target_time = now + datetime.timedelta(minutes=30)

        job_id = f"reminder_{int(datetime.datetime.now().timestamp())}"

        def reminder_fired():
            msg = f"Reminder: {message}"
            logger.info(msg)
            if self.notify_callback:
                self.notify_callback(msg)

        self.scheduler.add_job(
            reminder_fired,
            "date",
            run_date=target_time,
            id=job_id
        )

        if self.memory_manager:
            self.memory_manager.save_reminder(message, target_time.isoformat())

        formatted = target_time.strftime("%I:%M %p")
        return f"Reminder set for {formatted}: '{message}'."

    def shutdown(self):
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
