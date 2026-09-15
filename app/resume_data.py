"""
Master resume facts for Hamza Taheir Bu Obaid.

These are the FIXED, immutable facts extracted verbatim from the uploaded
master resume PDF. Agent 2 (the applicator) is only ever allowed to:
  - rewrite the professional summary
  - reorder skills / projects / experience emphasis
  - reword bullets for ATS alignment (without changing dates, numbers,
    names, or technologies)

It must NEVER invent a new employer, title, date, project name,
certification, metric, or skill that is not present here.
"""

CONTACT = {
    "name": "Hamza Taheir Bu Obaid",
    "location": "Saudi Arabia",
    "phone": "0544456373",
    "phone_tel": "+966544456373",
    "email": "hamzaboabid@gmail.com",
    "linkedin_label": "linkedin.com/in/hamza-bu-obaid-1062862b3",
    "linkedin_url": "https://www.linkedin.com/in/hamza-bu-obaid-1062862b3",
    "github_label": "github.com/Hamza19514",
    "github_url": "https://github.com/Hamza19514",
}

PROFESSIONAL_SUMMARY_DEFAULT = (
    "Artificial Intelligence graduate holding Bachelor's and Master's degrees in "
    "Artificial Intelligence with a minor in Statistics. Equipped with strong "
    "hands-on experience in business analytics, financial planning, stakeholder "
    "coordination, and data-driven decision-making. Highly skilled at analyzing "
    "complex datasets, identifying operational trends, and translating insights "
    "into clear, actionable recommendations. Eager to leverage strong technical, "
    "communication, and problem-solving skills to contribute to business "
    "consulting, organizational transformation, and talent strategy initiatives."
)

EDUCATION = [
    {
        "school": "Illinois Institute of Technology",
        "location": "Chicago, IL",
        "degrees": [
            {
                "degree": "Master of Science in Artificial Intelligence",
                "minor": "Minor in Statistics",
                "gpa": "3.30 / 4",
                "date": "May 2026",
            },
            {
                "degree": "Bachelor of Science in Artificial Intelligence",
                "minor": "Minor in Statistics",
                "gpa": "3.41 / 4",
                "date": None,
            },
        ],
    }
]

EXPERIENCE = [
    {
        "id": "finance_board_advisor",
        "title": "Finance Board Advisor (Business Analytics)",
        "org": "Student Government Association, Illinois Tech",
        "dates": "July 2025 – January 2026",
        "bullets": [
            "Managed $3M in funding for 35+ student organizations.",
            "Handled financial processes with vendors and student groups to improve payment efficiency.",
            "Analyzed financial data to identify trends and support better budget decisions.",
        ],
    }
]

PROJECTS = [
    {
        "id": "job_tracking_agent",
        "name": "AI-Powered Job Application Tracking Agent",
        "dates": "June 2026",
        "bullets": [
            "Built an AI agent to automatically sort and classify 200+ job emails weekly.",
            "Integrated Gmail and Google Calendar to automatically update interview schedules and deadlines.",
            "Reduced manual tracking errors through automated workflow logic.",
        ],
        "tags": ["ai_agent", "automation", "api", "genai", "n8n"],
    },
    {
        "id": "multilingual_chatbot",
        "name": "Multilingual AI Chatbot (Grant-Writing Assistant)",
        "dates": "October 2025 – December 2025",
        "bullets": [
            "Developed an AI tool to help users draft grant applications in Arabic and English.",
            "Used LLAMA and OpenAI models to match user inputs with specific funding requirements.",
            "Improved the quality and consistency of responses by 40%.",
        ],
        "tags": ["llm", "genai", "nlp"],
    },
    {
        "id": "energy_forecasting",
        "name": "Energy Consumption Forecasting (LSTM Model)",
        "dates": "January 2025 – March 2025",
        "bullets": [
            "Designed an AI model to predict electricity usage one hour in advance.",
            "Created a data pipeline to clean and prepare large weather and energy datasets.",
            "Tested and refined the model to ensure accurate performance predictions.",
        ],
        "tags": ["ml", "deep_learning", "data_pipeline", "statistics"],
    },
]

CERTIFICATIONS = [
    "From Excel to Power BI – Knowledge Accelerators (Issued Jan 2026)",
    "Data Analysis Certification (Credential ID: 153879709) – The Global Career Accelerator (Issued Jun 2025)",
    "Data Visualization Certification (Credential ID: 157486855) – The Global Career Accelerator (Issued Aug 2025)",
]

