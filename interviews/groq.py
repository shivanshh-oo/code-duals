import requests
from django.conf import settings


class AIError(Exception):
    def __init__(self, message, status=502):
        super().__init__(message)
        self.status = status


def complete(messages, structured=False):
    if not settings.GROQ_API_KEY:
        raise AIError('AI is not set up yet. Please contact the site administrator.', 503)
    payload = {'model': settings.GROQ_MODEL, 'messages': messages, 'max_completion_tokens': 2500}
    if structured:
        payload['response_format'] = {'type': 'json_object'}
    try:
        response = requests.post(
            'https://api.groq.com/openai/v1/chat/completions',
            headers={'Authorization': f'Bearer {settings.GROQ_API_KEY}'},
            json=payload, timeout=(5, 60),
        )
        if response.status_code in (401, 403):
            raise AIError('AI is temporarily unavailable. Please contact the site administrator.', 503)
        if response.status_code == 429:
            raise AIError('AI usage limit reached. Please try again later.', 429)
        response.raise_for_status()
        choice = response.json()['choices'][0]
        content = choice['message']['content']
        if choice.get('finish_reason') == 'length' or not isinstance(content, str) or not content.strip():
            raise ValueError()
        return content
    except (requests.RequestException, ValueError, KeyError, IndexError, TypeError):
        raise AIError('AI is temporarily unavailable. Please try again.') from None
