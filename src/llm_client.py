import os
import json
import logging
import base64
from pathlib import Path
from typing import Optional

import httpx
from PIL import Image
from image_handler import ImageHandler


class LLMClient:
    def __init__(self, model_name: Optional[str] = None, hf_token: Optional[str] = None, backend: str = "auto"):
        self.model_name = model_name or os.getenv("MODEL_NAME")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.google_api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.google_api_base = os.getenv("GOOGLE_API_BASE", "https://generativelanguage.googleapis.com/v1beta")
        self.google_model = self.model_name or os.getenv("GOOGLE_MODEL")
        self.hf_token = hf_token or os.getenv("HUGGINGFACE_API_TOKEN")
        self.backend_preference = backend
        self.backend = None
        self.client = None
        self._setup_backend()

    def _setup_backend(self):
        if self.backend_preference in {"google", "auto"} and self.google_api_key:
            try:
                import requests
            except ImportError as exc:
                raise ImportError("requests package is required for Google Gemini backend") from exc

            self.backend = "google"
            self.client = requests
            if not self.google_model:
                self.google_model = "gemini-flash-latest"
            logging.info("Using Google Gemini backend with model %s", self.google_model)
            return

        if self.backend_preference in {"openai", "auto"} and self.openai_api_key:
            try:
                import openai
            except ImportError as exc:
                raise ImportError("openai package is required for OPENAI_API_KEY usage") from exc

            verify_setting = os.getenv("OPENAI_VERIFY_SSL", "true").strip().lower()
            if verify_setting in {"0", "false", "no"}:
                verify = False
            else:
                verify = os.getenv("OPENAI_CA_BUNDLE") or True

            trust_env_setting = os.getenv("OPENAI_TRUST_ENV", "true").strip().lower()
            trust_env = trust_env_setting not in {"0", "false", "no"}

            proxy_url = os.getenv("OPENAI_PROXY_URL")
            proxy = proxy_url if proxy_url else None

            self.openai_module = openai
            self.openai_verify = verify
            self.openai_trust_env = trust_env
            self.openai_proxy = proxy
            self.openai_allow_insecure_fallback = verify_setting not in {"0", "false", "no"}

            http_client = httpx.Client(verify=verify, trust_env=trust_env, proxy=proxy)
            self.backend = "openai"
            self.client = openai.OpenAI(api_key=self.openai_api_key, http_client=http_client)
            logging.info(
                "Using OpenAI-compatible backend (trust_env=%s, proxy=%s, verify=%s)",
                trust_env,
                bool(proxy_url),
                verify is not False,
            )
            return

        if self.backend_preference in {"transformers", "auto"} and self.model_name:
            try:
                import torch
                from transformers import AutoModelForCausalLM, AutoTokenizer, TextGenerationPipeline
            except ImportError as exc:
                raise ImportError("transformers and torch packages are required for local model usage") from exc

            tokenizer = AutoTokenizer.from_pretrained(self.model_name, use_fast=True, use_auth_token=self.hf_token)
            model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                use_auth_token=self.hf_token,
                device_map="auto",
                torch_dtype="auto",
            )
            device = 0 if torch.cuda.is_available() else -1
            self.client = TextGenerationPipeline(model=model, tokenizer=tokenizer, device=device)
            self.backend = "transformers"
            logging.info("Using Transformers backend with model %s", self.model_name)
            return

        raise RuntimeError(
            "No LLM backend configured. Set GOOGLE_API_KEY, OPENAI_API_KEY, or MODEL_NAME with HUGGINGFACE_API_TOKEN."
        )

    def _should_openai_retry(self, exc):
        if self.backend != "openai" or not self.openai_allow_insecure_fallback or self.openai_verify is False:
            return False

        connection_error_types = (self.openai_module.APIConnectionError, httpx.ConnectError, httpx.TransportError)
        return isinstance(exc, connection_error_types)

    def _should_openai_proxy_fallback(self, exc):
        if self.backend != "openai" or not self.openai_trust_env:
            return False

        proxy_error_types = (self.openai_module.APIConnectionError, httpx.ProxyError)
        if not isinstance(exc, proxy_error_types):
            return False

        message = str(exc).lower()
        return "proxy" in message or "proxyerror" in message or "503" in message

    def _rebuild_openai_client(self, verify, trust_env=None, proxy=None):
        if trust_env is None:
            trust_env = self.openai_trust_env
        if proxy is None:
            proxy = self.openai_proxy
        http_client = httpx.Client(verify=verify, trust_env=trust_env, proxy=proxy)
        self.client = self.openai_module.OpenAI(api_key=self.openai_api_key, http_client=http_client)
        self.openai_verify = verify
        self.openai_trust_env = trust_env
        self.openai_proxy = proxy
        if verify is False:
            logging.warning("OpenAI client rebuilt with SSL verification disabled")
        if trust_env is False:
            logging.warning("OpenAI client rebuilt without trusting environment proxies")

    def _run_openai_request(self, request_func):
        try:
            return request_func()
        except Exception as exc:
            if self._should_openai_proxy_fallback(exc):
                logging.warning("OpenAI request failed via proxy, retrying once without environment proxy settings: %s", exc)
                self._rebuild_openai_client(self.openai_verify, trust_env=False, proxy=None)
                return request_func()
            if self._should_openai_retry(exc):
                logging.warning("OpenAI request failed, retrying once with SSL verification disabled: %s", exc)
                self._rebuild_openai_client(False)
                return request_func()
            raise

    def _flatten_google_content(self, content):
        if content is None:
            return ""
        if isinstance(content, str):
            return content
        if isinstance(content, dict):
            if "text" in content and isinstance(content["text"], str):
                return content["text"]
            if "contents" in content:
                return self._flatten_google_content(content["contents"])
            if "content" in content:
                return self._flatten_google_content(content["content"])
            if "parts" in content:
                return self._flatten_google_content(content["parts"])
            return "".join(self._flatten_google_content(v) for v in content.values())
        if isinstance(content, list):
            return "".join(self._flatten_google_content(item) for item in content)
        return str(content)

    def _parse_google_response(self, data):
        candidates = data.get("candidates") or []
        if not candidates:
            raise RuntimeError(f"No candidates returned from Google Gemini API: {json.dumps(data)[:400]}")

        first = candidates[0]
        content = first.get("content")
        if content is None:
            content = first.get("message", {}).get("content")
        if content is None:
            # Some responses may include `candidate[0].output[0].content` or other nested structures.
            content = first.get("output") or first.get("message")
        if content is None:
            raise RuntimeError(f"No content returned from Google Gemini API: {json.dumps(first)[:400]}")

        result = self._flatten_google_content(content).strip()
        if not result:
            raise RuntimeError(f"Unsupported Google Gemini content format: {json.dumps(content)[:400]}")
        return result

    def generate(self, prompt: str, max_tokens: int = 512) -> str:
        if self.backend == "google":
            # Use Generative Language API for all Google models
            url = f"{self.google_api_base}/models/{self.google_model}:generateContent"
            headers = {
                "Content-Type": "application/json",
                "X-goog-api-key": self.google_api_key,
            }
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt}
                        ]
                    }
                ]
            }
            response = self.client.post(url, headers=headers, json=payload, timeout=300)
            response.raise_for_status()
            data = response.json()
            return self._parse_google_response(data)

        if self.backend == "openai":
            response = self._run_openai_request(lambda: self.client.chat.completions.create(
                model=self.model_name or "gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0.6,
            ))
            return response.choices[0].message.content.strip()

        if self.backend == "transformers":
            output = self.client(prompt, max_new_tokens=max_tokens, do_sample=False)
            if isinstance(output, list) and output:
                return output[0]["generated_text"].strip()
            raise RuntimeError("Unexpected response from transformers pipeline")

        raise RuntimeError("No LLM backend is available")

    def generate_with_images(self, prompt: str, images: list, max_tokens: int = 1024) -> str:
        """Generate response with images for vision-capable models."""
        if self.backend == "google":
            return self._generate_with_images_google(prompt, images, max_tokens)
        elif self.backend == "openai":
            return self._generate_with_images_openai(prompt, images, max_tokens)
        else:
            # Fallback: transformers backend doesn't support vision; use text-only
            logging.warning("Vision mode not supported for %s backend; falling back to text-only", self.backend)
            return self.generate(prompt, max_tokens)

    def _generate_with_images_google(self, prompt: str, images: list, max_tokens: int) -> str:
        """Generate with Google Gemini Vision API."""
        url = f"{self.google_api_base}/models/{self.google_model}:generateContent"
        headers = {
            "Content-Type": "application/json",
            "X-goog-api-key": self.google_api_key,
        }
        
        # Build parts: first add images, then the text prompt
        parts = []
        
        # Add images as inline_data
        for img in images:
            base64_data = ImageHandler.encode_image_for_google(img)
            parts.append({
                "inline_data": {
                    "mime_type": "image/jpeg",
                    "data": base64_data
                }
            })
        
        # Add the text prompt
        parts.append({"text": prompt})
        
        payload = {
            "contents": [{"parts": parts}]
        }
        
        response = self.client.post(url, headers=headers, json=payload, timeout=300)
        response.raise_for_status()
        data = response.json()
        return self._parse_google_response(data)

    def _generate_with_images_openai(self, prompt: str, images: list, max_tokens: int) -> str:
        """Generate with OpenAI Vision API."""
        # Build content array with images and text
        content = []
        
        # Add images
        for img in images:
            base64_data = ImageHandler.encode_image_for_openai(img)
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_data}",
                    "detail": "high"
                }
            })
        
        # Add text prompt
        content.append({
            "type": "text",
            "text": prompt
        })
        
        response = self._run_openai_request(lambda: self.client.chat.completions.create(
            model=self.model_name or "gpt-4-vision-preview",
            messages=[{"role": "user", "content": content}],
            max_tokens=max_tokens,
            temperature=0.6,
        ))
        return response.choices[0].message.content.strip()
