"""
Core utility functions for DocPixie
"""
import re


def sanitize_llm_json(response: str) -> str:
    """
    Sanitize JSON response from LLM by removing markdown code blocks and extra whitespace.
    
    LLMs sometimes wrap JSON responses with markdown code blocks like:
    ```json
    {"key": "value"}
    ```
    
    This function strips those wrappers and returns clean JSON.
    
    Args:
        response: Raw response string from LLM
        
    Returns:
        Sanitized JSON string ready for json.loads()
    """
    # Strip leading/trailing whitespace
    cleaned = response.strip()
    
    # Remove markdown code block wrappers
    # Matches ```json...``` or ```...``` patterns
    code_block_pattern = r'^```(?:json)?\s*\n?(.*?)\n?```$'
    match = re.match(code_block_pattern, cleaned, re.DOTALL | re.IGNORECASE)
    
    if match:
        cleaned = match.group(1).strip()
    
    return cleaned