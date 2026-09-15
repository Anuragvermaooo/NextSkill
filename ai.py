import json
import os

from dotenv import load_dotenv
from google import genai


load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3.6-flash").strip()


def _empty_result(message):
    return {
        "skills": [],
        "missing_skills": [],
        "roadmap": [],
        "interview_questions": [],
        "error": message,
    }


def analyze_resume(resume_text, user_goal):
    if not GEMINI_API_KEY:
        return _empty_result(
            "Gemini API key is not configured. "
            "Add GEMINI_API_KEY to your .env file."
        )

    if GEMINI_API_KEY == "PASTE_YOUR_NEW_GEMINI_API_KEY_HERE":
        return _empty_result(
            "Please add your real Gemini API key to the .env file."
        )

    # Keep request reasonably small.
    resume_text = resume_text[:18000]

    prompt = f"""
You are a professional resume analyst and career advisor.

Analyze the resume only for the user's target career.

TARGET CAREER:
{user_goal}

RESUME:
{resume_text}

Rules:
- List only skills actually present and relevant to the target career.
- Do not invent skills or experience.
- List important missing skills for the target career.
- Give a practical beginner/student roadmap based on the gaps.
- Give exactly 5 relevant interview questions.
- Keep every list concise and useful.
- Return ONLY valid JSON.
- Do not use Markdown.
- Use exactly these keys:

{{
  "skills": ["skill 1"],
  "missing_skills": ["skill 1"],
  "roadmap": ["Step 1: ..."],
  "interview_questions": ["Question 1"]
}}
"""

    try:
        # Official Gemini SDK client.
        client = genai.Client(api_key=GEMINI_API_KEY)

        interaction = client.interactions.create(
            model=MODEL_NAME,
            input=prompt,
            store=False,
        )

        content = getattr(interaction, "output_text", "") or ""

        if not content:
            return _empty_result(
                "Gemini returned an empty response. Please try again."
            )

        # Remove accidental Markdown code fences if Gemini adds them.
        content = content.strip()

        if content.startswith("```json"):
            content = content[7:]

        if content.startswith("```"):
            content = content[3:]

        if content.endswith("```"):
            content = content[:-3]

        content = content.strip()

        result = json.loads(content)

        result.setdefault("skills", [])
        result.setdefault("missing_skills", [])
        result.setdefault("roadmap", [])
        result.setdefault("interview_questions", [])

        result.pop("error", None)

        return result

    except json.JSONDecodeError:
        return _empty_result(
            "Gemini returned invalid JSON. Please try again."
        )

    except Exception as exc:
        message = str(exc)

        if "401" in message or "403" in message:
            return _empty_result(
                "Gemini API key was rejected. "
                "Please check your Gemini API key."
            )

        if "429" in message:
            return _empty_result(
                "Gemini rate limit reached. Please wait and try again."
            )

        if "404" in message:
            return _empty_result(
                f"Gemini model '{MODEL_NAME}' was not found or is unavailable."
            )

        if "timeout" in message.lower():
            return _empty_result(
                "Gemini request timed out. Please try again."
            )

        return _empty_result(f"Gemini API error: {message}")