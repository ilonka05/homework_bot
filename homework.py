import json
import logging
import os
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

import custom_error

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    filename='main.log',
    filemode='a',
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s',
)

logger = logging.getLogger(__name__)
logger.addHandler(
    logging.StreamHandler()
)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
        )
        logger.info(
            f'Отправлено сообщение в чат {TELEGRAM_CHAT_ID}: {message}'
        )
    except telegram.TelegramError as error:
        text_error_send_message = 'Ошибка при отправке сообщения:'
        logger.error(f'{text_error_send_message} {error}')
        raise telegram.TelegramError(
            f'{text_error_send_message} {error}'
        )


def get_api_answer(current_timestamp):
    """Делает запрос к эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    text_error_get_api = 'Ошибка при запросе к эндпоинту API-сервиса:'
    try:
        homework_statuses = requests.get(
            ENDPOINT, headers=HEADERS, params=params
        )
    except requests.exceptions.RequestException as error:
        logger.error(f'{text_error_get_api} {error}')
        raise requests.exceptions.RequestException(
            f'{text_error_get_api} {error}'
        )
    if homework_statuses.status_code != HTTPStatus.OK:
        logger.error(
            f'{text_error_get_api} {homework_statuses.status_code}'
        )
        raise custom_error.IsNot200Error(
            f'{text_error_get_api} {homework_statuses.status_code}'
        )
    try:
        return homework_statuses.json()
    except json.JSONDecodeError as error:
        text_error_json = 'Ответ не преобразуется в json:'
        logger.error(
            f'{text_error_json} {error}'
        )
        raise json.JSONDecodeError(
            f'{text_error_json} {error}'
        )


def check_response(response):
    """Проверяет ответ API на корректность."""
    try:
        homeworks = response['homeworks']
    except KeyError as error:
        text_key_error = 'Отсутствует ключ "homeworks" в response:'
        logger.error(f'{text_key_error} {error}')
        raise custom_error.HomeworksKeyError(f'{text_key_error} {error}')
    if not isinstance(response, dict):
        raise custom_error.NotDictTypeError(
            f'Объект response должен быть dict, а получено: {type(response)}'
        )
    if not isinstance(homeworks, list):
        raise custom_error.NotListTypeError(
            f'Формат "homework" должен быть list, а получено: '
            f'{type(homeworks)}'
        )
    if len(homeworks) == 0:
        logger.error = 'Актуальных работ нет.'
        raise custom_error.ZeroHomeworksError(
            f'Актуальных работ нет, список пуст: {homeworks}'
        )
    return homeworks


def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе статус работы."""
    try:
        homework_name = homework['homework_name']
    except KeyError as error:
        text_error_key_hw_name = 'Отсутствует ключ "homework_name" в response:'
        logger.error(f'{text_error_key_hw_name} {error}')
        raise custom_error.HomeworkNameKeyError(
            f'{text_error_key_hw_name} {error}'
        )
    try:
        homework_status = homework['status']
    except KeyError as error:
        text_error_key_status = 'Отсутствует ключ "status" в response:'
        logger.error(f'{text_error_key_status} {error}')
        raise custom_error.StatusKeyError(f'{text_error_key_status} {error}')
    if homework_status not in HOMEWORK_STATUSES:
        text_error_status = 'Недокументированный статус домашней работы:'
        logger.error(f'{text_error_status} {homework_status}')
        raise custom_error.NotStatusError(
            f'{text_error_status} {homework_status}'
        )
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения."""
    if all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
        return True


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    if not check_tokens():
        text_check_tokens_error = 'Отсутствует переменная окружения'
        logger.critical(text_check_tokens_error)
        raise ValueError(text_check_tokens_error)
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)[0]
            message = parse_status(homework)
            send_message(bot, message)
            current_timestamp = response.get('current_data', current_timestamp)
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            time.sleep(RETRY_TIME)
        else:
            text_not_new_status = 'В ответе отсутствуют новые статусы.'
            logger.debug(text_not_new_status)
            raise custom_error.NotNewStatusError(text_not_new_status)


if __name__ == '__main__':
    main()
