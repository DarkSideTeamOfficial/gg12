# 🔄 Миграция данных из SQLite в PostgreSQL

Если у вас уже есть пользователи в старой базе данных SQLite (`users.db`), следуйте этой инструкции для переноса данных.

## Вариант 1: Ручной экспорт/импорт (простой)

### Шаг 1: Экспорт данных из SQLite

```python
# export_sqlite.py
import sqlite3
import json

conn = sqlite3.connect('users.db')
cursor = conn.cursor()

# Экспорт пользователей
cursor.execute("SELECT * FROM users")
users = cursor.fetchall()
users_columns = [description[0] for description in cursor.description]

# Экспорт настроек
cursor.execute("SELECT * FROM notification_settings")
settings = cursor.fetchall()
settings_columns = [description[0] for description in cursor.description]

data = {
    'users': {
        'columns': users_columns,
        'data': users
    },
    'notification_settings': {
        'columns': settings_columns,
        'data': settings
    }
}

with open('database_backup.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

conn.close()
print("✅ Данные экспортированы в database_backup.json")
```

### Шаг 2: Импорт в PostgreSQL

```python
# import_postgresql.py
import json
import psycopg2
from psycopg2.extras import execute_values
import os
from dotenv import load_dotenv

load_dotenv()

# Подключение к PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL")
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# Загрузка данных
with open('database_backup.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Импорт пользователей
users_data = data['users']['data']
if users_data:
    execute_values(
        cursor,
        """INSERT INTO users (user_id, username, first_name, last_name, city, 
           timezone, notification_time, is_active, created_at, updated_at)
           VALUES %s ON CONFLICT (user_id) DO NOTHING""",
        users_data
    )
    print(f"✅ Импортировано {len(users_data)} пользователей")

# Импорт настроек
settings_data = data['notification_settings']['data']
if settings_data:
    execute_values(
        cursor,
        """INSERT INTO notification_settings (user_id, morning_time, evening_time,
           send_morning, send_evening, weather_type)
           VALUES %s ON CONFLICT (user_id) DO NOTHING""",
        settings_data
    )
    print(f"✅ Импортировано {len(settings_data)} настроек")

conn.commit()
cursor.close()
conn.close()
print("✅ Миграция завершена!")
```

### Запуск миграции:

```bash
# 1. Экспортируем из SQLite
python export_sqlite.py

# 2. Устанавливаем зависимости для PostgreSQL
pip install psycopg2-binary python-dotenv

# 3. Настраиваем .env с DATABASE_URL

# 4. Импортируем в PostgreSQL
python import_postgresql.py
```

---

## Вариант 2: Автоматическая миграция (продвинутый)

```python
# migrate_db.py
import sqlite3
import psycopg2
from psycopg2.extras import execute_values
import os
from dotenv import load_dotenv

load_dotenv()

def migrate_sqlite_to_postgresql():
    """Миграция данных из SQLite в PostgreSQL"""
    
    # Подключение к SQLite
    sqlite_conn = sqlite3.connect('users.db')
    sqlite_cursor = sqlite_conn.cursor()
    
    # Подключение к PostgreSQL
    pg_conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    pg_cursor = pg_conn.cursor()
    
    try:
        # Миграция пользователей
        sqlite_cursor.execute("SELECT * FROM users")
        users = sqlite_cursor.fetchall()
        
        if users:
            execute_values(
                pg_cursor,
                """INSERT INTO users (user_id, username, first_name, last_name, 
                   city, timezone, notification_time, is_active, created_at, updated_at)
                   VALUES %s ON CONFLICT (user_id) DO UPDATE SET
                   username = EXCLUDED.username,
                   first_name = EXCLUDED.first_name,
                   last_name = EXCLUDED.last_name,
                   city = EXCLUDED.city,
                   updated_at = EXCLUDED.updated_at""",
                users
            )
            print(f"✅ Мигрировано {len(users)} пользователей")
        
        # Миграция настроек
        sqlite_cursor.execute("SELECT * FROM notification_settings")
        settings = sqlite_cursor.fetchall()
        
        if settings:
            execute_values(
                pg_cursor,
                """INSERT INTO notification_settings (user_id, morning_time, 
                   evening_time, send_morning, send_evening, weather_type)
                   VALUES %s ON CONFLICT (user_id) DO UPDATE SET
                   morning_time = EXCLUDED.morning_time,
                   evening_time = EXCLUDED.evening_time,
                   send_morning = EXCLUDED.send_morning,
                   send_evening = EXCLUDED.send_evening,
                   weather_type = EXCLUDED.weather_type""",
                settings
            )
            print(f"✅ Мигрировано {len(settings)} настроек")
        
        pg_conn.commit()
        print("✅ Миграция успешно завершена!")
        
    except Exception as e:
        print(f"❌ Ошибка миграции: {e}")
        pg_conn.rollback()
    finally:
        sqlite_cursor.close()
        sqlite_conn.close()
        pg_cursor.close()
        pg_conn.close()

if __name__ == "__main__":
    migrate_sqlite_to_postgresql()
```

---

## Проверка миграции

После миграции проверьте данные:

```python
# check_migration.py
from database import db

# Получаем всех пользователей
users = db.get_all_active_users()
print(f"Всего активных пользователей: {len(users)}")

for user in users:
    print(f"- {user['first_name']} ({user['city']}): {user['morning_time']}")
```

---

## ⚠️ Важные замечания

1. **Типы данных**: SQLite более гибок с типами, PostgreSQL строже
2. **BOOLEAN**: В SQLite `0/1`, в PostgreSQL `TRUE/FALSE` (конвертируется автоматически)
3. **BIGINT**: Telegram user_id может быть большим числом, используется BIGINT
4. **Транзакции**: Используйте `ON CONFLICT` для предотвращения дублирования

---

## После успешной миграции

1. **Сохраните бэкап SQLite**: `users.db` → безопасное место
2. **Удалите старую базу из проекта**: добавьте `*.db` в `.gitignore`
3. **Протестируйте бота**: проверьте все функции
4. **Деплойте на Render**: следуйте инструкции в `RENDER_SETUP.md`

Готово! Ваши данные успешно перенесены! 🎉
