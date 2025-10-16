from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from .models import TelegramUser, TestResult
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


@csrf_exempt
@require_http_methods(["POST"])
def get_test_status(request):
    """
    Проверяет, проходил ли пользователь тест
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
        
        try:
            user = TelegramUser.objects.get(telegram_id=telegram_id)
            
            if user.has_completed_test():
                test_result = user.testresult
                return JsonResponse({
                    'success': True,
                    'has_completed': True,
                    'test_result': {
                        'analyst_type': test_result.analyst_type,
                        'analyst_name': test_result.analyst_name,
                        'animal': test_result.animal,
                        'description': test_result.description,
                        'tags': test_result.tags,
                        'ei_score': test_result.ei_score,
                        'pj_score': test_result.pj_score,
                        'gift_received': test_result.gift_received,
                        'completed_at': test_result.completed_at.isoformat(),
                    }
                })
            else:
                return JsonResponse({
                    'success': True,
                    'has_completed': False
                })
                
        except TelegramUser.DoesNotExist:
            return JsonResponse({'error': 'User not registered'}, status=403)
            
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def save_test_result(request):
    """
    Сохраняет результат тестирования
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
        
        try:
            user = TelegramUser.objects.get(telegram_id=telegram_id)
            
            # Проверяем, не проходил ли уже тест
            if user.has_completed_test():
                return JsonResponse({'error': 'Test already completed'}, status=400)
            
            # Получаем данные результата
            test_data = data.get('testResult')
            if not test_data:
                return JsonResponse({'error': 'No test result data provided'}, status=400)
            
            # Создаем результат теста
            test_result = TestResult.objects.create(
                user=user,
                analyst_type=test_data['analyst_type'],
                analyst_name=test_data['analyst_name'],
                animal=test_data['animal'],
                description=test_data['description'],
                tags=test_data['tags'],
                ei_score=test_data['ei_score'],
                pj_score=test_data['pj_score'],
                gift_received=False
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Test result saved successfully'
            })
                
        except TelegramUser.DoesNotExist:
            return JsonResponse({'error': 'User not registered'}, status=403)
            
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def confirm_gift(request):
    """
    Подтверждает получение подарка
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
        
        try:
            user = TelegramUser.objects.get(telegram_id=telegram_id)
            
            if not user.has_completed_test():
                return JsonResponse({'error': 'Test not completed'}, status=400)
            
            # Обновляем статус подарка
            test_result = user.testresult
            test_result.gift_received = True
            test_result.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Gift confirmation saved successfully'
            })
                
        except TelegramUser.DoesNotExist:
            return JsonResponse({'error': 'User not registered'}, status=403)
            
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)