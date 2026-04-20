from openai import AsyncOpenAI
import os

class ChatService:
    def __init__(self):
        # This will use your OPENAI_API_KEY from Render Environment
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    async def get_chat_response(self, messages: list):
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini", # Use this instead of llama-3.3
                messages=messages,
                temperature=0.1
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Chat Error: {e}")
            raise Exception(f"The brain is having trouble: {e}")
