"""
State management for the Aria concierge system.
Defines the conversation state and user context.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime
import json


class UserPreferences(BaseModel):
    """User preferences and profile information."""
    dietary_restrictions: List[str] = Field(default_factory=list)
    cuisine_preferences: List[str] = Field(default_factory=list)
    budget_ranges: Dict[str, Dict[str, float]] = Field(default_factory=dict)  # category -> {min, max}
    location_preferences: Dict[str, str] = Field(default_factory=dict)  # home, work, etc.
    communication_preferences: Dict[str, bool] = Field(default_factory=dict)
    calendar_timezone: str = "UTC"
    preferred_travel_class: str = "economy"
    loyalty_programs: Dict[str, str] = Field(default_factory=dict)  # airline/hotel -> member_id


class TaskStatus(BaseModel):
    """Status of a task or request."""
    task_id: str
    description: str
    status: str  # pending, in_progress, completed, failed
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class ConversationState(BaseModel):
    """Main state object for the concierge conversation."""
    
    # User information
    user_id: str
    session_id: str
    preferences: UserPreferences = Field(default_factory=UserPreferences)
    
    # Current conversation
    messages: List[Dict[str, str]] = Field(default_factory=list)
    current_request: Optional[str] = None
    intent: Optional[str] = None
    entities: Dict[str, Any] = Field(default_factory=dict)
    
    # Context and memory
    conversation_history: List[Dict[str, Any]] = Field(default_factory=list)
    active_tasks: List[TaskStatus] = Field(default_factory=list)
    completed_tasks: List[TaskStatus] = Field(default_factory=list)
    
    # Agent routing
    current_agent: Optional[str] = None
    agent_context: Dict[str, Any] = Field(default_factory=dict)
    
    # External data
    search_results: List[Dict[str, Any]] = Field(default_factory=list)
    booking_details: Dict[str, Any] = Field(default_factory=dict)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        """Add a message to the conversation."""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        self.messages.append(message)
        self.updated_at = datetime.now()
    
    def add_task(self, task_id: str, description: str) -> TaskStatus:
        """Add a new task to track."""
        task = TaskStatus(task_id=task_id, description=description, status="pending")
        self.active_tasks.append(task)
        return task
    
    def update_task(self, task_id: str, status: str, result: Optional[Dict] = None, error: Optional[str] = None):
        """Update a task's status."""
        for task in self.active_tasks:
            if task.task_id == task_id:
                task.status = status
                task.updated_at = datetime.now()
                if result:
                    task.result = result
                if error:
                    task.error_message = error
                
                # Move completed/failed tasks to completed list
                if status in ["completed", "failed"]:
                    self.active_tasks.remove(task)
                    self.completed_tasks.append(task)
                break
    
    def get_context_summary(self) -> str:
        """Get a summary of the current context for the LLM."""
        summary_parts = []
        
        # User preferences
        if self.preferences.dietary_restrictions:
            summary_parts.append(f"Dietary restrictions: {', '.join(self.preferences.dietary_restrictions)}")
        
        if self.preferences.cuisine_preferences:
            summary_parts.append(f"Preferred cuisines: {', '.join(self.preferences.cuisine_preferences)}")
        
        # Active tasks
        if self.active_tasks:
            active_task_desc = [task.description for task in self.active_tasks]
            summary_parts.append(f"Active tasks: {', '.join(active_task_desc)}")
        
        # Recent conversation context
        if len(self.messages) > 1:
            recent_messages = self.messages[-3:]  # Last 3 messages
            context = " | ".join([f"{msg['role']}: {msg['content'][:100]}..." for msg in recent_messages])
            summary_parts.append(f"Recent context: {context}")
        
        return " | ".join(summary_parts) if summary_parts else "No specific context available"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary for serialization."""
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationState":
        """Create state from dictionary."""
        return cls.model_validate(data)