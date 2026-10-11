"""Validate reported usage without substituting text-length estimates."""


def reported_usage(payload, *, is_chat=True):
    if not isinstance(payload, dict) or not isinstance(payload.get('usage'), dict):
        return None
    usage = payload['usage']
    prompt = usage.get('prompt_tokens')
    completion = usage.get('completion_tokens') if is_chat else usage.get('completion_tokens', 0)
    if any(type(value) is not int or not 0 <= value < (1 << 63) for value in (prompt, completion)):
        return None
    total = prompt + completion
    if total >= (1 << 63):
        return None
    if 'total_tokens' in usage and (type(usage['total_tokens']) is not int or usage['total_tokens'] != total):
        return None
    return prompt, completion
