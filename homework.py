import os
import logging
import sys
import time
from pprint import pprint

import requests
import telegram
from dotenv import load_dotenv

...

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 10
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='logging.log',
    filemode='w',
)


def send_message(bot, message):
    print(TELEGRAM_CHAT_ID, message)


def get_api_answer(current_timestamp):
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    return response.json()


def check_response(response):
    if isinstance(response, dict):
        pprint(response)
        return response.get('homeworks')


def parse_status(homework):
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    ...

    verdict = HOMEWORK_STATUSES[homework_status]

    ...

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
            logging.critical(f'Отсутствует переменная окружения {key}')
    return tokens_exists


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        sys.exit('Программа принудительно остановлена')

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time()) - 2629743*2

    ...

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)

            if homeworks:
                message = parse_status(homeworks[0])
            else:
                message = f'На данный момент домашек нет.'

            send_message(bot, message)
            current_timestamp = int(time.time()) - 2629743*2
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            ...
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
