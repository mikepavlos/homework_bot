from http import HTTPStatus
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

TOKEN_VALUES = {
    'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
    'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
    'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
}

RETRY_TIME = 600
SEK_IN_MONTH = 2629743
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

    except telegram.error.Unauthorized as err:
        raise exceptions.SendMessageFailure(f'Бот не отвечает: {err}')


def get_api_answer(current_timestamp):
    """Получение ответа от API Practicum.Yandex."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}

    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code == HTTPStatus.OK:
            return response.json()
        raise exceptions.RequestError(
            f'Эндпоинт {ENDPOINT} недоступен. '
            f'Код ошибки ответа API: {response.status_code}'
        )

    except requests.ConnectionError as err:
        raise exceptions.ConnectError('Отсутствует подключение') from err

    except requests.exceptions.HTTPError as err:
        raise exceptions.ResponseHTTPError(
            f'Эндпоинт {ENDPOINT} недоступен. '
            f'Код ошибки ответа API: {err.response.status_code}')

    except requests.exceptions.RequestException as err:
        raise exceptions.RequestError(f'Ошибка ответа API: {err}')


def check_response(response):
    """Проверка ответа API на корректность."""
    if not isinstance(response, dict):
        err = 'Ответ API не соответствует ожидаемому типу <dict>'
        raise TypeError(err)

    homeworks = response.get('homeworks')
    if homeworks is None:
        err = 'В ответе API отсутствует ключ <homeworks>'
        raise KeyError(err)

    if not isinstance(homeworks, list):
        err = 'Под ключом <homeworks> должен быть список <list>'
        raise TypeError(err)

    return homeworks


def parse_status(homework):
    """Извлечение и проверка статуса домашней работы."""
    homework_name = homework['homework_name']
    homework_status = homework['status']

    if homework_status not in HOMEWORK_VERDICTS:
        raise exceptions.StatusError(
            f'Недокументированный статус "{homework_status}"'
        )

    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка токенов."""
    tokens_exists = True
    for name, token in TOKEN_VALUES.items():
        if token is None:
            tokens_exists = False
            logging.critical(f'Отсутствует переменная окружения {name}')
    return tokens_exists


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        sys.exit('Программа принудительно остановлена')

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time()) - SEK_IN_MONTH
    last_status = None
    last_error = None

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks[0])
            else:
                message = 'На данный момент домашних работ нет'
                logging.info(message)

            if message != last_status:
                send_message(bot, message)
                last_status = message
            else:
                logging.debug('Новые статусы в ответе отсутствуют')

            current_timestamp = response['current_date'] - SEK_IN_MONTH

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
            logging.FileHandler(
                filename=os.path.join(
                    os.path.dirname(__file__),
                    'program.log'
                ),
                mode='w',
                encoding='utf-8'
            )
        ]
    )
    main()
