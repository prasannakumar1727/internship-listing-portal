# Test Cases and Results

"Automated" = covered by `tests/test_api.py` (run in the build environment: 17 tests, all passed).
"Manual" = must be checked in a browser; not executed yet, so marked **Not run**.

| ID | Scenario | Expected | Result |
|---|---|---|---|
| TC_INTERN_01 | Search "design" | Only design-related internships shown | Pass (automated, API) |
| TC_INTERN_02 | Filter Chennai + Hybrid | Only matching internships | Pass (automated, API) |
| TC_INTERN_03 | Submit valid application | Saved, confirmation with ID | Pass (automated, API); confirmation page: Not run |
| TC_INTERN_04 | Invalid email | Error shown, not saved | Pass (automated, API); inline message: Not run |
| TC_INTERN_05 | Same email, same internship twice | Second blocked (409) with message | Pass (automated, API) |
| TC_INTERN_06 | Detail page, non-existing ID | "Internship not found", no crash | Pass (automated, API); page message: Not run |
| TC_INTERN_07 | Search special characters (`%`, `_`, quotes) | No error, no injection | Pass (automated) |
| TC_INTERN_08 | Empty search / no results | All shown / "No internships found" | API Pass; UI message: Not run |
| TC_INTERN_09 | Resume wrong type / over 5 MB | Rejected | Pass (automated) |
| TC_INTERN_10 | Records persist after server restart | Still present | Pass (automated) |
| TC_INTERN_11 | Expired internship | Apply disabled / API 400 | API Pass; UI: Not run |
| TC_INTERN_12 | Sort by deadline, pagination | Correct order, 9 per page | API Pass; UI: Not run |
| TC_INTERN_13 | Responsive layout (desktop/tablet/mobile) | One column on mobile | Not run (check with browser dev tools) |
| TC_INTERN_14 | Double-click Submit | Button disabled after first click | Not run |
| TC_INTERN_15 | Postman: status codes | 200/201/400/404/409 | Not run in Postman; same codes verified by automated tests |

After you run the manual cases, update the Result column and add screenshots to `screenshots/`.
