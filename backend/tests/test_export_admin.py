"""Admin system console + data export: admin-only access and valid payloads."""
from __future__ import annotations

import io
import zipfile


# --------------------------------------------------------------- /admin/system
def test_system_admin_only(client, auth_headers):
    # Officer (not admin) is forbidden.
    r = client.get("/api/admin/system", headers=auth_headers["officer"])
    assert r.status_code == 403, r.text

    r = client.get("/api/admin/system", headers=auth_headers["admin"])
    assert r.status_code == 200, r.text
    body = r.json()
    assert "lockdown" in body
    assert "models" in body
    assert set(body["models"]) >= {"clip", "yolo", "face"}


# ------------------------------------------------------- complaints.csv export
def test_complaints_csv_admin_only(client, auth_headers):
    # Citizen forbidden.
    r = client.get("/api/admin/export/complaints.csv", headers=auth_headers["citizen"])
    assert r.status_code == 403, r.text

    r = client.get("/api/admin/export/complaints.csv", headers=auth_headers["admin"])
    assert r.status_code == 200, r.text
    assert "text/csv" in r.headers["content-type"]
    first_line = r.text.splitlines()[0]
    # Header present with expected columns.
    assert "id" in first_line and "title" in first_line and "category" in first_line


# ----------------------------------------------------------------- backup.zip
def test_backup_zip_is_valid_and_contains_db(client, auth_headers):
    r = client.get("/api/admin/export/backup.zip", headers=auth_headers["admin"])
    assert r.status_code == 200, r.text
    data = r.content
    assert data, "backup.zip body was empty"

    zf = zipfile.ZipFile(io.BytesIO(data))
    names = zf.namelist()
    assert any(n.endswith(".db") for n in names), f"no .db in backup: {names}"
    # The .db member is non-empty (a real SQLite snapshot).
    db_name = next(n for n in names if n.endswith(".db"))
    assert zf.getinfo(db_name).file_size > 0


def test_backup_zip_forbidden_for_citizen(client, auth_headers):
    r = client.get("/api/admin/export/backup.zip", headers=auth_headers["citizen"])
    assert r.status_code == 403, r.text
