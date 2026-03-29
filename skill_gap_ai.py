import urllib.request
import json
import os

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# ─────────────────────────────────────────────
#  AI-POWERED SKILL GAP DETECTION
# ─────────────────────────────────────────────
def detect_skill_gap(role, resume_text):
    """
    Uses Claude AI to detect missing skills for ANY role.
    Returns a list of skill gap strings.
    """
    if not ANTHROPIC_API_KEY:
        return _keyword_gap_fallback(role, resume_text)

    prompt = f"""You are a career skills expert. Given this job role and resume, identify the TOP 6 most important skills that are MISSING from this resume for the role.

Role: {role}
Resume:
\"\"\"
{resume_text[:2500]}
\"\"\"

Rules:
- Only list skills genuinely missing from the resume
- Be specific and realistic for this role and domain
- Return ONLY a valid JSON array of skill name strings, nothing else

Example output:
["Skill One", "Skill Two", "Skill Three", "Skill Four", "Skill Five", "Skill Six"]"""

    try:
        payload = json.dumps({
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 400,
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
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        gaps = json.loads(raw.strip())
        return gaps if isinstance(gaps, list) else []

    except Exception as e:
        print(f"[AI skill gap error] {e} — using fallback")
        return _keyword_gap_fallback(role, resume_text)


def recommend_resources(skill_gaps):
    """
    For each skill gap, returns a learning resource URL.
    Uses AI to generate resource links for unknown skills,
    with a curated fallback database for common ones.
    """
    result = {}
    for skill in skill_gaps:
        url = _resources_db.get(skill.lower())
        if not url:
            # Generate a Google search link for unknown skills
            query = skill.replace(" ", "+")
            url = f"https://www.google.com/search?q=learn+{query}+free+course"
        result[skill] = url
    return result


# ─────────────────────────────────────────────
#  FALLBACK — keyword-based gap detection
# ─────────────────────────────────────────────
_role_skills_fallback = {
    "software developer":            ["OOP Concepts", "Data Structures", "Algorithms", "REST API", "Git & Version Control", "System Design"],
    "data analyst":                  ["SQL", "Excel / Spreadsheets", "Python (Pandas)", "Data Visualization", "Statistics", "Power BI / Tableau"],
    "web developer":                 ["HTML & CSS", "JavaScript", "React.js", "Node.js", "Responsive Design", "REST API"],
    "software tester":               ["Test Case Writing", "Selenium Automation", "JIRA", "Bug Reporting", "Agile / Scrum", "API Testing"],
    "accountant":                    ["Tally ERP", "GST Filing", "Tax Compliance", "Financial Reporting", "MS Excel", "Audit Procedures"],
    "business analyst":              ["Requirements Gathering", "Process Documentation", "Stakeholder Management", "Data Analysis", "Use Case Writing", "Agile Methodology"],
    "digital marketing executive":   ["SEO / SEM", "Social Media Marketing", "Google Analytics", "Content Strategy", "Email Marketing", "Paid Ads (Meta/Google)"],
    "hr executive":                  ["Talent Acquisition", "Onboarding Process", "HRMS Tools", "Labor Law Basics", "Employee Engagement", "Performance Management"],
    "mechanical engineer":           ["AutoCAD", "SolidWorks / CATIA", "GD&T", "Manufacturing Processes", "Thermodynamics", "Project Management"],
    "civil engineer":                ["AutoCAD / Civil 3D", "Structural Analysis", "Construction Planning", "Estimation & Costing", "Site Management", "Building Codes"],
    "electrical engineer":           ["Circuit Design", "PLC Programming", "Power Systems", "AutoCAD Electrical", "Electrical Safety", "Project Documentation"],
    "customer support executive":    ["CRM Tools", "Active Listening", "Email Etiquette", "Conflict Resolution", "Product Knowledge", "Ticketing Systems"],
    "content writer":                ["SEO Writing", "Copywriting", "Research Skills", "CMS (WordPress)", "Editing & Proofreading", "Social Media Content"],
    "teacher / lecturer":            ["Curriculum Design", "Lesson Planning", "Classroom Management", "Assessment Techniques", "Ed-Tech Tools", "Communication Skills"],
    "doctor / medical officer":      ["Clinical Diagnosis", "Patient Communication", "Medical Documentation", "Emergency Protocols", "Prescription Management", "Research Skills"],
    "nurse":                         ["Patient Assessment", "IV & Medication Administration", "Wound Care", "Electronic Health Records", "Emergency Response", "Patient Education"],
    "graphic designer":              ["Adobe Photoshop", "Adobe Illustrator", "Figma / XD", "Typography", "Brand Identity", "UI/UX Basics"],
    "project manager":               ["Agile / Scrum", "Risk Management", "MS Project / JIRA", "Budget Planning", "Stakeholder Communication", "Resource Allocation"],
    "sales executive":               ["CRM Software", "Lead Generation", "Negotiation Skills", "Product Demonstration", "Objection Handling", "Sales Reporting"],
    "legal / law":                   ["Legal Research", "Contract Drafting", "Litigation Support", "Legal Documentation", "Client Advisory", "Court Procedures"],
}

def _keyword_gap_fallback(role, resume_text):
    text = resume_text.lower()
    skills = _role_skills_fallback.get(role.lower(), [
        "Communication Skills", "MS Office", "Team Collaboration",
        "Problem Solving", "Time Management", "Domain Knowledge"
    ])
    return [s for s in skills if s.lower() not in text]


# ─────────────────────────────────────────────
#  LEARNING RESOURCES DATABASE
# ─────────────────────────────────────────────
_resources_db = {
    # Programming & Dev
    "sql":                        "https://www.w3schools.com/sql/",
    "python":                     "https://www.learnpython.org/",
    "python (pandas)":            "https://www.geeksforgeeks.org/python-pandas-tutorial/",
    "html & css":                 "https://www.w3schools.com/html/",
    "javascript":                 "https://www.javascript.info/",
    "react.js":                   "https://react.dev/learn",
    "node.js":                    "https://nodejs.dev/learn",
    "git & version control":      "https://www.atlassian.com/git/tutorials",
    "rest api":                   "https://restfulapi.net/",
    "data structures":            "https://www.geeksforgeeks.org/data-structures/",
    "algorithms":                 "https://www.geeksforgeeks.org/fundamentals-of-algorithms/",
    "oop concepts":               "https://www.geeksforgeeks.org/object-oriented-programming-oops-concept-in-java/",
    "system design":              "https://www.geeksforgeeks.org/system-design-tutorial/",
    # Data / Analytics
    "excel / spreadsheets":       "https://excel-practice-online.com/",
    "ms excel":                   "https://excel-practice-online.com/",
    "data visualization":         "https://www.tableau.com/learn/training",
    "statistics":                 "https://www.khanacademy.org/math/statistics-probability",
    "power bi / tableau":         "https://learn.microsoft.com/en-us/training/powerplatform/power-bi",
    # Testing
    "test case writing":          "https://www.guru99.com/test-case.html",
    "selenium automation":        "https://www.selenium.dev/documentation/",
    "jira":                       "https://www.atlassian.com/software/jira/guides",
    "bug reporting":              "https://www.guru99.com/bug-life-cycle.html",
    "api testing":                "https://www.postman.com/api-platform/api-testing/",
    "agile / scrum":              "https://www.atlassian.com/agile/scrum",
    # Finance / Accounts
    "tally erp":                  "https://tallysolutions.com/tally-for-gst/",
    "gst filing":                 "https://cleartax.in/s/gst-guide",
    "tax compliance":             "https://www.incometaxindia.gov.in/",
    # Marketing
    "seo / sem":                  "https://moz.com/learn/seo",
    "google analytics":           "https://skillshop.withgoogle.com/",
    "content strategy":           "https://contentmarketinginstitute.com/",
    "paid ads (meta/google)":     "https://skillshop.withgoogle.com/",
    # Design
    "adobe photoshop":            "https://www.adobe.com/learn/photoshop.html",
    "figma / xd":                 "https://www.figma.com/resources/learn-design/",
    "typography":                 "https://www.canva.com/learn/typography/",
    # Soft Skills / General
    "communication skills":       "https://www.toastmasters.org/",
    "crm tools":                  "https://www.salesforce.com/in/crm/what-is-crm/",
    "crm software":               "https://www.hubspot.com/crm",
    "problem solving":            "https://www.mindtools.com/pages/main/newMN_TMC.htm",
    "time management":            "https://www.mindtools.com/pages/article/newHTE_00.htm",
    "ms office":                  "https://support.microsoft.com/en-us/training",
    # Medical
    "patient assessment":         "https://www.coursera.org/courses?query=patient+assessment",
    "clinical diagnosis":         "https://www.coursera.org/courses?query=clinical+diagnosis",
    "electronic health records":  "https://www.coursera.org/courses?query=electronic+health+records",
    # Legal
    "legal research":             "https://www.coursera.org/courses?query=legal+research",
    "contract drafting":          "https://www.coursera.org/courses?query=contract+drafting",
    # Project Management
    "risk management":            "https://www.pmi.org/learning/library",
    "budget planning":            "https://www.coursera.org/courses?query=project+budget",
    "stakeholder communication":  "https://www.coursera.org/courses?query=stakeholder+management",
}