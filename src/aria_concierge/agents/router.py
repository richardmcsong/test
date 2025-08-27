"""
Router Agent - Determines which specialist agent should handle the request.
Acts as the entry point and traffic director for the concierge system.
"""

from typing import Dict, Any, List
from ..models.state import ConversationState
from .base import BaseAgent
import re
import json


class RouterAgent(BaseAgent):
    """Agent that routes requests to appropriate specialist agents."""
    
    def __init__(self):
        super().__init__(
            name="router",
            description="Routes user requests to appropriate specialist agents",
            temperature=0.0  # We want consistent routing decisions
        )
        
        # Define routing patterns and their corresponding agents
        self.routing_patterns = {
            "research": [
                r"(find|search|look up|tell me about|what is|where can|recommend)",
                r"(restaurant|hotel|flight|activity|event|place)",
                r"(information|details|options|choices)"
            ],
            "planning": [
                r"(plan|organize|schedule|arrange|coordinate)",
                r"(trip|itinerary|day|week|event|meeting)",
                r"(multi|several|multiple|complex)"
            ],
            "booking": [
                r"(book|reserve|purchase|buy|get tickets)",
                r"(reservation|appointment|table|room|flight)",
                r"(confirm|finalize|complete)"
            ],
            "communication": [
                r"(send|email|message|call|notify|remind)",
                r"(draft|write|compose|create)",
                r"(invitation|reminder|update|confirmation)"
            ]
        }
    
    def get_system_prompt(self) -> str:
        return """You are Aria's Router Agent, responsible for analyzing user requests and determining which specialist agent should handle them.

Available Specialist Agents:
1. RESEARCH - Finds information, recommendations, and options (restaurants, hotels, flights, events, etc.)
2. PLANNING - Creates itineraries, schedules, and multi-step plans
3. BOOKING - Makes reservations, purchases tickets, and handles transactions  
4. COMMUNICATION - Sends emails, messages, and manages communications

Your task is to:
1. Analyze the user's request and intent
2. Extract key entities (dates, locations, preferences, etc.)
3. Determine which agent(s) should handle the request
4. Provide routing decision with confidence score

Consider the complexity and dependencies:
- Simple information requests → RESEARCH
- Multi-step planning → PLANNING (may need RESEARCH first)
- Ready to book → BOOKING (may need RESEARCH/PLANNING first)
- Need to communicate → COMMUNICATION

Respond with JSON format:
{
    "primary_agent": "agent_name",
    "secondary_agents": ["agent1", "agent2"],
    "confidence": 0.95,
    "reasoning": "explanation",
    "extracted_entities": {
        "intent": "dining_reservation",
        "date": "2024-01-15",
        "location": "downtown",
        "party_size": 2,
        "cuisine": "italian",
        "budget": "moderate"
    },
    "complexity": "simple|moderate|complex",
    "requires_sequence": false
}"""
    
    async def process(self, state: ConversationState) -> ConversationState:
        """Route the request to appropriate agent(s)."""
        if not state.current_request:
            state.current_agent = "router"
            return state
        
        # Create routing prompt
        prompt = self.create_prompt_template(self.get_system_prompt())
        context = self.format_context(state)
        
        try:
            # Get routing decision from LLM
            response = await self.invoke_llm(prompt, context)
            
            # Parse the JSON response
            routing_decision = json.loads(response)
            
            # Update state with routing information
            state.current_agent = routing_decision["primary_agent"]
            state.intent = routing_decision["extracted_entities"].get("intent")
            state.entities.update(routing_decision["extracted_entities"])
            
            # Store routing context
            state.agent_context["routing_decision"] = routing_decision
            state.agent_context["agent_sequence"] = [routing_decision["primary_agent"]]
            
            if routing_decision.get("secondary_agents"):
                state.agent_context["agent_sequence"].extend(routing_decision["secondary_agents"])
            
            # Log the routing decision
            self.log_action(state, "route_request", {
                "primary_agent": routing_decision["primary_agent"],
                "confidence": routing_decision["confidence"],
                "reasoning": routing_decision["reasoning"]
            })
            
            # Add system message about routing
            state.add_message("system", f"Request routed to {routing_decision['primary_agent']} agent", {
                "routing_decision": routing_decision
            })
            
        except (json.JSONDecodeError, KeyError) as e:
            # Fallback to pattern-based routing
            state.current_agent = self._pattern_based_routing(state.current_request)
            self.log_action(state, "fallback_routing", {
                "error": str(e),
                "fallback_agent": state.current_agent
            })
        
        return state
    
    def _pattern_based_routing(self, request: str) -> str:
        """Fallback pattern-based routing if LLM routing fails."""
        request_lower = request.lower()
        
        # Score each agent based on pattern matches
        agent_scores = {agent: 0 for agent in self.routing_patterns.keys()}
        
        for agent, patterns in self.routing_patterns.items():
            for pattern in patterns:
                if re.search(pattern, request_lower):
                    agent_scores[agent] += 1
        
        # Return agent with highest score, default to research
        best_agent = max(agent_scores, key=agent_scores.get)
        return best_agent if agent_scores[best_agent] > 0 else "research"
    
    def _extract_entities_pattern(self, request: str) -> Dict[str, Any]:
        """Extract entities using regex patterns as fallback."""
        entities = {}
        request_lower = request.lower()
        
        # Date patterns
        date_patterns = [
            r"(tomorrow|today|tonight)",
            r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday)",
            r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            r"(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}"
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, request_lower)
            if match:
                entities["date"] = match.group(1)
                break
        
        # Location patterns
        location_patterns = [
            r"in\s+([\w\s]+?)(?:\s|$|,|\.|for)",
            r"at\s+([\w\s]+?)(?:\s|$|,|\.|for)",
            r"near\s+([\w\s]+?)(?:\s|$|,|\.|for)"
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, request_lower)
            if match:
                entities["location"] = match.group(1).strip()
                break
        
        # Party size patterns
        party_match = re.search(r"(\d+)\s+(?:people|person|guests?|party)", request_lower)
        if party_match:
            entities["party_size"] = int(party_match.group(1))
        
        return entities