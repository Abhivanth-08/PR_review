"""
Custom OpenRouter LLM Wrapper for LangChain
"""
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from typing import Any, List, Optional
import requests
import json


class OpenRouterChat(BaseChatModel):
    """OpenRouter Chat Model wrapper for LangChain"""

    api_key: str
    model: str = "openai/gpt-4o-mini"
    temperature: float = 0.7
    max_tokens: int = 2048
    base_url: str = "https://openrouter.ai/api/v1/chat/completions"

    @property
    def _llm_type(self) -> str:
        return "openrouter-chat"

    def _generate(
            self,
            messages: List[BaseMessage],
            stop: Optional[List[str]] = None,
            **kwargs: Any,
    ) -> ChatResult:
        """Generate chat completion"""

        # Convert LangChain messages to OpenRouter format
        formatted_messages = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                formatted_messages.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                formatted_messages.append({"role": "assistant", "content": msg.content})
            elif isinstance(msg, SystemMessage):
                formatted_messages.append({"role": "system", "content": msg.content})

        # Make API request
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": formatted_messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }

        if stop:
            payload["stop"] = stop

        response = requests.post(
            self.base_url,
            headers=headers,
            json=payload,
            timeout=60
        )

        if response.status_code != 200:
            raise Exception(f"OpenRouter API error: {response.status_code} - {response.text}")

        result = response.json()
        content = result["choices"][0]["message"]["content"]

        # Create ChatGeneration
        generation = ChatGeneration(message=AIMessage(content=content))

        return ChatResult(generations=[generation])

    @property
    def _identifying_params(self) -> dict:
        """Return identifying parameters"""
        return {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }