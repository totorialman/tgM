import sys
import json
from PyQt6 import QtWidgets
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTableWidget, QTableWidgetItem, QVBoxLayout, 
                             QPushButton, QLineEdit, QDialog, QMessageBox, QHeaderView, QStackedWidget)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from telethon.sync import TelegramClient
from telethon.tl.functions.messages import SendMessageRequest   
from telethon.tl.functions.channels import JoinChannelRequest   
import asyncio

# Файл для хранения данных аккаунтов
DATA_FILE = 'accounts.json'

class MainApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle('Telegram Account Manager')
        self.setGeometry(100, 100, 800, 600)

        self.accounts = []
        self.clients = {}

        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        self.create_main_menu()
        self.create_accounts_page()
        self.create_actions_page()
        self.create_purchase_page()

        self.load_accounts()
        self.update_table()

        # Применение "хакерского" стиля
        self.setStyleSheet("QMainWindow { background-color: #1e1e1e; }"
                           "QTableWidget { background-color: #2d2d2d; color: #00ff00; gridline-color: #00ff00; }"
                           "QHeaderView::section { background-color: #3d3d3d; color: #00ff00; }"
                           "QPushButton { background-color: #2d2d2d; color: #00ff00; border: 1px solid #00ff00; }"
                           "QLineEdit { background-color: #2d2d2d; color: #00ff00; border: 1px solid #00ff00; }"
                           "QDialog { background-color: #1e1e1e; }"
                           "QMessageBox { background-color: #1e1e1e; color: #00ff00; }")

    def create_main_menu(self):
        self.main_menu_widget = QtWidgets.QWidget()
        self.main_menu_layout = QVBoxLayout(self.main_menu_widget)

        accounts_button = QPushButton('Управление аккаунтами')
        accounts_button.clicked.connect(self.show_accounts_page)
        self.main_menu_layout.addWidget(accounts_button)

        actions_button = QPushButton('Действия')
        actions_button.clicked.connect(self.show_actions_page)
        self.main_menu_layout.addWidget(actions_button)

        purchase_button = QPushButton('Покупка аккаунтов')
        purchase_button.clicked.connect(self.show_purchase_page)
        self.main_menu_layout.addWidget(purchase_button)

        self.stacked_widget.addWidget(self.main_menu_widget)
        self.show_main_menu()

    def create_accounts_page(self):
        self.accounts_widget = QtWidgets.QWidget()
        self.accounts_layout = QVBoxLayout(self.accounts_widget)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(['API ID', 'API Hash', 'Phone Number', 'Proxy'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.accounts_layout.addWidget(self.table)

        self.add_button = QPushButton('Добавить новый')
        self.add_button.clicked.connect(self.add_account_dialog)
        self.accounts_layout.addWidget(self.add_button)

        back_button = QPushButton('Назад в меню')
        back_button.clicked.connect(self.show_main_menu)
        self.accounts_layout.addWidget(back_button)

        self.stacked_widget.addWidget(self.accounts_widget)

    def create_actions_page(self):
        self.actions_widget = QtWidgets.QWidget()
        self.actions_layout = QVBoxLayout(self.actions_widget)

        self.send_message_button = QPushButton('Отправить сообщение')
        self.send_message_button.clicked.connect(self.send_message_dialog)
        self.actions_layout.addWidget(self.send_message_button)

        self.subscribe_button = QPushButton('Подписаться на канал')
        self.subscribe_button.clicked.connect(self.subscribe_dialog)
        self.actions_layout.addWidget(self.subscribe_button)

        back_button = QPushButton('Назад в меню')
        back_button.clicked.connect(self.show_main_menu)
        self.actions_layout.addWidget(back_button)

        self.stacked_widget.addWidget(self.actions_widget)

    def create_purchase_page(self):
        self.purchase_widget = QtWidgets.QWidget()
        self.purchase_layout = QVBoxLayout(self.purchase_widget)
        
        self.purchase_info_label = QtWidgets.QLabel("Страница покупки аккаунтов")
        self.purchase_info_label.setStyleSheet("color: #00ff00;")
        self.purchase_layout.addWidget(self.purchase_info_label)

        back_button = QPushButton('Назад в меню')
        back_button.clicked.connect(self.show_main_menu)
        self.purchase_layout.addWidget(back_button)

        self.stacked_widget.addWidget(self.purchase_widget)

    def show_main_menu(self):
        self.stacked_widget.setCurrentWidget(self.main_menu_widget)

    def show_accounts_page(self):
        self.stacked_widget.setCurrentWidget(self.accounts_widget)

    def show_actions_page(self):
        self.stacked_widget.setCurrentWidget(self.actions_widget)

    def show_purchase_page(self):
        self.stacked_widget.setCurrentWidget(self.purchase_widget)

    def load_accounts(self):
        try:
            with open(DATA_FILE, 'r') as file:
                self.accounts = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            self.accounts = []

    def save_accounts(self):
        with open(DATA_FILE, 'w') as file:
            json.dump(self.accounts, file)

    def add_account_dialog(self):
        dialog = AddAccountDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            api_id, api_hash, phone_number, proxy = dialog.get_account_details()
            self.add_account(api_id, api_hash, phone_number, proxy)
            self.save_accounts()

    def add_account(self, api_id, api_hash, phone_number, proxy):
        self.accounts.append((api_id, api_hash, phone_number, proxy))
        self.update_table()

    def update_table(self):
        self.table.setRowCount(len(self.accounts))
        for row, account in enumerate(self.accounts):
            for col, item in enumerate(account):
                self.table.setItem(row, col, QTableWidgetItem(item))

    def send_message_dialog(self):
        selected_row = self.table.currentRow()
        if selected_row == -1:
            return

        account = self.accounts[selected_row]
        dialog = SendMessageDialog(self, account)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            message = dialog.get_message()
            self.send_message(account, message)

    def subscribe_dialog(self):
        selected_row = self.table.currentRow()
        if selected_row == -1:
            return

        account = self.accounts[selected_row]
        dialog = SubscribeDialog(self, account)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            message = dialog.get_message()
            self.subscribe(account, message)
        
    

    def send_message(self, account, message):
        api_id, api_hash, phone_number, proxy = account
        proxy_parts = proxy.split(':')
        if len(proxy_parts) == 2:
            proxy_type, proxy_addr, proxy_port = 'socks5', proxy_parts[0], int(proxy_parts[1])
            proxy = (proxy_type, proxy_addr, proxy_port)
        elif len(proxy_parts) == 4:
            proxy_type, proxy_addr, proxy_port, proxy_username, proxy_password = 'socks5', proxy_parts[0], int(proxy_parts[1]), proxy_parts[2], proxy_parts[3]
            proxy = (proxy_type, proxy_addr, proxy_port, proxy_username, proxy_password)
        else:
            proxy = None

        client = self.clients.get(account)

        if not client:
            client = TelegramClient(f'session_{phone_number}', api_id, api_hash, proxy=proxy)
            self.clients[account] = client

        def send_message_to_user():
            try:
                client.connect()
                if not client.is_user_authorized():
                    client.send_code_request(phone_number)
                    client.sign_in(phone_number, input('Введите код: '))
                    if not client.is_user_authorized():
                        client.sign_in(password=input('Введите пароль для двухэтапной аутентификации: '))

                client(SendMessageRequest(
                    peer='rezo_ntov',
                    message=message,
                    random_id=client.rngs.getrandbits(64)
                ))
                QMessageBox.information(self, "Сообщение отправлено", f"Сообщение отправлено с аккаунта {phone_number}")

            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось отправить сообщение: {e}")
            finally:
                client.disconnect()

        send_message_to_user()

    def subscribe_to_channel(account, channel_username):
        api_id, api_hash, phone_number, proxy = account
        proxy_parts = proxy.split(':')
        if len(proxy_parts) == 2:
            proxy = ('socks5', proxy_parts[0], int(proxy_parts[1]))
        elif len(proxy_parts) == 4:
            proxy = ('socks5', proxy_parts[0], int(proxy_parts[1]), proxy_parts[2], proxy_parts[3])
        else:
            proxy = None
        client = TelegramClient(f'session_{phone_number}', api_id, api_hash, proxy=proxy)
        def join_channel():
            try:
                client.connect()
                if not client.is_user_authorized():
                    client.send_code_request(phone_number)
                    client.sign_in(phone_number, input('Введите код: '))
                    if not client.is_user_authorized():
                        client.sign_in(password=input('Введите пароль для двухэтапной аутентификации: '))

                    client(JoinChannelRequest(channel_username))
                    QMessageBox.information(None, "Подписка выполнена", f"Успешная подписка на канал {channel_username}")
            except Exception as e:
                QMessageBox.critical(None, "Ошибка", f"Не удалось подписаться на канал: {e}")
            finally:
                client.disconnect()

        join_channel()

class AddAccountDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle('Добавить новый аккаунт')

        layout = QVBoxLayout()

        self.api_id_input = QLineEdit(self)
        self.api_id_input.setPlaceholderText('API ID')
        layout.addWidget(self.api_id_input)

        self.api_hash_input = QLineEdit(self)
        self.api_hash_input.setPlaceholderText('API Hash')
        layout.addWidget(self.api_hash_input)

        self.phone_number_input = QLineEdit(self)
        self.phone_number_input.setPlaceholderText('Phone Number')
        layout.addWidget(self.phone_number_input)

        self.proxy_input = QLineEdit(self)
        self.proxy_input.setPlaceholderText('Proxy (ip:port or ip:port:username:password)')
        layout.addWidget(self.proxy_input)

        self.confirm_button = QPushButton('Подтвердить', self)
        self.confirm_button.clicked.connect(self.accept)
        layout.addWidget(self.confirm_button)

        self.setLayout(layout)

    def get_account_details(self):
        return self.api_id_input.text(), self.api_hash_input.text(), self.phone_number_input.text(), self.proxy_input.text()

class SendMessageDialog(QDialog):
    def __init__(self, parent, account):
        super().__init__(parent)

        self.setWindowTitle('Отправить сообщение')

        layout = QVBoxLayout()

        self.message_input = QLineEdit(self)
        self.message_input.setPlaceholderText('Введите сообщение')
        layout.addWidget(self.message_input)

        self.send_button = QPushButton('Отправить', self)
        self.send_button.clicked.connect(self.accept)
        layout.addWidget(self.send_button)

        self.setLayout(layout)

    def get_message(self):
        return self.message_input.text()

class SubscribeDialog(QDialog):
    def __init__(self, parent, account):
        super().__init__(parent)

        self.setWindowTitle('Подписать на канал')

        layout = QVBoxLayout()

        self.message_input = QLineEdit(self)
        self.message_input.setPlaceholderText('Ссылка на канал')
        layout.addWidget(self.message_input)

        self.send_button = QPushButton('Подписаться', self)
        self.send_button.clicked.connect(self.accept)
        layout.addWidget(self.send_button)

        self.setLayout(layout)

    def get_message(self):
        return self.message_input.text()

async def main():
    app = QApplication(sys.argv)
    window = MainApp()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    asyncio.run(main())
