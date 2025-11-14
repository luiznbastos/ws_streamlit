"""
Conversation Manager Module

This module provides functionality for managing chatbot conversations in a PostgreSQL database.
It handles:
- Creating and storing conversations with AI-generated titles
- Saving user messages and assistant responses with RAG sources
- Loading conversation history
- Deleting conversations and their associated messages
- Updating conversation titles

The module uses the ZDK library for database operations and integrates with OpenAI
for automatic title generation from user queries.
"""

import uuid
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = None

from zdk.core.database import DBClient, PostgresEngine, ObjectMapper
from zdk.models import Conversation, Message
from src.settings import settings
from zdk.models import Conversation as ConvModel
from zdk.models import Message as MsgModel

logger = logging.getLogger(__name__)


class ConversationManager:
    """
    Manages conversation storage and retrieval for the chatbot
    """
    
    def __init__(self, db_client: DBClient = None):
        """
        Initialize the conversation manager
        
        Args:
            db_client: Optional DBClient instance. If not provided, will create one
                      using environment variables for database connection.
        """
        if db_client is None:
            # Create database connection
            db_engine = PostgresEngine(
                user=settings.rds_user or "company_admin",
                password=settings.rds_password or "diU59nM8Z0t+bb&x",
                host=settings.rds_host or "streamlit-fastapi-company.cet4y0iaow4o.us-east-1.rds.amazonaws.com",
                port=5432,
                dbname=settings.rds_db or "company"
            )
            
            # Create ORM and client
            orm = ObjectMapper(db_engine.engine, schema="public")
            db_client = DBClient(orm)
        
        self.db_client = db_client
        
        # Initialize OpenAI client for title generation
        self.openai_client = None
        if OPENAI_AVAILABLE and hasattr(settings, 'openai_api_key') and settings.openai_api_key:
            try:
                self.openai_client = OpenAI(api_key=settings.openai_api_key)
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI client: {e}")
                self.openai_client = None
    
    def generate_conversation_title(self, first_query: str) -> str:
        """
        Generate a concise title from the first user query using OpenAI
        
        Args:
            first_query: The first message from the user
            
        Returns:
            str: Generated title (max 5 words)
        """
        if not self.openai_client or not OPENAI_AVAILABLE:
            # Fallback: use first 50 characters of query
            return first_query[:50] + "..." if len(first_query) > 50 else first_query
        
        try:
            prompt = f'''Extract a short, concise title (max 5 words) that summarizes this question:
            "{first_query}"
            
            Return only the title, nothing else.'''
            
            response = self.openai_client.chat.completions.create(
                model="gpt-5-nano",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that creates concise titles."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=20
            )
            
            title = response.choices[0].message.content.strip()
            # Ensure title is not too long
            if len(title) > 100:
                title = title[:100] + "..."
            
            return title
            
        except Exception as e:
            logger.error(f"Error generating title: {e}")
            # Fallback: use first 50 characters of query
            return first_query[:50] + "..." if len(first_query) > 50 else first_query
    
    def create_conversation(self, title: str) -> str:
        """
        Create a new conversation in the database
        
        Args:
            title: The conversation title
            
        Returns:
            str: The conversation ID
        """
        try:
            conversation_id = str(uuid.uuid4())
            now = datetime.now()
            
            conversation = Conversation(
                conversation_id=conversation_id,
                title=title,
                created_at=now,
                updated_at=now
            )
            
            self.db_client.write([conversation])
            logger.info(f"Created conversation '{title}' (ID: {conversation_id[:8]}...)")
            
            return conversation_id
            
        except Exception as e:
            logger.error(f"Error creating conversation: {e}")
            raise
    
    def save_message(self, conversation_id: str, role: str, content: str, sources: List[Dict] = None):
        """
        Save a message to the database
        
        Args:
            conversation_id: The conversation ID
            role: 'user' or 'assistant'
            content: The message content
            sources: Optional RAG sources as list of dicts
        """
        try:
            message_id = str(uuid.uuid4())
            
            # Convert sources to JSON string for proper database storage
            sources_json = None
            if sources:
                sources_json = json.dumps(sources)
            elif sources is not None:
                sources_json = json.dumps([])
            
            message = Message(
                message_id=message_id,
                conversation_id=conversation_id,
                role=role,
                content=content,
                sources=sources_json,
                created_at=datetime.now()
            )
            
            self.db_client.write([message])
            logger.info(f"Saved {role} message for conversation {conversation_id[:8]}...")
            
        except Exception as e:
            logger.error(f"Error saving message: {e}")
            raise
    
    def load_conversation(self, conversation_id: str) -> List[Dict]:
        """
        Load all messages for a conversation
        
        Args:
            conversation_id: The conversation ID
            
        Returns:
            List[Dict]: List of message dictionaries
        """
        try:
            # Get messages for this conversation (order_by has issues, sort in Python)
            results = self.db_client.get(   
                entity=MsgModel,
                where_clause=MsgModel.conversation_id == conversation_id,
                as_df=False
            )
            
            # Sort by created_at ASC in Python
            results = sorted(results, key=lambda x: x.created_at)
            
            messages = []
            for msg in results:
                # Parse sources JSON back to Python objects
                sources = None
                if msg.sources:
                    try:
                        sources = json.loads(msg.sources) if isinstance(msg.sources, str) else msg.sources
                    except (json.JSONDecodeError, TypeError):
                        sources = None
                
                messages.append({
                    "role": msg.role,
                    "content": msg.content,
                    "sources": sources,
                    "created_at": msg.created_at
                })
            
            return messages
            
        except Exception as e:
            logger.error(f"Error loading conversation: {e}")
            return []
    
    def list_conversations(self, limit: int = 50) -> List[Dict]:
        """
        Get list of conversations with metadata
        
        Args:
            limit: Maximum number of conversations to return
            
        Returns:
            List[Dict]: List of conversation dictionaries
        """
        try:
            # Get all conversations from database
            results = self.db_client.get(entity=ConvModel, as_df=False)
            
            # Sort by updated_at DESC and limit
            sorted_results = sorted(results, key=lambda x: x.updated_at, reverse=True)[:limit]
            
            # Convert to dictionary format
            conversations = [
                {
                    "conversation_id": conv.conversation_id,
                    "title": conv.title,
                    "created_at": conv.created_at,
                    "updated_at": conv.updated_at
                }
                for conv in sorted_results
            ]
            
            return conversations
            
        except Exception as e:
            logger.error(f"Error listing conversations: {e}")
            return []
    
    def delete_conversation(self, conversation_id: str):
        """
        Delete a conversation and all its messages
        
        Args:
            conversation_id: The conversation ID to delete
        """
        try:
            # Use a simpler approach with direct SQL execution
            # Delete messages first (foreign key constraint)
            messages_delete_sql = f"DELETE FROM messages WHERE conversation_id = '{conversation_id}'"
            self.db_client.query(messages_delete_sql)
            
            # Delete conversation
            conversation_delete_sql = f"DELETE FROM conversations WHERE conversation_id = '{conversation_id}'"
            self.db_client.query(conversation_delete_sql)
            
            logger.info(f"Deleted conversation {conversation_id[:8]}...")
            
        except Exception as e:
            logger.error(f"Error deleting conversation: {e}")
            raise
    
    def update_conversation_title(self, conversation_id: str, new_title: str):
        """
        Update the title of a conversation
        
        Args:
            conversation_id: The conversation ID
            new_title: The new title
        """
        try:
            # Use db_client.get to find and update the conversation
            conversations = self.db_client.get(
                entity=ConvModel,
                where_clause=ConvModel.conversation_id == conversation_id,
                as_df=False
            )
            if conversations:
                conv = conversations[0]
                conv.title = new_title
                conv.updated_at = datetime.now()
                self.db_client.write([conv])
            
            logger.info(f"Updated conversation {conversation_id[:8]}... to '{new_title}'")
            
        except Exception as e:
            logger.error(f"Error updating conversation title: {e}")
            raise


# Global conversation manager instance
_conversation_manager = None

def get_conversation_manager() -> ConversationManager:
    """Get conversation manager with lazy initialization"""
    global _conversation_manager
    if _conversation_manager is None:
        _conversation_manager = ConversationManager()
    return _conversation_manager
