import urllib.request
import json
import os

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")


def get_mock_questions(role):
    """
    Uses Claude AI to generate 5 relevant interview questions
    for ANY job role. Falls back to generic questions if no API key.
    """
    if not ANTHROPIC_API_KEY:
        return _fallback_questions(role)

    prompt = f"""Generate exactly 5 interview questions for the role: "{role}"

Rules:
- Questions should be specific and relevant to this role
- Mix of technical, situational, and behavioural questions
- Suitable for a fresher or junior-level candidate
- Return ONLY a valid JSON array of 5 question strings

Example format:
["Question 1?", "Question 2?", "Question 3?", "Question 4?", "Question 5?"]"""

    try:
        payload = json.dumps({
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 500,
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

        questions = json.loads(raw.strip())
        return questions if isinstance(questions, list) else _fallback_questions(role)

    except Exception as e:
        print(f"[AI interview questions error] {e}")
        return _fallback_questions(role)


def evaluate_answer(question, answer):
    """
    Uses Claude AI to evaluate a candidate's answer.
    Returns (score, feedback) where score is 0-10.
    """
    if not answer.strip():
        return 0, "No answer provided. Please attempt the question."

    if not ANTHROPIC_API_KEY:
        return _fallback_evaluate(question, answer)

    prompt = f"""You are an interview evaluator. Evaluate this candidate's answer.

Question: {question}
Answer: {answer}

Score the answer from 0 to 10 based on:
- Relevance to the question
- Depth and detail
- Clarity and structure

Return ONLY valid JSON in this exact format:
{{"score": 7, "feedback": "Your feedback here in 1-2 sentences."}}"""

    try:
        payload = json.dumps({
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 200,
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

        result = json.loads(raw.strip())
        score = min(int(result.get("score", 5)), 10)
        feedback = result.get("feedback", "Good attempt!")
        return score, feedback

    except Exception as e:
        print(f"[AI evaluate error] {e}")
        return _fallback_evaluate(question, answer)


# ─────────────────────────────────────────────
#  FALLBACKS
# ─────────────────────────────────────────────
def _fallback_questions(role):
    role_lower = role.lower()

    if any(x in role_lower for x in ["software", "developer", "programmer", "engineer"]):
        return [
            "Tell me about a project you have built or contributed to.",
            "Explain the difference between a stack and a queue.",
            "How do you approach debugging a difficult problem?",
            "What is version control and why is it important?",
            "Where do you see yourself in 3 years as a developer?"
        ]
    if "data" in role_lower:
        return [
            "What is the difference between INNER JOIN and LEFT JOIN in SQL?",
            "How do you handle missing or null values in a dataset?",
            "Describe a data analysis project you have worked on.",
            "What tools have you used for data visualization?",
            "How would you explain a complex data finding to a non-technical person?"
        ]
    if any(x in role_lower for x in ["doctor", "medical", "nurse"]):
        return [
            "How do you handle a patient who is anxious or uncooperative?",
            "Describe a challenging clinical situation and how you managed it.",
            "How do you ensure patient confidentiality in your work?",
            "How do you stay updated with the latest medical guidelines?",
            "How do you prioritise when you have multiple patients needing attention?"
        ]
    if any(x in role_lower for x in ["teacher", "lecturer", "education"]):
        return [
            "How do you make a difficult concept easy to understand for students?",
            "Describe your approach to classroom management.",
            "How do you handle students with different learning abilities?",
            "What teaching methods or tools do you prefer and why?",
            "How do you assess whether students have understood a lesson?"
        ]

    # Generic fallback for any other role
    return [
        f"Why are you interested in the role of {role}?",
        "What are your greatest strengths relevant to this position?",
        "Describe a situation where you solved a difficult problem.",
        "How do you manage your time when handling multiple tasks?",
        "Where do you see yourself professionally in the next 3 years?"
    ]


def _fallback_evaluate(question, answer):
    words = answer.split()
    score = min(len(words) // 8, 10)
    if score >= 8:
        feedback = "Excellent answer with good detail and clarity."
    elif score >= 5:
        feedback = "Good answer. Try to add more specific examples or detail."
    else:
        feedback = "Answer is too brief. Expand with examples and key concepts."
    return score, feedback