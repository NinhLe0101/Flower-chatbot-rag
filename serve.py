import time
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import os
import tiktoken
from flask_cors import CORS
from rag.core import RAG
from openai_client import OpenAIClient
from semantic_router import SemanticRouter, Route
from semantic_router.samples import questions_product, chitchatSample
from semantic_cache.core import SemanticCache
from reflection import Reflection
from embeddings.core import Embedding
import pymongo

# Load environment variables from .env file
load_dotenv()

# Initialize database and API configurations
MONGODB_URI = os.getenv('MONGODB_URI')
DB_NAME = os.getenv('DB_NAME')
COLLECTION_FLOWER_DATA = os.getenv('DB_COLLECTION_DATA')
COLLECTION_VECTORSEARCH = os.getenv('DB_COLLECTION_VECTORSEARCH')
COLLECTION_SEMANTIC_CACHE = os.getenv('DB_COLLECTION_CACHE')
COLLECTION_CHAT_HISTORY = os.getenv('DB_COLLECTION_CHAT_HISTORY')

# Initialize MongoDB client and select database
mongoClient = pymongo.MongoClient(MONGODB_URI)
mongoFlowerDB = mongoClient[DB_NAME]

# Set up Flask and CORS
app = Flask(__name__)
CORS(app)

# Initialize embeddings, LLM, and other components
embeddings = Embedding()
llm = OpenAIClient(model='gpt-3.5-turbo')
# llm = OpenAIClient(model='gpt-4')
semantic_cache = SemanticCache(mongoFlowerDB, COLLECTION_SEMANTIC_CACHE)
reflection = Reflection(mongoFlowerDB, COLLECTION_CHAT_HISTORY, semantic_cache, embeddings, llm)
rag = RAG(mongoFlowerDB, COLLECTION_FLOWER_DATA, COLLECTION_VECTORSEARCH)

# Define routes and setup for SemanticRouter
PRODUCT_ROUTE_NAME = 'products'
CHITCHAT_ROUTE_NAME = 'chitchat'
productRoute = Route(name=PRODUCT_ROUTE_NAME, samples=questions_product)
chitchatRoute = Route(name=CHITCHAT_ROUTE_NAME, samples=chitchatSample)
semanticRouter = SemanticRouter(routes=[productRoute, chitchatRoute])

# def truncate_chat_history(chat_history, max_tokens=16000):
#     encoding = tiktoken.encoding_for_model('gpt-4')
#     current_tokens = 0
#     truncated_history = []
#     for message in reversed(chat_history):  # Process from the latest message backward
#         message_tokens = len(encoding.encode(message["content"]))
#         if current_tokens + message_tokens <= max_tokens:
#             truncated_history.insert(0, message)
#             current_tokens += message_tokens
#         else:
#             break
#     return truncated_history

def log_token_usage(prompt, model_name='gpt-4'):
    encoding = tiktoken.encoding_for_model(model_name)
    token_count = len(encoding.encode(prompt))
    print(f"Token Count: {token_count}")
    return token_count


# def truncate_text(text, max_tokens=16000):
#     encoding = tiktoken.encoding_for_model('gpt-4')  # Replace with the appropriate model
#     tokens = encoding.encode(text)
#     if len(tokens) > max_tokens:
#         truncated_tokens = tokens[:max_tokens]
#         return encoding.decode(truncated_tokens)
#     return text

# @app.route('/api/chat', methods=['POST'])
# def chat():
#     start_time = time.time()  # Start total response timer

#     # Get JSON data from the request
#     data = request.get_json()
#     session_id = data.get('sessionID', '')
#     query = data.get('query', '')

#     guided_route = semanticRouter.guide(query)[1]
#     print(f"Semantic Route: {guided_route}")

#     try:
#         if guided_route == PRODUCT_ROUTE_NAME:
#             query_embedding = embeddings.get_embedding(query)
            
#             # Cache Search Timing
#             cache_start_time = time.time()
#             cached_result = semantic_cache.search_in_cache(query_embedding)
#             cache_end_time = time.time()
#             print(f"Cache Search Time: {cache_end_time - cache_start_time:.4f} seconds")

#             if cached_result:
#                 print(f'Cache hit: {cached_result}')
#                 response = cached_result
#             else:
#                 # RAG Enhancement Timing
#                 rag_start_time = time.time()
#                 enhanced_prompt = rag.enhance_prompt(query, query_embedding)
#                 rag_end_time = time.time()
#                 print(f"RAG Enhancement Time: {rag_end_time - rag_start_time:.4f} seconds")
                
