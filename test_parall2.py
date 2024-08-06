import asyncio
import aiohttp
import aiofiles
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, PhoneCodeExpiredError, FloodWaitError
from telethon.tl.functions.auth import SendCodeRequest, SignUpRequest
from telethon.tl.functions.account import UpdateProfileRequest
from telethon.tl.types import CodeSettings
import json
from datetime import datetime

# Ваши данные API
api_key = 'za4xKY12mXHhKblhQfZpO14lL7htEpf2AdiBqxjt'
api_id = 27785381  # Должно быть целым числом
api_hash = 'be0217ddf9be2bf16126b4ab6eee1ea4'
service = 'tg'  # Сервис Telegram

countries = ['kz', 'lv', 'lt', 'am', 'by', 'ru', 'az', 'kg', 'uz']  # Казахстан, Латвия, Литва, Армения
max_price = 75  # Максимальная цена за номер в рублях

# Файлы для сохранения информации
numbers_file = 'activated_numbers.txt'
attempts_file = 'attempts.txt'
log_file = 'log.txt'

# Глобальный счетчик попыток
attempt = 0

async def load_attempt_count():
    global attempt
    try:
        async with aiofiles.open(attempts_file, 'r') as file:
            attempt = int(await file.read())
    except FileNotFoundError:
        attempt = 0

async def log_to_file(filename, data):
    async with aiofiles.open(filename, 'a') as file:
        await file.write(data + '\n')

async def save_attempt_count():
    global attempt
    async with aiofiles.open(attempts_file, 'w') as file:
        await file.write(str(attempt))

def get_current_time():
    return datetime.now().strftime('%H:%M %d.%m.%y')

async def log_message(message):
    timestamped_message = f"{get_current_time()} {message}"
    print(timestamped_message)  # выводим в консоль
    await log_to_file(log_file, timestamped_message)

async def check_balance(session):
    url = f"https://smslive.pro/stubs/handler_api.php?api_key={api_key}&action=getBalance"
    async with session.get(url) as response:
        balance_text = await response.text()
        if balance_text.startswith('ACCESS_BALANCE'):
            balance = float(balance_text.split(':')[1])
            await log_message(f"Текущий баланс: {balance} рублей")
            return balance
        else:
            await log_message(f"Ошибка при получении баланса: {balance_text}")
            return 0

async def check_available_numbers(session):
    url = f"https://smslive.pro/stubs/handler_api.php?api_key={api_key}&action=getNumbersStatus"
    async with session.get(url) as response:
        response_text = await response.text()
        if response_text.startswith('{"'):
            data = json.loads(response_text)
            available_balance = data.get('tg', 0)  # Получаем количество доступных номеров для Telegram
            await log_message(f"Доступные номера для Telegram: {available_balance}")
            return int(available_balance)  # Приводим к целому числу
        else:
            await log_message(f"Ошибка при получении статуса доступных номеров: {response_text}")
            return 0

async def get_number(session, country):
    url = f"https://smslive.pro/stubs/handler_api.php?api_key={api_key}&action=getNumber&service={service}&country={country}&maxPrice={max_price}"
    async with session.get(url) as response:
        response_text = await response.text()
        if response_text.startswith('ACCESS_NUMBER'):
            parts = response_text.split(':')
            activation_id = parts[1]
            phone_number = parts[2]
            return activation_id, phone_number
        else:
            await log_message(f"Ошибка при получении номера для {country.upper()}: {response_text}")
            return None, None

async def get_sms_code(session, activation_id):
    url = f"https://smslive.pro/stubs/handler_api.php?api_key={api_key}&action=getStatus&id={activation_id}"
    start_time = asyncio.get_event_loop().time()
    wait_time = 200  # Время ожидания в секундах

    while True:
        elapsed_time = int(asyncio.get_event_loop().time() - start_time)
        await log_message(f'Прошло {elapsed_time} секунд')

        if elapsed_time >= wait_time:
            await log_message(f'Время ожидания истекло для активации {activation_id}. Отмена номера.')
            # Отмена активации номера
            await session.get(f"https://smslive.pro/stubs/handler_api.php?api_key={api_key}&action=setStatus&status=8&id={activation_id}")
            return None

        async with session.get(url) as response:
            response_text = await response.text()
            if response_text.startswith('STATUS_OK'):
                return response_text.split(':')[1]
            elif response_text == 'STATUS_WAIT_CODE':
                await asyncio.sleep(5)  # Ждем 5 секунд перед повторной проверкой
            else:
                await log_message(f"Ошибка при получении кода для активации {activation_id}: {response_text}")
                return None

