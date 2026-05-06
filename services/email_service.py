import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import inngest

async def send_email_task(ctx: inngest.Context) -> dict:
    """
    Inngest function to send an email via SMTP.
    """
    data = ctx.event.data
    to_email = data.get("to")
    subject = data.get("subject")
    body = data.get("body")
    
    # Get SMTP settings from env
    smtp_host = os.getenv("EMAIL_HOST")
    smtp_port = int(os.getenv("EMAIL_PORT", 587))
    smtp_user = os.getenv("EMAIL_HOST_USER")
    smtp_pass = os.getenv("EMAIL_HOST_PASSWORD")
    from_email = os.getenv("DEFAULT_FROM_EMAIL", smtp_user)
    use_tls = os.getenv("EMAIL_USE_TLS", "True").lower() == "true"
    use_ssl = os.getenv("EMAIL_USE_SSL", "False").lower() == "true"

    if not all([smtp_host, smtp_user, smtp_pass]):
        ctx.logger.error("SMTP settings are incomplete")
        return {"status": "error", "message": "SMTP settings are incomplete"}

    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html'))

    try:
        ctx.logger.info(f"Attempting to send email to {to_email} via {smtp_host}")
        
        if use_ssl:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port)
            if use_tls:
                server.starttls()
        
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()
        
        ctx.logger.info(f"Email successfully sent to {to_email}")
        return {"status": "sent", "to": to_email}
    except Exception as e:
        ctx.logger.error(f"Failed to send email to {to_email}: {e}")
        raise e # Let Inngest retry
