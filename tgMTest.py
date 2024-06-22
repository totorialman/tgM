import sys
import json
from PyQt6 import QtWidgets, QtGui
from PyQt6.QtWidgets import QApplication, QMainWindow, QTableWidget, QTableWidgetItem, QVBoxLayout, QPushButton, QLineEdit, QDialog, QMessageBox
from PyQt6.QtCore import Qt
from telethon import TelegramClient
import asyncio

# Файл для хранения данных аккаунтов
DATA_FILE = 'accounts.json'

class MainApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle('Telegram Account Manager')
        self.setGeometry(100, 100, 600, 400)

        self.accounts = []
        self.clients = {}

        self.layout = QVBoxLayout()
        
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(['API ID', 'API Hash', 'Phone Number'])
        self.layout.addWidget(self.table)

        self.add_button = QPushButton('Добавить новый')
        self.add_button.clicked.connect(self.add_account_dialog)
        self.layout.addWidget(self.add_button)

        self.send_message_button = QPushButton('Отправить сообщение')
        self.send_message_button.clicked.connect(self.send_message_dialog)
        self.layout.addWidget(self.send_message_button)

        container = QtWidgets.QWidget()
        container.setLayout(self.layout)
        self.setCentralWidget(container)

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
            api_id, api_hash, phone_number = dialog.get_account_details()
            self.add_account(api_id, api_hash, phone_number)
            self.save_accounts()

    def add_account(self, api_id, api_hash, phone_number):
        self.accounts.append((api_id, api_hash, phone_number))
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
            asyncio.create_task(self.send_message(account, message))

    async def send_message(self, account, message):
        api_id, api_hash, phone_number = account
        client = self.clients.get(account)

        if not client:
            client = TelegramClient(f'session_{phone_number}', api_id, api_hash)
            self.clients[account] = client
            await client.start(phone=phone_number)

        await client.send_message('rezo_ntov', message)
        QMessageBox.information(self, "Сообщение отправлено", f"Сообщение отправлено с аккаунта {phone_number}")

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

        self.confirm_button = QPushButton('Подтвердить', self)
        self.confirm_button.clicked.connect(self.accept)
        layout.addWidget(self.confirm_button)

        self.setLayout(layout)

    def get_account_details(self):
        return self.api_id_input.text(), self.api_hash_input.text(), self.phone_number_input.text()

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

async def main():
    app = QApplication(sys.argv)
    window = MainApp()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    asyncio.run(main())
