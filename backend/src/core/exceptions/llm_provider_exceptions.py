"""Domain exceptions for LLM Provider interactions."""


class LLMProviderError(Exception):
    """Base exception for all LLM generation failures."""

    def __init__(self, message: str = "An error occurred during LLM generation."):
        self.message = message
        super().__init__(self.message)


class LLMConnectionError(LLMProviderError):
    """Raised when the provider is unreachable (e.g., local Ollama engine is down)."""

    def __init__(self, provider_name: str, endpoint: str):
        super().__init__(f"Failed to connect to {provider_name} at {endpoint}.")
        self.provider_name = provider_name
        self.endpoint = endpoint


class LLMAuthenticationError(LLMProviderError):
    """Raised when cloud API keys are invalid or missing."""

    def __init__(self, provider_name: str):
        super().__init__(
            f"Authentication failed for provider: {provider_name}. Check API keys."
        )


class LLMContextLimitExceededError(LLMProviderError):
    """Raised when the conversation history and retrieved documents exceed the model's token limit."""

    def __init__(
        self,
        message: str = "Context limit exceeded. The prompt is too large for this model.",
    ):
        super().__init__(message)


class LLMRateLimitError(LLMProviderError):
    """Raised when a cloud provider throttles the application."""

    def __init__(
        self,
        message: str = "Rate limit exceeded. Please wait a moment before trying again.",
    ):
        super().__init__(message)


class LocalModelNotFoundError(LLMProviderError):
    def __init__(self, model_name: str):
        super().__init__(
            f"Model '{model_name}' is not downloaded. Run `ollama run {model_name}` first."
        )
