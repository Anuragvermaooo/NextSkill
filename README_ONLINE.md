# NextSkill - Online deployment

This version keeps the same Flask pages and separate CSS files, but replaces local Ollama with the Gemini API and supports PostgreSQL for online users.

## Local test
1. Create/activate a virtual environment.
2. `python -m pip install -r requirements.txt`
3. Put your new Gemini API key in `.env` as `GEMINI_API_KEY=...`
4. Run `python app.py`
5. Open `http://127.0.0.1:5000`

## Online deployment
The included `render.yaml` is prepared for Render: it creates a web service plus a PostgreSQL database. Set `GEMINI_API_KEY` as a secret in the hosting dashboard. Do not put the key in HTML, JavaScript, GitHub, or this ZIP.

## Environment variables
- `GEMINI_API_KEY`: your Gemini API key
- `GEMINI_MODEL`: `gemini-2.5-flash`
- `SECRET_KEY`: long random Flask secret (Render can generate it)
- `DATABASE_URL`: PostgreSQL connection string for online deployment

## Important
The old local SQLite database is intentionally not included. Passwords are now hashed before storage.
