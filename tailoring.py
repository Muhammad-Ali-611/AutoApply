from typing import List

def extract_keywords(text: str, limit: int = 15) -> List[str]:
    common = {"and","or","the","with","for","to","in","on","of","a","an"}
    words = [w.strip(".,:;()[]").lower() for w in text.split()]
    freq = {}
    for w in words:
        if len(w) > 2 and w not in common:
            freq[w] = freq.get(w, 0) + 1
    return [w for w, _ in sorted(freq.items(), key=lambda x: x[1], reverse=True)[:limit]]

def tailor_bullets(base_bullets: List[str], job_desc: str) -> List[str]:
    kws = set(extract_keywords(job_desc))
    prioritized = []
    for b in base_bullets:
        score = sum(1 for k in kws if k in b.lower())
        prioritized.append((score, b))
    prioritized.sort(reverse=True, key=lambda x: x[0])
    return [b for _, b in prioritized]

def generate_cover_letter(name: str, company: str, role: str, highlights: List[str]) -> str:
    lines = [
        f"Dear Hiring Team at {company},",
        f"I'm excited to apply for the {role} role. My background aligns with your needs:",
    ]
    for h in highlights[:5]:
        lines.append(f"- {h}")
    lines += [
        "I'd welcome the opportunity to discuss how I can contribute.",
        f"Sincerely,\n{name}"
    ]
    return "\n".join(lines)

# New functions for per-application tailoring
from typing import Dict

SECTION_HEADERS = {
    "skills": "Skills",
    "experience": "Experience",
    "projects": "Projects",
    "education": "Education",
    "summary": "Summary",
}

def extract_qualifications(job_desc: str) -> Dict[str, List[str]]:
    lines = [l.strip("•-* \t").strip() for l in job_desc.splitlines() if l.strip()]
    req, pref = [], []
    mode = None
    for l in lines:
        ll = l.lower()
        if any(h in ll for h in ["requirements", "qualifications", "what you'll need", "must have"]):
            mode = "req"
            continue
        if any(h in ll for h in ["nice to have", "preferred", "bonus", "good to have"]):
            mode = "pref"
            continue
        if len(l.split()) > 2 and len(l) < 220:
            if mode == "req":
                req.append(l)
            elif mode == "pref":
                pref.append(l)
    return {"required": req, "preferred": pref}

def extract_skills(job_desc: str, extra_stop: List[str] = None, limit: int = 20) -> List[str]:
    stop = set(extra_stop or [])
    stop.update({"experience", "years", "software", "developer", "engineering", "engineer"})
    kws = extract_keywords(job_desc, limit=60)
    skills = []
    for k in kws:
        if k in stop:
            continue
        if any(ch.isdigit() for ch in k):
            continue
        if len(k) <= 2:
            continue
        skills.append(k)
        if len(skills) >= limit:
            break
    return skills

def build_skills_line(base_skills: List[str], job_desc: str, limit: int = 18) -> str:
    jd_skills = extract_skills(job_desc, limit=limit * 2)
    jd_set = {s.lower() for s in jd_skills}
    prioritized = []
    for s in base_skills:
        score = 1 if s.lower() in jd_set else 0
        prioritized.append((score, s))
    prioritized.sort(key=lambda x: (x[0], x[1].lower()), reverse=True)
    picked = [s for _, s in prioritized[:limit]]
    return ", ".join(picked)

def assemble_resume_text(
    name: str,
    contact: Dict[str, str],
    base_summary: str,
    base_skills: List[str],
    experience_bullets: List[str],
    project_bullets: List[str],
    education_lines: List[str],
    job_desc: str,
    max_exp_bullets: int = 8,
    max_proj_bullets: int = 4
) -> str:
    exp = tailor_bullets(experience_bullets, job_desc)[:max_exp_bullets]
    projs = tailor_bullets(project_bullets, job_desc)[:max_proj_bullets]
    skills_line = build_skills_line(base_skills, job_desc)

    contact_parts = [contact.get("email",""), contact.get("phone",""), contact.get("location",""), contact.get("linkedin",""), contact.get("github","")]
    contact_line = " | ".join([p for p in contact_parts if p])

    sections = []
    sections.append(f"{name}\n{contact_line}\n")
    if base_summary:
        sections.append(f"{SECTION_HEADERS['summary']}\n- {base_summary.strip()}")
    if skills_line:
        sections.append(f"{SECTION_HEADERS['skills']}\n{skills_line}")
    if exp:
        sections.append(f"{SECTION_HEADERS['experience']}\n" + "\n".join(f"- {b}" for b in exp))
    if projs:
        sections.append(f"{SECTION_HEADERS['projects']}\n" + "\n".join(f"- {b}" for b in projs))
    if education_lines:
        sections.append(f"{SECTION_HEADERS['education']}\n" + "\n".join(f"- {e}" for e in education_lines))

    return "\n\n".join(sections).strip()

def generate_application_package(
    applicant: Dict[str, str],
    base_resume: Dict[str, List[str] | str],
    job_meta: Dict[str, str]
) -> Dict[str, str]:
    name = applicant.get("name", "")
    contact = {
        "email": applicant.get("email", ""),
        "phone": applicant.get("phone", ""),
        "location": applicant.get("location", ""),
        "linkedin": applicant.get("linkedin", ""),
        "github": applicant.get("github", ""),
    }
    company = job_meta.get("company", "the company")
    role = job_meta.get("role", "the role")
    job_desc = job_meta.get("job_desc", "")

    resume_text = assemble_resume_text(
        name=name,
        contact=contact,
        base_summary=base_resume.get("summary", ""),
        base_skills=list(base_resume.get("skills", [])),
        experience_bullets=list(base_resume.get("experience_bullets", [])),
        project_bullets=list(base_resume.get("project_bullets", [])),
        education_lines=list(base_resume.get("education_lines", [])),
        job_desc=job_desc,
    )

    top_highlights = tailor_bullets(
        list(base_resume.get("experience_bullets", [])) + list(base_resume.get("project_bullets", [])),
        job_desc
    )[:5]

    cover_letter_text = generate_cover_letter(
        name=name,
        company=company,
        role=role,
        highlights=top_highlights
    )

    keywords_csv = ", ".join(extract_skills(job_desc, limit=20))
    return {
        "resume_text": resume_text,
        "cover_letter_text": cover_letter_text,
        "keywords_csv": keywords_csv,
    }