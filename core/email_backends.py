"""
Custom email backend for Resend HTTP API
Replaces SMTP with reliable HTTP-based email delivery via Resend
"""

import logging
from django.core.mail.backends.base import BaseEmailBackend
from django.conf import settings

try:
    import resend
except ImportError:
    resend = None

logger = logging.getLogger(__name__)


class ResendEmailBackend(BaseEmailBackend):
    """
    Email backend that uses Resend's HTTP API for sending emails.
    
    Requires:
    - resend package: pip install resend
    - RESEND_API_KEY environment variable
    
    This avoids SMTP timeouts on restricted networks like Render.
    """

    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        
        if resend is None:
            raise ImportError(
                "The resend library is not installed. "
                "Install it with: pip install resend"
            )
        
        self.api_key = settings.RESEND_API_KEY
        if not self.api_key:
            raise ValueError("RESEND_API_KEY setting is not configured")
        
        resend.api_key = self.api_key

    def send_messages(self, email_messages):
        """
        Send one or more EmailMessage objects and return the number of email
        messages sent.
        """
        if not email_messages:
            return 0

        msg_count = 0
        for message in email_messages:
            try:
                self._send(message)
                msg_count += 1
            except Exception as e:
                if not self.fail_silently:
                    logger.error(
                        f"Error sending email to {message.to}: {e}",
                        exc_info=True
                    )
                    raise
                else:
                    logger.warning(
                        f"Failed to send email to {message.to}: {e}"
                    )
        
        return msg_count

    def _send(self, message):
        """Send a single email message via Resend API"""
        try:
            # Extract recipients
            to_emails = message.to
            cc_emails = message.cc or []
            bcc_emails = message.bcc or []
            
            if not to_emails:
                raise ValueError("Email message has no recipients")
            
            # Prepare the email payload
            email_payload = {
                "from": message.from_email,
                "to": to_emails,
                "subject": message.subject,
            }
            
            # Add CC and BCC if present
            if cc_emails:
                email_payload["cc"] = cc_emails
            if bcc_emails:
                email_payload["bcc"] = bcc_emails
            
            # Add body content
            if message.body:
                email_payload["text"] = message.body
            
            # Add HTML content if available
            if message.alternatives:
                for content, mimetype in message.alternatives:
                    if mimetype == "text/html":
                        email_payload["html"] = content
                        break
            
            # Add reply-to if set
            if message.reply_to:
                email_payload["reply_to"] = message.reply_to[0]
            
            # Send via Resend API
            response = resend.Emails.send(email_payload)
            
            logger.info(
                f"Email sent successfully via Resend API to {', '.join(to_emails)}: {response.get('id', 'unknown')}"
            )
            
            return response
            
        except Exception as e:
            logger.error(
                f"Resend API error while sending email to {message.to}: {str(e)}",
                exc_info=True
            )
            raise
