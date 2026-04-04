from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from database import get_db, init_db
from resume_parser import extract_text_from_pdf, extract_text_from_docx
from job_recommender import recommend_jobs
from skill_gap_ai import detect_skill_gap, recommend_resources
from interview_module import get_mock_questions, evaluate_answer
from job_links import generate_job_links
from werkzeug.security import generate_password_hash, check_password_hash
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
            error = "Username and password required"

        elif len(password) < 6:
            error = "Password must be 6 characters"

        else:
            db = get_db()

            existing = db.execute(
                "SELECT id FROM users WHERE username=?",
                (username,)
            ).fetchone()

            if existing:
                error = "Username already exists"

            else:
                db.execute(
                    "INSERT INTO users(username,password) VALUES (?,?)",
                    (username, generate_password_hash(password))
                )

                db.commit()

                return redirect(url_for("login"))

    return render_template("register.html", error=error)

# ================= LOGIN =================
@app.route("/login", methods=["GET","POST"])
def login():

    error=None

    if request.method=="POST":

        username=request.form["username"].strip()
        password=request.form["password"]

        db=get_db()

        user=db.execute(
            "SELECT * FROM users WHERE username=?",
            (username,)
        ).fetchone()

        if user and check_password_hash(user["password"],password):

            session["user_id"]=user["id"]
            session["username"]=user["username"]

            return redirect(url_for("dashboard"))

        else:
            error="Invalid credentials"

    return render_template("login.html",error=error)

# ================= LOGOUT =================
@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))

# ================= DASHBOARD =================
@app.route("/dashboard",methods=["GET","POST"])
def dashboard():

    if "user_id" not in session:

        return redirect(url_for("login"))

    if request.method=="POST":

        if "resume" not in request.files:

            return render_template(
                "dashboard.html",
                error="Upload resume"
            )

        file=request.files["resume"]

        if file.filename=="":
            return render_template(
                "dashboard.html",
                error="Select file"
            )

        filename=file.filename

        if not(filename.endswith(".pdf") or filename.endswith(".docx")):

            return render_template(
                "dashboard.html",
                error="Only PDF/DOCX allowed"
            )

        filepath=os.path.join(UPLOAD_FOLDER,filename)

        file.save(filepath)

        try:

            if filename.endswith(".pdf"):

                resume_text=extract_text_from_pdf(filepath)

            else:

                resume_text=extract_text_from_docx(filepath)

        except Exception as e:

            return render_template(
                "dashboard.html",
                error=str(e)
            )

        if len(resume_text)<50:

            return render_template(
                "dashboard.html",
                error="Resume empty"
            )

        jobs=recommend_jobs(resume_text)

        import job_recommender as jr

        reasons=jr._last_reasons.copy()

        role_actions=[]

        db=get_db()

        for role,match in jobs:

            job_links=generate_job_links(role)

            reason=reasons.get(role,"")

            if match>=70:

                db.execute(

                    """INSERT INTO resume_history
                    (user_id,filename,role,match_score,gaps,resources)
                    VALUES(?,?,?,?,?,?)""",

                    (session["user_id"],
                     filename,
                     role,
                     match,
                     "",
                     "")
                )

                db.commit()

                role_actions.append({

                    "role":role,
                    "match":match,
                    "type":"interview",
                    "reason":reason,
                    "job_links":job_links

                })

            else:

                gaps=detect_skill_gap(role,resume_text)

                resources=recommend_resources(gaps)

                db.execute(

                    """INSERT INTO resume_history
                    (user_id,filename,role,match_score,gaps,resources)
                    VALUES(?,?,?,?,?,?)""",

                    (session["user_id"],
                     filename,
                     role,
                     match,
                     str(gaps),
                     str(resources))

                )

                db.commit()

                role_actions.append({

                    "role":role,
                    "match":match,
                    "type":"learning",
                    "reason":reason,
                    "gaps":gaps,
                    "resources":resources,
                    "job_links":job_links

                })

        return render_template(
            "result.html",
            role_actions=role_actions
        )

    return render_template("dashboard.html")

# ================= INTERVIEW =================
@app.route("/start_interview/<role>")
def start_interview(role):

    if "user_id" not in session:

        return redirect(url_for("login"))

    session["role"]=role

    session["questions"]=get_mock_questions(role)

    session["current_q"]=0

    session["score"]=0

    session["feedback"]=""

    return redirect(url_for("interview_question"))

@app.route("/interview_question")
def interview_question():

    if "user_id" not in session:

        return redirect(url_for("login"))

    questions=session.get("questions",[])

    current=session.get("current_q",0)

    total=len(questions)

    if current>=total:

        return render_template(

            "interview_result.html",

            score=session.get("score",0),

            feedback=session.get("feedback","Good"),

            max_score=total*10

        )

    return render_template(

        "interview.html",

        question=questions[current],

        current=current+1,

        total=total

    )

# ================= TEXT ANSWER =================
@app.route("/submit_answer",methods=["POST"])
def submit_answer():

    if "user_id" not in session:

        return jsonify({"error":"login"}),401

    answer=request.form.get("answer_text","").lower()

    questions=session.get("questions",[])

    current=session.get("current_q",0)

    score,feedback=evaluate_answer(

        questions[current],

        answer

    )

    session["score"]=session.get("score",0)+score

    session["feedback"]=feedback

    session["current_q"]=current+1

    return jsonify({

        "score":score,

        "feedback":feedback,

        "next":url_for("interview_question")

    })

# ================= HISTORY =================
@app.route("/history")
def history():

    if "user_id" not in session:

        return redirect(url_for("login"))

    db=get_db()

    rows=db.execute(

        """SELECT filename,role,match_score,
        created_at FROM resume_history
        WHERE user_id=?
        ORDER BY created_at DESC""",

        (session["user_id"],)

    ).fetchall()

    return render_template(

        "history.html",

        rows=rows

    )

# ================= PING =================
@app.route("/ping")
def ping():

    return "ok"

if __name__=="__main__":

    port=int(os.environ.get("PORT",5000))

    app.run(

        host="0.0.0.0",

        port=port

    )