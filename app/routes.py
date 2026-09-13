from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from flask import Blueprint, current_app, redirect, render_template, send_file, url_for, flash, abort

from app.models import db, Job, SearchRun
from app.scheduler import trigger_manual_run, is_eligible_to_run, today_apply_count, local_now

bp = Blueprint("main", __name__)


@bp.route("/")
def dashboard():
    app = current_app._get_current_object()
    now_local = local_now(app)
    today = now_local.date()

    jobs = (
        Job.query.filter(Job.status == "ready")
        .order_by(Job.found_date.desc(), Job.fit_score.desc())
        .limit(60)
        .all()
    )

    today_jobs = [j for j in jobs if j.found_date == today]
    earlier_jobs = [j for j in jobs if j.found_date != today]

    count_today = today_apply_count(app, today)
    cap = app.config["DAILY_JOB_CAP"]
    cutoff_hour = app.config["SEARCH_CUTOFF_HOUR_LOCAL"]
    eligible, reason = is_eligible_to_run(app)

    last_run = SearchRun.query.order_by(SearchRun.run_at.desc()).first()
    pending_jobs = Job.query.filter(Job.status.in_(["generating"])).count()
    error_jobs = Job.query.filter(
        Job.status == "error", Job.found_date == today
    ).count()

    return render_template(
        "dashboard.html",
        today_jobs=today_jobs,
        earlier_jobs=earlier_jobs,
        count_today=count_today,
        cap=cap,
        cutoff_hour=cutoff_hour,
        timezone=app.config["TIMEZONE"],
        eligible=eligible,
        reason=reason,
        last_run=last_run,
        pending_jobs=pending_jobs,
        error_jobs=error_jobs,
        now_local=now_local,
    )


@bp.route("/run-now", methods=["POST"])
def run_now():
    app = current_app._get_current_object()
    started, reason = trigger_manual_run(app)
    if started:
        flash("Search started in the background — refresh in a bit to see new jobs.", "success")
    else:
        flash(f"Couldn't start a search: {reason}", "error")
    return redirect(url_for("main.dashboard"))


@bp.route("/jobs/<int:job_id>/resume.pdf")
def resume_pdf(job_id):
    job = Job.query.get_or_404(job_id)
    if not job.resume_pdf_path or not Path(job.resume_pdf_path).exists():
        abort(404)
    filename = f"Hamza_Bu_Obaid_Resume_{job.company}_{job.title}.pdf".replace(" ", "_")
    return send_file(job.resume_pdf_path, as_attachment=False, download_name=filename)


@bp.route("/jobs/<int:job_id>/cover-letter.pdf")
def cover_letter_pdf(job_id):
    job = Job.query.get_or_404(job_id)
    if not job.cover_letter_pdf_path or not Path(job.cover_letter_pdf_path).exists():
        abort(404)
    filename = f"Hamza_Bu_Obaid_CoverLetter_{job.company}_{job.title}.pdf".replace(" ", "_")
    return send_file(job.cover_letter_pdf_path, as_attachment=False, download_name=filename)
