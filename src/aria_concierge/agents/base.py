"""
Base agent class for all Aria concierge agents.
Provides common functionality and interface.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, PydanticOutputParser
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
import os
from ..models.state import ConversationState


class BaseAgent(ABC):
    """Base class for all concierge agents."""
    
    def __init__(
        self,
        name: str,
        description: str,
        llm: Optional[BaseChatModel] = None,
        temperature: float = 0.1
    ):
        self.name = name
        self.description = description
        self.llm = llm or self._get_default_llm(temperature)
        self.tools = []
    
    def _get_default_llm(self, temperature: float) -> BaseChatModel:
        """Get the default LLM based on available API keys."""
        if os.getenv("OPENAI_API_KEY"):
            return ChatOpenAI(
                model="gpt-4-turbo-preview",
                temperature=temperature
            )
        elif os.getenv("ANTHROPIC_API_KEY"):
            return ChatAnthropic(
                model="claude-3-sonnet-20240229",
                temperature=temperature
            )
        else:
            raise ValueError("No LLM API key found. Please set OPENAI_API_KEY or ANTHROPIC_API_KEY")
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """Get the system prompt for this agent."""
        pass
    
    @abstractmethod
    async def process(self, state: ConversationState) -> ConversationState:
        """Process the current state and return updated state."""
        pass
    
    def create_prompt_template(self, system_message: str, include_context: bool = True) -> ChatPromptTemplate:
        """Create a prompt template with optional context."""
        messages = [("system", system_message)]
        
        if include_context:
            messages.append(("human", """
Context: {context}
Current request: {current_request}
User preferences: {preferences}

Please process this request and provide your response.
"""))
        else:
            messages.append(("human", "{current_request}"))
        
        return ChatPromptTemplate.from_messages(messages)
    
    def format_context(self, state: ConversationState) -> Dict[str, str]:
        """Format the state into context for the LLM."""
        return {
            "context": state.get_context_summary(),
            "current_request": state.current_request or "",
            "preferences": str(state.preferences.model_dump()),
            "active_tasks": str([task.description for task in state.active_tasks]),
            "entities": str(state.entities)
        }
    
    async def invoke_llm(
        self, 
        prompt_template: ChatPromptTemplate, 
        context: Dict[str, Any],
        parser: Optional[Any] = None
    ) -> str:
        """Invoke the LLM with the given prompt and context."""
        chain = prompt_template | self.llm
        
        if parser:
            chain = chain | parser
        else:
            chain = chain | StrOutputParser()
        
        return await chain.ainvoke(context)
    
    def log_action(self, state: ConversationState, action: str, details: Optional[Dict] = None):
        """Log an action taken by this agent."""
        log_entry = {
            "agent": self.name,
            "action": action,
            "details": details or {},
            "timestamp": state.updated_at.isoformat()
        }
        
        if "agent_logs" not in state.agent_context:
            state.agent_context["agent_logs"] = []
        
        state.agent_context["agent_logs"].append(log_entry)
    
    def should_handle(self, state: ConversationState) -> bool:
        """Determine if this agent should handle the current request."""
        return state.current_agent == self.name or state.current_agent is None