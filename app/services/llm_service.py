import ollama

from app.config.settings import OLLAMA_MODEL


class LLMService:

    def generate(self, prompt):

        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        return response["message"]["content"]