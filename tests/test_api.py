"""Automated API tests. Run: python -m unittest discover -s tests -v"""
import io, os, sys, tempfile, unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
KEY = {"X-Admin-Key": "testkey"}
VALID = {"internship_id": "1", "name": "Priya Sharma", "email": "priya@example.com",
         "phone": "9876543210", "resume_link": "https://example.com/priya.pdf",
         "cover_note": "I am interested in front-end development."}


class PortalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ.update(PORTAL_DB=os.path.join(self.tmp.name, "t.db"), UPLOAD_DIR=self.tmp.name, ADMIN_KEY="testkey")
        import app as portal
        self.portal = portal
        self.c = portal.create_app().test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def post(self, **over):
        d = {**VALID, **over}
        return self.c.post("/applications", data=d, content_type="multipart/form-data")

    def test_list_all_loaded(self):
        r = self.c.get("/internships?per_page=50").get_json()
        self.assertEqual(r["total"], 13)

    def test_tc01_search_design(self):  # TC_INTERN_01
        items = self.c.get("/internships?search=design").get_json()["items"]
        self.assertTrue(items)
        self.assertTrue(all("design" in (i["title"] + i["domain"] + i["description"] + i["requirements"]).lower() for i in items))

    def test_tc02_filter_location_mode(self):  # TC_INTERN_02
        items = self.c.get("/internships?location=Chennai&work_mode=Hybrid").get_json()["items"]
        self.assertTrue(items)
        self.assertTrue(all(i["location"] == "Chennai" and i["work_mode"] == "Hybrid" for i in items))

    def test_search_plus_filter_and_empty(self):
        self.assertTrue(self.c.get("/internships?search=design&work_mode=Remote").get_json()["items"])
        self.assertEqual(self.c.get("/internships?search=zzzqqq").get_json()["total"], 0)
        self.assertEqual(self.c.get("/internships?search=").get_json()["total"], 13)

    def test_special_characters_search(self):
        for s in ("%", "_", "'; DROP TABLE internships;--", "<script>"):
            r = self.c.get("/internships", query_string={"search": s})
            self.assertEqual(r.status_code, 200)
        self.assertEqual(self.c.get("/internships").get_json()["total"], 13)

    def test_sort_and_pagination(self):
        r = self.c.get("/internships?sort=deadline&per_page=5").get_json()
        d = [i["deadline"] for i in r["items"]]
        self.assertEqual(d, sorted(d))
        self.assertEqual(len(r["items"]), 5); self.assertEqual(r["pages"], 3)
        self.assertEqual(self.c.get("/internships?page=abc").status_code, 400)

    def test_detail_and_tc06_not_found(self):  # TC_INTERN_06
        self.assertEqual(self.c.get("/internships/1").status_code, 200)
        r = self.c.get("/internships/9999")
        self.assertEqual(r.status_code, 404)
        self.assertIn("not found", r.get_json()["error"].lower())

    def test_tc03_valid_application(self):  # TC_INTERN_03
        r = self.post()
        self.assertEqual(r.status_code, 201)
        aid = r.get_json()["application_id"]
        apps = self.c.get("/applications", headers=KEY).get_json()["items"]
        self.assertEqual([a["id"] for a in apps], [aid])
        self.assertTrue(apps[0]["applied_date"])

    def test_tc04_invalid_email_not_saved(self):  # TC_INTERN_04
        r = self.post(email="not-an-email")
        self.assertEqual(r.status_code, 400)
        self.assertIn("email", r.get_json()["errors"])
        self.assertEqual(self.c.get("/applications", headers=KEY).get_json()["total"], 0)

    def test_validation_fields(self):
        self.assertIn("phone", self.post(phone="123").get_json()["errors"])
        self.assertIn("name", self.post(name="").get_json()["errors"])
        self.assertIn("resume_link", self.post(resume_link="").get_json()["errors"])
        self.assertIn("cover_note", self.post(cover_note="x" * 501).get_json()["errors"])

    def test_tc05_duplicate_blocked(self):  # TC_INTERN_05
        self.assertEqual(self.post().status_code, 201)
        r = self.post(email="PRIYA@example.com")  # case-insensitive
        self.assertEqual(r.status_code, 409)
        self.assertIn("already applied", r.get_json()["error"])
        self.assertEqual(self.post(internship_id="2").status_code, 201)  # other internship OK

    def test_expired_and_unknown_internship(self):
        self.assertEqual(self.post(internship_id="13").status_code, 400)
        self.assertEqual(self.post(internship_id="9999").status_code, 404)

    def test_resume_upload_rules(self):
        def up(name, body):
            return self.c.post("/applications", data={**VALID, "resume_link": "", "resume_file": (io.BytesIO(body), name)},
                               content_type="multipart/form-data")
        self.assertEqual(up("cv.exe", b"MZ....").status_code, 400)
        self.assertEqual(up("cv.pdf", b"not a pdf").status_code, 400)
        self.assertEqual(up("cv.pdf", b"%PDF-1.4 test").status_code, 201)
        self.assertEqual(len([f for f in os.listdir(self.tmp.name) if f.endswith(".pdf")]), 1)
        big = b"%PDF" + b"0" * (5 * 1024 * 1024 + 10)
        self.assertEqual(up("big.pdf", big).status_code, 400)

    def test_admin_protected_and_status(self):
        self.assertEqual(self.c.get("/applications").status_code, 401)
        aid = self.post().get_json()["application_id"]
        r = self.c.patch(f"/applications/{aid}", json={"status": "Shortlisted"}, headers=KEY)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.c.patch(f"/applications/{aid}", json={"status": "Bogus"}, headers=KEY).status_code, 400)

    def test_admin_add_internship(self):
        body = {"title": "T", "company": "C", "location": "L", "domain": "D", "work_mode": "remote",
                "duration_months": 2, "stipend": 0, "description": "d", "requirements": "a\nb", "benefits": "x", "deadline": "2027-05-01"}
        self.assertEqual(self.c.post("/internships", json=body).status_code, 401)
        self.assertEqual(self.c.post("/internships", json=body, headers=KEY).status_code, 201)
        self.assertEqual(self.c.post("/internships", json={**body, "deadline": "bad"}, headers=KEY).status_code, 400)

    def test_records_persist_after_restart(self):
        self.post()
        c2 = self.portal.create_app().test_client()  # simulated server restart
        self.assertEqual(c2.get("/applications", headers=KEY).get_json()["total"], 1)
        self.assertEqual(c2.get("/internships?per_page=50").get_json()["total"], 13)

    def test_frontend_served(self):
        self.assertEqual(self.c.get("/").status_code, 200)
        self.assertEqual(self.c.get("/script.js").status_code, 200)
        self.assertEqual(self.c.get("/../backend/app.py").status_code, 404)


if __name__ == "__main__":
    unittest.main()
