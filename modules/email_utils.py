import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Read credentials from Render Environment Variables
EMAIL_USER = os.environ.get("EMAIL_USER")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")


def send_email(to_email: str, subject: str, html_content: str):
    if not EMAIL_USER or not EMAIL_PASSWORD:
        raise RuntimeError("EMAIL_USER or EMAIL_PASSWORD not set in environment")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = EMAIL_USER
    msg["To"] = to_email

    msg.attach(MIMEText(html_content, "html"))

    try:
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_USER, to_email, msg.as_string())
        server.quit()
    except Exception as e:
        print("EMAIL ERROR:", e)
        raise
