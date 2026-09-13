"""
Daily job-hunt orchestration: Agent 1 -> Agent 2 -> PDF rendering -> DB,
capped at DAILY_JOB_CAP APPLY/APPLY_IMMEDIATELY jobs per day and stopping
after SEARCH_CUTOFF_HOUR_LOCAL in the configured timezone (Asia/Riyadh by
default). Runs automatically on a background schedule; a manual "run now"
trigger reuses the exact same eligibility rules so it refuses to run once
the cap or cutoff has been hit, same as the automatic runs.
"""

import logging
import threading
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler

from app.models import db, Job, SearchRun
from app.agents.job_hunter import hunt_jobs
from app.agents.applicator import tailor_application
from app.pdf.render import render_resume_pdf, render_cover_letter_pdf

logger = logging.getLogger(__name__)

_run_lock = threading.Lock()
_run_in_progress = False
_run_started_at = None

# Safety valve: a real run (search + tailoring for up to DAILY_JOB_CAP jobs)
# should never take this long. If the in-progress flag is still set after
# this many seconds, treat it as wedged (e.g. a hung network call) rather
# than letting it block the button/scheduler indefinitely.
MAX_RUN_SECONDS = 15 * 60

APPLY_RECOMMENDATIONS = ("APPLY_IMMEDIATELY", "APPLY")


def local_now(app):
    return datetime.now(ZoneInfo(app.config["TIMEZONE"]))


def today_apply_count(app, local_date):
    return Job.query.filter(
        Job.found_date == local_date,
        Job.recommendation.in_(APPLY_RECOMMENDATIONS),
    ).count()


def _is_run_actually_in_progress():
    """Treats the in-progress flag as stale (and clears it) if it's been set
    far longer than any real run should take — guards against a wedged
    background thread permanently blocking future runs."""
    global _run_in_progress, _run_started_at

    if not _run_in_progress:
        return False

    if _run_started_at is not None and (time.monotonic() - _run_started_at) > MAX_RUN_SECONDS:
        logger.warning("Search flag was stuck in-progress for over %ss; clearing it.", MAX_RUN_SECONDS)
        _run_in_progress = False
        _run_started_at = None
        if _run_lock.locked():
            try:
                _run_lock.release()
            except RuntimeError:
                pass
        return False

    return True


def is_eligible_to_run(app):
    """Returns (eligible: bool, reason: str)."""
    if _is_run_actually_in_progress():
        return False, "A search is already running."

    now_local = local_now(app)
    count_today = today_apply_count(app, now_local.date())
    cap = app.config["DAILY_JOB_CAP"]
    cutoff_hour = app.config["SEARCH_CUTOFF_HOUR_LOCAL"]

    if count_today >= cap:
        return False, f"Today's cap of {cap} jobs has already been reached."
    if now_local.hour >= cutoff_hour:
        return False, f"Past today's {cutoff_hour}:00 search cutoff ({app.config['TIMEZONE']})."
    return True, ""


def run_search_cycle(app):
    global _run_in_progress, _run_started_at

    if not _run_lock.acquire(blocking=False):
        logger.info("Search cycle already running, skipping this trigger.")
        return

    try:
        _run_in_progress = True
        _run_started_at = time.monotonic()
        with app.app_context():
            _run_search_cycle_locked(app)
    finally:
        _run_in_progress = False
        _run_started_at = None
        _run_lock.release()