LEADERSHIP = [
    {
        "title": "Soccer Club President & Treasurer",
        "org": "Illinois Tech",
        "dates": "2024 – 2026",
        "bullets": [
            "Managed a $20,000 budget, including financial planning and day-to-day club operations."
        ],
    },
    {
        "title": "Undocumented Students & Allies Outreach Volunteer",
        "org": "Illinois Tech",
        "dates": "2025 – 2026",
        "bullets": [
            "Coordinated meetings between undocumented students and immigration attorneys, "
            "connecting students with relevant support and resources."
        ],
    },
    {
        "title": "Machine Learning Club Member",
        "org": "Illinois Tech",
        "dates": "2024 – 2024",
        "bullets": [
            "Coordinated logistics for guest speaker events, including reserving campus venues, "
            "organizing schedules, and supporting speakers visiting from outside the university."
        ],
    },
]

SKILLS = {
    "technical": {
        "Programming Languages": ["Python", "SQL", "R", "Java"],
        "Data & BI": ["Power BI", "Tableau", "Advanced Excel", "Google Sheets", "MySQL"],
        "Artificial Intelligence": [
            "Machine Learning",
            "Deep Learning",
            "Generative AI",
            "LLMs",
            "PyTorch",
            "TensorFlow",
        ],
        "Tools & Platforms": ["n8n", "OpenAI API", "LLaMA", "Google Cloud Platform (GCP)"],
    },
    "professional": [
        "Financial Planning & Budget Management",
        "Business & Data Analytics",
        "Stakeholder Management",
        "Process Automation & Workflow Design",
        "Data Visualization & Reporting",
    ],
    "personal": [
        "Analytical Thinking",
        "Problem-Solving",
        "Cross-Functional Collaboration",
        "Time Management",
        "Adaptability",
    ],
}

LANGUAGES = {"Arabic": "Native", "English": "Fluent"}

# Numbers/facts that must never be silently dropped or altered by Agent 2
# when it rewords bullets. Used as a lightweight post-generation sanity check.
PROTECTED_FACT_TOKENS = [
    "$3M",
    "35+",
    "200+",
    "40%",
    "$20,000",
    "3.30",
    "3.41",
    "May 2026",
]


def all_project_ids():
    return [p["id"] for p in PROJECTS]


def project_by_id(project_id):
    for p in PROJECTS:
        if p["id"] == project_id:
            return p
    return None


def as_prompt_context():
    """Serializes the master facts into a compact text block for LLM prompts."""
    lines = []
    lines.append(f"NAME: {CONTACT['name']}")
    lines.append(f"LOCATION: {CONTACT['location']}")
    lines.append(f"CONTACT: {CONTACT['email']} | {CONTACT['linkedin_url']} | {CONTACT['github_url']}")
    lines.append("")
    lines.append("EDUCATION:")
    for school in EDUCATION:
        lines.append(f"- {school['school']} ({school['location']})")
        for d in school["degrees"]:
            date = f" | {d['date']}" if d["date"] else ""
            lines.append(f"  - {d['degree']} | {d['minor']} | GPA {d['gpa']}{date}")
    lines.append("")
    lines.append("EXPERIENCE:")
    for e in EXPERIENCE:
        lines.append(f"- {e['title']} | {e['org']} | {e['dates']}")
        for b in e["bullets"]:
            lines.append(f"    * {b}")
    lines.append("")
    lines.append("PROJECTS:")
    for p in PROJECTS:
        lines.append(f"- [{p['id']}] {p['name']} | {p['dates']}")
        for b in p["bullets"]:
            lines.append(f"    * {b}")
    lines.append("")
    lines.append("CERTIFICATIONS:")
    for c in CERTIFICATIONS:
        lines.append(f"- {c}")
    lines.append("")
    lines.append("LEADERSHIP & VOLUNTEER:")
    for l in LEADERSHIP:
        lines.append(f"- {l['title']} | {l['org']} | {l['dates']}")
        for b in l["bullets"]:
            lines.append(f"    * {b}")
    lines.append("")
    lines.append("SKILLS:")
    for cat, items in SKILLS["technical"].items():
        lines.append(f"- {cat}: {', '.join(items)}")
    lines.append(f"- Professional Skills: {', '.join(SKILLS['professional'])}")
    lines.append(f"- Personal Skills: {', '.join(SKILLS['personal'])}")
    lines.append("")
    lines.append(f"LANGUAGES: Arabic (Native), English (Fluent)")
    return "\n".join(lines)
