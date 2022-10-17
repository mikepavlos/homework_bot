from http import HTTPStatus
import logging
from logging.handlers import RotatingFileHandler
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

TOKENS_VALUES = {
    'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
    'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
    'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID,
}

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправка сообщения в чат Telegram."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.info(f'Сообщение отправлено в Telegram: {message}')

    except Exception as err:
        raise exceptions.SendMessageFailure(
            f'Сообщение не отправлено. '
            f'Ошибка обращения к API Telegram. {err}, '
            f'id чата: {TELEGRAM_CHAT_ID}'
        )


def get_api_answer(current_timestamp):
    """Получение ответа от API Practicum.Yandex."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}

    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)

    except requests.RequestException as err:
        raise exceptions.RequestError(
            f'Ошибка запроса API: {err}, '
            f'Эндпоинт {ENDPOINT}, '
            f'headers: {HEADERS}, '
            f'params: {params}.'
        ) from err

    if response.status_code != HTTPStatus.OK:
        raise exceptions.RequestError(
            f'Эндпоинт {ENDPOINT} недоступен. '
            f'headers: {HEADERS}, params: {params}. '
            f'Код ошибки ответа API: {response.status_code}'
        )

    return response.json()


def check_response(response):
    """Проверка ответа API на корректность."""
    if not isinstance(response, dict):
        raise TypeError('Ответ API не соответствует ожидаемому типу <dict>')

    homeworks = response.get('homeworks')
    if homeworks is None:
        raise KeyError('В ответе API отсутствует ключ <homeworks>')

    if not isinstance(homeworks, list):
        raise TypeError('Под ключом <homeworks> должен быть список <list>')

    return homeworks


def parse_status(homework):
    """Извлечение и проверка статуса домашней работы."""
    homework_name = homework['homework_name']
    homework_status = homework['status']

    if homework_status not in HOMEWORK_VERDICTS:
        raise ValueError(f'Недокументированный статус "{homework_status}"')

    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка токенов."""
    if all([TELEGRAM_TOKEN, PRACTICUM_TOKEN, TELEGRAM_CHAT_ID]):
        return True

    for name, token in TOKENS_VALUES.items():
        if token is None:
            logging.critical(
                f'Отсутствует переменная окружения {name}')
    return False


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        raise SystemExit('Программа принудительно остановлена')

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    last_error = None

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks[0])
                send_message(bot, message)
            else:
                logging.debug('Изменений статусов работ нет')

            current_timestamp = response['current_date']

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)

            if message != last_error:
                send_message(bot, message)
                last_error = message

        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s '
               '[%(levelname)s] '
               '%(funcName)s, '
               '%(lineno)d: '
               '%(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            RotatingFileHandler(
                filename=os.path.join(
                    os.path.dirname(__file__),
                    'program.log'
                ),
                mode='w',
                maxBytes=5000000,
                backupCount=5,
                encoding='utf-8',
            )
        ]
    )
    main()
