"""
TravelPilot LLM Service
Integrates with Google Gemini via the official google-genai SDK.
Loads credentials securely from environment variables
and returns structured JSON.
"""

import json
import logging
import os
import re
from typing import Any, Dict, Optional

from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

logger = logging.getLogger(__name__)


class LLMService:
    """
    Encapsulates Gemini API communication with
    structured JSON extraction and error resilience.
    """

    def __init__(self, api_key: Optional[str] = None):
        # Never hardcode API keys.
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self._client = None

    @property
    def client(self):
        """Create and cache the Gemini client."""

        if self._client is None and self.is_configured():
            try:
                from google import genai

                self._client = genai.Client(
                    api_key=self.api_key
                )

            except Exception as e:
                logger.warning(
                    "Failed to initialize genai.Client: %s",
                    e,
                )

                self._client = None

        return self._client

    def is_configured(self) -> bool:
        """
        Returns True if a valid Gemini API key
        is present in the environment.
        """

        if not self.api_key:
            return False

        cleaned = self.api_key.strip()

        return bool(
            cleaned
            and cleaned != "your_gemini_api_key_here"
            and len(cleaned) > 10
        )

    def generate_json(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        model: str = "gemini-3.8-flash",
        temperature: float = 0.2,
    ) -> Dict[str, Any]:
        """
        Sends a prompt to Gemini requesting structured JSON.

        Returns:
            {
                "success": bool,
                "data": parsed JSON or None,
                "error": error message or None,
                "source": "gemini" or "unavailable"
            }
        """

        if not self.is_configured():
            return {
                "success": False,
                "data": None,
                "error": (
                    "GEMINI_API_KEY is not configured "
                    "in environment."
                ),
                "source": "unavailable",
            }

        try:
            from google.genai import types

            client = self.client

            if not client:
                return {
                    "success": False,
                    "data": None,
                    "error": "Failed to create Gemini client.",
                    "source": "unavailable",
                }

            config_args = {
                "response_mime_type": "application/json",
                "temperature": temperature,
            }

            if system_instruction:
                config_args["system_instruction"] = (
                    system_instruction
                )

            config = types.GenerateContentConfig(
                **config_args
            )

            # Only use the currently selected stable model.
            candidate_models = [model]

            last_error = None

            for candidate_model in candidate_models:
                try:
                    logger.info(
                        "Calling Gemini model: %s",
                        candidate_model,
                    )

                    response = client.models.generate_content(
                        model=candidate_model,
                        contents=prompt,
                        config=config,
                    )

                    raw_text = response.text or ""

                    # First try direct JSON parsing.
                    try:
                        parsed_data = json.loads(raw_text)

                        return {
                            "success": True,
                            "data": parsed_data,
                            "error": None,
                            "source": (
                                f"gemini ({candidate_model})"
                            ),
                        }

                    except json.JSONDecodeError:
                        # Fallback: extract JSON object or array.
                        match = re.search(
                            r"\{.*\}|\[.*\]",
                            raw_text,
                            re.DOTALL,
                        )

                        if match:
                            parsed_data = json.loads(
                                match.group(0)
                            )

                            return {
                                "success": True,
                                "data": parsed_data,
                                "error": None,
                                "source": (
                                    f"gemini ({candidate_model})"
                                ),
                            }

                        raise

                except Exception as model_err:
                    last_error = model_err

                    logger.warning(
                        "Model %s failed: %s",
                        candidate_model,
                        model_err,
                    )

            if last_error:
                raise last_error

            raise RuntimeError(
                "No Gemini model was available."
            )

        except Exception as e:
            logger.error(
                "Gemini API call failed: %s",
                e,
            )

            return {
                "success": False,
                "data": None,
                "error": str(e),
                "source": "gemini_error",
            }


# Default global instance
default_llm_service = LLMService()