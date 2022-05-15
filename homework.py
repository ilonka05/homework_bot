import logging
import os
import requests
import telegram
import time

from dotenv import load_dotenv
from http import HTTPStatus

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
    except Exception as error:
        logger.error(f'Ошибка при отправке сообщения: {error}')


def get_api_answer(current_timestamp):
    """Делает запрос к эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    text_error = 'Ошибка при запросе к эндпоинту API-сервиса:'
    try:
        homework_statuses = requests.get(
            ENDPOINT, headers=HEADERS, params=params
        )
    except Exception as error:
        logger.error(f'{text_error} {error}')
    if homework_statuses.status_code != HTTPStatus.OK:
        logger.error(
            f'Ошибка при запросе к эндпоинту API-сервиса: '
            f'{homework_statuses.status_code}'
        )
        raise Exception(
            f'Ошибка при запросе к эндпоинту API-сервиса: '
            f'{homework_statuses.status_code}'
        )
    return homework_statuses.json()


def check_response(response):
    """Проверяет ответ API на корректность."""
    try:
        homeworks = response['homeworks']
    except KeyError as error:
        text_key_error = 'Отсутствует ключ "homeworks" в response:'
        logger.error(f'{text_key_error} {error}')
        raise Exception(f'{text_key_error} {error}')
    if not isinstance(response, dict):
        raise TypeError(
            f'Объект response должен быть dict, а получено: {type(response)}'
        )
    if not isinstance(homeworks, list):
        raise TypeError(
            f'Формат "homework" должен быть list, а получено: '
            f'{type(homeworks)}'
        )
    if len(homeworks) == 0:
        logger.error = 'Актуальных работ нет.'
        raise Exception(f'Актуальных работ нет, список пуст: {homeworks}')
    return homeworks


def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе статус работы."""
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_STATUSES:
        text_error_status = 'Недокументированный статус домашней работы:'
        logger.error(f'{text_error_status} {homework_status}')
        raise Exception(f'{text_error_status} {homework_status}')
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
        logger.critical('Отсутствует обязательная переменная окружения')
        raise ValueError('Отсутствует обязательная переменная окружения')
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)[0]
            if homework:
                message = parse_status(homework)
                send_message(bot, message)
            current_timestamp = response.get('current_data', current_timestamp)
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            time.sleep(RETRY_TIME)
        else:
            logger.debug('В ответе отсутствуют новые статусы.')


if __name__ == '__main__':
    main()
