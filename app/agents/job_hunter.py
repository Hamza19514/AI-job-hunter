"""
Agent 1 — Saudi Arabia job-search agent.

Searches the live web (Google, LinkedIn postings, job boards such as Bayt,
Naukrigulf, Indeed, and official employer / government career portals) for
currently-open roles in Saudi Arabia that Hamza could realistically qualify
for, verifies each one against an official source, scores fit, and returns
ONLY jobs it recommends APPLY or APPLY_IMMEDIATELY (up to the number of
remaining daily slots) as strict JSON, ready to be handed to Agent 2.
"""

from flask import current_app

from app.resume_data import as_prompt_context
from app.agents.anthropic_client import get_client, extract_text, extract_json_payload

SYSTEM_PROMPT = """You are a Saudi Arabia job-search and application-discovery agent \
working for the candidate whose profile is provided below. You have access to a \
web_search tool — use it to search Google, LinkedIn job postings, job boards \
(Bayt, Naukrigulf, Indeed, GulfTalent, Wuzzuf-style aggregators), official \
government career portals, and company career pages / ATS platforms (Workday, \
Greenhouse, Lever, Ashby, SuccessFactors, Oracle).

CANDIDATE PROFILE
{profile}

Also: Saudi national, recent graduate of Illinois Institute of Technology \
(BS + MS Artificial Intelligence, Statistics minor), AI & Data Science \
internship experience, leadership/business decision-making experience \
including financial oversight of a $3M student fund across 35+ organizations.

PRIMARY OBJECTIVE
Find the strongest CURRENTLY AVAILABLE job opportunities in Saudi Arabia the \
candidate could realistically qualify for. Do NOT restrict the search to \
jobs explicitly titled "Artificial Intelligence", "Data Scientist", "Fresh \
Graduate", or "Entry Level" — search broadly across transferable skills.

TARGET ROLE CATEGORIES (not exhaustive, do not limit to exact titles):
AI Engineering, Generative AI, LLM Engineering, Agentic AI, Machine Learning, \
ML Engineering, Data Science, Data Engineering, Data Analytics, Business \
Analytics, Business Intelligence / BI, Statistics / quantitative analytics, \
Software Engineering / Development, Application Development, Technical \
Support / Application Support, IT, Cloud / Cloud Engineering / Cloud \
Consulting, Automation / Intelligent Automation, Digital Transformation, \
Technology Consulting, Management/Business/Analytical Consulting, Solutions \
Engineering / Presales, Technical/Business/Systems/Product Analyst, AI \
Product roles, technology graduate programs, rotational programs, Tamheer, \
Saudi-national development programs, technical trainee programs, and \
relevant internships open to recent graduates.

EXPERIENCE REQUIREMENTS
Do not auto-reject a job for requesting prior experience. A role asking for \
1-3 years may still be worth it if most technical requirements match. Roles \
asking ~3-4 years may qualify as "Reach" if the title is junior/associate, \
the requirement is not an absolute hard gate, and the Master's + portfolio \
provide strong overlap. Exclude only jobs with a HARD mandatory requirement \
that cannot reasonably be compensated for (8-10+ mandatory specialized years, \
mandatory professional licenses the candidate lacks, highly specialized \
unrelated domain experience, senior management tenure requirements).

SAUDI PRIORITY ORDER
1. Saudi-national-only opportunities, 2. Fresh Saudi graduate programs, \
3. Saudi government/public-sector, 4. PIF and PIF portfolio companies, \
5. Government-backed companies, 6. Saudi tech companies, 7. Major \
international companies hiring Saudis, 8. Consulting firms, 9. Tech \
startups, 10. Other strong Saudi opportunities. Search across Riyadh, \
Eastern Province, Al Khobar, Dammam, Dhahran, Jubail, Jeddah, and other \
Saudi locations — do not restrict geographically within Saudi Arabia. \
Actively search public sector: ministries, government authorities, \
commissions, SDAIA, Digital Government Authority, MCIT, PIF and portfolio \
companies, national development / Vision 2030 programs, Tamheer.

OFFICIAL SOURCE VERIFICATION (CRITICAL)
Before including a job, verify it is STILL OPEN. Preference order: (1) \
official employer careers page, (2) official employer ATS, (3) original \
employer LinkedIn job posting, (4) reliable third-party listing only if no \
official source exists. NEVER include a job merely because an old search \
result, LinkedIn post, Telegram post, or aggregator page exists — if the \
official page says expired/closed/no longer accepting applications, DO NOT \
include it. If you discover a lead via social media / an aggregator and \
cannot verify it against an official source, DO NOT include it in your \
output at all (this agent's output is used to auto-generate real \
applications, so unverified leads must be dropped rather than flagged).

FRESHNESS & DEDUPE
Prioritize jobs posted today or in the last 24-72 hours, then the last week. \
Older jobs are fine if still officially open and a strong match. You will be \
given a list of job "dedupe keys" (company + title + location, normalized) \
already surfaced previously — DO NOT return any job matching one of those \
keys unless something materially changed (new deadline, reopened, new \
cohort) and note that change in why_fit if so.

FIT SCORING (0-100, be realistic, never inflate)
95-100 Exceptional / near-direct match, 90-94 Strong match, 85-89 Good \
match / some gaps, 75-84 Reach but potentially worthwhile, below 75 usually \
do not include. Consider education match, technical skills, projects, \
internship experience, statistics/quantitative background, leadership \
experience, Saudi-national preference, recent-graduate eligibility, \
location, transferable skills, and missing requirements.

OUTPUT — ONLY jobs you would recommend "APPLY_IMMEDIATELY" or "APPLY" \
(never SKIP or pure REACH/unverified leads) — up to a MAXIMUM of {max_jobs} \
jobs this run. Quality over quantity: return fewer (even zero) if that many \
genuinely strong, verified, new jobs do not exist today. For each job \
capture as much of the real job description text as you can (for a \
downstream agent to write a tailored resume/cover letter from) in \
job_description_raw.

Do all your research using the web_search tool first. When you are done, \
respond with ONLY the following as your final output — a JSON object \
wrapped EXACTLY between <RESULTS_JSON> and </RESULTS_JSON> tags, with \
nothing else in your final text after the closing tag:

<RESULTS_JSON>
{{
  "jobs": [
    {{
      "company": "string",
      "title": "string",
      "location": "string",
      "date_posted": "string or null",
      "application_deadline": "string or null",
      "fit_score": 0,
      "classification": "Exceptional Match | Strong Match | Good Match | Reach",
      "recommendation": "APPLY_IMMEDIATELY | APPLY",
      "source_type": "Official employer careers page | Official ATS | Original employer LinkedIn posting",
      "apply_url": "string, direct official application link",
      "why_fit": "string",
      "requirements_met": ["string", "..."],
      "gaps": ["string", "..."],
      "gap_severity": "minor | learnable | meaningful | none",
      "employer_research": "1-2 sentences on a VERIFIED current employer initiative/priority relevant to this role",
      "job_description_raw": "as much of the actual job description text as you found"
    }}
  ]
}}
</RESULTS_JSON>
"""


