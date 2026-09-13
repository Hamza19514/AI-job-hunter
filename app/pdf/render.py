import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

from app import resume_data

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
_env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))


def render_resume_pdf(agent2_result: dict, output_path: Path) -> Path:
    resume = agent2_result["resume"]

    ordered_projects = []
    for pid in resume["project_order"]:
        project = resume_data.project_by_id(pid)
        ordered_projects.append(
            {
                "name": project["name"],
                "dates": project["dates"],
                "bullets": resume["project_bullets"][pid],
            }
        )

    experience = []
    for exp in resume_data.EXPERIENCE:
        experience.append(
            {
                "title": exp["title"],
                "org": exp["org"],
                "dates": exp["dates"],
                "bullets": resume["experience_bullets"].get(exp["id"], exp["bullets"]),
            }
        )

    context = {
        "contact": resume_data.CONTACT,
        "professional_summary": resume["professional_summary"],
        "education": resume_data.EDUCATION,
        "experience": experience,
        "projects": ordered_projects,
        "certifications": resume_data.CERTIFICATIONS,
        "leadership": resume_data.LEADERSHIP,
        "technical_skills": resume["skills_order"],
        "professional_skills": resume["professional_skills_order"],
        "personal_skills": resume["personal_skills_order"],
        "languages": resume_data.LANGUAGES,
    }

    html = _env.get_template("resume.html").render(**context)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    HTML(string=html).write_pdf(str(output_path))
    return output_path


def render_cover_letter_pdf(job: dict, agent2_result: dict, output_path: Path) -> Path:
    cover = agent2_result["cover_letter"]
    context = {
        "contact": resume_data.CONTACT,
        "today": datetime.date.today().strftime("%B %d, %Y"),
        "company": job.get("company", ""),
        "opening": cover.get("opening", ""),
        "body_paragraphs": cover.get("body_paragraphs", []),
        "closing": cover.get("closing", ""),
    }
    html = _env.get_template("cover_letter.html").render(**context)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    HTML(string=html).write_pdf(str(output_path))
    return output_path
