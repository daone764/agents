"""
Email sender for trading reports.
Uses Gmail SMTP to send HTML reports.
"""

import smtplib
import ssl
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class EmailSender:
    """Send trading reports via Gmail SMTP"""
    
    def __init__(self):
        self.sender_email = os.getenv("GMAIL_ADDRESS", "")
        self.app_password = os.getenv("GMAIL_APP_PASSWORD", "")
        self.recipient_email = os.getenv("REPORT_RECIPIENT", self.sender_email)
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        
    def is_configured(self) -> bool:
        """Check if email credentials are configured"""
        return bool(self.sender_email and self.app_password)
    
    def send_html_report(
        self,
        html_content: str,
        subject: str = None,
        recipient: str = None,
        attach_file: str = None
    ) -> bool:
        """
        Send HTML report via email.
        
        Args:
            html_content: The HTML content to send as email body
            subject: Email subject (auto-generated if not provided)
            recipient: Override recipient email
            attach_file: Optional file path to attach
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.is_configured():
            logger.warning("Email not configured. Set GMAIL_ADDRESS and GMAIL_APP_PASSWORD in .env")
            return False
        
        recipient = recipient or self.recipient_email
        if not recipient:
            logger.error("No recipient email specified")
            return False
        
        # Generate subject if not provided
        if not subject:
            date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            subject = f"Polymarket Trading Report - {date_str}"
        
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.sender_email
            msg["To"] = recipient
            
            # Plain text fallback
            text_content = """
            Polymarket Trading Report
            
            Your HTML email client is required to view this report.
            Please enable HTML emails or view the attached file.
            """
            
            # Attach both plain text and HTML
            part1 = MIMEText(text_content, "plain")
            part2 = MIMEText(html_content, "html")
            msg.attach(part1)
            msg.attach(part2)
            
            # Attach file if specified
            if attach_file and Path(attach_file).exists():
                with open(attach_file, "rb") as f:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(f.read())
                encoders.encode_base64(part)
                filename = Path(attach_file).name
                part.add_header("Content-Disposition", f"attachment; filename={filename}")
                msg.attach(part)
            
            # Send email
            logger.info(f"Sending email to {recipient}...")
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.app_password)
                server.sendmail(self.sender_email, recipient, msg.as_string())
            
            logger.info(f"✅ Email sent successfully to {recipient}")
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"❌ Gmail authentication failed: {e}")
            logger.error("   Make sure 2-Step Verification is ON at: https://myaccount.google.com/security")
            logger.error("   Then get an app password at: https://myaccount.google.com/apppasswords")
            return False
        except Exception as e:
            logger.error(f"❌ Failed to send email: {e}")
            return False
    
    def send_report_file(self, html_file_path: str, recipient: str = None) -> bool:
        """
        Send an HTML report file via email.
        
        Args:
            html_file_path: Path to the HTML file
            recipient: Override recipient email
            
        Returns:
            True if sent successfully
        """
        path = Path(html_file_path)
        if not path.exists():
            logger.error(f"HTML file not found: {html_file_path}")
            return False
        
        html_content = path.read_text(encoding="utf-8")
        
        # Extract date from filename if possible
        subject = f"🎯 Polymarket Report - {path.stem}"
        
        return self.send_html_report(
            html_content=html_content,
            subject=subject,
            recipient=recipient,
            attach_file=html_file_path
        )


def send_trading_report(html_content: str, html_file: str = None) -> bool:
    """
    Convenience function to send trading report.
    
    Args:
        html_content: HTML content to send
        html_file: Optional path to HTML file to attach
        
    Returns:
        True if sent successfully
    """
    sender = EmailSender()
    if not sender.is_configured():
        print("\n📧 Email not configured. To enable email reports:")
        print("   1. Add to your .env file:")
        print("      GMAIL_ADDRESS=your.email@gmail.com")
        print("      GMAIL_APP_PASSWORD=your-16-char-app-password")
        print("      REPORT_RECIPIENT=daviddgreene77@gmail.com")
        print("   2. Get app password: https://myaccount.google.com/apppasswords")
        return False
    
    return sender.send_html_report(html_content, attach_file=html_file)


# Quick test
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    sender = EmailSender()
    if sender.is_configured():
        test_html = """
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h1 style="color: #2563eb;">🎯 Test Email</h1>
            <p>This is a test email from the Polymarket trading bot.</p>
            <p>If you received this, email is configured correctly!</p>
        </body>
        </html>
        """
        sender.send_html_report(test_html, subject="Test - Polymarket Bot Email")
    else:
        print("Email not configured. Set GMAIL_ADDRESS and GMAIL_APP_PASSWORD in .env")