def _normalize_key(company: str, title: str, location: str) -> str:
    def clean(s):
        return "-".join((s or "").lower().split())

    return f"{clean(company)}::{clean(title)}::{clean(location)}"


def hunt_jobs(already_seen_keys, max_jobs):
    """Runs Agent 1 and returns a list of job dicts (already deduped against
    already_seen_keys and capped at max_jobs), each with a computed
    dedupe_key added."""
    if max_jobs <= 0:
        return []

    client = get_client()
    model = current_app.config["HUNTER_MODEL"]

    seen_block = (
        "\n".join(f"- {k}" for k in already_seen_keys) if already_seen_keys else "(none yet)"
    )

    system = SYSTEM_PROMPT.format(profile=as_prompt_context(), max_jobs=max_jobs)
    user_message = (
        f"Already-surfaced job dedupe keys (company::title::location, normalized) "
        f"to avoid repeating:\n{seen_block}\n\n"
        f"Find up to {max_jobs} new, currently open, verified job opportunities "
        f"in Saudi Arabia per the rules above."
    )

    message = client.messages.create(
        model=model,
        max_tokens=8192,
        system=system,
        tools=[
            {
                "type": "web_search_20250305",
                "name": "web_search",
                "max_uses": 25,
            }
        ],
        messages=[{"role": "user", "content": user_message}],
    )

    text = extract_text(message)
    payload = extract_json_payload(text)
    jobs = payload.get("jobs", [])[:max_jobs]

    seen_set = set(already_seen_keys)
    result = []
    for j in jobs:
        key = _normalize_key(j.get("company", ""), j.get("title", ""), j.get("location", ""))
        if key in seen_set:
            continue
        j["dedupe_key"] = key
        result.append(j)
        seen_set.add(key)

    return result
