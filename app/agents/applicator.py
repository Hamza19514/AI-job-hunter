"""
Agent 2 — resume + cover letter application agent.

Takes a specific job (link, description, employer research handed off by
Agent 1) and produces: a tailored resume (reordered/reworded but 100%
factually grounded in app.resume_data), a job-specific cover letter, and a
realistic fit-percentage analysis. Never invents employers, titles, dates,
metrics, or skills.
"""

from flask import current_app

from app import resume_data
from app.agents.anthropic_client import get_client, extract_text, extract_json_payload

SYSTEM_PROMPT = """You are a resume and cover-letter tailoring agent for the \
candidate below. You will be given ONE specific job (title, company, \
location, job description, apply link, and any employer research notes). \
Your job is to tailor the candidate's application to this exact role.

MASTER RESUME FACTS (100% fixed — never invent, add, or remove employers, \
titles, dates, degrees, GPA, project names, certifications, metrics, or \
skills not listed here; you MAY reorder sections/items and reword bullets \
for ATS alignment as long as every fact and number stays true and every \
protected number below still appears somewhere in your rewording of the \
bullet it came from):
{profile}

PROTECTED NUMBERS THAT MUST NEVER BE DROPPED OR CHANGED WHEN A BULLET \
MENTIONING THEM IS REWORDED: {protected_tokens}

RULES
- Never claim experience, tools, or skills the candidate does not have.
- Never copy sentences verbatim from the job description (natural ATS \
keyword use only, no keyword stuffing).
- Academic-only exposure (e.g. GCP via coursework) must be described as \
academic/coursework exposure, never as professional experience.
- Be realistic and honest in the fit percentage — do not inflate.
- The cover letter must reference 1-2 of the VERIFIED employer initiatives \
provided in employer_research (or the job description itself) and connect \
them to 1-2 of the candidate's real projects/experience most relevant to \
this specific role. No generic praise, no clichés.
- Keep the cover letter to roughly 3-4 short paragraphs (opening, 2 body \
paragraphs, closing) that would fit one page.

Respond with ONLY a JSON object wrapped EXACTLY between <RESULTS_JSON> and \
</RESULTS_JSON> tags, nothing else after the closing tag:

<RESULTS_JSON>
{{
  "fit_percentage": 0,
  "fit_category": "strong application | reasonable application | stretch application",
  "strongest_matches": ["string", "..."],
  "genuine_gaps": ["string", "..."],
  "resume": {{
    "headline": "string, e.g. 'AI & Data Science Graduate | Machine Learning, GenAI, Analytics'",
    "professional_summary": "string, 3-4 sentences tailored to this role",
    "project_order": ["job_tracking_agent", "multilingual_chatbot", "energy_forecasting"],
    "project_bullets": {{
      "job_tracking_agent": ["bullet 1", "bullet 2", "bullet 3"],
      "multilingual_chatbot": ["bullet 1", "bullet 2", "bullet 3"],
      "energy_forecasting": ["bullet 1", "bullet 2", "bullet 3"]
    }},
    "experience_bullets": {{
      "finance_board_advisor": ["bullet 1", "bullet 2", "bullet 3"]
    }},
    "skills_order": {{
      "Programming Languages": ["..."],
      "Data & BI": ["..."],
      "Artificial Intelligence": ["..."],
      "Tools & Platforms": ["..."]
    }},
    "professional_skills_order": ["..."],
    "personal_skills_order": ["..."]
  }},
  "cover_letter": {{
    "opening": "string",
    "body_paragraphs": ["string", "string"],
    "closing": "string"
  }},
  "ats_keywords_supported": ["string", "..."],
  "ats_keywords_unsupported_excluded": ["string", "..."]
}}
</RESULTS_JSON>
"""