async def register_telegram_account(session, phone_number, activation_id, country):
    global attempt
    attempt += 1
    await save_attempt_count()
    
    client = TelegramClient('temp_session', api_id, api_hash)  # Временный session файл
    await client.connect()

    if not await client.is_user_authorized():
        try:
            await log_message(f"Отправка кода на номер: {phone_number}")
            send_code = await client(SendCodeRequest(phone_number=phone_number, api_id=api_id, api_hash=api_hash, settings=CodeSettings()))
            phone_code_hash = send_code.phone_code_hash

            # Сообщаем сервису о том, что SMS отправлена
            status_response = await session.get(f"https://smslive.pro/stubs/handler_api.php?api_key={api_key}&action=setStatus&status=1&id={activation_id}")
            await log_message(f"Статус отправки SMS: {await status_response.text()}")

            # Запускаем задачу получения SMS-кода
            sms_code_task = asyncio.create_task(get_sms_code(session, activation_id))

            # Ожидаем получения SMS-кода
            sms_code = await sms_code_task
            if not sms_code:
                await log_message(f"Не удалось получить SMS-код для {phone_number}.")
                return False

            await log_message(f"Получен код: {sms_code} для номера {phone_number}")

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

            await log_message(f"Аккаунт успешно зарегистрирован: {phone_number} из {country.upper()}")
            await log_to_file(numbers_file, phone_number)

            # Сохранение session файла
            await client.session.save(f'{phone_number}.session')
            return True
        except FloodWaitError as e:
            await log_message(f"Слишком много запросов. Необходима пауза в {e.seconds} секунд.")
            return e.seconds  # Возвращаем количество секунд паузы
        except Exception as e:
            await log_message(f"Ошибка при регистрации аккаунта для {phone_number}: {e}")
            return False
    else:
        await log_message(f"Аккаунт уже авторизован: {phone_number}")
        return False

    await client.disconnect()

async def main():
    pause_duration = 0  # Время паузы, если FloodWaitError
    async with aiohttp.ClientSession() as session:
        # Очистка лог файла при запуске программы
        async with aiofiles.open(log_file, 'w') as file:
            await file.write('')

        # Загрузка счетчика попыток
        await load_attempt_count()

        while True:
            if pause_duration > 0:
                await log_message(f"Ожидание окончания паузы: {pause_duration} секунд.")
                await asyncio.sleep(1)  # Ждем 1 секунду
                pause_duration -= 1
                continue  # Переходим к следующей итерации, не закупая номера
            
            balance = await check_balance(session)
            if balance < max_price:
                await log_message("Недостаточно средств в резерве для покупки нового номера. Завершение работы.")
                break  # Завершаем работу, если средств в резерве меньше max_price
            
            available_numbers = await check_available_numbers(session)
            if available_numbers < 1:  # Проверяем, есть ли доступные номера
                await log_message("Нет доступных номеров для покупки. Ожидание SMS-кодов...")
                await asyncio.sleep(10)  # Ждем 10 секунд перед повторной проверкой
                continue
            
            for country in countries:
                activation_id, phone_number = await get_number(session, country)
                if phone_number:
                    await log_message(f"Получен номер: {phone_number} из {country.upper()}")
                    pause_duration = await register_telegram_account(session, phone_number, activation_id, country)
                    if pause_duration:  # Если регистрация не удалась и необходимо ждать
                        break
                else:
                    await log_message(f"Не удалось получить номер для страны: {country.upper()}")

            await asyncio.sleep(1)  # Задержка перед следующей попыткой

if __name__ == "__main__":
    asyncio.run(main())
