import requests
import time
import threading
import json  # Импортируем json для обработки ответов
from telethon.sync import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, PhoneCodeExpiredError
from telethon.tl.functions.auth import SendCodeRequest, SignUpRequest
from telethon.tl.functions.account import UpdateProfileRequest
from telethon.tl.types import CodeSettings

# Ваши данные API
api_key = 'za4xKY12mXHhKblhQfZpO14lL7htEpf2AdiBqxjt'
api_id = 29199205  # Должно быть целым числом
api_hash = '0873b4b190e6115e45845ae7bcdea3dc'
service = 'tg'  # Сервис Telegram

countries = ['kz', 'lv', 'lt', 'am']  # Казахстан, Латвия, Литва, Армения
max_price = 50  # Максимальная цена за номер в рублях

# Файлы для сохранения информации
numbers_file = 'activated_numbers.txt'

def log_to_file(filename, data):
    with open(filename, 'a') as file:
        file.write(data + '\n')

def get_number(country):
    url = f"https://smslive.pro/stubs/handler_api.php?api_key={api_key}&action=getNumber&service={service}&country={country}&maxPrice={max_price}"
    response = requests.get(url).text
    if response.startswith('ACCESS_NUMBER'):
        parts = response.split(':')
        activation_id = parts[1]
        phone_number = parts[2]
        return activation_id, phone_number
    else:
        print(f"Ошибка при получении номера для {country.upper()}: {response}")
        return None, None

def check_numbers_availability(country):
    url = f"https://smslive.pro/stubs/handler_api.php?api_key={api_key}&action=getNumbersStatus&country={country}"
    response = requests.get(url).text
    try:
        data = json.loads(response)  # Преобразуем строку в JSON
        return data.get(country, {}).get(service, {}).get('count', 0) > 0
    except json.JSONDecodeError:
        print(f"Ошибка при декодировании JSON для страны {country}: {response}")
        return False

def get_sms_code(activation_id):
    url = f"https://smslive.pro/stubs/handler_api.php?api_key={api_key}&action=getStatus&id={activation_id}"
    start_time = time.time()
    wait_time = 300  # Время ожидания в секундах

    while True:
        elapsed_time = int(time.time() - start_time)
        print(f'Прошло {elapsed_time} секунд', end='\r')

        if elapsed_time >= wait_time:
            print(f'\nВремя ожидания истекло для активации {activation_id}.')
            return None

        response = requests.get(url).text
        if response.startswith('STATUS_OK'):
            return response.split(':')[1]
        elif response == 'STATUS_WAIT_CODE':
            time.sleep(5)  # Ждем 5 секунд перед повторной проверкой
        else:
            print(f"Ошибка при получении кода для активации {activation_id}: {response}")
            return None

def register_telegram_account(phone_number, activation_id, country):
    client = TelegramClient('temp_session', api_id, api_hash)  # Временный session файл
    try:
        client.connect()
        if not client.is_user_authorized():
            print(f"Отправка кода на номер: {phone_number}")
            send_code = client(SendCodeRequest(phone_number=phone_number, api_id=api_id, api_hash=api_hash, settings=CodeSettings()))
            phone_code_hash = send_code.phone_code_hash

            # Сообщаем сервису о том, что SMS отправлена
            requests.get(f"https://smslive.pro/stubs/handler_api.php?api_key={api_key}&action=setStatus&status=1&id={activation_id}")

            sms_code = get_sms_code(activation_id)
            if not sms_code:
                return False

            client(SignUpRequest(
                phone_number=phone_number,
                phone_code_hash=phone_code_hash,
                phone_code=sms_code,
                first_name='Имя',
                last_name='Фамилия'
            ))

            client(UpdateProfileRequest(
                first_name='Имя',
                last_name='Фамилия',
                about='Описание профиля'
            ))

            print(f"Аккаунт успешно зарегистрирован: {phone_number} из {country.upper()}")
            log_to_file(numbers_file, phone_number)

            # Сохранение session файла
            client.session.save(f'{phone_number}.session')
            return True
        else:
            print(f"Аккаунт уже авторизован: {phone_number}")
            return False
    except PhoneCodeInvalidError:
        print("Ошибка: неверный код подтверждения.")
    except PhoneCodeExpiredError:
        print("Ошибка: код подтверждения истек.")
    except Exception as e:
        print(f"Ошибка при регистрации: {e}")
    finally:
        client.disconnect()

    return False

def process_country(country):
    if check_numbers_availability(country):
        activation_id, phone_number = get_number(country)
        if phone_number:
            print(f"Получен номер: {phone_number} из {country.upper()}")
            if register_telegram_account(phone_number, activation_id, country):
                print(f"Аккаунт зарегистрирован: {phone_number} из {country.upper()}")
                return True
            else:
                print(f"Не удалось зарегистрировать аккаунт: {phone_number} из {country.upper()}")
                requests.get(f"https://smslive.pro/stubs/handler_api.php?api_key={api_key}&action=setStatus&status=8&id={activation_id}")
        else:
            print(f"Не удалось получить номер для страны: {country.upper()}")
    else:
        print(f"Нет доступных номеров для страны: {country.upper()}")

# Основной поток
activated = False
threads = []

while not activated:
    for country in countries:
        thread = threading.Thread(target=process_country, args=(country,))
        thread.start()
        threads.append(thread)

    # Ждем завершения всех потоков
    for thread in threads:
        thread.join()

    # Проверка на успешную активацию
    if any(thread.result for thread in threads):
        activated = True
