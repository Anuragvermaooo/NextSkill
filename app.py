import os
import json
from datetime import timedelta

from flask import Flask, render_template, request, redirect, session
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

from db import base, engine, SessionLocal
import models

import PyPDF2
import docx

from ai import analyze_resume

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change-me-in-production")
app.permanent_session_lifetime = timedelta(days=30)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB upload limit

base.metadata.create_all(bind=engine)


@app.route("/")
def home():
    if "user" in session:
        return redirect("/dashboard")
    return redirect("/login")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            return "Email and password are required.", 400
        if len(password) < 6:
            return "Password must be at least 6 characters.", 400

        db = SessionLocal()
        try:
            existing_user = db.query(models.User).filter_by(email=email).first()
            if existing_user:
                return "User already exists. Please login.", 409

            user = models.User(
                email=email,
                password=generate_password_hash(password)
            )
            db.add(user)
            db.commit()
            return redirect("/login")
        finally:
            db.close()

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        db = SessionLocal()
        try:
            user = db.query(models.User).filter_by(email=email).first()
            if user and check_password_hash(user.password, password):
                session.permanent = True
                session["user"] = user.email
                return redirect("/dashboard")
            return "Invalid email or password.", 401
        finally:
            db.close()

    return render_template("login.html")


def extract_resume(file):
    filename = (file.filename or "").lower()

    if filename.endswith(".pdf"):
        reader = PyPDF2.PdfReader(file)
        return "\n".join(page.extract_text() or "" for page in reader.pages).strip()

    if filename.endswith(".docx"):
        document = docx.Document(file)
        return "\n".join(p.text for p in document.paragraphs).strip()

    raise ValueError("Only PDF and DOCX files are supported.")


@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user" not in session:
        return redirect("/login")

    result = None

    if request.method == "POST":
        user_goal = request.form.get("role", "").strip()
        resume_text = request.form.get("resume", "").strip()
        file = request.files.get("file")

        if file and file.filename:
            try:
                resume_text = extract_resume(file)
            except Exception as exc:
                result = {"error": f"File error: {exc}"}

        if not result and not user_goal:
            result = {"error": "Please enter your career goal."}
        elif not result and not resume_text:
            result = {"error": "Please paste your resume or upload a PDF/DOCX file."}

        if not result:
            try:
                result = analyze_resume(resume_text, user_goal)

                if not result.get("error"):
                    db = SessionLocal()
                    try:
                        user = db.query(models.User).filter_by(email=session["user"]).first()
                        if user:
                            report = models.Report(
                                user_id=user.id,
                                resume_text=resume_text,
                                result=json.dumps(result)
                            )
                            db.add(report)
                            db.commit()
                    finally:
                        db.close()
            except Exception as exc:
                result = {"error": f"AI error: {exc}"}

    return render_template("dashboard.html", user=session["user"], result=result)


@app.route("/history")
def history():
    if "user" not in session:
        return redirect("/login")

    db = SessionLocal()
    try:
        user = db.query(models.User).filter_by(email=session["user"]).first()
        if not user:
            session.pop("user", None)
            return redirect("/login")

        reports = (
            db.query(models.Report)
            .filter_by(user_id=user.id)
            .order_by(models.Report.id.desc())
            .all()
        )

        parsed_reports = []
        for report in reports:
            try:
                parsed_result = json.loads(report.result)
            except Exception:
                parsed_result = {}
            parsed_reports.append({
                "resume_text": report.resume_text,
                "result": parsed_result
            })

        return render_template("history.html", reports=parsed_reports)
    finally:
        db.close()


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/health")
def health():
    return {"status": "ok", "app": "NextSkill"}


if __name__ == "__main__":
    app.run(debug=True)
