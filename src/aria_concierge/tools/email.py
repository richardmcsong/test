"""
Email tools for the Aria concierge system.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os


class EmailTool:
    """Tool for email management."""
    
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.username = os.getenv("SMTP_USERNAME")
        self.password = os.getenv("SMTP_PASSWORD")
    
    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        attachments: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Send an email (simulated for demo)."""
        
        # In production, this would actually send the email
        return {
            "message_id": f"msg_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "to": to,
            "subject": subject,
            "status": "sent",
            "sent_at": datetime.now().isoformat(),
            "preview": f"Subject: {subject}\nTo: {to}\n\n{body[:200]}..."
        }
    
    async def draft_confirmation_email(
        self,
        booking_details: Dict[str, Any],
        recipient: str
    ) -> Dict[str, Any]:
        """Draft a booking confirmation email."""
        
        booking_info = booking_details.get("booking_details", {})
        confirmation = booking_details.get("confirmation", {})
        
        subject = f"Confirmation: {booking_info.get('venue_name', 'Your Reservation')}"
        
        body = f"""Dear Valued Guest,

Your reservation has been confirmed! Here are the details:

Venue: {booking_info.get('venue_name', 'N/A')}
Date: {booking_info.get('date', 'N/A')}
Time: {booking_info.get('time', 'N/A')}
Party Size: {booking_info.get('party_size', 'N/A')}
Confirmation Number: {confirmation.get('confirmation_number', 'N/A')}

Please arrive 10-15 minutes early and present this confirmation.

If you need to make changes or cancel, please contact us at least 24 hours in advance.

Best regards,
Aria Concierge Service
"""
        
        return {
            "to": recipient,
            "subject": subject,
            "body": body,
            "type": "confirmation",
            "booking_reference": confirmation.get('confirmation_number')
        }
    
    async def draft_reminder_email(
        self,
        event_details: Dict[str, Any],
        recipient: str,
        reminder_type: str = "1_day"
    ) -> Dict[str, Any]:
        """Draft a reminder email."""
        
        if reminder_type == "1_day":
            subject = f"Reminder: {event_details.get('title', 'Your Event')} Tomorrow"
            timing = "tomorrow"
        else:
            subject = f"Reminder: {event_details.get('title', 'Your Event')} Today"
            timing = "today"
        
        body = f"""Hello,

This is a friendly reminder that you have an event {timing}:

Event: {event_details.get('title', 'N/A')}
Date: {event_details.get('date', 'N/A')}
Time: {event_details.get('time', 'N/A')}
Location: {event_details.get('location', 'N/A')}

Please don't forget to bring any required items and arrive on time.

Best regards,
Aria Concierge Service
"""
        
        return {
            "to": recipient,
            "subject": subject,
            "body": body,
            "type": "reminder",
            "event_reference": event_details.get('event_id')
        }