def _run_search_cycle_locked(app):
    now_local = local_now(app)
    today = now_local.date()
    cap = app.config["DAILY_JOB_CAP"]
    cutoff_hour = app.config["SEARCH_CUTOFF_HOUR_LOCAL"]

    count_today = today_apply_count(app, today)
    if count_today >= cap:
        _log_run(today, status="skipped_cap", notes=f"{count_today}/{cap} already found today.")
        return
    if now_local.hour >= cutoff_hour:
        _log_run(today, status="skipped_cutoff", notes=f"Local time {now_local.strftime('%H:%M')} past cutoff.")
        return

    remaining = cap - count_today
    already_seen_keys = [j.dedupe_key for j in Job.query.with_entities(Job.dedupe_key).all()]

    try:
        candidates = hunt_jobs(already_seen_keys, remaining)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Agent 1 (job hunter) failed")
        _log_run(today, status="error", notes=f"Agent 1 failed: {exc}")
        return

    ready_count = 0
    for job_data in candidates:
        job_row = _create_job_row(today, job_data)
        db.session.add(job_row)
        db.session.commit()

        try:
            agent2_result = tailor_application(job_data)

            resume_path = app.config["GENERATED_FILES_DIR"] / f"job_{job_row.id}_resume.pdf"
            cover_path = app.config["GENERATED_FILES_DIR"] / f"job_{job_row.id}_cover_letter.pdf"
            render_resume_pdf(agent2_result, resume_path)
            render_cover_letter_pdf(job_data, agent2_result, cover_path)

            job_row.resume_pdf_path = str(resume_path)
            job_row.cover_letter_pdf_path = str(cover_path)
            job_row.agent2_fit_percentage = agent2_result.get("fit_percentage")
            job_row.agent2_fit_category = agent2_result.get("fit_category")
            job_row.status = "ready"
            ready_count += 1
        except Exception as exc:  # noqa: BLE001
            logger.exception("Agent 2 / PDF generation failed for job %s", job_row.id)
            job_row.status = "error"
            job_row.error_message = str(exc)

        db.session.commit()

    _log_run(
        today,
        status="ok",
        jobs_considered=len(candidates),
        new_apply_jobs=ready_count,
        notes=f"Found {len(candidates)} candidate(s), {ready_count} ready.",
    )


def _create_job_row(found_date, job_data) -> Job:
    return Job(
        dedupe_key=job_data["dedupe_key"],
        company=job_data.get("company", "")[:255],
        title=job_data.get("title", "")[:255],
        location=job_data.get("location", "")[:255],
        date_posted=job_data.get("date_posted"),
        application_deadline=job_data.get("application_deadline"),
        fit_score=job_data.get("fit_score", 0),
        classification=job_data.get("classification", "Reach"),
        recommendation=job_data.get("recommendation", "APPLY"),
        source_type=job_data.get("source_type"),
        apply_url=job_data.get("apply_url", ""),
        why_fit=job_data.get("why_fit"),
        requirements_met="\n".join(job_data.get("requirements_met", []) or []),
        gaps="\n".join(job_data.get("gaps", []) or []),
        gap_severity=job_data.get("gap_severity"),
        employer_research=job_data.get("employer_research"),
        job_description_raw=job_data.get("job_description_raw"),
        found_date=found_date,
        status="generating",
    )


def _log_run(ast_date, status, jobs_considered=0, new_apply_jobs=0, notes=""):
    db.session.add(
        SearchRun(
            ast_date=ast_date,
            jobs_considered=jobs_considered,
            new_apply_jobs=new_apply_jobs,
            status=status,
            notes=notes,
        )
    )
    db.session.commit()


def trigger_manual_run(app):
    """Kicks off a search cycle in a background thread if eligible. Returns
    (started: bool, reason: str)."""
    eligible, reason = is_eligible_to_run(app)
    if not eligible:
        return False, reason

    thread = threading.Thread(target=run_search_cycle, args=(app,), daemon=True)
    thread.start()
    return True, "Search started."


def start_scheduler(app):
    scheduler = BackgroundScheduler(timezone=app.config["TIMEZONE"])
    scheduler.add_job(
        run_search_cycle,
        "interval",
        minutes=app.config["SEARCH_INTERVAL_MINUTES"],
        args=[app],
        id="daily_job_hunt",
        next_run_time=datetime.now(ZoneInfo(app.config["TIMEZONE"])),  # also fire once shortly after startup
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    app.extensions["scheduler"] = scheduler
    return scheduler
