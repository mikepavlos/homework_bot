class RequestError(Exception):
    """Прочие ошибки запроса."""
    pass


class SendMessageFailure(Exception):
    """Сбой отправки сообщения в Telegram."""
    pass
