#!/usr/bin/env python3
"""
Simple test script for the Aria AI Concierge system.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from aria_concierge.workflows.concierge_workflow import ConciergeWorkflow


async def test_concierge():
    """Test the concierge workflow with sample requests."""
    
    print("🤖 Testing Aria AI Concierge System\n")
    print("=" * 50)
    
    # Initialize the workflow
    try:
        concierge = ConciergeWorkflow()
        print("✅ Concierge workflow initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize workflow: {e}")
        return
    
    # Test requests
    test_requests = [
        "Hello Aria, can you help me find a good Italian restaurant for tonight?",
        "I need to plan a romantic dinner for my anniversary next Friday",
        "Find me a hotel in downtown for this weekend",
        "Plan a day trip to the local attractions"
    ]
    
    user_id = "test_user"
    session_id = "test_session"
    
    for i, request in enumerate(test_requests, 1):
        print(f"\n🧪 Test {i}: {request}")
        print("-" * 50)
        
        try:
            result = await concierge.process_message(
                user_id=user_id,
                session_id=f"{session_id}_{i}",
                message=request
            )
            
            print(f"✅ Response: {result['response'][:200]}...")
            if result['active_tasks']:
                print(f"📋 Active Tasks: {len(result['active_tasks'])}")
            if result['recommendations']:
                print(f"💡 Recommendations: {len(result['recommendations'])}")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Testing complete!")


async def interactive_test():
    """Interactive test mode."""
    
    print("🤖 Aria AI Concierge - Interactive Mode")
    print("Type 'quit' to exit\n")
    
    concierge = ConciergeWorkflow()
    user_id = "interactive_user"
    session_id = "interactive_session"
    
    while True:
        try:
            user_input = input("You: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                break
            
            if not user_input:
                continue
            
            print("Aria: Thinking...")
            
            result = await concierge.process_message(
                user_id=user_id,
                session_id=session_id,
                message=user_input
            )
            
            print(f"Aria: {result['response']}\n")
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}\n")
    
    print("Goodbye! 👋")


if __name__ == "__main__":
    # Check if we have required environment variables
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
        print("⚠️  Warning: No LLM API key found!")
        print("Please set either OPENAI_API_KEY or ANTHROPIC_API_KEY in your environment")
        print("The system will use mock responses for testing.\n")
    
    # Run tests
    if len(sys.argv) > 1 and sys.argv[1] == "interactive":
        asyncio.run(interactive_test())
    else:
        asyncio.run(test_concierge())