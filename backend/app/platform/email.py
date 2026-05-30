"""Hybrid email: send via SMTP when configured, else write to an offline outbox.

Keeps the citizen-response / password-reset / notification flows fully
demonstrable with no internet or mail server (the outbox is stored in SQLite and
surfaced to admins), and upgrades to real email when SMTP env vars are set.
"""
from __future__ import annotations

import logging
import smtplib
from email.mime.text import MIMEText

from ..config import get_settings
from ..database import get_conn

log = logging.getLogger("visionscan.platform.email")


def smtp_configured() -> bool:
    s = get_settings()
    return bool(s.smtp_host and s.smtp_user)


def send_email(to_email: str, subject: str, body: str) -> bool:
    """Returns True if delivered via SMTP, False if stored to the outbox only."""
    s = get_settings()
    delivered = False
    if smtp_configured():
        try:
            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"] = s.smtp_from
            msg["To"] = to_email
            with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=15) as server:
                server.starttls()
                server.login(s.smtp_user, s.smtp_password)
                server.send_message(msg)
            delivered = True
        except Exception as e:  # pragma: no cover
            log.warning("SMTP send failed, storing to outbox: %s", e)

    with get_conn() as conn:
        conn.execute(
            "INSERT INTO email_outbox (to_email, subject, body, sent) "
            "VALUES (?, ?, ?, ?)",
            (to_email, subject, body, 1 if delivered else 0),
        )
    return delivered
