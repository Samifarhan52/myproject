import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


SENDER_EMAIL = "samifarhan64@gmail.com"
APP_PASSWORD = "olrk rope dore zkrq"  # App password you provided. Change if you regenerate.


def send_email(to_email: str, subject: str, html_content: str):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SENDER_EMAIL
    msg["To"] = to_email

    msg.attach(MIMEText(html_content, "html"))

    server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
    server.login(SENDER_EMAIL, APP_PASSWORD)
    server.sendmail(SENDER_EMAIL, to_email, msg.as_string())
    server.quit()
