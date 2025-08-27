"""
Research Agent - Gathers information and provides recommendations.
Handles searches for restaurants, hotels, flights, events, and general information.
"""

from typing import Dict, Any, List, Optional
from ..models.state import ConversationState
from .base import BaseAgent
from ..tools.search import SearchTool
from ..tools.maps import MapsTool
from ..tools.recommendations import RecommendationTool
import json


class ResearchAgent(BaseAgent):
    """Agent that researches and provides recommendations."""
    
    def __init__(self):
        super().__init__(
            name="research",
            description="Researches information and provides recommendations for dining, travel, entertainment, and services",
            temperature=0.3
        )
        
        # Initialize research tools
        self.search_tool = SearchTool()
        self.maps_tool = MapsTool()
        self.recommendation_tool = RecommendationTool()
        
        self.tools = [self.search_tool, self.maps_tool, self.recommendation_tool]
    
    def get_system_prompt(self) -> str:
        return """You are Aria's Research Agent, an expert at finding information and providing personalized recommendations.

Your capabilities include:
- Restaurant research with cuisine, location, price, and dietary filters
- Hotel and accommodation searches
- Flight and travel option research  
- Event and entertainment discovery
- Local business and service recommendations
- Comparative analysis of options

When researching, consider:
1. User preferences and dietary restrictions
2. Budget constraints and value
3. Location convenience and accessibility
4. Quality ratings and reviews
5. Availability and timing

For each recommendation, provide:
- Name and basic details
- Why it matches user preferences
- Price/budget information
- Location and accessibility
- Ratings or quality indicators
- Any special notes or considerations

Always aim to provide 3-5 well-researched options with clear reasoning for each recommendation.

Respond in this JSON format:
{
    "research_type": "restaurants|hotels|flights|events|services",
    "search_criteria": {
        "location": "specified location",
        "date": "date if applicable",
        "budget": "budget range",
        "preferences": ["pref1", "pref2"]
    },
    "recommendations": [
        {
            "name": "Business Name",
            "type": "restaurant|hotel|flight|etc",
            "description": "Brief description",
            "match_reason": "Why this matches user needs",
            "details": {
                "address": "address",
                "price_range": "$-$$$$",
                "rating": "4.5/5",
                "cuisine": "if applicable",
                "availability": "availability info"
            },
            "pros": ["advantage 1", "advantage 2"],
            "cons": ["limitation 1", "limitation 2"],
            "booking_info": "how to book or contact"
        }
    ],
    "summary": "Overall summary and next steps",
    "additional_notes": "Any important considerations"
}"""
    
    async def process(self, state: ConversationState) -> ConversationState:
        """Research information based on the user's request."""
        
        # Determine research type from entities and request
        research_type = self._determine_research_type(state)
        
        # Create research prompt
        prompt = self.create_prompt_template(self.get_system_prompt())
        context = self.format_context(state)
        context["research_type"] = research_type
        
        try:
            # Get research results from LLM
            response = await self.invoke_llm(prompt, context)
            research_results = json.loads(response)
            
            # Enhance results with external data if needed
            enhanced_results = await self._enhance_with_external_data(research_results, state)
            
            # Update state with research results
            state.search_results = enhanced_results["recommendations"]
            state.agent_context["research_results"] = enhanced_results
            
            # Create user-friendly response
            response_text = self._format_research_response(enhanced_results)
            state.add_message("assistant", response_text, {
                "research_type": research_type,
                "recommendations_count": len(enhanced_results["recommendations"])
            })
            
            # Log research action
            self.log_action(state, "research_completed", {
                "research_type": research_type,
                "recommendations_count": len(enhanced_results["recommendations"]),
                "search_criteria": enhanced_results.get("search_criteria", {})
            })
            
            # Determine next steps
            if self._should_route_to_planning(enhanced_results, state):
                state.current_agent = "planning"
            elif self._should_route_to_booking(enhanced_results, state):
                state.current_agent = "booking"
            else:
                state.current_agent = None  # Research complete, await user input
            
        except (json.JSONDecodeError, KeyError) as e:
            # Fallback to simple text response
            fallback_response = await self._fallback_research(state)
            state.add_message("assistant", fallback_response)
            
            self.log_action(state, "research_fallback", {
                "error": str(e),
                "fallback_used": True
            })
        
        return state
    
    def _determine_research_type(self, state: ConversationState) -> str:
        """Determine what type of research to perform."""
        request_lower = state.current_request.lower() if state.current_request else ""
        
        # Check entities first
        if state.intent:
            if "dining" in state.intent or "restaurant" in state.intent:
                return "restaurants"
            elif "travel" in state.intent or "hotel" in state.intent:
                return "hotels"
            elif "flight" in state.intent:
                return "flights"
            elif "event" in state.intent or "entertainment" in state.intent:
                return "events"
        
        # Fallback to keyword matching
        if any(word in request_lower for word in ["restaurant", "food", "dining", "eat", "cuisine"]):
            return "restaurants"
        elif any(word in request_lower for word in ["hotel", "stay", "accommodation", "room"]):
            return "hotels"
        elif any(word in request_lower for word in ["flight", "fly", "airline", "plane"]):
            return "flights"
        elif any(word in request_lower for word in ["event", "show", "concert", "activity", "entertainment"]):
            return "events"
        else:
            return "general"
    
    async def _enhance_with_external_data(self, research_results: Dict, state: ConversationState) -> Dict:
        """Enhance research results with data from external APIs."""
        research_type = research_results.get("research_type", "general")
        
        # For now, return the original results
        # In a full implementation, this would call external APIs like:
        # - Google Places API for restaurant data
        # - Yelp API for reviews and ratings
        # - Hotel booking APIs for availability
        # - Flight search APIs for real-time prices
        
        return research_results
    
    def _format_research_response(self, research_results: Dict) -> str:
        """Format research results into a user-friendly response."""
        recommendations = research_results.get("recommendations", [])
        research_type = research_results.get("research_type", "options")
        
        if not recommendations:
            return f"I couldn't find any {research_type} that match your criteria. Could you provide more details or adjust your preferences?"
        
        response_parts = [f"I found {len(recommendations)} great {research_type} for you:\n"]
        
        for i, rec in enumerate(recommendations, 1):
            name = rec.get("name", "Unknown")
            description = rec.get("description", "")
            match_reason = rec.get("match_reason", "")
            details = rec.get("details", {})
            
            response_parts.append(f"{i}. **{name}**")
            if description:
                response_parts.append(f"   {description}")
            if match_reason:
                response_parts.append(f"   ✨ {match_reason}")
            
            # Add key details
            detail_items = []
            if details.get("price_range"):
                detail_items.append(f"Price: {details['price_range']}")
            if details.get("rating"):
                detail_items.append(f"Rating: {details['rating']}")
            if details.get("address"):
                detail_items.append(f"Location: {details['address']}")
            
            if detail_items:
                response_parts.append(f"   📍 {' | '.join(detail_items)}")
            
            response_parts.append("")  # Empty line between recommendations
        
        # Add summary
        if research_results.get("summary"):
            response_parts.append(research_results["summary"])
        
        return "\n".join(response_parts)
    
    def _should_route_to_planning(self, research_results: Dict, state: ConversationState) -> bool:
        """Determine if we should route to planning agent next."""
        # Route to planning if the request involves multiple steps or itinerary creation
        request_lower = state.current_request.lower() if state.current_request else ""
        planning_keywords = ["plan", "itinerary", "schedule", "organize", "day", "trip"]
        
        return any(keyword in request_lower for keyword in planning_keywords)
    
    def _should_route_to_booking(self, research_results: Dict, state: ConversationState) -> bool:
        """Determine if we should route to booking agent next."""
        # Route to booking if user expressed intent to book/reserve
        request_lower = state.current_request.lower() if state.current_request else ""
        booking_keywords = ["book", "reserve", "make reservation", "get table", "purchase"]
        
        return any(keyword in request_lower for keyword in booking_keywords)
    
    async def _fallback_research(self, state: ConversationState) -> str:
        """Provide a fallback research response when JSON parsing fails."""
        research_type = self._determine_research_type(state)
        
        # Create a simple prompt for fallback
        fallback_prompt = f"""Based on the user's request for {research_type}, provide 2-3 helpful recommendations with brief descriptions. 
        Consider their preferences: {state.preferences.model_dump()}
        
        Request: {state.current_request}
        
        Provide a conversational response with specific recommendations."""
        
        prompt = self.create_prompt_template(fallback_prompt, include_context=False)
        context = {"current_request": state.current_request}
        
        return await self.invoke_llm(prompt, context)