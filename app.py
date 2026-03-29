from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from database import get_db, init_db
from resume_parser import extract_text_from_pdf, extract_text_from_docx
from job_recommender import recommend_jobs
from skill_gap_ai import detect_skill_gap, recommend_resources
from interview_module import get_mock_questions, evaluate_answer
from job_links import generate_job_links
from werkzeug.security import generate_password_hash, check_password_hash
import speech_recognition as sr
import os
import tempfile

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "career_ai_secret_dev_only")

UPLOAD_FOLDER = tempfile.gettempdir()
init_db()


# ================= HOME =================
@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


# ================= REGISTER =================
@app.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        if not username or not password:
            error = "Username and password are required."
        elif len(password) < 6:
            error = "Password must be at least 6 characters."
        else:
            db = get_db()
            existing = db.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
            if existing:
                error = "Username already taken. Please choose another."
            else:
                db.execute("INSERT INTO users(username, password) VALUES (?, ?)",
                           (username, generate_password_hash(password)))
                db.commit()
                return redirect(url_for("login"))
    return render_template("register.html", error=error)


# ================= LOGIN =================
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("dashboard"))
        else:
            error = "Invalid username or password."
    return render_template("login.html", error=error)


# ================= LOGOUT =================
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ================= DASHBOARD =================
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        if "resume" not in request.files or request.files["resume"].filename == "":
            return render_template("dashboard.html", error="Please upload a resume file.")

        file = request.files["resume"]
        filename = file.filename

        if not (filename.endswith(".pdf") or filename.endswith(".docx")):
            return render_template("dashboard.html", error="Only PDF and DOCX files are supported.")

        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        try:
            if filename.endswith(".pdf"):
                resume_text = extract_text_from_pdf(filepath)
            else:
                resume_text = extract_text_from_docx(filepath)
        except Exception as e:
            return render_template("dashboard.html", error=f"Could not read file: {str(e)}")

        if len(resume_text.strip()) < 50:
            return render_template("dashboard.html",
                                   error="Resume appears empty or unreadable. Please check your file.")

        jobs = recommend_jobs(resume_text)

        # Pull AI reasons if they were generated
        import job_recommender as jr
        reasons = jr._last_reasons.copy()

        role_actions = []
        db = get_db()

        for role, match in jobs:
            job_links = generate_job_links(role)
            reason = reasons.get(role, "")

            if match >= 70:
                db.execute(
                    "INSERT INTO resume_history(user_id,filename,role,match_score,gaps,resources) VALUES(?,?,?,?,?,?)",
                    (session["user_id"], filename, role, match, "", "")
                )
                db.commit()
                role_actions.append({
                    "role": role, "match": match, "type": "interview",
                    "reason": reason, "job_links": job_links
                })
            else:
                gaps = detect_skill_gap(role, resume_text)
                resources = recommend_resources(gaps)
                db.execute(
                    "INSERT INTO resume_history(user_id,filename,role,match_score,gaps,resources) VALUES(?,?,?,?,?,?)",
                    (session["user_id"], filename, role, match, str(gaps), str(resources))
                )
                db.commit()
                role_actions.append({
                    "role": role, "match": match, "type": "learning",
                    "reason": reason, "gaps": gaps, "resources": resources,
                    "job_links": job_links
                })

        return render_template("result.html", role_actions=role_actions)

    return render_template("dashboard.html")


# ================= INTERVIEW =================
@app.route("/start_interview/<role>")
def start_interview(role):
    if "user_id" not in session:
        return redirect(url_for("login"))
    session["role"] = role
    session["questions"] = get_mock_questions(role)
    session["current_q"] = 0
    session["score"] = 0
    session["feedback"] = ""
    return redirect(url_for("interview_question"))


@app.route("/interview_question")
def interview_question():
    if "user_id" not in session:
        return redirect(url_for("login"))
    questions = session.get("questions", [])
    current_q = session.get("current_q", 0)
    total = len(questions)
    if not questions or current_q >= total:
        final_score = session.get("score", 0)
        feedback = session.get("feedback", "Good attempt!")
        return render_template("interview_result.html",
                               score=final_score, feedback=feedback,
                               max_score=total * 10)
    return render_template("interview.html",
                           question=questions[current_q],
                           current=current_q + 1, total=total)


# ================= TEXT ANSWER =================
@app.route("/submit_answer", methods=["POST"])
def submit_answer():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401
    answer_text = request.form.get("answer_text", "").lower()
    questions = session.get("questions", [])
    current_q = session.get("current_q", 0)
    if current_q >= len(questions):
        return jsonify({"score": 0, "feedback": "No more questions",
                        "next": url_for("interview_question")})
    score, feedback = evaluate_answer(questions[current_q], answer_text)
    session["score"] = session.get("score", 0) + score
    session["feedback"] = feedback
    session["current_q"] = current_q + 1
    return jsonify({"score": score, "feedback": feedback,
                    "next": url_for("interview_question")})


# ================= VOICE ANSWER =================
@app.route("/submit_voice", methods=["POST"])
def submit_voice():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401
    try:
        file = request.files["audio_data"]
        wav_path = os.path.join(UPLOAD_FOLDER, "answer.wav")
        file.save(wav_path)
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio = recognizer.record(source)
        try:
            text = recognizer.recognize_google(audio).lower()
        except Exception:
            text = ""
        questions = session.get("questions", [])
        current_q = session.get("current_q", 0)
        if current_q >= len(questions):
            return jsonify({"score": 0, "feedback": "No more questions",
                            "next": url_for("interview_question")})
        score, feedback = evaluate_answer(questions[current_q], text)
        session["score"] = session.get("score", 0) + score
        session["feedback"] = feedback
        session["current_q"] = current_q + 1
        return jsonify({"score": score, "feedback": feedback,
                        "next": url_for("interview_question")})
    except Exception as e:
        return jsonify({"score": 0, "feedback": f"Audio processing failed: {str(e)}",
                        "next": url_for("interview_question")})


# ================= HISTORY =================
@app.route("/history")
def history():
    if "user_id" not in session:
        return redirect(url_for("login"))
    db = get_db()
    records = db.execute(
        "SELECT * FROM resume_history WHERE user_id=? ORDER BY id DESC",
        (session["user_id"],)
    ).fetchall()
    return render_template("history.html", records=records)


# ================= HEALTH CHECK =================
@app.route("/ping")
def ping():
    return "pong", 200


# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=False)