"""Form validation helpers (used on every request; the browser validates too)."""
import re
from datetime import date

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}$")
PHONE_RE = re.compile(r"^[6-9]\d{9}$")
URL_RE = re.compile(r"^https?://[^\s/]+\.[^\s/]+\S*$", re.I)
ALLOWED_EXT = {"pdf", "docx"}
MAX_FILE = 5 * 1024 * 1024
WORK_MODES = ("Remote", "Onsite", "Hybrid")


def clean_phone(p):
    p = re.sub(r"[\s\-()]", "", p or "")
    return re.sub(r"^(\+91|91|0)(?=\d{10}$)", "", p)


def validate_application(data, file):
    """Return (errors, cleaned). `file` is a werkzeug FileStorage or None."""
    errors = {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    phone = clean_phone(data.get("phone"))
    link = (data.get("resume_link") or "").strip()
    note = (data.get("cover_note") or "").strip()

    if not name:
        errors["name"] = "Name is required."
    elif len(name) < 2 or len(name) > 100:
        errors["name"] = "Name must be 2-100 characters."
    if not email:
        errors["email"] = "Email is required."
    elif len(email) > 254 or not EMAIL_RE.match(email):
        errors["email"] = "Enter a valid email address (e.g. name@example.com)."
    if not phone:
        errors["phone"] = "Phone number is required."
    elif not PHONE_RE.match(phone):
        errors["phone"] = "Enter a valid 10-digit mobile number."
    if len(note) > 500:
        errors["cover_note"] = "Cover note must be 500 characters or fewer."

    has_file = bool(file and file.filename)
    if link and not URL_RE.match(link):
        errors["resume_link"] = "Enter a valid link starting with http:// or https://."
    if has_file:
        ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
        head = file.stream.read(4)
        file.stream.seek(0, 2)
        size = file.stream.tell()
        file.stream.seek(0)
        if ext not in ALLOWED_EXT:
            errors["resume_file"] = "Only PDF or DOCX files are allowed."
        elif size > MAX_FILE:
            errors["resume_file"] = "File is too large (max 5 MB)."
        elif size == 0 or (ext == "pdf" and head != b"%PDF") or (ext == "docx" and head[:2] != b"PK"):
            errors["resume_file"] = "File content does not match its type."
    if not link and not has_file and "resume_link" not in errors:
        errors["resume_link"] = "Provide a resume link or upload a PDF/DOCX file."

    return errors, {"name": name, "email": email, "phone": phone,
                    "resume_link": link or None, "cover_note": note or None, "has_file": has_file}


def validate_internship(d):
    errors, out = {}, {}
    for k in ("title", "company", "location", "domain", "description"):
        v = str(d.get(k) or "").strip()
        if not v:
            errors[k] = "Required."
        out[k] = v
    for k in ("requirements", "benefits"):
        v = d.get(k)
        if isinstance(v, list):
            v = "\n".join(str(x).strip() for x in v if str(x).strip())
        v = str(v or "").strip()
        if not v:
            errors[k] = "Required (one item per line)."
        out[k] = v
    out["work_mode"] = str(d.get("work_mode") or "").strip().capitalize()
    if out["work_mode"] not in WORK_MODES:
        errors["work_mode"] = "Must be Remote, Onsite or Hybrid."
    for k, lo, hi in (("duration_months", 1, 24), ("stipend", 0, 10_000_000)):
        try:
            out[k] = int(d.get(k))
            if not lo <= out[k] <= hi:
                raise ValueError
        except (TypeError, ValueError):
            errors[k] = f"Enter a whole number between {lo} and {hi}."
    try:
        out["deadline"] = date.fromisoformat(str(d.get("deadline") or "")).isoformat()
    except ValueError:
        errors["deadline"] = "Use the format YYYY-MM-DD."
    return errors, out
