# =============================================================================
# llm_helpers.py
# Reusable LLM communication layer for Anthropic Claude experiments.
#
# USAGE IN ANY NOTEBOOK:
#   import llm_helpers
#   llm_helpers.init(api_key, model_name, max_tokens)
#   from llm_helpers import chat, add_user_message, add_assistant_message, text_from_message
#
# Each notebook calls init() with its own model/token settings.
# The helper functions then work exactly the same regardless of which
# notebook is using them.
#
# CHANGE LOG
# ----------
# 2026-03-06  Added `thinking` parameter to chat().
#             When extended thinking is enabled, the API returns a list of
#             content blocks — a thinking block (type="thinking") followed by
#             a text block (type="text"). text_from_message() already filters
#             by type="text" so it is safe with or without thinking enabled.
# =============================================================================

import time
from anthropic import Anthropic
from anthropic.types import Message

# Exception handling with fallback for older SDK versions
try:
    from anthropic import APITimeoutError, APIConnectionError, RateLimitError
except ImportError:
    APITimeoutError = TimeoutError
    APIConnectionError = ConnectionError
    RateLimitError = Exception

# -----------------------------------------------------------------------------
# Module-level state
# These are set once by init() and then used by all functions below.
# Think of these as the module's "memory" of how it was configured.
# -----------------------------------------------------------------------------
_client = None
_model = None
_max_tokens = None
_initialized = False


def init(api_key, model_name, max_tokens):
    """
    Initialize the LLM helper module.
    Call this once at the top of each notebook before using any other functions.

    Args:
        api_key (str):     Your Anthropic API key (from os.getenv)
        model_name (str):  The Claude model to use (e.g. 'claude-haiku-4-5-20251001')
        max_tokens (int):  Maximum tokens for responses

    Example:
        import llm_helpers
        llm_helpers.init(
            api_key=os.getenv('ANTHROPIC_API_KEY'),
            model_name=os.getenv('MODEL_NAME'),
            max_tokens=int(os.getenv('MAX_TOKENS'))
        )
    """
    global _client, _model, _max_tokens, _initialized

    _client = Anthropic(api_key=api_key)
    _model = model_name
    _max_tokens = max_tokens
    _initialized = True

    print(f"✓ llm_helpers initialized")
    print(f"  Model:      {_model}")
    print(f"  Max tokens: {_max_tokens}")


def _check_initialized():
    """
    Internal guard — raises a clear error if init() was not called first.
    This is a private function (note the underscore prefix), meaning it is
    intended for use only within this module, not by callers.
    """
    if not _initialized:
        raise RuntimeError(
            "llm_helpers not initialized. "
            "Call llm_helpers.init(api_key, model_name, max_tokens) first."
        )


# -----------------------------------------------------------------------------
# Public helper functions
# These are the functions you import and use in your notebooks.
# -----------------------------------------------------------------------------

def add_user_message(messages, message):
    """
    Append a user message to a conversation list.

    Args:
        messages (list): The conversation history list (modified in place)
        message:         A string or a Claude Message object
    """
    user_message = {
        "role": "user",
        "content": message.content if isinstance(message, Message) else message,
    }
    messages.append(user_message)


def add_assistant_message(messages, message):
    """
    Append an assistant message to a conversation list.

    Args:
        messages (list): The conversation history list (modified in place)
        message:         A string or a Claude Message object
    """
    assistant_message = {
        "role": "assistant",
        "content": message.content if isinstance(message, Message) else message,
    }
    messages.append(assistant_message)


def text_from_message(message):
    """
    Extract plain text from a Claude API response.

    Safe to use with or without extended thinking enabled.
    When thinking is enabled, the response contains multiple content blocks
    (a thinking block followed by a text block). Filtering by type="text"
    ensures we always get only the final answer, never the thinking.

    Args:
        message: A Claude Message object

    Returns:
        str: All text blocks joined with newlines
    """
    return "\n".join([block.text for block in message.content if block.type == "text"])


def chat(messages, system=None, temperature=1.0, stop_sequences=None, tools=None, timeout=60, thinking=None):
    """
    Send a message to Claude and return the response.
    Uses the model and max_tokens set during init().

    Args:
        messages (list):        Conversation history
        system (str):           Optional system prompt
        temperature (float):    Sampling temperature (0.0 - 1.0)
                                NOTE: Extended thinking requires temperature=1.0.
                                      The API will raise an error if you pass a
                                      thinking dict with any other temperature.
        stop_sequences (list):  Optional stop sequences. Pass a list of strings
                                to stop generation at. Defaults to None (no stop sequences).
        tools (list):           Optional tool definitions
        timeout (int):          Request timeout in seconds
        thinking (dict):        Optional extended thinking config.
                                Pass {"type": "enabled", "budget_tokens": N}
                                to activate Claude's chain-of-thought reasoning.
                                The thinking block will appear in response.content
                                alongside the text block — use text_from_message()
                                to get just the answer, or inspect response.content
                                directly to extract the thinking text.

    Returns:
        Message: The Claude API response object

    Examples:
        # Standard call (no thinking)
        messages = []
        add_user_message(messages, "How many cards are in Clue?")
        response = chat(messages, system=my_system_prompt, temperature=0.3)
        print(text_from_message(response))

        # With extended thinking (temperature must be 1.0)
        response = chat(
            messages,
            system=my_system_prompt,
            temperature=1.0,
            thinking={"type": "enabled", "budget_tokens": 1000}
        )
        # Get just the answer
        print(text_from_message(response))
        # Get just the thinking
        for block in response.content:
            if block.type == "thinking":
                print(block.thinking)
    """
    _check_initialized()

    params = {
        "model": _model,
        "max_tokens": _max_tokens,
        "messages": messages,
        "temperature": temperature,
        "timeout": timeout
    }

    # Only add optional parameters if they were provided.
    # This keeps API calls clean — no null/empty fields sent unnecessarily.

    if stop_sequences is not None:
        params["stop_sequences"] = stop_sequences

    if tools:
        params["tools"] = tools

    # Pass thinking config to the API when provided.
    # WHY: The Anthropic API activates extended thinking only when this key
    # is present. Without it, even temperature=1.0 calls behave normally.
    # The thinking block that comes back is separate from the text block —
    # text_from_message() filters it out automatically.
    if thinking:
        params["thinking"] = thinking

    if system:
        # Structured as a list with cache_control for prompt caching.
        # The system prompt is cached after the first call, saving ~90% on
        # system prompt tokens for all subsequent calls in the same session.
        params["system"] = [
            {
                "type": "text",
                "text": system,
                "cache_control": {"type": "ephemeral"}
            }
        ]

    return _client.messages.create(**params)
