"""
Planning Agent - Creates itineraries, schedules, and multi-step plans.
Handles complex requests that require coordination of multiple activities.
"""

from typing import Dict, Any, List, Optional
from ..models.state import ConversationState
from .base import BaseAgent
import json
from datetime import datetime, timedelta


class PlanningAgent(BaseAgent):
    """Agent that creates plans, itineraries, and schedules."""
    
    def __init__(self):
        super().__init__(
            name="planning",
            description="Creates itineraries, schedules, and multi-step plans for complex requests",
            temperature=0.2
        )
    
    def get_system_prompt(self) -> str:
        return """You are Aria's Planning Agent, specialized in creating detailed itineraries, schedules, and multi-step plans.

Your capabilities include:
- Multi-day travel itineraries with activities, dining, and logistics
- Event planning and coordination
- Daily/weekly schedule optimization
- Task sequencing and timeline creation
- Resource allocation and booking coordination

When planning, consider:
1. Logical sequence and timing of activities
2. Travel time between locations
3. Operating hours and availability
4. User preferences and constraints
5. Backup options and contingencies
6. Budget allocation across activities

Create comprehensive plans with:
- Clear timeline with specific times
- Location details and directions
- Estimated costs and duration
- Prerequisites and dependencies
- Alternative options when relevant

Respond in JSON format:
{
    "plan_type": "itinerary|schedule|event_plan|task_plan",
    "title": "Plan Title",
    "duration": "3 days|5 hours|etc",
    "total_estimated_cost": "$500-700",
    "plan_items": [
        {
            "sequence": 1,
            "time": "9:00 AM",
            "activity": "Activity name",
            "location": "Address/venue",
            "duration": "2 hours",
            "cost": "$50",
            "description": "Detailed description",
            "prerequisites": ["booking required", "bring ID"],
            "alternatives": ["backup option if needed"],
            "notes": "Special considerations"
        }
    ],
    "logistics": {
        "transportation": "How to get around",
        "accommodations": "Where to stay if applicable", 
        "reservations_needed": ["list of items requiring booking"],
        "packing_list": ["items to bring"]
    },
    "summary": "Plan overview and key highlights",
    "next_steps": ["actions user needs to take"]
}"""
    
    async def process(self, state: ConversationState) -> ConversationState:
        """Create a detailed plan based on the user's request."""
        
        # Determine plan type
        plan_type = self._determine_plan_type(state)
        
        # Create planning prompt with context
        prompt = self.create_prompt_template(self.get_system_prompt())
        context = self.format_context(state)
        context["plan_type"] = plan_type
        
        # Include research results if available
        if state.search_results:
            context["available_options"] = str(state.search_results)
        
        try:
            # Generate plan
            response = await self.invoke_llm(prompt, context)
            plan = json.loads(response)
            
            # Store plan in state
            state.agent_context["current_plan"] = plan
            
            # Create tasks for items requiring booking/action
            self._create_tasks_from_plan(plan, state)
            
            # Format response for user
            response_text = self._format_plan_response(plan)
            state.add_message("assistant", response_text, {
                "plan_type": plan_type,
                "items_count": len(plan.get("plan_items", [])),
                "estimated_cost": plan.get("total_estimated_cost")
            })
            
            # Log planning action
            self.log_action(state, "plan_created", {
                "plan_type": plan_type,
                "items_count": len(plan.get("plan_items", [])),
                "requires_bookings": len(plan.get("logistics", {}).get("reservations_needed", []))
            })
            
            # Determine next steps
            if self._requires_booking(plan):
                state.current_agent = "booking"
            elif self._requires_communication(plan):
                state.current_agent = "communication"
            else:
                state.current_agent = None  # Plan complete
            
        except (json.JSONDecodeError, KeyError) as e:
            # Fallback to simple planning
            fallback_response = await self._fallback_planning(state)
            state.add_message("assistant", fallback_response)
            
            self.log_action(state, "planning_fallback", {
                "error": str(e),
                "fallback_used": True
            })
        
        return state
    
    def _determine_plan_type(self, state: ConversationState) -> str:
        """Determine what type of plan to create."""
        request_lower = state.current_request.lower() if state.current_request else ""
        
        if any(word in request_lower for word in ["trip", "travel", "vacation", "visit"]):
            return "itinerary"
        elif any(word in request_lower for word in ["event", "party", "celebration", "wedding"]):
            return "event_plan"
        elif any(word in request_lower for word in ["schedule", "day", "week", "organize"]):
            return "schedule"
        else:
            return "task_plan"
    
    def _create_tasks_from_plan(self, plan: Dict, state: ConversationState):
        """Create tasks for plan items that require action."""
        reservations_needed = plan.get("logistics", {}).get("reservations_needed", [])
        
        for i, reservation in enumerate(reservations_needed):
            task_id = f"booking_{i+1}"
            description = f"Book {reservation}"
            state.add_task(task_id, description)
        
        # Add communication tasks if needed
        next_steps = plan.get("next_steps", [])
        for i, step in enumerate(next_steps):
            if any(word in step.lower() for word in ["email", "call", "contact", "notify"]):
                task_id = f"communication_{i+1}"
                state.add_task(task_id, step)
    
    def _format_plan_response(self, plan: Dict) -> str:
        """Format the plan into a user-friendly response."""
        response_parts = [f"# {plan.get('title', 'Your Plan')}\n"]
        
        # Add overview
        if plan.get("duration"):
            response_parts.append(f"**Duration:** {plan['duration']}")
        if plan.get("total_estimated_cost"):
            response_parts.append(f"**Estimated Cost:** {plan['total_estimated_cost']}")
        
        response_parts.append("")  # Empty line
        
        # Add plan items
        plan_items = plan.get("plan_items", [])
        if plan_items:
            response_parts.append("## Schedule")
            
            for item in plan_items:
                time_str = item.get("time", "")
                activity = item.get("activity", "")
                location = item.get("location", "")
                duration = item.get("duration", "")
                cost = item.get("cost", "")
                
                response_parts.append(f"### {time_str} - {activity}")
                
                if location:
                    response_parts.append(f"📍 **Location:** {location}")
                if duration:
                    response_parts.append(f"⏱️ **Duration:** {duration}")
                if cost:
                    response_parts.append(f"💰 **Cost:** {cost}")
                
                if item.get("description"):
                    response_parts.append(f"{item['description']}")
                
                if item.get("prerequisites"):
                    prereq_list = ", ".join(item["prerequisites"])
                    response_parts.append(f"⚠️ **Requirements:** {prereq_list}")
                
                response_parts.append("")  # Empty line between items
        
        # Add logistics
        logistics = plan.get("logistics", {})
        if logistics:
            response_parts.append("## Logistics")
            
            if logistics.get("transportation"):
                response_parts.append(f"🚗 **Transportation:** {logistics['transportation']}")
            if logistics.get("accommodations"):
                response_parts.append(f"🏨 **Accommodations:** {logistics['accommodations']}")
            if logistics.get("reservations_needed"):
                reservations = ", ".join(logistics["reservations_needed"])
                response_parts.append(f"📅 **Reservations Needed:** {reservations}")
            if logistics.get("packing_list"):
                packing = ", ".join(logistics["packing_list"])
                response_parts.append(f"🎒 **What to Bring:** {packing}")
            
            response_parts.append("")
        
        # Add summary and next steps
        if plan.get("summary"):
            response_parts.append("## Summary")
            response_parts.append(plan["summary"])
            response_parts.append("")
        
        if plan.get("next_steps"):
            response_parts.append("## Next Steps")
            for i, step in enumerate(plan["next_steps"], 1):
                response_parts.append(f"{i}. {step}")
        
        return "\n".join(response_parts)
    
    def _requires_booking(self, plan: Dict) -> bool:
        """Check if the plan requires booking actions."""
        reservations = plan.get("logistics", {}).get("reservations_needed", [])
        return len(reservations) > 0
    
    def _requires_communication(self, plan: Dict) -> bool:
        """Check if the plan requires communication actions."""
        next_steps = plan.get("next_steps", [])
        return any(
            word in step.lower() 
            for step in next_steps 
            for word in ["email", "call", "contact", "notify", "send"]
        )
    
    async def _fallback_planning(self, state: ConversationState) -> str:
        """Provide fallback planning when JSON parsing fails."""
        plan_type = self._determine_plan_type(state)
        
        fallback_prompt = f"""Create a simple {plan_type} based on the user's request. 
        Include timing, activities, and practical considerations.
        
        Request: {state.current_request}
        Available options: {state.search_results if state.search_results else 'None'}
        
        Provide a clear, structured response with specific recommendations."""
        
        prompt = self.create_prompt_template(fallback_prompt, include_context=False)
        context = {"current_request": state.current_request}
        
        return await self.invoke_llm(prompt, context)