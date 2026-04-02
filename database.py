import os
import sqlite3

class Database:
    def __init__(self):
        # По умолчанию создаем БД в той же папке, но позволяем переопределить через переменную окружения
        # Это важно для Railway: если подключить Volume, можно указать путь к нему (например, /data/users_data.db)
        db_path = os.getenv("DATABASE_PATH")
        if not db_path:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(base_dir, "users_data.db")
        
        print(f"📁 Используется база данных по адресу: {db_path}")
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        # Таблица подписок: кто следит, за чем именно и какая была цена
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                title TEXT,
                link TEXT,
                last_price TEXT
            )
        ''')
        self.conn.commit()

    # В файле database.py внутри add_subscription
    def add_subscription(self, user_id, title, link, price):
        print(f"DEBUG: Пытаюсь добавить подписку для {user_id}: {title}")  # Добавь это
        self.cursor.execute('SELECT id FROM subscriptions WHERE user_id = ? AND link = ?', (user_id, link))
        if self.cursor.fetchone() is None:
            self.cursor.execute(
                'INSERT INTO subscriptions (user_id, title, link, last_price) VALUES (?, ?, ?, ?)',
                (user_id, title, link, price)
            )
            self.conn.commit()
            print("DEBUG: Успешно сохранено в БД!")  # И это
            return True
        print("DEBUG: Подписка уже существует.")  # И это
        return False

    def get_user_subscriptions(self, user_id):
        self.cursor.execute('SELECT title, link, last_price FROM subscriptions WHERE user_id = ?', (user_id,))
        return self.cursor.fetchall()

    def remove_subscription(self, user_id, link):
        self.cursor.execute('DELETE FROM subscriptions WHERE user_id = ? AND link = ?', (user_id, link))
        self.conn.commit()

    def remove_all_subscriptions(self, user_id):
        self.cursor.execute('DELETE FROM subscriptions WHERE user_id = ?', (user_id,))
        self.conn.commit()

    def get_all_subscriptions(self):
        # Достаем абсолютно ВСЕ подписки всех пользователей для чекера
        self.cursor.execute('SELECT user_id, title, link, last_price FROM subscriptions')
        return self.cursor.fetchall()

    def update_price(self, link, user_id, new_price):
        # Обновляем цену в базе, когда она изменилась
        self.cursor.execute(
            'UPDATE subscriptions SET last_price = ? WHERE link = ? AND user_id = ?',
            (new_price, link, user_id)
        )
        self.conn.commit()