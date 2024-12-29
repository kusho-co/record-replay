# test_utils.py
import logging
import json
import asyncio
from typing import Dict, List, AsyncGenerator
from functools import partial

from .llm_utils import (
    chat_completion_streaming,
    GPT_3_5_16K
)

logger = logging.getLogger(__name__)

TEST_GENERATION_PROMPT = """Generate API test cases for this endpoint based on the provided traffic patterns.
Return each test case one at a time in valid JSON format.

Endpoint: {url}
Method: {http_method}

Complete request
{complete_request}

For each test case, return in this exact JSON format:
{{
    "description": "Meaningful description for the Test case",
    "category": ["functional"|"security"|"performance"|"validation"],
    "priority": "high"|"medium"|"low",
    "request": {{
        "method": "{http_method}",
        "url": "{url}",
        "headers": {{}},
        "path_params": {{}},
        "query_params": {{}},
        "body": {{}}
    }}
}}

Generate realistic test cases based on the sample traffic patterns.
Return one complete test case at a time, ensuring each is valid JSON."""

class TestGenerator:
    def __init__(self):
        self.cache = {}
        logger.info("TestGenerator initialized")

    async def generate_streaming(self, endpoint_data: Dict) -> AsyncGenerator[str, None]:
        """Generate test cases with streaming response"""
        logger.info(f"Starting generation for endpoint: {endpoint_data.get('url')}")
        prompt = self._create_prompt(endpoint_data)
        
        current_chunk = ""
        try:
            # Create a loop and executor for running the streaming function
            loop = asyncio.get_event_loop()
            chat_completion_partial = partial(
                chat_completion_streaming,
                prompt=prompt,
                model=GPT_3_5_16K,
                temperature=0.7
            )
            
            # Run the streaming in the executor
            stream_generator = await loop.run_in_executor(None, chat_completion_partial)
            
            for chunk in stream_generator:
                if chunk == "[DONE]":
                    if current_chunk:
                        try:
                            # Try to parse any remaining chunk
                            json.loads(current_chunk)
                            yield current_chunk
                        except:
                            pass
                    yield "[DONE]"
                    break
                
                current_chunk += chunk
                
                # Try to find complete JSON objects
                try:
                    # Check if we have a complete JSON object
                    json.loads(current_chunk)
                    yield current_chunk
                    current_chunk = ""
                except json.JSONDecodeError:
                    # Keep accumulating chunks until we have valid JSON
                    continue
                
        except Exception as e:
            logger.error(f"Error in generate_streaming: {str(e)}", exc_info=True)
            raise

    def _create_prompt(self, endpoint_data: Dict) -> str:
        """Create prompt from endpoint data"""
        logger.debug("Creating prompt from endpoint data")
        
        prompt = TEST_GENERATION_PROMPT.format(
            url=endpoint_data.get("url", ""),
            http_method=endpoint_data.get("http_method", ""),
            complete_request=endpoint_data
        )
        logger.debug(f"Created prompt: {prompt[:200]}...")  # Log first 200 chars
        return prompt