#                 combined_information = f"Hãy giúp tôi trả lời câu hỏi '{query}' của khách hàng bằng cách sử dụng các thông tin sau:\n{enhanced_prompt.replace('<br>', '\n')}"
#                 combined_information = truncate_text(combined_information, max_tokens=16000 - 2000)  # Truncate input to fit model limit
                
#                 # Log token usage
#                 log_token_usage(combined_information)

#                 # Reflection Chat Timing
#                 reflection_start_time = time.time()
#                 response = reflection.chat(
#                     session_id=session_id,
#                     enhanced_message=combined_information,
#                     original_message=query,
#                     cache_response=True
#                 )
#                 reflection_end_time = time.time()
#                 print(f"Reflection Chat Time: {reflection_end_time - reflection_start_time:.4f} seconds")
#         else:
#             # Casual Chat Timing
#             reflection_start_time = time.time()
#             response = reflection.chat(
#                 session_id=session_id,
#                 enhanced_message=query,
#                 original_message=query,
#                 cache_response=False
#             )
#             reflection_end_time = time.time()
#             print(f"Reflection Chat Time (Casual): {reflection_end_time - reflection_start_time:.4f} seconds")

#     except Exception as e:
#         print(f"Error during processing: {str(e)}")
#         response = "Xin lỗi, tôi không thể xử lý yêu cầu này do lỗi kỹ thuật."

#     end_time = time.time()  # End total response timer
#     print(f"Total API Response Time: {end_time - start_time:.4f} seconds")

#     return jsonify({
#         "role": "assistant",
#         "content": response,
#         "content_type": "text/markdown"
#     })



@app.route('/api/chat', methods=['POST'])
def chat():
    start_time = time.time()  # Start total response timer
    
    # Get JSON data from the request
    data = request.get_json()
    session_id = data.get('sessionID', '')
    query = data.get('query', '')

    guided_route = semanticRouter.guide(query)[1]
    print(f"Semantic Route: {guided_route}")

    if guided_route == PRODUCT_ROUTE_NAME:
        query_embedding = embeddings.get_embedding(query)
        
        # Cache Search Timing
        cache_start_time = time.time()
        cached_result = semantic_cache.search_in_cache(query_embedding)
        cache_end_time = time.time()
        print(f"Cache Search Time: {cache_end_time - cache_start_time:.4f} seconds")

        if cached_result:
            print(f'Cache hit: {cached_result}')
            response = cached_result
        else:
            # RAG Enhancement Timing
            rag_start_time = time.time()
            enhanced_prompt = rag.enhance_prompt(query, query_embedding)
            rag_end_time = time.time()
            print(f"RAG Enhancement Time: {rag_end_time - rag_start_time:.4f} seconds")
            
            combined_information = f"Hãy giúp tôi trả lời câu hỏi '{query}' của khách hàng bằng cách sử dụng các thông tin sau:\n{enhanced_prompt.replace('<br>', '\n')}"
            # combined_information = f"Hãy trở thành chuyên gia tư vấn bán hàng cho một cửa hàng điện thoại. Câu hỏi của khách hàng: {query}\nTrả lời câu hỏi dựa vào các thông tin sản phẩm dưới đây: {enhanced_prompt}."
            # Log token usage
            log_token_usage(combined_information)
            # Reflection Chat Timing
            reflection_start_time = time.time()
            response = reflection.chat(
                session_id=session_id,
                enhanced_message=combined_information,
                original_message=query,
                cache_response=True
            )
            reflection_end_time = time.time()
            print(f"Reflection Chat Time: {reflection_end_time - reflection_start_time:.4f} seconds")
    else:
        # Casual Chat Timing
        reflection_start_time = time.time()
        response = reflection.chat(
            session_id=session_id,
            enhanced_message=query,
            original_message=query,
            cache_response=False
        )
        reflection_end_time = time.time()
        print(f"Reflection Chat Time (Casual): {reflection_end_time - reflection_start_time:.4f} seconds")

    end_time = time.time()  # End total response timer
    print(f"Total API Response Time: {end_time - start_time:.4f} seconds")

    return jsonify({
        "role": "assistant",
        "content": response,
        "content_type": "text/markdown"
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
