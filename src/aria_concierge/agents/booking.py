"""
Booking Agent - Handles reservations, purchases, and transactions.
Manages the booking process for restaurants, hotels, events, and services.
"""

from typing import Dict, Any, List, Optional
from ..models.state import ConversationState
from .base import BaseAgent
import json
from datetime import datetime


class BookingAgent(BaseAgent):
    """Agent that handles bookings and reservations."""
    
    def __init__(self):
        super().__init__(
            name="booking",
            description="Handles reservations, bookings, and purchase transactions",
            temperature=0.1  # Low temperature for precise booking actions
        )
    
    def get_system_prompt(self) -> str:
        return """You are Aria's Booking Agent, responsible for making reservations and handling transactions.

Your capabilities include:
- Restaurant reservations (OpenTable, direct calls)
- Hotel bookings and room reservations
- Event tickets and entertainment bookings
- Service appointments (spa, salon, medical)
- Transportation bookings (flights, car rentals)

For each booking request, you should:
1. Confirm all booking details with the user
2. Check availability and pricing
3. Handle the booking process
4. Provide confirmation details
5. Add to user's calendar if requested

IMPORTANT: For this demo version, you will SIMULATE bookings rather than make real transactions.
Always inform users that this is a simulation and provide them with the information they need to make real bookings.

Respond in JSON format:
{
    "booking_type": "restaurant|hotel|event|service|transportation",
    "status": "confirmed|pending|failed|requires_confirmation",
    "booking_details": {
        "venue_name": "Business name",
        "date": "2024-01-15",
        "time": "7:00 PM",
        "party_size": 2,
        "duration": "2 hours",
        "special_requests": ["dietary restrictions", "accessibility needs"]
    },
    "confirmation": {
        "confirmation_number": "ABC123",
        "total_cost": "$150.00",
        "deposit_required": "$25.00",
        "cancellation_policy": "24 hours notice",
        "contact_info": "Phone or email for changes"
    },
    "next_actions": [
        "Add to calendar",
        "Send confirmation email",
        "Set reminder 1 day before"
    ],
    "booking_instructions": "Since this is a demo, here's how to make the real booking: Call (555) 123-4567 or visit their website.",
    "message": "User-friendly confirmation message"
}"""
    
    async def process(self, state: ConversationState) -> ConversationState:
        """Handle the booking process."""
        
        # Determine what needs to be booked
        booking_type = self._determine_booking_type(state)
        
        # Check if we have enough information to proceed
        if not self._has_sufficient_booking_info(state, booking_type):
            return await self._request_booking_details(state, booking_type)
        
        # Create booking prompt
        prompt = self.create_prompt_template(self.get_system_prompt())
        context = self.format_context(state)
        context["booking_type"] = booking_type
        
        # Include selected option if available
        if state.search_results:
            context["selected_option"] = str(state.search_results[0])  # Assume first result is selected
        
        try:
            # Process booking
            response = await self.invoke_llm(prompt, context)
            booking_result = json.loads(response)
            
            # Store booking in state
            state.booking_details = booking_result
            
            # Update relevant tasks
            self._update_booking_tasks(booking_result, state)
            
            # Format response for user
            response_text = self._format_booking_response(booking_result)
            state.add_message("assistant", response_text, {
                "booking_type": booking_type,
                "status": booking_result.get("status"),
                "confirmation_number": booking_result.get("confirmation", {}).get("confirmation_number")
            })
            
            # Log booking action
            self.log_action(state, "booking_processed", {
                "booking_type": booking_type,
                "status": booking_result.get("status"),
                "venue": booking_result.get("booking_details", {}).get("venue_name")
            })
            
            # Determine next steps
            if self._needs_calendar_update(booking_result):
                state.current_agent = "communication"
            else:
                state.current_agent = None  # Booking complete
            
        except (json.JSONDecodeError, KeyError) as e:
            # Fallback booking response
            fallback_response = await self._fallback_booking(state, booking_type)
            state.add_message("assistant", fallback_response)
            
            self.log_action(state, "booking_fallback", {
                "error": str(e),
                "booking_type": booking_type
            })
        
        return state
    
    def _determine_booking_type(self, state: ConversationState) -> str:
        """Determine what type of booking is needed."""
        request_lower = state.current_request.lower() if state.current_request else ""
        
        # Check active tasks first
        for task in state.active_tasks:
            task_desc = task.description.lower()
            if "restaurant" in task_desc or "table" in task_desc:
                return "restaurant"
            elif "hotel" in task_desc or "room" in task_desc:
                return "hotel"
            elif "flight" in task_desc:
                return "transportation"
            elif "event" in task_desc or "ticket" in task_desc:
                return "event"
        
        # Fallback to request analysis
        if any(word in request_lower for word in ["restaurant", "table", "dinner", "lunch"]):
            return "restaurant"
        elif any(word in request_lower for word in ["hotel", "room", "stay"]):
            return "hotel"
        elif any(word in request_lower for word in ["flight", "plane", "airline"]):
            return "transportation"
        elif any(word in request_lower for word in ["event", "ticket", "show", "concert"]):
            return "event"
        else:
            return "service"
    
    def _has_sufficient_booking_info(self, state: ConversationState, booking_type: str) -> bool:
        """Check if we have enough information to make a booking."""
        entities = state.entities
        
        # Common required fields
        required_fields = ["date"]
        
        if booking_type == "restaurant":
            required_fields.extend(["time", "party_size"])
        elif booking_type == "hotel":
            required_fields.extend(["check_out", "guests"])
        elif booking_type == "event":
            required_fields.extend(["event_name"])
        
        # Check if we have the required information
        for field in required_fields:
            if field not in entities or not entities[field]:
                return False
        
        return True
    
    async def _request_booking_details(self, state: ConversationState, booking_type: str) -> ConversationState:
        """Request missing booking information from user."""
        entities = state.entities
        missing_info = []
        
        if booking_type == "restaurant":
            if not entities.get("date"):
                missing_info.append("date")
            if not entities.get("time"):
                missing_info.append("preferred time")
            if not entities.get("party_size"):
                missing_info.append("number of people")
        
        elif booking_type == "hotel":
            if not entities.get("date"):
                missing_info.append("check-in date")
            if not entities.get("check_out"):
                missing_info.append("check-out date")
            if not entities.get("guests"):
                missing_info.append("number of guests")
        
        if missing_info:
            missing_str = ", ".join(missing_info)
            response = f"I'd be happy to help you book that! I just need a few more details: {missing_str}. Could you please provide this information?"
            
            state.add_message("assistant", response, {
                "action": "request_booking_details",
                "missing_info": missing_info
            })
        
        return state
    
    def _update_booking_tasks(self, booking_result: Dict, state: ConversationState):
        """Update tasks related to this booking."""
        booking_type = booking_result.get("booking_type")
        status = booking_result.get("status")
        
        # Find and update relevant booking tasks
        for task in state.active_tasks:
            if booking_type in task.description.lower():
                if status == "confirmed":
                    state.update_task(task.task_id, "completed", booking_result)
                elif status == "failed":
                    state.update_task(task.task_id, "failed", None, "Booking failed")
    
    def _format_booking_response(self, booking_result: Dict) -> str:
        """Format booking result into user-friendly response."""
        status = booking_result.get("status", "unknown")
        booking_details = booking_result.get("booking_details", {})
        confirmation = booking_result.get("confirmation", {})
        
        if status == "confirmed":
            response_parts = ["✅ **Booking Confirmed!**\n"]
            
            # Add booking details
            venue_name = booking_details.get("venue_name", "Venue")
            date = booking_details.get("date", "")
            time = booking_details.get("time", "")
            
            response_parts.append(f"**{venue_name}**")
            if date:
                response_parts.append(f"📅 Date: {date}")
            if time:
                response_parts.append(f"🕐 Time: {time}")
            
            party_size = booking_details.get("party_size")
            if party_size:
                response_parts.append(f"👥 Party Size: {party_size}")
            
            # Add confirmation details
            conf_number = confirmation.get("confirmation_number")
            if conf_number:
                response_parts.append(f"\n🎫 **Confirmation:** {conf_number}")
            
            total_cost = confirmation.get("total_cost")
            if total_cost:
                response_parts.append(f"💰 **Total Cost:** {total_cost}")
            
            # Add special instructions
            if booking_result.get("booking_instructions"):
                response_parts.append(f"\n⚠️ **Note:** {booking_result['booking_instructions']}")
            
            # Add next actions
            next_actions = booking_result.get("next_actions", [])
            if next_actions:
                response_parts.append(f"\n**Next Steps:**")
                for action in next_actions:
                    response_parts.append(f"• {action}")
        
        elif status == "pending":
            response_parts = ["⏳ **Booking Pending**\n"]
            response_parts.append("Your booking request is being processed. I'll update you once it's confirmed.")
            
        elif status == "requires_confirmation":
            response_parts = ["❓ **Confirmation Required**\n"]
            response_parts.append("Please confirm these booking details:")
            
            # Add details for confirmation
            for key, value in booking_details.items():
                response_parts.append(f"• {key.replace('_', ' ').title()}: {value}")
            
            response_parts.append("\nShould I proceed with this booking?")
        
        else:  # failed
            response_parts = ["❌ **Booking Failed**\n"]
            response_parts.append("I wasn't able to complete your booking. Please try again or contact the venue directly.")
        
        return "\n".join(response_parts)
    
    def _needs_calendar_update(self, booking_result: Dict) -> bool:
        """Check if booking should be added to calendar."""
        next_actions = booking_result.get("next_actions", [])
        return any("calendar" in action.lower() for action in next_actions)
    
    async def _fallback_booking(self, state: ConversationState, booking_type: str) -> str:
        """Provide fallback booking response."""
        fallback_prompt = f"""The user wants to book a {booking_type}. 
        Provide helpful guidance on how to make this booking, including:
        - What information they need
        - How to contact the venue
        - Any special considerations
        
        Request: {state.current_request}
        Available options: {state.search_results if state.search_results else 'None'}"""
        
        prompt = self.create_prompt_template(fallback_prompt, include_context=False)
        context = {"current_request": state.current_request}
        
        return await self.invoke_llm(prompt, context)