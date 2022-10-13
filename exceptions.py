class ResponseKeyError(Exception):
    """Отсутствует необходимый ключ в ответе."""


class ResponseHTTPError(Exception):
    """Ошибка доступности эндпоинта."""


class ConnectError(Exception):
    """Ошибка соединения."""


class RequestError(Exception):
    """Прочие ошибки запроса."""


class StatusError(Exception):
    """Недокументированный статус в ответе API."""


class SendMessageFailure(Exception):
    """Сбой отправки сообщения в Telegram."""
