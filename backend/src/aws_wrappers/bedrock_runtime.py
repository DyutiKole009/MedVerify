"""
Amazon Bedrock Runtime wrapper for text generation, multimodal vision OCR, and structured JSON inference.
"""
import json
import base64
import re
from typing import Dict, Any, Optional, List, Union
from src.aws_wrappers.base import BaseAWSWrapper, catch_aws_errors
from src.aws_wrappers.client_factory import get_boto_client
from src.utils.exceptions import ModelInferenceException
from src.utils.logger import logger

class BedrockRuntimeWrapper(BaseAWSWrapper):
    """
    Encapsulates Amazon Bedrock Runtime model invocations.
    Supports both Anthropic Claude models and Amazon Nova models, with automatic JSON sanitization.
    """
    def __init__(self):
        super().__init__("BedrockRuntime")
        self.client = get_boto_client("bedrock-runtime")

    def _clean_json_markdown(self, raw_text: str) -> str:
        """Strips markdown code blocks like ```json ... ``` from model outputs."""
        text = raw_text.strip()
        # Remove ```json ... ``` or ``` ... ```
        pattern = r"^```(?:json)?\s*([\s\S]*?)\s*```$"
        match = re.match(pattern, text)
        if match:
            return match.group(1).strip()
        return text

    @catch_aws_errors("InvokeModel")
    def invoke_model(
        self,
        model_id: str,
        body: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Raw invoke_model call on Bedrock."""
        response = self.client.invoke_model(
            modelId=model_id,
            body=json.dumps(body),
            contentType="application/json",
            accept="application/json"
        )
        return json.loads(response["body"].read().decode("utf-8"))

    @catch_aws_errors("Converse")
    def converse(
        self,
        model_id: str,
        messages: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.0
    ) -> str:
        """
        Calls Bedrock Converse API - a unified interface across Claude, Nova, Llama, and Mistral.
        """
        kwargs: Dict[str, Any] = {
            "modelId": model_id,
            "messages": messages,
            "inferenceConfig": {
                "maxTokens": max_tokens,
                "temperature": temperature
            }
        }
        if system_prompt:
            kwargs["system"] = [{"text": system_prompt}]

        response = self.client.converse(**kwargs)
        output_message = response.get("output", {}).get("message", {})
        content = output_message.get("content", [])
        if content and "text" in content[0]:
            return content[0]["text"]
        return ""

    def invoke_structured_json(
        self,
        model_id: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.0
    ) -> Dict[str, Any]:
        """
        Sends a prompt and guarantees a validated JSON dictionary response.
        Automatically removes markdown formatting and parses JSON.
        """
        # Formulate user message
        messages = [{
            "role": "user",
            "content": [{"text": prompt}]
        }]

        raw_output = self.converse(
            model_id=model_id,
            messages=messages,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature
        )

        cleaned_text = self._clean_json_markdown(raw_output)
        try:
            return json.loads(cleaned_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse model JSON output: {raw_output}")
            raise ModelInferenceException(
                "BedrockRuntime",
                f"Model response was not valid JSON: {str(e)}",
                e
            ) from e

    def extract_from_image(
        self,
        model_id: str,
        image_bytes: bytes,
        mime_type: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 2048
    ) -> Dict[str, Any]:
        """
        Multimodal vision analysis: passes packaging image bytes directly to Bedrock
        to extract structured medicine fields (batch_no, drug_name, expiry, etc.).
        """
        # Determine image format for Converse API
        # Supported formats in Converse: 'png' | 'jpeg' | 'gif' | 'webp'
        fmt = "jpeg"
        if "png" in mime_type.lower():
            fmt = "png"
        elif "webp" in mime_type.lower():
            fmt = "webp"
        elif "gif" in mime_type.lower():
            fmt = "gif"

        messages = [{
            "role": "user",
            "content": [
                {
                    "image": {
                        "format": fmt,
                        "source": {
                            "bytes": image_bytes
                        }
                    }
                },
                {
                    "text": prompt
                }
            ]
        }]

        raw_output = self.converse(
            model_id=model_id,
            messages=messages,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=0.0
        )

        cleaned_text = self._clean_json_markdown(raw_output)
        try:
            return json.loads(cleaned_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse vision model JSON output: {raw_output}")
            raise ModelInferenceException(
                "BedrockRuntime",
                f"Vision extraction response was not valid JSON: {str(e)}",
                e
            ) from e
