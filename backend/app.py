"""Internship Listing Portal - Flask REST API + static frontend server."""
import os
import sqlite3
import uuid
from datetime import date

from flask import Flask, jsonify, request, send_from_directory

from database import ROOT, get_db, init_db, upload_dir
from validators import validate_application, validate_internship

FRONTEND = os.path.join(ROOT, "frontend")
STATUSES = ("Received", "Shortlisted", "Rejected")


def row(r, today=None):
    d = dict(r)
    if "deadline" in d:
        d["expired"] = d["deadline"] < (today or date.today().isoformat())
    return d


def create_app():
    app = Flask(__name__, static_folder=None)
    app.config["MAX_CONTENT_LENGTH"] = 6 * 1024 * 1024
    init_db()

    def err(msg, code, **extra):
        return jsonify({"error": msg, **extra}), code

    def is_admin():
        key = request.headers.get("X-Admin-Key") or request.args.get("key")
        return bool(key) and key == os.environ.get("ADMIN_KEY", "change-me-admin-key")

    @app.after_request
    def cors(r):  # allows the Android (Capacitor) app to call the API
        r.headers["Access-Control-Allow-Origin"] = "*"
        r.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Admin-Key"
        r.headers["Access-Control-Allow-Methods"] = "GET, POST, PATCH, OPTIONS"
        return r

    @app.errorhandler(404)
    def e404(_):
        return err("Not found", 404)

    @app.errorhandler(405)
    def e405(_):
        return err("Method not allowed", 405)

    @app.errorhandler(413)
    def e413(_):
        return err("Validation failed", 400, errors={"resume_file": "File is too large (max 5 MB)."})

    # ---------- internships ----------
    @app.get("/filters")
    def filters():
        with get_db() as db:
            col = lambda c: [r[0] for r in db.execute(f"SELECT DISTINCT {c} FROM internships ORDER BY {c}")]
            return jsonify({"locations": col("location"), "domains": col("domain"),
                            "durations": col("duration_months")})

    @app.get("/internships")
    def list_internships():
        a, where, params = request.args, [], []
        s = a.get("search", "").strip()
        if s:
            like = "%" + s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
            cols = ("title", "company", "domain", "description", "requirements")
            where.append("(" + " OR ".join(f"{c} LIKE ? ESCAPE '\\'" for c in cols) + ")")
            params += [like] * len(cols)
        for k in ("location", "domain", "work_mode"):
            if a.get(k, "").strip():
                where.append(f"{k} = ? COLLATE NOCASE")
                params.append(a[k].strip())
        try:
            for k, col, op in (("duration", "duration_months", "="), ("min_stipend", "stipend", ">=")):
                if a.get(k, "").strip():
                    where.append(f"{col} {op} ?")
                    params.append(int(a[k]))
            page = max(int(a.get("page", 1)), 1)
            per = min(max(int(a.get("per_page", 9)), 1), 50)
        except ValueError:
            return err("duration, min_stipend, page and per_page must be whole numbers", 400)
        order = "deadline ASC, id DESC" if a.get("sort") == "deadline" else "id DESC"
        w = (" WHERE " + " AND ".join(where)) if where else ""
        with get_db() as db:
            total = db.execute(f"SELECT COUNT(*) FROM internships{w}", params).fetchone()[0]
            rows = db.execute(f"SELECT * FROM internships{w} ORDER BY {order} LIMIT ? OFFSET ?",
                              params + [per, (page - 1) * per]).fetchall()
        return jsonify({"items": [row(r) for r in rows], "total": total, "page": page,
                        "pages": max((total + per - 1) // per, 1)})

    @app.get("/internships/<int:iid>")
    def get_internship(iid):
        with get_db() as db:
            r = db.execute("SELECT * FROM internships WHERE id = ?", (iid,)).fetchone()
        return jsonify(row(r)) if r else err("Internship not found", 404)

    @app.post("/internships")
    def add_internship():
        if not is_admin():
            return err("Admin key required", 401)
        errors, d = validate_internship(request.get_json(silent=True) or {})
        if errors:
            return err("Validation failed", 400, errors=errors)
        with get_db() as db:
            cur = db.execute(
                """INSERT INTO internships (title, company, location, domain, duration_months,
                   stipend, work_mode, description, requirements, benefits, deadline)
                   VALUES (:title,:company,:location,:domain,:duration_months,:stipend,
                   :work_mode,:description,:requirements,:benefits,:deadline)""", d)
        return jsonify({"message": "Internship added", "id": cur.lastrowid}), 201

    # ---------- applications ----------
    @app.post("/applications")
    def apply():
        data = request.form.to_dict() if request.form else (request.get_json(silent=True) or {})
        file = request.files.get("resume_file")
        try:
            iid = int(data.get("internship_id"))
        except (TypeError, ValueError):
            return err("Validation failed", 400, errors={"internship_id": "A valid internship is required."})
        with get_db() as db:
            it = db.execute("SELECT * FROM internships WHERE id = ?", (iid,)).fetchone()
        if not it:
            return err("Internship not found", 404)
        if row(it)["expired"]:
            return err("The application deadline for this internship has passed.", 400)
        errors, c = validate_application(data, file)
        if errors:
            return err("Validation failed", 400, errors=errors)
        dup_msg = "You have already applied to this internship with this email."
        with get_db() as db:
            if db.execute("SELECT 1 FROM applications WHERE internship_id=? AND email=?",
                          (iid, c["email"])).fetchone():
                return err(dup_msg, 409)
        stored = None
        if c["has_file"]:  # rename: never trust the client file name
            stored = uuid.uuid4().hex + "." + file.filename.rsplit(".", 1)[-1].lower()
            file.save(os.path.join(upload_dir(), stored))
        try:
            with get_db() as db:
                cur = db.execute(
                    """INSERT INTO applications (internship_id,name,email,phone,resume_link,resume_file,cover_note)
                       VALUES (?,?,?,?,?,?,?)""",
                    (iid, c["name"], c["email"], c["phone"], c["resume_link"], stored, c["cover_note"]))
                aid = cur.lastrowid
                applied = db.execute("SELECT applied_date FROM applications WHERE id=?", (aid,)).fetchone()[0]
        except sqlite3.IntegrityError:  # race condition safety net (UNIQUE constraint)
            if stored:
                os.remove(os.path.join(upload_dir(), stored))
            return err(dup_msg, 409)
        return jsonify({"message": "Application submitted successfully", "application_id": aid,
                        "applied_date": applied}), 201

    @app.get("/applications")
    def list_applications():
        if not is_admin():
            return err("Admin key required", 401)
        sql = """SELECT a.*, i.title AS internship_title, i.company FROM applications a
                 JOIN internships i ON i.id = a.internship_id"""
        params = []
        if request.args.get("internship_id"):
            sql += " WHERE a.internship_id = ?"
            params.append(request.args["internship_id"])
        with get_db() as db:
            rows = db.execute(sql + " ORDER BY a.id DESC", params).fetchall()
        return jsonify({"items": [dict(r) for r in rows], "total": len(rows)})

    @app.patch("/applications/<int:aid>")
    def set_status(aid):
        if not is_admin():
            return err("Admin key required", 401)
        status = (request.get_json(silent=True) or {}).get("status")
        if status not in STATUSES:
            return err("Status must be one of: " + ", ".join(STATUSES), 400)
        with get_db() as db:
            n = db.execute("UPDATE applications SET status=? WHERE id=?", (status, aid)).rowcount
        return jsonify({"message": "Status updated", "status": status}) if n else err("Application not found", 404)

    @app.get("/applications/<int:aid>/resume")
    def resume(aid):
        if not is_admin():
            return err("Admin key required", 401)
        with get_db() as db:
            r = db.execute("SELECT resume_file FROM applications WHERE id=?", (aid,)).fetchone()
        if not r or not r["resume_file"]:
            return err("No uploaded resume", 404)
        return send_from_directory(upload_dir(), r["resume_file"], as_attachment=True)

    # ---------- frontend ----------
    @app.get("/")
    def home():
        return send_from_directory(FRONTEND, "index.html")

    @app.get("/<path:p>")
    def static_files(p):
        if p.split(".")[-1] in ("html", "css", "js") and os.path.exists(os.path.join(FRONTEND, p)):
            return send_from_directory(FRONTEND, p)
        return err("Not found", 404)

    return app


if __name__ == "__main__":
    create_app().run(host=os.environ.get("HOST", "0.0.0.0"), port=int(os.environ.get("PORT", 5000)))
