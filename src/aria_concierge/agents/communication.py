"""
Communication Agent - Handles emails, messages, and notifications.
Manages communication tasks like sending confirmations, reminders, and updates.
"""

from typing import Dict, Any, List, Optional
from ..models.state import ConversationState
from .base import BaseAgent
import json
from datetime import datetime


class CommunicationAgent(BaseAgent):
    """Agent that handles communication tasks."""
    
    def __init__(self):
        super().__init__(
            name="communication",
            description="Handles emails, messages, calendar events, and notifications",
            temperature=0.2
        )
    
    def get_system_prompt(self) -> str:
        return """You are Aria's Communication Agent, responsible for drafting and managing communications.

Your capabilities include:
- Email drafting and sending
- Calendar event creation
- SMS/message composition
- Reminder scheduling
- Invitation management
- Follow-up communications

For each communication task:
1. Determine the appropriate communication method
2. Draft professional, clear content
3. Include all necessary details
4. Set appropriate timing and reminders
5. Provide user with preview before sending

IMPORTANT: This is a demo system. You will draft communications but not actually send them.
Always show the user what would be sent and provide instructions for manual sending.

Respond in JSON format:
{
    "communication_type": "email|calendar|sms|reminder|invitation",
    "action": "draft|schedule|send_preview",
    "content": {
        "to": "recipient@example.com",
        "subject": "Email subject",
        "body": "Email body content",
        "attachments": ["list of attachments if any"]
    },
    "calendar_event": {
        "title": "Event title",
        "date": "2024-01-15",
        "time": "7:00 PM",
        "duration": "2 hours",
        "location": "Event location",
        "description": "Event description",
        "attendees": ["attendee emails"],
        "reminders": ["15 minutes", "1 day"]
    },
    "scheduling": {
        "send_time": "immediately|2024-01-15 09:00",
        "reminders": [
            {"time": "1 day before", "message": "Reminder message"}
        ]
    },
    "preview_message": "Here's what I've prepared for you...",
    "instructions": "To actually send this, please..."
}"""
    
    async def process(self, state: ConversationState) -> ConversationState:
        """Handle communication tasks."""
        
        # Determine communication type needed
        comm_type = self._determine_communication_type(state)
        
        # Create communication prompt
        prompt = self.create_prompt_template(self.get_system_prompt())
        context = self.format_context(state)
        context["communication_type"] = comm_type
        
        # Include booking details if available for confirmations
        if state.booking_details:
            context["booking_details"] = str(state.booking_details)
        
        try:
            # Generate communication
            response = await self.invoke_llm(prompt, context)
            comm_result = json.loads(response)
            
            # Store communication in state
            state.agent_context["communication_result"] = comm_result
            
            # Update relevant tasks
            self._update_communication_tasks(comm_result, state)
            
            # Format response for user
            response_text = self._format_communication_response(comm_result)
            state.add_message("assistant", response_text, {
                "communication_type": comm_type,
                "action": comm_result.get("action")
            })
            
            # Log communication action
            self.log_action(state, "communication_prepared", {
                "communication_type": comm_type,
                "action": comm_result.get("action"),
                "recipient": comm_result.get("content", {}).get("to", "unknown")
            })
            
            # Communication tasks typically complete the workflow
            state.current_agent = None
            
        except (json.JSONDecodeError, KeyError) as e:
            # Fallback communication
            fallback_response = await self._fallback_communication(state, comm_type)
            state.add_message("assistant", fallback_response)
            
            self.log_action(state, "communication_fallback", {
                "error": str(e),
                "communication_type": comm_type
            })
        
        return state
    
    def _determine_communication_type(self, state: ConversationState) -> str:
        """Determine what type of communication is needed."""
        request_lower = state.current_request.lower() if state.current_request else ""
        
        # Check active tasks for communication needs
        for task in state.active_tasks:
            task_desc = task.description.lower()
            if "email" in task_desc:
                return "email"
            elif "calendar" in task_desc:
                return "calendar"
            elif "reminder" in task_desc:
                return "reminder"
            elif "invitation" in task_desc:
                return "invitation"
        
        # Check if we need to create calendar event from booking
        if state.booking_details and state.booking_details.get("status") == "confirmed":
            return "calendar"
        
        # Analyze request content
        if any(word in request_lower for word in ["email", "send", "message"]):
            return "email"
        elif any(word in request_lower for word in ["calendar", "schedule", "add to calendar"]):
            return "calendar"
        elif any(word in request_lower for word in ["remind", "reminder", "alert"]):
            return "reminder"
        elif any(word in request_lower for word in ["invite", "invitation"]):
            return "invitation"
        else:
            return "email"  # Default
    
    def _update_communication_tasks(self, comm_result: Dict, state: ConversationState):
        """Update tasks related to communication."""
        comm_type = comm_result.get("communication_type")
        
        # Find and update relevant communication tasks
        for task in state.active_tasks:
            task_desc = task.description.lower()
            if (comm_type in task_desc or 
                "email" in task_desc or 
                "calendar" in task_desc or 
                "reminder" in task_desc):
                state.update_task(task.task_id, "completed", comm_result)
    
    def _format_communication_response(self, comm_result: Dict) -> str:
        """Format communication result into user-friendly response."""
        comm_type = comm_result.get("communication_type", "communication")
        action = comm_result.get("action", "prepared")
        
        response_parts = [f"📧 **{comm_type.title()} {action.title()}**\n"]
        
        # Add preview message if available
        if comm_result.get("preview_message"):
            response_parts.append(comm_result["preview_message"])
            response_parts.append("")
        
        # Format email content
        content = comm_result.get("content", {})
        if content:
            if content.get("to"):
                response_parts.append(f"**To:** {content['to']}")
            if content.get("subject"):
                response_parts.append(f"**Subject:** {content['subject']}")
            if content.get("body"):
                response_parts.append(f"\n**Message:**\n{content['body']}")
        
        # Format calendar event
        calendar_event = comm_result.get("calendar_event", {})
        if calendar_event:
            response_parts.append("**Calendar Event:**")
            if calendar_event.get("title"):
                response_parts.append(f"• **Title:** {calendar_event['title']}")
            if calendar_event.get("date"):
                response_parts.append(f"• **Date:** {calendar_event['date']}")
            if calendar_event.get("time"):
                response_parts.append(f"• **Time:** {calendar_event['time']}")
            if calendar_event.get("location"):
                response_parts.append(f"• **Location:** {calendar_event['location']}")
            if calendar_event.get("attendees"):
                attendees = ", ".join(calendar_event['attendees'])
                response_parts.append(f"• **Attendees:** {attendees}")
        
        # Add scheduling info
        scheduling = comm_result.get("scheduling", {})
        if scheduling:
            send_time = scheduling.get("send_time", "immediately")
            response_parts.append(f"\n**Scheduled:** {send_time}")
            
            reminders = scheduling.get("reminders", [])
            if reminders:
                response_parts.append("**Reminders:**")
                for reminder in reminders:
                    response_parts.append(f"• {reminder.get('time', '')}: {reminder.get('message', '')}")
        
        # Add instructions for manual action
        if comm_result.get("instructions"):
            response_parts.append(f"\n**Instructions:** {comm_result['instructions']}")
        else:
            response_parts.append(f"\n**Note:** This is a demo system. In production, this {comm_type} would be sent automatically.")
        
        return "\n".join(response_parts)
    
    def _create_calendar_event_from_booking(self, booking_details: Dict) -> Dict:
        """Create calendar event from booking details."""
        booking_info = booking_details.get("booking_details", {})
        
        return {
            "title": f"Reservation at {booking_info.get('venue_name', 'Venue')}",
            "date": booking_info.get("date", ""),
            "time": booking_info.get("time", ""),
            "duration": booking_info.get("duration", "2 hours"),
            "location": booking_info.get("venue_name", ""),
            "description": f"Party of {booking_info.get('party_size', 'N/A')}",
            "reminders": ["1 day", "2 hours"]
        }
    
    async def _fallback_communication(self, state: ConversationState, comm_type: str) -> str:
        """Provide fallback communication response."""
        fallback_prompt = f"""Help the user with their {comm_type} request. 
        Provide a draft or guidance on what they need to communicate.
        
        Request: {state.current_request}
        Context: {state.get_context_summary()}
        
        Be helpful and specific."""
        
        prompt = self.create_prompt_template(fallback_prompt, include_context=False)
        context = {"current_request": state.current_request}
        
        return await self.invoke_llm(prompt, context)