import logging
import os
import sqlite3
import sys
import time
from http import HTTPStatus

import requests
from requests import RequestException
from dotenv import load_dotenv
from telebot import TeleBot

from exceptions import (DebugInfo, EnvVariableIsMissing, ErrorInfo,
                        ErrorStatusCode, ListIsEmpty,
                        NoListHomeworks, StatusDoesNotExist)

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
TIMESTAMP = int(time.time())

HOMEWORK_VERDICTS = dict(
    approved='Работа проверена: ревьюеру всё понравилось. Ура!',
    reviewing='Работа взята на проверку ревьюером.',
    rejected='Работа проверена: у ревьюера есть замечания.'
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    encoding='utf-8',
    level=logging.DEBUG,
    filename='bot_logs.log')
logger = logging.getLogger(__name__)
handler = logging.StreamHandler(stream=sys.stdout)
logger.addHandler(handler)

with sqlite3.connect('homework_db.sqlite') as con:
    cur = con.cursor()
    query = '''
    CREATE TABLE IF NOT EXISTS homeworks(
        id TEXT PRIMARY KEY,
        status TEXT,
        date_updated TEXT
        );
        '''
    cur.execute(query)
    con.commit()


def check_tokens():
    """Функция проверки переменных из окружения."""
    data = dict(
        PRACTICUM_TOKEN=PRACTICUM_TOKEN,
        TELEGRAM_TOKEN=TELEGRAM_TOKEN,
        TELEGRAM_CHAT_ID=TELEGRAM_CHAT_ID,
        HEADERS=HEADERS,
        ENDPOINT=ENDPOINT,
        TIMESTAMP=TIMESTAMP,
        HOMEWORK_VERDICTS=HOMEWORK_VERDICTS)

    for key, variable in data.items():
        if not variable:
            raise EnvVariableIsMissing(
                f'Отсутствует обязательная переменная окружения: {key}.')


def get_api_answer(timestamp):
    """Проверка работоспособности эндпоинта."""
    payload = dict(from_date=timestamp)
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
    except RequestException:
        raise f'Нет ответа от API {ENDPOINT}'
    if response.status_code != HTTPStatus.OK:
        raise ErrorStatusCode(
            f'Ответ на запрос к API {response.status_code} '
            f'!= {HTTPStatus.OK}')
    return response.json()


def check_response(json_response):
    """Проверка корректности ответа от API."""
    if not isinstance(json_response, dict):
        raise TypeError
    try:
        homeworks = json_response['homeworks']
    except KeyError:
        raise NoListHomeworks(
            'В ответе от API отсутсвует список homeworks.')
    if not isinstance(homeworks, list):
        raise TypeError
    return homeworks


def availability_homeworks(homeworks):
    """Проверка наполненности списка домашних работ."""
    try:
        return homeworks[0]
    except IndexError:
        raise ListIsEmpty('Список актуальных домашних работ пуст.')


def load_last_status(homework):
    """Функция передает последнюю запись о домашке в базе данных."""
    with sqlite3.connect('homework_db.sqlite') as con:
        cursor_db = con.cursor()
        cursor_db.execute(f'''
                        SELECT id, status, date_updated
                        FROM homeworks
                        WHERE id = {homework['id']}''')
        row = cursor_db.fetchone()
        if row:
            homework_id, status, date_updated = row
            return dict(
                id=homework_id,
                status=status,
                date_updated=date_updated)


def status_has_been_changed(homework, last_status):
    """Функция сверки статуса домашней работы."""
    if homework['status'] != last_status['status']:
        return True
    return False


def save_status(homework):
    """Функция согхранения статуса в БД."""
    data = (
        homework['id'],
        homework['status'],
        homework['date_updated'],)
    with sqlite3.connect('homework_db.sqlite') as con:
        cursor_db = con.cursor()
        cursor_db.execute('''INSERT OR REPLACE INTO homeworks
                          (id, status, date_updated)
                          VALUES (?, ?, ?)''', data)
        con.commit()


def parse_status(homework):
    """Проверка соответствия статуса."""
    last_status = load_last_status(homework)
    homework_name = homework['homework_name']
    try:
        verdict = HOMEWORK_VERDICTS[homework['status']]
    except KeyError:
        raise StatusDoesNotExist(
            f'Неопознанный статус: "{homework["status"]}"')
    if not last_status or status_has_been_changed(homework, last_status):
        save_status(homework)
    else:
        logger.debug('Отсутствуют новые статусы.')
    return (f'Изменился статус проверки работы "{homework_name}". {verdict}')


def send_message(bot, message):
    """Функция отправки сообщения в Телеграмм."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,)
        logger.debug(f'Отправлено сообщение Телеграмм: {message}')
    except Exception as error:
        logger.error(error)


def main():
    """Основная логика программы."""
    bot = TeleBot(token=TELEGRAM_TOKEN)

    not_errors = True

    while True:
        try:
            check_tokens()
            response = get_api_answer(TIMESTAMP)
            homeworks = check_response(response)
            homework = availability_homeworks(homeworks)
            message = parse_status(homework)
            send_message(bot, message)
            not_errors = True
        except EnvVariableIsMissing as critical:
            logger.critical(critical)
            send_message(bot, critical)
            break
        except DebugInfo as info:
            logger.debug(info)
        except ErrorInfo as error:
            logger.error(error)
            if not_errors:
                send_message(bot, error)
                not_errors = False
        except Exception as error:
            logger.error(error)

        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
