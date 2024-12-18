import pymongo
from datetime import datetime
from semantic_cache.core import SemanticCache
from embeddings.core import Embedding


ROLE_MAPPING = {
    "human": "user",
    "ai": "assistant"
}

class Reflection:
    def __init__(self, 
                 flowerDb, 
                 dbChatHistoryCollection: str, 
                 semanticCache: SemanticCache, 
                 embeddings: Embedding, 
                 llm):
        self.collection_chat_history = flowerDb[dbChatHistoryCollection]
        self.semantic_cache = semanticCache
        self.embeddings = embeddings
        self.llm = llm

    def chat(self, session_id: str, enhanced_message: str, original_message: str = '', cache_response: bool = False):
        """
        Handles the chat process by checking the cache for a response, building the message history, 
        and getting a response from the language model if necessary.

        Args:
            session_id (str): The unique identifier for the chat session.
            enhanced_message (str): The processed message sent by the user.
            original_message (str, optional): The original user message before any enhancement (default is '').
            cache_response (bool, optional): Whether to store the response in the cache (default is False).

        Returns:
            str or None: The response from the language model, or None if an error occurs.
        """
        # Generate embedding for the enhanced message and check cache for a pre-existing response
        query_embedding = self.embeddings.get_embedding(enhanced_message)

        # Build message history and send to language model
        messages = self._build_messages(session_id, enhanced_message)

        response = self.llm.chat(messages)

        # If a response is received, record messages and optionally cache the response
        if response and response.choices:
            self._record_message(session_id, "human", original_message, enhanced_message)
            self._record_message(session_id, "ai", response.choices[0].message.content)
            if cache_response:
                self.semantic_cache.add_to_cache(query_embedding, response.choices[0].message.content)
            return response.choices[0].message.content
        else:
            print("Error: No response from LLM")
            return None


    def _build_messages(self, session_id: str, enhanced_message: str):
        """
        Constructs a message history to provide context to the language model based on previous messages in the session.

        Args:
            session_id (str): The unique identifier for the chat session.
            enhanced_message (str): The enhanced message from the user to add to the conversation.

        Returns:
            list: A list of message dictionaries formatted for the language model, including system, user, and assistant messages.
        """
        # Define the system prompt with guidance for the chatbot's behavior
        system_prompt_content = '''
        As a chatbot for a flower shop, helping customers choose bouquets and services from the store in a friendly and approachable manner. Your role is to assist customers with products, flower types, promotional prices, and services, but do so as a sincere advisor, not as a salesperson.
**Important Notes**:  
1. Provide specific sale prices/promotional prices and images for each product.  
2. Respond quickly and accurately, formatting replies in a clear and visually appealing way.  
3. Keep the conversation enjoyable and friendly.  '''
        
        messages = [{"role": "system", "content": system_prompt_content}]
        
        # Retrieve and add recent messages from chat history for context, in reverse order for chronological display
        session_messages = self.collection_chat_history.find({"sessionID": session_id}).sort("history.data.timestamp", pymongo.DESCENDING).limit(1)
        for message in reversed(list(session_messages)):
            role = ROLE_MAPPING.get(message['history']['type'], "user")
            messages.append({"role": role, "content": message['history']['data']['content']})
        
        # Add the latest user message to the message history
        messages.append({"role": "user", "content": enhanced_message})
        return messages
    
    def _record_message(self, session_id: str, message_type: str, content: str, enhanced_content: str = None):
        """
        Records a message in the chat history collection, storing both original and enhanced messages if provided.

        Args:
            session_id (str): The unique identifier for the chat session.
            message_type (str): The type of message (e.g., 'human' or 'ai').
            content (str): The message content to store.
            enhanced_content (str, optional): The enhanced content of the message, if applicable.

        Returns:
            None
        """
        # Insert a document into chat history with session details, type, content, and timestamp
        self.collection_chat_history.insert_one({
            "sessionID": session_id,
            "history": {
                "type": message_type,
                "data": {
                    "content": content,
                    "enhanced_content": enhanced_content,
                    "timestamp": datetime.now()
                }
            }
        })

