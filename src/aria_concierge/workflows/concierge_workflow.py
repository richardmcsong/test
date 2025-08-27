"""
Main LangGraph workflow for the Aria concierge system.
Orchestrates the flow between different agents and manages conversation state.
"""

from typing import Dict, Any, List, Optional
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from ..models.state import ConversationState
from ..agents.router import RouterAgent
from ..agents.research import ResearchAgent
from ..agents.planning import PlanningAgent
from ..agents.booking import BookingAgent
from ..agents.communication import CommunicationAgent
import sqlite3
import os


class ConciergeWorkflow:
    """Main workflow orchestrator for the Aria concierge system."""
    
    def __init__(self, db_path: str = "./data/checkpoints.db"):
        self.db_path = db_path
        
        # Initialize agents
        self.router_agent = RouterAgent()
        self.research_agent = ResearchAgent()
        self.planning_agent = PlanningAgent()
        self.booking_agent = BookingAgent()
        self.communication_agent = CommunicationAgent()
        
        # Create workflow graph
        self.workflow = self._create_workflow()
        
        # Setup checkpointing for conversation memory
        self._setup_checkpointing()
    
    def _create_workflow(self) -> StateGraph:
        """Create the LangGraph workflow."""
        
        # Define the state graph
        workflow = StateGraph(ConversationState)
        
        # Add nodes for each agent
        workflow.add_node("router", self._router_node)
        workflow.add_node("research", self._research_node)
        workflow.add_node("planning", self._planning_node)
        workflow.add_node("booking", self._booking_node)
        workflow.add_node("communication", self._communication_node)
        workflow.add_node("user_input", self._user_input_node)
        
        # Define the flow logic
        workflow.set_entry_point("router")
        
        # Router decides which agent to use
        workflow.add_conditional_edges(
            "router",
            self._route_to_agent,
            {
                "research": "research",
                "planning": "planning", 
                "booking": "booking",
                "communication": "communication",
                "user_input": "user_input",
                "end": END
            }
        )
        
        # Each agent can route to others or back to user
        for agent in ["research", "planning", "booking", "communication"]:
            workflow.add_conditional_edges(
                agent,
                self._agent_next_step,
                {
                    "research": "research",
                    "planning": "planning",
                    "booking": "booking", 
                    "communication": "communication",
                    "user_input": "user_input",
                    "router": "router",
                    "end": END
                }
            )
        
        # User input always goes back to router
        workflow.add_edge("user_input", "router")
        
        return workflow
    
    def _setup_checkpointing(self):
        """Setup SQLite checkpointing for conversation memory."""
        # Ensure data directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # Create checkpointer
        self.checkpointer = SqliteSaver.from_conn_string(f"sqlite:///{self.db_path}")
        
        # Compile workflow with checkpointing
        self.app = self.workflow.compile(checkpointer=self.checkpointer)
    
    async def _router_node(self, state: ConversationState) -> ConversationState:
        """Router agent node."""
        return await self.router_agent.process(state)
    
    async def _research_node(self, state: ConversationState) -> ConversationState:
        """Research agent node."""
        return await self.research_agent.process(state)
    
    async def _planning_node(self, state: ConversationState) -> ConversationState:
        """Planning agent node."""
        return await self.planning_agent.process(state)
    
    async def _booking_node(self, state: ConversationState) -> ConversationState:
        """Booking agent node."""
        return await self.booking_agent.process(state)
    
    async def _communication_node(self, state: ConversationState) -> ConversationState:
        """Communication agent node."""
        return await self.communication_agent.process(state)
    
    async def _user_input_node(self, state: ConversationState) -> ConversationState:
        """Handle user input and prepare for next routing."""
        # This node represents waiting for user input
        # In practice, this would be handled by the web interface
        state.current_agent = None
        return state
    
    def _route_to_agent(self, state: ConversationState) -> str:
        """Determine which agent should handle the request."""
        if not state.current_request:
            return "user_input"
        
        if state.current_agent:
            return state.current_agent
        
        return "research"  # Default fallback
    
    def _agent_next_step(self, state: ConversationState) -> str:
        """Determine next step after agent processing."""
        
        # Check if agent set a specific next agent
        if state.current_agent and state.current_agent != state.messages[-1].get("metadata", {}).get("from_agent"):
            return state.current_agent
        
        # Check if there are pending tasks that need other agents
        if state.active_tasks:
            for task in state.active_tasks:
                if "booking" in task.description.lower() and task.status == "pending":
                    return "booking"
                elif "plan" in task.description.lower() and task.status == "pending":
                    return "planning"
                elif "email" in task.description.lower() or "message" in task.description.lower():
                    return "communication"
        
        # Check agent sequence from routing decision
        agent_sequence = state.agent_context.get("agent_sequence", [])
        if len(agent_sequence) > 1:
            current_index = 0
            current_agent = state.agent_context.get("current_agent_in_sequence")
            
            if current_agent in agent_sequence:
                current_index = agent_sequence.index(current_agent)
            
            if current_index + 1 < len(agent_sequence):
                next_agent = agent_sequence[current_index + 1]
                state.agent_context["current_agent_in_sequence"] = next_agent
                return next_agent
        
        # Default to waiting for user input
        return "user_input"
    
    async def process_message(
        self,
        user_id: str,
        session_id: str,
        message: str,
        preferences: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Process a user message through the workflow."""
        
        # Create or load conversation state
        config = {"configurable": {"thread_id": f"{user_id}_{session_id}"}}
        
        try:
            # Try to get existing state
            current_state = await self.app.aget_state(config)
            if current_state.values:
                state = ConversationState.from_dict(current_state.values)
            else:
                # Create new state
                state = ConversationState(
                    user_id=user_id,
                    session_id=session_id
                )
                if preferences:
                    state.preferences = state.preferences.model_validate(preferences)
        except:
            # Create new state if loading fails
            state = ConversationState(
                user_id=user_id,
                session_id=session_id
            )
        
        # Add user message
        state.add_message("user", message)
        state.current_request = message
        
        # Process through workflow
        try:
            result = await self.app.ainvoke(state.to_dict(), config)
            final_state = ConversationState.from_dict(result)
            
            # Get the last assistant message
            assistant_messages = [msg for msg in final_state.messages if msg["role"] == "assistant"]
            last_response = assistant_messages[-1]["content"] if assistant_messages else "I'm here to help! What can I do for you?"
            
            return {
                "response": last_response,
                "state": final_state.to_dict(),
                "active_tasks": [task.model_dump() for task in final_state.active_tasks],
                "recommendations": final_state.search_results
            }
            
        except Exception as e:
            print(f"Error processing message: {e}")
            return {
                "response": "I apologize, but I encountered an error processing your request. Could you please try again?",
                "state": state.to_dict(),
                "active_tasks": [],
                "recommendations": [],
                "error": str(e)
            }
    
    async def get_conversation_history(
        self,
        user_id: str,
        session_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get conversation history for a user session."""
        config = {"configurable": {"thread_id": f"{user_id}_{session_id}"}}
        
        try:
            current_state = await self.app.aget_state(config)
            if current_state.values:
                state = ConversationState.from_dict(current_state.values)
                return state.messages[-limit:] if len(state.messages) > limit else state.messages
        except:
            pass
        
        return []
    
    async def clear_conversation(self, user_id: str, session_id: str) -> bool:
        """Clear conversation history for a user session."""
        # Note: LangGraph doesn't have a built-in clear method
        # In production, you'd implement this by deleting from the checkpoint database
        return True