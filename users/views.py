from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from .models import TelegramUser
from .telegram_auth import verify_telegram_webapp_data, get_user_from_telegram_data

TELEGRAM_BOT_TOKEN = '8429850519:AAHSSPY3TAhuyTJQEc0cqFQAelXPrD2qKAs'

@csrf_exempt
@require_http_methods(["POST"])
def verify_user(request):
    """
    Проверяет авторизацию пользователя через Telegram WebApp initData
    """
    try:
        data = json.loads(request.body)
        init_data = data.get('initData')
        
        if not init_data:
            return JsonResponse({'error': 'No initData provided'}, status=400)
        
        # Проверяем подпись Telegram
        telegram_data = verify_telegram_webapp_data(init_data, TELEGRAM_BOT_TOKEN)
        
        if not telegram_data:
            return JsonResponse({'error': 'Invalid Telegram signature'}, status=401)
        
        # Извлекаем telegram_id
        telegram_id = get_user_from_telegram_data(telegram_data)
        
        if not telegram_id:
            return JsonResponse({'error': 'No telegram_id in data'}, status=400)
        
        # Проверяем, зарегистрирован ли пользователь
        try:
            user = TelegramUser.objects.get(telegram_id=telegram_id)
            return JsonResponse({
                'success': True,
                'user': {
                    'id': user.id,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'username': user.username,
                    'email': user.email,
                    'workplace': user.workplace,
                    'position': user.position,
                }
            })
        except TelegramUser.DoesNotExist:
            return JsonResponse({'error': 'User not registered'}, status=403)
            
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)