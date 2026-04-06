"""
Email utility. Sends emails via SMTP when configured, logs to console otherwise.
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def send_email(to, subject, body_html):
    """Send an email. If SMTP is not configured, logs the email to stdout.

    Args:
        to: Recipient email address.
        subject: Email subject line.
        body_html: HTML body content.
    """
    smtp_host = os.environ.get("SMTP_HOST")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER")
    smtp_password = os.environ.get("SMTP_PASSWORD")
    smtp_from = os.environ.get("SMTP_FROM", "noreply@immediate.co.uk")

    if not smtp_host or not smtp_user or not smtp_password:
        print("[EMAIL] SMTP not configured — logging email instead:")
        print("[EMAIL] To: %s" % to)
        print("[EMAIL] Subject: %s" % subject)
        print("[EMAIL] Body: %s" % body_html)
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_from
    msg["To"] = to
    msg.attach(MIMEText(body_html, "html"))

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_from, to, msg.as_string())
