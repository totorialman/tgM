import requests
import time
import threading
import json
import asyncio
from telethon.sync import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, PhoneCodeExpiredError
from telethon.tl.functions.auth import SendCodeRequest, SignUpRequest
from telethon.tl.functions.account import UpdateProfileRequest
from telethon.tl.types import CodeSettings
import queue

# Ваши данные API
api_key = 'za4xKY12mXHhKblhQfZpO14lL7htEpf2AdiBqxjt'
api_id = 29199205
api_hash = '0873b4b190e6115e45845ae7bcdea3dc'
service = 'tg'

countries = ['kz', 'lv', 'lt', 'am','by','ru','az','kg','tg', 'uz']  # Список стран
max_price = 60  # Максимальная цена за номер в рублях

numbers_file = 'activated_numbers.txt'  # Файл для сохранения активированных номеров

def log_to_file(filename, data):
    """Записывает данные в файл."""
    with open(filename, 'a') as file:
        file.write(data + '\n')

def get_number(country):
    """Получает номер телефона для указанной страны."""
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

async def get_sms_code(activation_id):
    """Получает код SMS для активации."""
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
            continue  # Удаляем задержку на 5 секунд
        else:
            print(f"Ошибка при получении кода для активации {activation_id}: {response}")
            return None

async def register_telegram_account(phone_number, activation_id, country):
    """Регистрирует аккаунт Telegram с указанным номером телефона."""
    client = TelegramClient('temp_session', api_id, api_hash)
    try:
        await client.start()
        if not client.is_user_authorized():
            print(f"Отправка кода на номер: {phone_number}")
            send_code = await client(SendCodeRequest(phone_number=phone_number, api_id=api_id, api_hash=api_hash, settings=CodeSettings()))
            phone_code_hash = send_code.phone_code_hash

            # Сообщаем сервису, что SMS отправлено
            requests.get(f"https://smslive.pro/stubs/handler_api.php?api_key={api_key}&action=setStatus&status=1&id={activation_id}")

            sms_code = await get_sms_code(activation_id)
            if not sms_code:
                return False

            await client(SignUpRequest(
                phone_number=phone_number,
                phone_code_hash=phone_code_hash,
                phone_code=sms_code,
                first_name='Имя',
                last_name='Фамилия'
            ))

            await client(UpdateProfileRequest(
                first_name='Имя',
                last_name='Фамилия',
                about='Описание профиля'
            ))

            print(f"Аккаунт успешно зарегистрирован: {phone_number} из {country.upper()}")
            log_to_file(numbers_file, phone_number)

            # Сохранение session файла
            await client.session.save(f'{phone_number}.session')
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
        await client.disconnect()

    return False

def process_country(country, result_queue):
    """Обрабатывает регистрацию для указанной страны."""
    activation_id, phone_number = get_number(country)
    if phone_number:
        print(f"Получен номер: {phone_number} из {country.upper()}")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        success = loop.run_until_complete(register_telegram_account(phone_number, activation_id, country))
        result_queue.put(success)
    else:
        print(f"Не удалось получить номер для страны: {country.upper()}")
        result_queue.put(False)

# Основной поток
activated = False
result_queue = queue.Queue()

while not activated:
    threads = []
    for country in countries:
        thread = threading.Thread(target=process_country, args=(country, result_queue))
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()

    # Проверка на успешную активацию
    activated = any(result_queue.get() for _ in range(len(threads)))
