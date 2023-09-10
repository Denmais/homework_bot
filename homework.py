import requests
import os
import telegram
import time
from dotenv import load_dotenv
import logging
from urllib.error import HTTPError
from exceptions import TokenNotExistsError


load_dotenv()
logging.basicConfig(
    filename='program.log',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяет доступность переменных окружения."""
    token_dict = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
    }
    for i, j in token_dict.items():
        if j is None:
            logging.critical(f'Отсутствие обязательных '
                             f'переменных окружения: {i}.')
            raise TokenNotExistsError


def send_message(bot: telegram.Bot, text: str):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, text)
    except Exception as error:
        logging.error(f'Ошибка при отправке сообщения {error}.')
    else:
        logging.debug('Сообщение отправлено!!')


def get_api_answer(timestamp):
    """Длает запрос к единственному эндпоинту API-сервиса."""
    payload = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
    except requests.RequestException:
        logging.error('Не удалось получить ответ API.')
    if response.status_code != 200:
        logging.error(f'Ошибка {response.status_code}')
        raise HTTPError
    return response.json()


def check_response(response):
    """Проверяет на совпадение с документацией."""
    if type(response) != dict:
        raise TypeError
    elif not ('homeworks' in response and 'current_date' in response):
        logging.error('Подходящие ключи не найдены!')
        raise KeyError
    elif type(response.get('homeworks')) != list:
        logging.error('Неподходящий формат данных.')
        raise TypeError
    return True


def parse_status(homework):
    """Извлекает из информации о конкретной домашней
    работе статус этой работы.
    """
    try:
        homework_name = homework['homework_name']
        verdict = HOMEWORK_VERDICTS[homework['status']]
    except KeyError:
        logging.error('Неожиданный статус домашней работы')
        raise KeyError
    else:
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(timestamp - 60 * 60 * 24)
            check_response(response)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
        else:
            if response.get('homeworks') != []:
                message = parse_status(response.get('homeworks')[0])
                print(message)
                send_message(bot, message)
            else:
                logging.debug('Нет обновлений.')
        time.sleep(600)


if __name__ == '__main__':
    main()
