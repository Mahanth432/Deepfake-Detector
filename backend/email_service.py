import asyncio
import os
import smtplib
import logging
from email.message import EmailMessage
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

base_dir = os.path.dirname(__file__)
load_dotenv()
backend_env = os.path.join(base_dir, '.env')
if os.path.exists(backend_env):
    load_dotenv(backend_env)
    print(f"Loading backend email environment from: {backend_env}")

logger = logging.getLogger(__name__)

EMAIL_USER = os.getenv("EMAIL_USER", "")
EMAIL_PASS = os.getenv("EMAIL_PASS", "")
MAIL_FROM = os.getenv("MAIL_FROM", EMAIL_USER)
MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
MAIL_PORT = int(os.getenv("MAIL_PORT", 587))
MAIL_STARTTLS = os.getenv("MAIL_STARTTLS", "True").lower() == "true"
MAIL_SSL_TLS = os.getenv("MAIL_SSL_TLS", "False").lower() == "true"


def validate_email_config() -> tuple[bool, str]:
    """Validate email configuration and return (is_valid, message)"""
    missing_vars = []
    if not EMAIL_USER:
        missing_vars.append("EMAIL_USER")
    if not EMAIL_PASS:
        missing_vars.append("EMAIL_PASS")

    if missing_vars:
        return (
            False,
            "Missing required environment variables: "
            + ", ".join(missing_vars)
            + ". Please create backend/.env with EMAIL_USER and EMAIL_PASS."
        )

    return True, "Email configuration is valid."

def _send_email_sync(message: MIMEMultipart):
    try:
        is_valid, msg = validate_email_config()
        if not is_valid:
            raise RuntimeError(f"Email service is not configured properly: {msg}")

        # DEBUG
        print("\n===== EMAIL DEBUG =====")
        print("EMAIL_USER   =", repr(EMAIL_USER))
        print("MAIL_FROM    =", repr(MAIL_FROM))
        print("MAIL_SERVER  =", repr(MAIL_SERVER))
        print("MAIL_PORT    =", repr(MAIL_PORT))
        print("MAIL_STARTTLS=", repr(MAIL_STARTTLS))
        print("MAIL_SSL_TLS =", repr(MAIL_SSL_TLS))
        print("=======================\n")

        logger.info(f"Connecting to SMTP server: {MAIL_SERVER}:{MAIL_PORT}")

        if MAIL_SSL_TLS:
            smtp = smtplib.SMTP_SSL(MAIL_SERVER, MAIL_PORT, timeout=20)
        else:
            smtp = smtplib.SMTP(MAIL_SERVER, MAIL_PORT, timeout=20)

        smtp.ehlo()

        if MAIL_STARTTLS:
            smtp.starttls()
            smtp.ehlo()

        logger.info(f"Attempting login with username: {EMAIL_USER}")

        smtp.login(EMAIL_USER, EMAIL_PASS)

        logger.info("SMTP login successful")

        smtp.send_message(message)
        smtp.quit()

        logger.info("Email sent successfully")

    except Exception as e:
        logger.exception("Email error")
        raise RuntimeError(f"Email service error: {str(e)}")


async def send_email(to_email: str, subject: str, body: str, html_body: str = None):
    """Send email asynchronously with optional HTML content"""
    message = MIMEMultipart("alternative")
    message["From"] = MAIL_FROM
    message["To"] = to_email
    message["Subject"] = subject

    # Add plain text version
    text_part = MIMEText(body, "plain")
    message.attach(text_part)

    # Add HTML version if provided
    if html_body:
        html_part = MIMEText(html_body, "html")
        message.attach(html_part)

    await asyncio.to_thread(_send_email_sync, message)


async def send_otp_email(email: str, otp: str):
    """Send OTP email with professional HTML template"""
    subject = "Deepfake Detection AI - Verification Code"

    # Plain text version
    text_body = f"""Your Deepfake Detection AI verification code is:

{otp}

This code will expire in 5 minutes. Please use it to complete your verification.

If you did not request this code, please ignore this email."""

    # HTML version with futuristic styling
    html_body = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Deepfake Detection AI - OTP</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 0;
            color: #333;
        }}
        .container {{
            max-width: 600px;
            margin: 40px auto;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
            backdrop-filter: blur(10px);
        }}
        .header {{
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            padding: 40px 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 28px;
            font-weight: 300;
            letter-spacing: 2px;
        }}
        .content {{
            padding: 40px 30px;
            text-align: center;
        }}
        .otp-code {{
            font-size: 48px;
            font-weight: bold;
            color: #1e3c72;
            letter-spacing: 8px;
            margin: 30px 0;
            text-shadow: 0 2px 4px rgba(0,0,0,0.1);
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        .message {{
            font-size: 16px;
            line-height: 1.6;
            color: #666;
            margin: 20px 0;
        }}
        .expiry {{
            color: #e74c3c;
            font-weight: bold;
            margin: 20px 0;
        }}
        .footer {{
            background: #f8f9fa;
            padding: 20px 30px;
            text-align: center;
            font-size: 14px;
            color: #888;
        }}
        .logo {{
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 10px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">🤖 Deepfake Detection AI</div>
            <h1>Verification Code</h1>
        </div>
        <div class="content">
            <p class="message">Your verification code for Deepfake Detection AI is:</p>
            <div class="otp-code">{otp}</div>
            <p class="expiry">⚠️ This code will expire in 5 minutes</p>
            <p class="message">Please enter this code to complete your verification. If you did not request this code, please ignore this email.</p>
        </div>
        <div class="footer">
            <p>© 2024 Deepfake Detection AI. All rights reserved.</p>
            <p>This is an automated message. Please do not reply.</p>
        </div>
    </div>
</body>
</html>
"""

    await send_email(email, subject, text_body, html_body)
