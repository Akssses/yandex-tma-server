import hashlib
import hmac
import json
import urllib.parse
from typing import Optional, Dict, Any
from django.conf import settings

def verify_telegram_webapp_data(init_data: str, bot_token: str) -> Optional[Dict[str, Any]]:
    """
    Проверяет подпись Telegram WebApp initData и возвращает данные пользователя
    """
    try:
        # Парсим initData
        parsed_data = urllib.parse.parse_qs(init_data)
        
        # Извлекаем hash и остальные данные
        received_hash = parsed_data.get('hash', [None])[0]
        if not received_hash:
            return None
            
        # Удаляем hash из данных для проверки
        data_check_string_parts = []
        for key, value in parsed_data.items():
            if key != 'hash':
                data_check_string_parts.append(f"{key}={value[0]}")
        
        # Сортируем и объединяем
        data_check_string_parts.sort()
        data_check_string = '\n'.join(data_check_string_parts)
        
        # Создаем секретный ключ
        secret_key = hmac.new(
            "WebAppData".encode(),
            bot_token.encode(),
            hashlib.sha256
        ).digest()
        
        # Вычисляем hash
        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Проверяем подпись
        if calculated_hash != received_hash:
            return None
            
        # Извлекаем данные пользователя
        user_data = {}
        if 'user' in parsed_data:
            user_data = json.loads(parsed_data['user'][0])
            
        return {
            'user': user_data,
            'auth_date': parsed_data.get('auth_date', [None])[0],
            'query_id': parsed_data.get('query_id', [None])[0]
        }
        
    except Exception as e:
        print(f"Error verifying Telegram data: {e}")
        return None

def get_user_from_telegram_data(telegram_data: Dict[str, Any]) -> Optional[int]:
    """
    Извлекает telegram_id из данных Telegram
    """
    try:
        user_data = telegram_data.get('user', {})
        return user_data.get('id')
    except Exception:
        return None
