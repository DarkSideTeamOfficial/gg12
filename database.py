#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль для работы с базой данных подписок пользователей (PostgreSQL)
"""

import psycopg
from psycopg_pool import ConnectionPool
from psycopg.rows import dict_row
import json
import os
from datetime import datetime, time
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

class UserDatabase:
    def __init__(self, database_url: str = None):
        """
        Инициализация подключения к PostgreSQL
        :param database_url: URL подключения к БД (например, postgresql://user:password@host:port/dbname)
        """
        self.database_url = database_url or os.getenv("DATABASE_URL")
        
        if not self.database_url:
            raise ValueError("DATABASE_URL не найден в переменных окружения!")
        
        # Создаем пул соединений для лучшей производительности
        try:
            self.connection_pool = ConnectionPool(
                self.database_url,
                min_size=1,
                max_size=10,
                open=True
            )
            print("✅ Пул соединений с PostgreSQL создан успешно")
        except Exception as e:
            print(f"❌ Ошибка создания пула соединений: {e}")
            raise
        
        self.init_database()
    
    def close_all_connections(self):
        """Закрытие всех соединений в пуле"""
        if self.connection_pool:
            self.connection_pool.close()
            print("✅ Все соединения с PostgreSQL закрыты")
    
    def init_database(self):
        """Инициализация базы данных (создание таблиц)"""
        try:
            with self.connection_pool.connection() as conn:
                with conn.cursor() as cursor:
                    # Создаем таблицу пользователей
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS users (
                            user_id BIGINT PRIMARY KEY,
                            username VARCHAR(255),
                            first_name VARCHAR(255),
                            last_name VARCHAR(255),
                            city VARCHAR(255),
                            timezone VARCHAR(50) DEFAULT 'Europe/Moscow',
                            notification_time VARCHAR(5) DEFAULT '08:00',
                            is_active BOOLEAN DEFAULT TRUE,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    
                    # Создаем таблицу настроек уведомлений
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS notification_settings (
                            user_id BIGINT PRIMARY KEY,
                            morning_time VARCHAR(5) DEFAULT '08:00',
                            evening_time VARCHAR(5) DEFAULT '20:00',
                            send_morning BOOLEAN DEFAULT TRUE,
                            send_evening BOOLEAN DEFAULT FALSE,
                            weather_type VARCHAR(20) DEFAULT 'brief',
                            FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
                        )
                    """)
                    
                    conn.commit()
                    print("✅ Таблицы базы данных проверены/созданы")
        except Exception as e:
            print(f"❌ Ошибка инициализации базы данных: {e}")
            raise
    
    def add_user(self, user_id: int, username: str = None, first_name: str = None, 
                 last_name: str = None, city: str = None) -> bool:
        """Добавление нового пользователя"""
        try:
            with self.connection_pool.connection() as conn:
                with conn.cursor() as cursor:
                    # Используем INSERT ON CONFLICT для PostgreSQL (аналог INSERT OR REPLACE)
                    cursor.execute("""
                        INSERT INTO users 
                        (user_id, username, first_name, last_name, city, updated_at)
                        VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (user_id) DO UPDATE SET
                            username = EXCLUDED.username,
                            first_name = EXCLUDED.first_name,
                            last_name = EXCLUDED.last_name,
                            city = EXCLUDED.city,
                            updated_at = CURRENT_TIMESTAMP
                    """, (user_id, username, first_name, last_name, city))
                    
                    # Добавляем настройки уведомлений по умолчанию
                    cursor.execute("""
                        INSERT INTO notification_settings (user_id)
                        VALUES (%s)
                        ON CONFLICT (user_id) DO NOTHING
                    """, (user_id,))
                    
                    conn.commit()
            return True
        except Exception as e:
            print(f"❌ Ошибка при добавлении пользователя: {e}")
            return False
    
    def update_user_city(self, user_id: int, city: str) -> bool:
        """Обновление города пользователя"""
        try:
            with self.connection_pool.connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE users 
                        SET city = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = %s
                    """, (city, user_id))
                    conn.commit()
                    return cursor.rowcount > 0
        except Exception as e:
            print(f"❌ Ошибка при обновлении города: {e}")
            return False
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """Получение информации о пользователе"""
        try:
            with self.connection_pool.connection() as conn:
                with conn.cursor(row_factory=dict_row) as cursor:
                    cursor.execute("""
                        SELECT u.*, ns.morning_time, ns.evening_time, 
                               ns.send_morning, ns.send_evening, ns.weather_type
                        FROM users u
                        LEFT JOIN notification_settings ns ON u.user_id = ns.user_id
                        WHERE u.user_id = %s
                    """, (user_id,))
                    
                    row = cursor.fetchone()
                    return dict(row) if row else None
        except Exception as e:
            print(f"❌ Ошибка при получении пользователя: {e}")
            return None
    
    def update_notification_settings(self, user_id: int, **kwargs) -> bool:
        """Обновление настроек уведомлений"""
        try:
            with self.connection_pool.connection() as conn:
                with conn.cursor() as cursor:
                    # Обновляем основные настройки пользователя
                    if 'city' in kwargs:
                        cursor.execute("""
                            UPDATE users SET city = %s, updated_at = CURRENT_TIMESTAMP
                            WHERE user_id = %s
                        """, (kwargs['city'], user_id))
                    
                    # Обновляем настройки уведомлений
                    update_fields = []
                    values = []
                    
                    for key, value in kwargs.items():
                        if key in ['morning_time', 'evening_time', 'send_morning', 
                                  'send_evening', 'weather_type']:
                            update_fields.append(f"{key} = %s")
                            values.append(value)
                    
                    if update_fields:
                        values.append(user_id)
                        cursor.execute(f"""
                            UPDATE notification_settings 
                            SET {', '.join(update_fields)}
                            WHERE user_id = %s
                        """, values)
                    
                    conn.commit()
            return True
        except Exception as e:
            print(f"❌ Ошибка при обновлении настроек: {e}")
            return False
    
    def get_users_for_notification(self, current_time: str) -> List[Dict]:
        """Получение пользователей для отправки уведомлений в указанное время"""
        try:
            with self.connection_pool.connection() as conn:
                with conn.cursor(row_factory=dict_row) as cursor:
                    cursor.execute("""
                        SELECT u.*, ns.morning_time, ns.evening_time, 
                               ns.send_morning, ns.send_evening, ns.weather_type
                        FROM users u
                        LEFT JOIN notification_settings ns ON u.user_id = ns.user_id
                        WHERE u.is_active = TRUE AND u.city IS NOT NULL
                        AND (
                            (ns.send_morning = TRUE AND ns.morning_time = %s) OR
                            (ns.send_evening = TRUE AND ns.evening_time = %s)
                        )
                    """, (current_time, current_time))
                    
                    rows = cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            print(f"❌ Ошибка при получении пользователей для уведомлений: {e}")
            return []
    
    def get_all_active_users(self) -> List[Dict]:
        """Получение всех активных пользователей"""
        try:
            with self.connection_pool.connection() as conn:
                with conn.cursor(row_factory=dict_row) as cursor:
                    cursor.execute("""
                        SELECT u.*, ns.morning_time, ns.evening_time, 
                               ns.send_morning, ns.send_evening, ns.weather_type
                        FROM users u
                        LEFT JOIN notification_settings ns ON u.user_id = ns.user_id
                        WHERE u.is_active = TRUE AND u.city IS NOT NULL
                    """)
                    
                    rows = cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            print(f"❌ Ошибка при получении активных пользователей: {e}")
            return []
    
    def deactivate_user(self, user_id: int) -> bool:
        """Деактивация пользователя"""
        try:
            with self.connection_pool.connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE users 
                        SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = %s
                    """, (user_id,))
                    conn.commit()
                    return cursor.rowcount > 0
        except Exception as e:
            print(f"❌ Ошибка при деактивации пользователя: {e}")
            return False

# Глобальный экземпляр базы данных
db = UserDatabase()