def _validate_and_repair(result: dict) -> dict:
    """Guards against fabrication / dropped facts by falling back to master
    data wherever the model's output doesn't check out."""
    resume = result.setdefault("resume", {})

    # Project order must be exactly a permutation of the real project ids.
    master_ids = set(resume_data.all_project_ids())
    order = resume.get("project_order") or []
    if set(order) != master_ids:
        order = resume_data.all_project_ids()
    resume["project_order"] = order

    # Project bullets: same count as master, and any bullet that reworded
    # away a protected number gets reverted to the original.
    project_bullets = resume.get("project_bullets") or {}
    for project in resume_data.PROJECTS:
        pid = project["id"]
        master_bullets = project["bullets"]
        candidate_bullets = project_bullets.get(pid)
        if not candidate_bullets or len(candidate_bullets) != len(master_bullets):
            candidate_bullets = list(master_bullets)
        else:
            candidate_bullets = [
                _repair_bullet(master, cand) for master, cand in zip(master_bullets, candidate_bullets)
            ]
        project_bullets[pid] = candidate_bullets
    resume["project_bullets"] = project_bullets

    # Experience bullets: same treatment.
    experience_bullets = resume.get("experience_bullets") or {}
    for exp in resume_data.EXPERIENCE:
        eid = exp["id"]
        master_bullets = exp["bullets"]
        candidate_bullets = experience_bullets.get(eid)
        if not candidate_bullets or len(candidate_bullets) != len(master_bullets):
            candidate_bullets = list(master_bullets)
        else:
            candidate_bullets = [
                _repair_bullet(master, cand) for master, cand in zip(master_bullets, candidate_bullets)
            ]
        experience_bullets[eid] = candidate_bullets
    resume["experience_bullets"] = experience_bullets

    # Skills: item sets must match master exactly (reordering only).
    skills_order = resume.get("skills_order") or {}
    fixed_skills = {}
    for category, master_items in resume_data.SKILLS["technical"].items():
        candidate_items = skills_order.get(category)
        if not candidate_items or set(candidate_items) != set(master_items):
            candidate_items = list(master_items)
        fixed_skills[category] = candidate_items
    resume["skills_order"] = fixed_skills

    for key, master_items in (
        ("professional_skills_order", resume_data.SKILLS["professional"]),
        ("personal_skills_order", resume_data.SKILLS["personal"]),
    ):
        candidate_items = resume.get(key)
        if not candidate_items or set(candidate_items) != set(master_items):
            candidate_items = list(master_items)
        resume[key] = candidate_items

    if not resume.get("professional_summary"):
        resume["professional_summary"] = resume_data.PROFESSIONAL_SUMMARY_DEFAULT
    if not resume.get("headline"):
        resume["headline"] = "Artificial Intelligence Graduate | Machine Learning & Data Analytics"

    result["resume"] = resume

    cover = result.setdefault("cover_letter", {})
    cover.setdefault("opening", "")
    cover.setdefault("body_paragraphs", [])
    cover.setdefault("closing", "")
    result["cover_letter"] = cover

    result.setdefault("fit_percentage", 0)
    result.setdefault("fit_category", "stretch application")
    result.setdefault("strongest_matches", [])
    result.setdefault("genuine_gaps", [])
    result.setdefault("ats_keywords_supported", [])
    result.setdefault("ats_keywords_unsupported_excluded", [])

    return result


def _repair_bullet(master_bullet: str, candidate_bullet: str) -> str:
    for token in resume_data.PROTECTED_FACT_TOKENS:
        if token in master_bullet and token not in candidate_bullet:
            return master_bullet
    return candidate_bullet


def tailor_application(job: dict) -> dict:
    """job is a dict with at least: company, title, location, apply_url,
    job_description_raw, employer_research. Returns the validated/repaired
    Agent 2 result dict."""
    client = get_client()
    model = current_app.config["APPLICATOR_MODEL"]

    system = SYSTEM_PROMPT.format(
        profile=resume_data.as_prompt_context(),
        protected_tokens=", ".join(resume_data.PROTECTED_FACT_TOKENS),
    )

    user_message = (
        f"COMPANY: {job.get('company')}\n"
        f"TITLE: {job.get('title')}\n"
        f"LOCATION: {job.get('location')}\n"
        f"APPLY URL: {job.get('apply_url')}\n"
        f"EMPLOYER RESEARCH NOTES: {job.get('employer_research', '')}\n\n"
        f"JOB DESCRIPTION:\n{job.get('job_description_raw', '')}\n"
    )

    message = client.messages.create(
        model=model,
        max_tokens=4096,
        system=system,
        messages=[{"role": "user", "content": user_message}],
    )

    text = extract_text(message)
    payload = extract_json_payload(text)
    return _validate_and_repair(payload)
