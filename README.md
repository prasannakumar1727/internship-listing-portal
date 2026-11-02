# Internship Listing Portal

Full-stack web app (Week 3 project): browse, search and filter internships, view details, apply online. Applications are stored in SQLite.

- **Frontend:** HTML, CSS, JavaScript (responsive, no build step)
- **Backend:** Python + Flask REST API
- **Database:** SQLite (`database/portal.db`, created automatically, seeded from `data/sample_internships.json`)
- **Android:** Capacitor wrapper (see below)

## Features
Cards listing; keyword search (role/skill/company); filters for location, domain, duration, stipend, work mode (combinable); sort (newest/deadline); pagination; detail page; application form (resume link or PDF/DOCX upload up to 5 MB, cover note); validation in browser and backend; duplicate-application block (UNIQUE email + internship); confirmation page with application ID; deadline check; admin page (add internships, view applications, set status Received/Shortlisted/Rejected). Sample data is fake.

## Run on Windows
```bat
cd internship-portal
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python backend\app.py
```
Open http://localhost:5000. Admin page: http://localhost:5000/admin.html (key = `ADMIN_KEY` in `.env`).

## Tests
```bat
python -m unittest discover -s tests -v
```
Manual cases and results: `tests/test_cases.md`.

## Database tables
- `internships(id, title, company, location, domain, duration_months, stipend, work_mode, description, requirements, benefits, deadline, created_at)`
- `applications(id, internship_id -> internships.id, name, email, phone, resume_link, resume_file, cover_note, status, applied_date)`, `UNIQUE(email, internship_id)`

## API
| Method | Endpoint | Notes |
|---|---|---|
| GET | `/internships?search=&location=&domain=&duration=&work_mode=&min_stipend=&sort=newest\|deadline&page=&per_page=` | 200 |
| GET | `/internships/<id>` | 200 / 404 |
| POST | `/applications` (form-data) | 201 / 400 invalid / 404 / 409 duplicate |
| GET | `/applications` | admin (`X-Admin-Key` header), 200 / 401 |
| POST | `/internships` | admin, 201 / 400 / 401 |
| PATCH | `/applications/<id>` | admin, set status |
| GET | `/filters` | filter option values |

## Upload to GitHub
Create an empty repository on github.com first (no README), then:
```bat
git init
git add .
git commit -m "Internship Listing Portal"
git branch -M main
git remote add origin https://github.com/<YOUR-USERNAME>/<YOUR-REPO>.git
git push -u origin main
```
Or with GitHub CLI: `gh repo create internship-portal --public --source=. --push`

## Build the Android APK (Windows)
Needs Node.js 18+, Android Studio (SDK installed) and JDK 17+. The app is a wrapper around the same frontend, so the Flask backend must be reachable from the phone.
1. Start the backend (`python backend\app.py`); phone and PC on the same Wi-Fi; allow port 5000 in Windows Firewall.
2. Find your PC IP (`ipconfig`) and set it in `frontend\config.js`: `window.API_BASE = "http://192.168.x.x:5000";`
3. Then:
```bat
npm install
npx cap add android
npx cap sync android
cd android
gradlew.bat assembleDebug
```
APK: `android\app\build\outputs\apk\debug\app-debug.apk` (or use `npx cap open android` and Build > Build APK).

## Notes
- Only fake data; never commit `.env` or uploaded resumes.
- The built-in admin key is for learning purposes; use a proper login for real deployments.
- Screenshots: add desktop and mobile screenshots to `screenshots/`.
