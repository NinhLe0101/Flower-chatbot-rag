import openai
import os
import time
from dotenv import load_dotenv

load_dotenv()

class OpenAIClient:
    def __init__(self, model):
        openai.api_key = os.getenv("OPEN_AI_KEY")
        self.model = model
    
    def chat(self, messages, max_retries=3):
        retries = 0
        while retries < max_retries:
            try:
                response = openai.ChatCompletion.create(
                    # model="gpt-3.5-turbo",
                    model = self.model,
                    messages=messages,
                    # max_tokens=2048,
                    # messages=messages[-2:],  # Chỉ gửi 3 tin nhắn gần nhất để giảm tải
                    # temperature=1
                )
                return response
            except openai.error.APIConnectionError as e:
                print(f"Connection error: {e}. Retrying in 2 seconds...")
                retries += 1
                time.sleep(2)  # Chờ 2 giây trước khi thử lại
            except Exception as e:
                print(f"An error occurred: {e}")
                break
        return None