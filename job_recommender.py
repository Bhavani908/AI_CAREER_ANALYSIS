import urllib.request
import urllib.error
import json
import os

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# ─────────────────────────────────────────────
#  MAIN FUNCTION  (called from app.py)
# ─────────────────────────────────────────────
def recommend_jobs(resume_text):
    """
    Uses Claude AI to analyse any resume and return
    [(role, match_score), ...] sorted by score, top 5.
    Falls back to keyword matching if API key is missing.
    """
    if not ANTHROPIC_API_KEY:
        return _keyword_fallback(resume_text)

    prompt = f"""You are a professional career counsellor. Analyse the resume text below and suggest the TOP 5 most suitable job roles for this person.

Rules:
- Suggest roles from ANY domain (IT, Non-IT, Medical, Arts, Engineering, Finance, Education, Law, etc.)
- Base suggestions ONLY on what is actually in the resume
- Give a realistic match percentage (0-100) for each role
- Return ONLY a valid JSON array, no extra text

Resume:
\"\"\"
{resume_text[:3000]}
\"\"\"

Return exactly this JSON format:
[
  {{"role": "Role Name", "match": 85, "reason": "One sentence why"}},
  {{"role": "Role Name", "match": 72, "reason": "One sentence why"}},
  {{"role": "Role Name", "match": 65, "reason": "One sentence why"}},
  {{"role": "Role Name", "match": 55, "reason": "One sentence why"}},
  {{"role": "Role Name", "match": 40, "reason": "One sentence why"}}
]"""

    try:
        payload = json.dumps({
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 1000,
            "messages": [{"role": "user", "content": prompt}]
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01"
            },
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        raw = data["content"][0]["text"].strip()

        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        roles = json.loads(raw.strip())

        # Store reasons in a module-level dict so app.py can optionally use them
        global _last_reasons
        _last_reasons = {r["role"]: r.get("reason", "") for r in roles}

        return [(r["role"], float(r["match"])) for r in roles]

    except Exception as e:
        print(f"[AI job recommender error] {e} — falling back to keyword match")
        return _keyword_fallback(resume_text)


# ─────────────────────────────────────────────
#  FALLBACK — keyword matching (original logic)
# ─────────────────────────────────────────────
_last_reasons = {}

_fallback_roles = {
    "Data Analyst":                  ["python", "sql", "excel", "power bi", "statistics", "tableau"],
    "Software Developer":            ["java", "python", "c++", "api", "git", "programming"],
    "Web Developer":                 ["html", "css", "javascript", "react", "node"],
    "Software Tester":               ["testing", "selenium", "automation", "jira"],
    "Accountant":                    ["tally", "gst", "tax", "finance", "accounting"],
    "Business Analyst":              ["analysis", "requirements", "documentation", "stakeholder"],
    "Digital Marketing Executive":   ["seo", "social media", "marketing", "content"],
    "HR Executive":                  ["recruitment", "communication", "hiring", "hr"],
    "Mechanical Engineer":           ["autocad", "solidworks", "design", "manufacturing"],
    "Civil Engineer":                ["construction", "planning", "site", "autocad"],
    "Electrical Engineer":           ["circuits", "electrical", "power", "plc"],
    "Customer Support Executive":    ["communication", "customer", "support", "crm"],
    "Content Writer":                ["writing", "content", "seo", "editing"],
    "Teacher / Lecturer":            ["teaching", "curriculum", "education", "training"],
    "Doctor / Medical Officer":      ["mbbs", "clinical", "patient", "diagnosis", "medicine"],
    "Nurse":                         ["nursing", "patient care", "hospital", "medication"],
    "Graphic Designer":              ["photoshop", "illustrator", "design", "figma", "ui"],
    "Project Manager":               ["project", "planning", "team", "management", "agile"],
    "Sales Executive":               ["sales", "target", "crm", "revenue", "client"],
    "Legal / Law":                   ["law", "legal", "advocate", "litigation", "court"],
}

def _keyword_fallback(resume_text):
    text = resume_text.lower()
    scores = []
    for role, skills in _fallback_roles.items():
        match_count = sum(1 for s in skills if s in text)
        similarity = round((match_count / len(skills)) * 100, 2)
        scores.append((role, similarity))
    scores.sort(key=lambda x: x[1], reverse=True)
    return scores[:5]