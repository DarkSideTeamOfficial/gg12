#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль для работы с базой данных подписок пользователей (PostgreSQL)
"""

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
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
            self.connection_pool = psycopg2.pool.SimpleConnectionPool(
                1, 10,  # минимум 1, максимум 10 соединений
                self.database_url
            )
            if self.connection_pool:
                print("✅ Пул соединений с PostgreSQL создан успешно")
        except Exception as e:
            print(f"❌ Ошибка создания пула соединений: {e}")
            raise
        
        self.init_database()
    
    def get_connection(self):
        """Получение соединения из пула"""
        return self.connection_pool.getconn()
    
    def return_connection(self, conn):
        """Возврат соединения в пул"""
        self.connection_pool.putconn(conn)
    
    def close_all_connections(self):
        """Закрытие всех соединений в пуле"""
        if self.connection_pool:
            self.connection_pool.closeall()
            print("✅ Все соединения с PostgreSQL закрыты")
    
    def init_database(self):
        """Инициализация базы данных (создание таблиц)"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
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
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                cursor.close()
                self.return_connection(conn)
    
    def add_user(self, user_id: int, username: str = None, first_name: str = None, 
                 last_name: str = None, city: str = None) -> bool:
        """Добавление нового пользователя"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
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
            cursor.close()
            return True
        except Exception as e:
            print(f"❌ Ошибка при добавлении пользователя: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                self.return_connection(conn)
    
    def update_user_city(self, user_id: int, city: str) -> bool:
        """Обновление города пользователя"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users 
                SET city = %s, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = %s
            """, (city, user_id))
            conn.commit()
            rows_affected = cursor.rowcount
            cursor.close()
            return rows_affected > 0
        except Exception as e:
            print(f"❌ Ошибка при обновлении города: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                self.return_connection(conn)
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """Получение информации о пользователе"""
        conn = None
        try:
            conn = self.get_connection()
            # Используем RealDictCursor для получения результата в виде словаря
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("""
                SELECT u.*, ns.morning_time, ns.evening_time, 
                       ns.send_morning, ns.send_evening, ns.weather_type
                FROM users u
                LEFT JOIN notification_settings ns ON u.user_id = ns.user_id
                WHERE u.user_id = %s
            """, (user_id,))
            
            row = cursor.fetchone()
            cursor.close()
            return dict(row) if row else None
        except Exception as e:
            print(f"❌ Ошибка при получении пользователя: {e}")
            return None
        finally:
            if conn:
                self.return_connection(conn)
    
    def update_notification_settings(self, user_id: int, **kwargs) -> bool:
        """Обновление настроек уведомлений"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
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
            cursor.close()
            return True
        except Exception as e:
            print(f"❌ Ошибка при обновлении настроек: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                self.return_connection(conn)
    
    def get_users_for_notification(self, current_time: str) -> List[Dict]:
        """Получение пользователей для отправки уведомлений в указанное время"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
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
            cursor.close()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"❌ Ошибка при получении пользователей для уведомлений: {e}")
            return []
        finally:
            if conn:
                self.return_connection(conn)
    
    def get_all_active_users(self) -> List[Dict]:
        """Получение всех активных пользователей"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("""
                SELECT u.*, ns.morning_time, ns.evening_time, 
                       ns.send_morning, ns.send_evening, ns.weather_type
                FROM users u
                LEFT JOIN notification_settings ns ON u.user_id = ns.user_id
                WHERE u.is_active = TRUE AND u.city IS NOT NULL
            """)
            
            rows = cursor.fetchall()
            cursor.close()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"❌ Ошибка при получении активных пользователей: {e}")
            return []
        finally:
            if conn:
                self.return_connection(conn)
    
    def deactivate_user(self, user_id: int) -> bool:
        """Деактивация пользователя"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users 
                SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = %s
            """, (user_id,))
            conn.commit()
            rows_affected = cursor.rowcount
            cursor.close()
            return rows_affected > 0
        except Exception as e:
            print(f"❌ Ошибка при деактивации пользователя: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                self.return_connection(conn)

# Глобальный экземпляр базы данных
db = UserDatabase()
