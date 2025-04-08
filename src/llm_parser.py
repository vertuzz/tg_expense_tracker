import json
import base64
import httpx
import logging
import datetime

from .config import OPENROUTER_API_KEY, OPENROUTER_API_URL, LLM_MODEL, YOUR_SITE_URL, YOUR_SITE_NAME, EXPENSE_CATEGORIES

logger = logging.getLogger(__name__)

def _validate_api_key() -> bool:
    """Validate the OpenRouter API key."""
    if not OPENROUTER_API_KEY or OPENROUTER_API_KEY == "YOUR_OPENROUTER_API_KEY":
        logger.error("OpenRouter API Key not configured.")
        return False
    return True

def _get_headers() -> dict:
    """Get common HTTP headers for OpenRouter API requests."""
    return {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": YOUR_SITE_URL,
        "X-Title": YOUR_SITE_NAME,
        "Content-Type": "application/json"
    }

async def _make_llm_request(headers: dict, payload: dict, timeout: int = 15) -> dict:
    """Make a request to the OpenRouter API with error handling."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                OPENROUTER_API_URL,
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"HTTP request failed: {e}", exc_info=True)
        return None
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error response: {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Unexpected error during LLM request: {e}", exc_info=True)
        return None

def _parse_llm_response(response_content: str) -> list:
    """Parse and clean the LLM response content."""
    if not response_content:
        logger.error("LLM returned empty content")
        return []

    try:
        # Clean potential markdown code blocks
        content = response_content.strip()
        if content.startswith("```json"):
            content = content[7:-3].strip()
        elif content.startswith("```"):
            content = content[3:-3].strip()

        parsed_json = json.loads(content)
    except json.JSONDecodeError:
        logger.error(f"Failed to decode JSON from LLM response: {response_content}")
        return []

    if not isinstance(parsed_json, list):
        logger.warning(f"Expected a list of expenses but got: {parsed_json}")
        return []

    return parsed_json

def _validate_expense_item(item: dict, user_id: int) -> dict:
    """Validate and format an individual expense item."""
    amount = item.get("amount")
    category = item.get("category")
    description = item.get("description")
    date_str = item.get("date")

    # Validate amount
    try:
        amount = abs(float(amount))
    except (ValueError, TypeError):
        logger.warning(f"Skipping expense with invalid amount: {item}")
        return None

    # Validate category
    if not isinstance(category, str) or not category.strip():
        category = "Other"
    else:
        # Map to known categories (case-insensitive)
        matched = next((c for c in EXPENSE_CATEGORIES if c.lower() == category.lower().strip()), None)
        category = matched if matched else "Other"

    # Parse date if provided
    timestamp = datetime.datetime.utcnow()
    if date_str:
        try:
            timestamp = datetime.datetime.fromisoformat(date_str)
        except (ValueError, TypeError):
            pass  # fallback to now

    return {
        "user_id": user_id,
        "amount": amount,
        "category": category,
        "description": str(description).strip() if description else None,
        "timestamp": timestamp
    }

async def parse_expense_data(text: str, user_id: int) -> list[dict]:
    """Parses potentially multiple expenses from text using an LLM. Returns a list of Expense objects."""
    if not _validate_api_key():
        return []

    prompt = f"""
    Analyze the following text which may contain multiple expense entries. Extract each expense with the following details:
    - "amount": number (float or integer)
    - "category": a relevant category word or phrase
    - "description": optional brief description or null
    - "date": optional date string in ISO format (YYYY-MM-DD), or null if not specified

    Return ONLY a JSON array of objects, each with keys: "amount", "category", "description", "date".
    Valid categories include: {', '.join(EXPENSE_CATEGORIES)}.
    If the category is not recognized, use "Other".
    If you cannot extract any expenses, return an empty JSON array [].

    Text to analyze: "{text}"

    JSON Output:
    """

    headers = _get_headers()
    payload = {
        "model": LLM_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1
    }

    api_result = await _make_llm_request(headers, payload)
    if not api_result:
        return []

    llm_response_content = api_result.get("choices", [{}])[0].get("message", {}).get("content", "")
    parsed_items = _parse_llm_response(llm_response_content)

    expenses = []
    for item in parsed_items:
        expense = _validate_expense_item(item, user_id)
        if expense:
            expenses.append(expense)

    logger.info(f"LLM parsed {len(expenses)} expenses from input.")
    return expenses

async def parse_expense_image_data(image_bytes: bytearray, user_id: int) -> list[dict]:
    """Parses potentially multiple expenses from an image using an LLM. Returns a list of Expense objects."""
    if not _validate_api_key():
        return []

    try:
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        base64_string = f"data:image/jpeg;base64,{base64_image}"

        prompt = f"""
        Analyze the attached image, which may contain multiple expense entries (e.g., a photo of a receipt). Extract each expense with the following details:
        - "amount": number (float or integer)
        - "category": a relevant category word or phrase
        - "description": optional brief description or null
        - "date": optional date string in ISO format (YYYY-MM-DD), or null if not specified

        Return ONLY a JSON array of objects, each with keys: "amount", "category", "description", "date".
        Valid categories include: {', '.join(EXPENSE_CATEGORIES)}.
        If the category is not recognized, use "Other".
        If you cannot extract any expenses, return an empty JSON array [].

        JSON Output:
        """

        headers = _get_headers()
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
            "max_tokens": 1000,
            "temperature": 0.1
        }

        api_result = await _make_llm_request(headers, payload, timeout=30)
        if not api_result:
            return []

        llm_response_content = api_result.get("choices", [{}])[0].get("message", {}).get("content", "")
        parsed_items = _parse_llm_response(llm_response_content)

        expenses = []
        for item in parsed_items:
            expense = _validate_expense_item(item, user_id)
            if expense:
                expenses.append(expense)

        logger.info(f"LLM parsed {len(expenses)} expenses from image for user {user_id}.")
        return expenses

    except Exception as e:
        logger.error(f"Error processing image: {e}", exc_info=True)
        return []