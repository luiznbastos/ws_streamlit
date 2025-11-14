import streamlit as st
import requests
from typing import List, Dict, Any

# Mock data to simulate API responses
MOCK_CONVERSATIONS = []

MOCK_MESSAGES = {}

def get_conversations() -> List[Dict[str, Any]]:
    """
    Fetches the list of all conversations.
    """
    return MOCK_CONVERSATIONS

def get_conversation_messages(conversation_id: str) -> List[Dict[str, Any]]:
    """
    Fetches all messages for a specific conversation.
    """
    return MOCK_MESSAGES.get(conversation_id, [])
