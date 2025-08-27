# 🤖 Aria AI Concierge

Your Personal Lifestyle Assistant powered by LangGraph

## Overview

Aria is an intelligent AI concierge system that helps with dining, travel, personal organization, and lifestyle management. Built with LangGraph, it uses specialized agents to handle complex multi-step requests through natural conversation.

## ✨ Features

### Core Capabilities
- **🍽️ Dining & Entertainment**: Restaurant recommendations, reservations, event discovery
- **✈️ Travel Planning**: Multi-city itineraries, hotel bookings, activity suggestions  
- **📅 Personal Organization**: Calendar management, task scheduling, email drafting
- **🏠 Lifestyle Services**: Appointment booking, personal shopping, service coordination

### Technical Features
- **LangGraph Workflow**: Orchestrated agent system with state management
- **Specialized Agents**: Router, Research, Planning, Booking, Communication
- **Memory & Context**: Persistent conversation history and user preferences
- **External Integrations**: Ready for Google Maps, OpenTable, hotel APIs, etc.
- **Web Interface**: FastAPI-based REST API with chat interface

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up Environment

Copy the example environment file and add your API keys:

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:
```bash
# Required: At least one LLM API key
OPENAI_API_KEY=your_openai_api_key_here
# OR
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Optional: External service APIs
GOOGLE_MAPS_API_KEY=your_google_maps_key
YELP_API_KEY=your_yelp_key
```

### 3. Run the System

#### Option A: Web Server (Recommended)
```bash
python run_server.py
```

Then visit: http://localhost:8000

#### Option B: Command Line Test
```bash
python test_aria.py
```

#### Option C: Interactive Mode
```bash
python test_aria.py interactive
```

## 🧪 Testing the System

### Sample Requests to Try

1. **Restaurant Reservation**:
   ```
   "I need a romantic Italian restaurant for Friday night, party of 2"
   ```

2. **Travel Planning**:
   ```
   "Plan a weekend trip to San Francisco with good hotels and activities"
   ```

3. **Complex Request**:
   ```
   "Plan my anniversary dinner - Italian food, downtown, under $200, my partner has shellfish allergies"
   ```

4. **Multi-step Planning**:
   ```
   "Organize a business dinner for 6 people next Tuesday, need restaurant reservation and calendar invites"
   ```

### API Testing

Test the chat API directly:

```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Find me a good sushi restaurant for tonight",
    "user_id": "test_user",
    "session_id": "test_session"
  }'
```

## 🏗️ Architecture

### Agent System
- **RouterAgent**: Analyzes requests and routes to appropriate specialists
- **ResearchAgent**: Finds restaurants, hotels, events, and information
- **PlanningAgent**: Creates itineraries and multi-step plans
- **BookingAgent**: Handles reservations and transactions (simulated)
- **CommunicationAgent**: Manages emails, calendar events, and notifications

### Workflow Flow
1. User sends message
2. Router analyzes intent and extracts entities
3. Appropriate specialist agent processes request
4. Results are formatted and returned to user
5. State is persisted for conversation continuity

### State Management
- **ConversationState**: Tracks messages, tasks, preferences, and context
- **SQLite Checkpointing**: Persistent conversation memory
- **User Preferences**: Dietary restrictions, budget ranges, location preferences

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key for GPT models | One of OpenAI/Anthropic |
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude | One of OpenAI/Anthropic |
| `GOOGLE_MAPS_API_KEY` | Google Maps API for locations | Optional |
| `YELP_API_KEY` | Yelp API for restaurant data | Optional |
| `HOST` | Server host (default: 0.0.0.0) | Optional |
| `PORT` | Server port (default: 8000) | Optional |
| `DEBUG` | Debug mode (default: True) | Optional |

### Mock Mode

The system works without external API keys by using mock data for:
- Restaurant searches
- Hotel recommendations  
- Event listings
- Booking confirmations

This is perfect for testing and development!

## 📁 Project Structure

```
aria-concierge/
├── src/aria_concierge/
│   ├── agents/          # Specialized AI agents
│   ├── tools/           # External API integrations
│   ├── workflows/       # LangGraph workflow orchestration
│   ├── models/          # Data models and state management
│   ├── api/             # FastAPI web interface
│   └── web/             # Frontend assets
├── tests/               # Test files
├── data/                # Database and checkpoints
├── credentials/         # API credentials
├── requirements.txt     # Python dependencies
├── test_aria.py         # Test script
├── run_server.py        # Web server launcher
└── README.md           # This file
```

## 🛠️ Development

### Adding New Agents

1. Create new agent in `src/aria_concierge/agents/`
2. Inherit from `BaseAgent`
3. Implement `get_system_prompt()` and `process()` methods
4. Add to workflow in `concierge_workflow.py`

### Adding External APIs

1. Create new tool in `src/aria_concierge/tools/`
2. Add API integration logic
3. Include in relevant agent's tool list
4. Add API keys to `.env.example`

### Testing

```bash
# Run all tests
python -m pytest tests/

# Test specific functionality
python test_aria.py

# Interactive testing
python test_aria.py interactive
```

## 🚨 Known Limitations

- **Demo System**: Bookings are simulated, not real transactions
- **Mock Data**: Uses placeholder data when external APIs aren't configured
- **No Authentication**: Current version has no user authentication
- **Limited Integrations**: External APIs need to be implemented for production use

## 🎯 Production Deployment

For production use:

1. **Add Authentication**: Implement user authentication and authorization
2. **External APIs**: Integrate real booking and search APIs
3. **Database**: Use PostgreSQL instead of SQLite
4. **Monitoring**: Add logging, metrics, and error tracking
5. **Security**: Add rate limiting, input validation, and security headers
6. **Scaling**: Deploy with Docker and container orchestration

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is open source and available under the MIT License.

---

**Happy Concierging! 🎩✨**

For questions or support, please open an issue on GitHub.