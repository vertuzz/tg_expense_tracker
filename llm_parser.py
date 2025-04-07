import json
import base64
import httpx
import logging

from config import OPENROUTER_API_KEY, OPENROUTER_API_URL, LLM_MODEL, YOUR_SITE_URL, YOUR_SITE_NAME
from models import Expense

logger = logging.getLogger(__name__)

async def parse_expense_data(text: str, user_id: int) -> Expense | None:
    """Parses expense data from text using an LLM."""
    if not OPENROUTER_API_KEY or OPENROUTER_API_KEY == "YOUR_OPENROUTER_API_KEY":
        logger.error("OpenRouter API Key not configured.")
        return None

    prompt = f"""
    Analyze the following text which represents an expense entry. Extract the numerical amount, a single category word, and an optional brief description.
    Return the result ONLY as a JSON object with the keys "amount", "category", and "description".
    - "amount" should be a number (float or integer).
    - "category" should be a single, relevant noun or short phrase (e.g., 'food', 'transport', 'groceries', 'utility-bill').
    - "description" should be a string containing any extra details, or null if no description is provided.
    - If you cannot reliably extract these details, return a JSON object with null values, like {{"amount": null, "category": null, "description": null}}.

    Text to analyze: "{text}"

    JSON Output:
    """

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": YOUR_SITE_URL,
        "X-Title": YOUR_SITE_NAME,
        "Content-Type": "application/json"
    }
    payload = {
        "model": LLM_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                OPENROUTER_API_URL,
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            api_result = response.json()
    except httpx.RequestError as e:
        logger.error(f"HTTP request failed: {e}", exc_info=True)
        return None
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error response: {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Unexpected error during LLM request: {e}", exc_info=True)
        return None

    llm_response_content = api_result.get("choices", [{}])[0].get("message", {}).get("content", "")

    if not llm_response_content:
        logger.error(f"LLM returned empty content for text: '{text}'")
        return None

    try:
        # Clean potential markdown code blocks
        content = llm_response_content.strip()
        if content.startswith("```json"):
            content = content[7:-3].strip()
        elif content.startswith("```"):
            content = content[3:-3].strip()

        parsed_json = json.loads(content)
    except json.JSONDecodeError:
        logger.error(f"Failed to decode JSON from LLM response: {llm_response_content}")
        return None

    amount = parsed_json.get("amount")
    category = parsed_json.get("category")
    description = parsed_json.get("description")

    # Validation
    if amount is None or category is None:
        logger.warning(f"LLM parsing incomplete for '{text}'. Response: {parsed_json}")
        return None
    try:
        amount = float(amount)
    except (ValueError, TypeError):
        logger.warning(f"Invalid amount '{amount}' in LLM response: {parsed_json}")
        return None
    if not isinstance(category, str) or not category.strip():
        logger.warning(f"Invalid category '{category}' in LLM response: {parsed_json}")
        return None

    logger.info(f"LLM parsed expense: Amount={amount}, Category='{category}', Desc='{description}'")
    return Expense(
        user_id=user_id,
        amount=amount,
        category=category.lower().strip(),
        description=str(description).strip() if description else None
    )

async def parse_income_data(image_bytes: bytearray, user_id: int) -> dict | None:
    """Parses income data from an image using an LLM."""
    if not OPENROUTER_API_KEY or OPENROUTER_API_KEY == "YOUR_OPENROUTER_API_KEY":
        logger.error("OpenRouter API Key not configured.")
        return None

    try:
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        base64_string = f"data:image/jpeg;base64,{base64_image}"

        prompt = """
        Analyze the attached image, which likely represents income (e.g., receipt, invoice, payment confirmation). Extract the total numerical amount received and a brief source or description for this income.
        Return the result ONLY as a JSON object with the keys "amount" and "source".
        - "amount" should be the total income figure (float or integer).
        - "source" should be a short string identifying the origin or reason for the income (e.g., 'Salary', 'Client X Payment', 'Refund').
        - If you cannot reliably extract these details, return a JSON object with null values, like {"amount": null, "source": null}.

        JSON Output:
        """

        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "HTTP-Referer": YOUR_SITE_URL,
            "X-Title": YOUR_SITE_NAME,
            "Content-Type": "application/json"
        }
        payload = {
            "model": LLM_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": base64_string}}
                    ]
                }
            ],
            "max_tokens": 300,
            "temperature": 0.1
        }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                OPENROUTER_API_URL,
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            api_result = response.json()

    except httpx.RequestError as e:
        logger.error(f"HTTP request failed for image: {e}", exc_info=True)
        return None
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error response for image: {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Unexpected error during LLM image request: {e}", exc_info=True)
        return None

    llm_response_content = api_result.get("choices", [{}])[0].get("message", {}).get("content", "")

    if not llm_response_content:
        logger.error(f"LLM returned empty content for image from user {user_id}")
        return None

    try:
        content = llm_response_content.strip()
        if content.startswith("```json"):
            content = content[7:-3].strip()
        elif content.startswith("```"):
            content = content[3:-3].strip()

        parsed_json = json.loads(content)
    except json.JSONDecodeError:
        logger.error(f"Failed to decode JSON from LLM image response: {llm_response_content}")
        return None

    amount = parsed_json.get("amount")
    source = parsed_json.get("source")

    if amount is None or source is None:
        logger.warning(f"LLM image parsing incomplete. Response: {parsed_json}")
        return None
    try:
        amount = float(amount)
    except (ValueError, TypeError):
        logger.warning(f"Invalid amount '{amount}' in LLM image response: {parsed_json}")
        return None
    if not isinstance(source, str) or not source.strip():
        logger.warning(f"Invalid source '{source}' in LLM image response: {parsed_json}")
        return None

    logger.info(f"LLM parsed income: Amount={amount}, Source='{source}'")
    return {"amount": amount, "source": source.strip()}