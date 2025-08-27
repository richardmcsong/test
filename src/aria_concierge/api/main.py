"""
FastAPI main application for the Aria concierge system.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import uuid
import os
from pathlib import Path

from ..workflows.concierge_workflow import ConciergeWorkflow
from ..models.state import UserPreferences

# Initialize FastAPI app
app = FastAPI(
    title="Aria AI Concierge",
    description="Your Personal Lifestyle Assistant powered by LangGraph",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the concierge workflow
concierge = ConciergeWorkflow()

# Pydantic models for API
class ChatMessage(BaseModel):
    message: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str
    active_tasks: List[Dict[str, Any]]
    recommendations: List[Dict[str, Any]]
    conversation_id: str

class UserPreferencesUpdate(BaseModel):
    user_id: str
    preferences: Dict[str, Any]

# API Routes
@app.post("/api/chat", response_model=ChatResponse)
async def chat(message: ChatMessage):
    """Main chat endpoint for interacting with Aria."""
    
    try:
        # Generate IDs if not provided
        user_id = message.user_id or str(uuid.uuid4())
        session_id = message.session_id or str(uuid.uuid4())
        
        # Process the message
        result = await concierge.process_message(
            user_id=user_id,
            session_id=session_id,
            message=message.message,
            preferences=message.preferences
        )
        
        return ChatResponse(
            response=result["response"],
            session_id=session_id,
            active_tasks=result["active_tasks"],
            recommendations=result["recommendations"],
            conversation_id=f"{user_id}_{session_id}"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")

@app.get("/api/conversation/{conversation_id}/history")
async def get_conversation_history(conversation_id: str, limit: int = 50):
    """Get conversation history for a specific conversation."""
    
    try:
        user_id, session_id = conversation_id.split("_", 1)
        history = await concierge.get_conversation_history(user_id, session_id, limit)
        return {"history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving history: {str(e)}")

@app.delete("/api/conversation/{conversation_id}")
async def clear_conversation(conversation_id: str):
    """Clear conversation history."""
    
    try:
        user_id, session_id = conversation_id.split("_", 1)
        success = await concierge.clear_conversation(user_id, session_id)
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing conversation: {str(e)}")

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "Aria AI Concierge"}

# Serve static files and web interface
static_dir = Path(__file__).parent.parent / "web" / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/", response_class=HTMLResponse)
async def serve_web_interface():
    """Serve the main web interface."""
    html_file = Path(__file__).parent.parent / "web" / "index.html"
    
    if html_file.exists():
        return HTMLResponse(content=html_file.read_text(), status_code=200)
    else:
        return HTMLResponse(content="""
<!DOCTYPE html>
<html>
<head>
    <title>Aria AI Concierge</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #333; text-align: center; }
        .status { text-align: center; color: #666; margin: 20px 0; }
        .api-info { background: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0; }
        code { background: #e9ecef; padding: 2px 6px; border-radius: 3px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Aria AI Concierge</h1>
        <div class="status">Your Personal Lifestyle Assistant is running!</div>
        
        <div class="api-info">
            <h3>API Endpoints:</h3>
            <p><strong>POST</strong> <code>/api/chat</code> - Chat with Aria</p>
            <p><strong>GET</strong> <code>/api/health</code> - Health check</p>
            <p><strong>GET</strong> <code>/api/conversation/{id}/history</code> - Get conversation history</p>
        </div>
        
        <div class="api-info">
            <h3>Example Chat Request:</h3>
            <pre><code>{
  "message": "I need a romantic dinner reservation for Friday night",
  "user_id": "user123",
  "session_id": "session456"
}</code></pre>
        </div>
        
        <div class="api-info">
            <h3>Quick Test:</h3>
            <p>Try this curl command:</p>
            <pre><code>curl -X POST "http://localhost:8000/api/chat" \\
  -H "Content-Type: application/json" \\
  -d '{"message": "Hello Aria, can you help me find a good Italian restaurant?"}'</code></pre>
        </div>
    </div>
</body>
</html>
        """, status_code=200)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    print(f"Starting Aria AI Concierge on {host}:{port}")
    uvicorn.run(app, host=host, port=port)