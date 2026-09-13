from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Job(db.Model):
    __tablename__ = "jobs"

    id = db.Column(db.Integer, primary_key=True)

    # Stable key used to avoid resurfacing the same job (normalized apply_url,
    # or company+title+location when no clean url is available).
    dedupe_key = db.Column(db.String(512), unique=True, nullable=False, index=True)

    company = db.Column(db.String(255), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    location = db.Column(db.String(255))
    date_posted = db.Column(db.String(100))
    application_deadline = db.Column(db.String(100))

    fit_score = db.Column(db.Integer, nullable=False)
    classification = db.Column(db.String(50), nullable=False)  # Exceptional/Strong/Good/Reach
    recommendation = db.Column(db.String(30), nullable=False)  # APPLY_IMMEDIATELY/APPLY/APPLY_AS_REACH/SKIP
    source_type = db.Column(db.String(80))

    apply_url = db.Column(db.Text, nullable=False)

    why_fit = db.Column(db.Text)
    requirements_met = db.Column(db.Text)   # newline-separated
    gaps = db.Column(db.Text)               # newline-separated
    gap_severity = db.Column(db.String(30)) # minor/learnable/meaningful/hard_blocker

    employer_research = db.Column(db.Text)
    job_description_raw = db.Column(db.Text)

    # Date (in Asia/Riyadh) this job was discovered — used for the daily cap.
    found_date = db.Column(db.Date, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # discovered -> generating -> ready -> error
    status = db.Column(db.String(20), default="discovered")
    error_message = db.Column(db.Text)

    resume_pdf_path = db.Column(db.String(512))
    cover_letter_pdf_path = db.Column(db.String(512))

    agent2_fit_percentage = db.Column(db.Integer)
    agent2_fit_category = db.Column(db.String(50))  # strong/reasonable/stretch application

    def requirements_met_list(self):
        return [l for l in (self.requirements_met or "").split("\n") if l.strip()]

    def gaps_list(self):
        return [l for l in (self.gaps or "").split("\n") if l.strip()]

    def to_dict(self):
        return {
            "id": self.id,
            "company": self.company,
            "title": self.title,
            "location": self.location,
            "date_posted": self.date_posted,
            "application_deadline": self.application_deadline,
            "fit_score": self.fit_score,
            "classification": self.classification,
            "recommendation": self.recommendation,
            "source_type": self.source_type,
            "apply_url": self.apply_url,
            "why_fit": self.why_fit,
            "requirements_met": self.requirements_met_list(),
            "gaps": self.gaps_list(),
            "gap_severity": self.gap_severity,
            "employer_research": self.employer_research,
            "status": self.status,
            "resume_pdf_path": self.resume_pdf_path,
            "cover_letter_pdf_path": self.cover_letter_pdf_path,
            "agent2_fit_percentage": self.agent2_fit_percentage,
            "agent2_fit_category": self.agent2_fit_category,
            "found_date": self.found_date.isoformat() if self.found_date else None,
        }


class SearchRun(db.Model):
    __tablename__ = "search_runs"

    id = db.Column(db.Integer, primary_key=True)
    run_at = db.Column(db.DateTime, default=datetime.utcnow)
    ast_date = db.Column(db.Date, nullable=False, index=True)

    jobs_considered = db.Column(db.Integer, default=0)
    new_apply_jobs = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default="ok")  # ok/error/skipped_cap/skipped_cutoff
    notes = db.Column(db.Text)
