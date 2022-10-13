import logging
import os
import sys
import time

from dotenv import load_dotenv
import requests
import telegram

import exceptions

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 60 * 10
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter(
    '%(asctime)s '
    '[%(levelname)s] '
    '%(message)s'
)
handler_stream = logging.StreamHandler(sys.stdout)
handler_file = logging.FileHandler('program.log', mode='w')
handler_stream.setFormatter(formatter)
handler_file.setFormatter(formatter)

logger.addHandler(handler_stream)
logger.addHandler(handler_file)


def send_message(bot, message):
    """Отправка сообщения в чат Telegram."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(f'Сообщение отправлено в Telegram: {message}')

    except telegram.error.Unauthorized as err:
        raise exceptions.SendMessageFailure(f'Бот не отвечает: {err}')

    except telegram.error.TelegramError as err:
        raise exceptions.SendMessageFailure(f'Сбой отправки сообщения: {err}')


def get_api_answer(current_timestamp):
    """Получение ответа от API Practicum.Yandex."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}

    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        response.raise_for_status()
        return response.json()

    except requests.ConnectionError:
        raise exceptions.ConnectError('Отсутствует подключение.')

    except requests.exceptions.HTTPError as err:
        raise exceptions.ResponseHTTPError(
            f'Эндпоинт {ENDPOINT} недоступен. '
            f'Код ошибки ответа API: {err.response.status_code}')

    except requests.exceptions.RequestException as err:
        raise exceptions.RequestError(f'Ошибка ответа API: {err}')


def check_response(response):
    """Проверка ответа API на корректность."""
    if not isinstance(response, dict):
        err = 'Ответ API не соответствует ожидаемому типу <dict>.'
        raise TypeError(err)

    if response.get('homeworks') is None:
        err = 'В ответе API отсутствует ключ <homeworks>.'
        raise exceptions.ResponseKeyError(err)

    return response.get('homeworks')


def parse_status(homework):
    """Извлечение и проверка статуса домашней работы."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_STATUSES:
        raise exceptions.StatusError(
            f'Недокументированный статус "{homework_status}"'
        )
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка токенов."""
    tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
    }
    tokens_exists = True
    for key, value in tokens.items():
        if value is None:
            tokens_exists = False
            logger.critical(f'Отсутствует переменная окружения {key}')
    return tokens_exists


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        sys.exit('Программа принудительно остановлена')

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    last_status = None
    last_error = None

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)

            if homeworks:
                message = parse_status(homeworks[0])
            else:
                message = 'На данный момент домашек нет.'
                logger.info(response)

            if message != last_status:
                send_message(bot, message)
                last_status = message
            else:
                logger.debug('Новые статусы в ответе отсутствуют.')

            current_timestamp = int(time.time())

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)

            if message != last_error:
                send_message(bot, message)
                last_error = message

        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
