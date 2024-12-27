import json
from typing import List, Literal, Optional, Tuple
import openai
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random,
)
from collections import OrderedDict
import tiktoken
import logging
import os

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

ORG_ID = os.getenv('OPENAI_ORG_ID', '')
API_KEY = os.getenv('OPENAI_API_KEY', '')

openai.organization = ORG_ID
openai.api_key = API_KEY

MODEL = "text-davinci-003"

GPT_3_5_4K: str = "gpt-3.5-turbo"
GPT_3_5_16K: str = "gpt-3.5-turbo-16k"
GPT_4_8K: str = "gpt-4"

openai_client = openai.Client(
    api_key=API_KEY,
    organization=ORG_ID,
)


MODEL_INFO = OrderedDict(
    [
        (
            GPT_3_5_4K,
            {
                "description": "Currently points to gpt-3.5-turbo-0613.",
                "token_limit": 4096,
                "max_return_token_ratio": 2.0,
                "prompt_token_limit": 3000,
                "up_to_date": "Up to Sep 2021",
                "prompt_pricing": 0.0015 / 1000,
                "response_pricing": 0.0020 / 1000,
            },
        ),
        (
            GPT_3_5_16K,
            {
                "description": "Currently points to gpt-3.5-turbo-0613.",
                "token_limit": 16385,
                "max_return_token_ratio": 1.5,
                "prompt_token_limit": 12000,
                "up_to_date": "Up to Sep 2021",
                "prompt_pricing": 0.0010 / 1000,
                "response_pricing": 0.0020 / 1000,
            },
        ),
        (
            GPT_4_8K,
            {
                "description": "Currently points to gpt-4-0613. See continuous model upgrades.",
                "token_limit": 8192,
                "max_return_token_ratio": 1.8,
                "prompt_token_limit": 6000,
                "up_to_date": "Up to Sep 2021",
                "prompt_pricing": 0.03 / 1000,
                "response_pricing": 0.06 / 1000,
            },
        ),
    ]
)

BIGGEST_MODEL = MODEL_INFO[GPT_3_5_16K]

def get_models():
    return openai_client.models.list()

# @retry(
#     stop=stop_after_attempt(3),
#     wait=wait_random(min=0.5, max=1.5),
# )
# def chat_completion_streaming(
#     prompt: str,
#     model: str = GPT_3_5_4K,
#     max_tokens: int = 1000,
#     temperature: float = 0.5,
# ):
#     messages: List = [
#         {"role": "system", "content": "You are a helpful assistant."},
#         {"role": "user", "content": prompt},
#     ]
#     model, max_tokens = get_model_max_token_from_prompt(
#         prompt=json.dumps(messages),
#         model=model  # type: ignore
#     )
#     print(f"[openai_utils - chat completion streaming] model: {model}, max_tokens: {max_tokens}")
#     response = openai.chat.completions.create(
#         model=model,
#         messages=messages,
#         max_tokens=max_tokens,
#         temperature=temperature,
#         stream=True
#     )
    
#     current_response = ""
#     for chunk in response:
#         data = chunk.model_dump()
#         delta = data["choices"][0]["delta"]
        
#         if "content" in delta and delta["content"]:
#             content = delta["content"]
#             current_response += content
#             logger.info(f"this is content data {content}")
#             yield content
        
#         # Check if we're at the end of the stream
#         if data["choices"][0]["finish_reason"] is not None:
#             yield "[DONE]"
#             break
    
#     calculate_cost(prompt, current_response, model)

@retry(
    stop=stop_after_attempt(3),
    wait=wait_random(min=0.5, max=1.5),
)
def chat_completion_streaming(
    prompt: str,
    model: str = GPT_3_5_4K,
    max_tokens: int = 1000,
    temperature: float = 0.5,
):
    messages: List = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": prompt},
    ]
    model, max_tokens = get_model_max_token_from_prompt(
        prompt=json.dumps(messages),
        model=model  # type: ignore
    )
    print(f"[openai_utils - chat completion streaming] model: {model}, max_tokens: {max_tokens}")
    
    response = openai.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    
    data = response.model_dump()
    # logger.info(f"Complete response data: {json.dumps(data, indent=2)}")
    
    content = data["choices"][0]["message"]["content"]
    
    calculate_cost(prompt, content, model)
    
    yield content
    yield "[DONE]"

def get_model_max_token_from_prompt(
    prompt: str,
    min_response_token_length: Optional[int] = None,
    model: Literal["gpt-3.5-turbo", "gpt-3.5-turbo-16k", "gpt-4"] = GPT_3_5_4K,
) -> Tuple[str, int]:
    token_len = get_tokens_len(prompt=prompt, model=model)
    if int(MODEL_INFO[model]["prompt_token_limit"]) >= token_len and not min_response_token_length:
        return (model, int(MODEL_INFO[model]["token_limit"]) - token_len)
    for model_name, model_info in MODEL_INFO.items():
        token_len = get_tokens_len(prompt=prompt, model=model_name)
        if min_response_token_length:
            if int(model_info["prompt_token_limit"]) >= token_len and (min_response_token_length <= (int(model_info["token_limit"]) - token_len)):
                return (model_name, int(model_info["token_limit"]) - token_len)
        elif int(model_info["prompt_token_limit"]) >= token_len:
            return (model_name, int(model_info["token_limit"]) - token_len)
    return (BIGGEST_MODEL, int(BIGGEST_MODEL["token_limit"]) - token_len)

def get_tokens_len(prompt: str, model: str = GPT_3_5_4K) -> int:
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    buffer = 100  
    return len(encoding.encode(prompt)) + buffer

total = {"cost": 0}

def calculate_cost(prompt, response, model) -> float:
    prompt_tokens = get_tokens_len(prompt, model)
    response_tokens = get_tokens_len(response, model)
    prompt_price = prompt_tokens * float(MODEL_INFO[model]["prompt_pricing"])
    response_price = response_tokens * float(MODEL_INFO[model]["response_pricing"])
    total["cost"] += prompt_price + response_price
    return prompt_price + response_price
