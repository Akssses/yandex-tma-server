from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import TelegramUser
from .telegram_auth import verify_telegram_webapp_data, get_user_from_telegram_data
import os

TELEGRAM_BOT_TOKEN = '7986098041:AAG7kR2rxwICzBRvP53yyUMtYonbceyW2Rg'


@api_view(['GET'])
@swagger_auto_schema(
    operation_description="Получить список всех пользователей",
    responses={
        200: openapi.Response('Список пользователей', openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'first_name': openapi.Schema(type=openapi.TYPE_STRING),
                    'last_name': openapi.Schema(type=openapi.TYPE_STRING),
                    'username': openapi.Schema(type=openapi.TYPE_STRING),
                    'is_expert': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                }
            )
        )),
    },
    tags=['Users']
)
def api_users_list(request):
    """
    Получить список всех пользователей
    """
    users = TelegramUser.objects.all()
    data = []
    for user in users:
        data.append({
            'id': user.id,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'username': user.username,
            'is_expert': user.is_expert,
        })
    return Response(data)


@api_view(['POST'])
@swagger_auto_schema(
    operation_description="Проверить статус теста пользователя",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'initData': openapi.Schema(type=openapi.TYPE_STRING, description='Telegram WebApp initData'),
        },
        required=['initData']
    ),
    responses={
        200: openapi.Response('Статус теста', openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                'has_completed': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                'test_result': openapi.Schema(type=openapi.TYPE_OBJECT, description='Результат теста (если пройден)'),
            }
        )),
        400: openapi.Response('Ошибка запроса'),
        401: openapi.Response('Неверная подпись Telegram'),
    },
    tags=['Test']
)
def api_test_status(request):
    """
    Проверить статус теста пользователя
    """
    try:
        init_data = request.data.get('initData')
        
        if not init_data:
            return Response({'error': 'No initData provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Проверяем подпись Telegram
        telegram_data = verify_telegram_webapp_data(init_data, TELEGRAM_BOT_TOKEN)
        
        if not telegram_data:
            return Response({'error': 'Invalid Telegram signature'}, status=status.HTTP_401_UNAUTHORIZED)
        
        # Извлекаем telegram_id
        telegram_id = get_user_from_telegram_data(telegram_data)
        
        if not telegram_id:
            return Response({'error': 'No telegram_id in data'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = TelegramUser.objects.get(telegram_id=telegram_id)
            
            # Проверяем, проходил ли уже тест
            if user.has_completed_test():
                test_result = user.testresult
                return Response({
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
                    }
                })
            else:
                return Response({
                    'success': True,
                    'has_completed': False,
                })
                
        except TelegramUser.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
            
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@swagger_auto_schema(
    operation_description="Получить статистику пользователей",
    responses={
        200: openapi.Response('Статистика', openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'total_users': openapi.Schema(type=openapi.TYPE_INTEGER),
                'experts': openapi.Schema(type=openapi.TYPE_INTEGER),
                'regular_users': openapi.Schema(type=openapi.TYPE_INTEGER),
                'completed_tests': openapi.Schema(type=openapi.TYPE_INTEGER),
                'completed_quizzes': openapi.Schema(type=openapi.TYPE_INTEGER),
            }
        )),
    },
    tags=['Statistics']
)
def api_statistics(request):
    """
    Получить статистику пользователей
    """
    total_users = TelegramUser.objects.count()
    experts = TelegramUser.objects.filter(is_expert=True).count()
    regular_users = total_users - experts
    
    completed_tests = 0
    completed_quizzes = 0
    
    for user in TelegramUser.objects.all():
        if user.has_completed_test():
            completed_tests += 1
        if user.has_completed_quiz():
            completed_quizzes += 1
    
    return Response({
        'total_users': total_users,
        'experts': experts,
        'regular_users': regular_users,
        'completed_tests': completed_tests,
        'completed_quizzes': completed_quizzes,
    })




@api_view(['POST'])
@swagger_auto_schema(
    operation_description="Выгрузить всех пользователей в Google Sheets",
    responses={
        200: openapi.Response('Результат экспорта', openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                'exported': openapi.Schema(type=openapi.TYPE_INTEGER),
            }
        )),
        401: openapi.Response('Unauthorized'),
        500: openapi.Response('Server error'),
    },
    tags=['Users']
)
def export_users_to_sheets(request):
    """
    Экспортирует всех пользователей в указанный лист Google Sheets.
    Защищено простым токеном через заголовок X-Admin-Token.
    """
    # Lazy import gspread so the app can run even if it's not installed
    try:
        import gspread  # type: ignore
    except Exception as e:
        return Response({'error': 'gspread_not_installed', 'details': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    admin_token = request.headers.get('X-Admin-Token')
    if not admin_token or admin_token != os.getenv('EXPORT_ADMIN_TOKEN'):
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    sa_path = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE')
    spreadsheet_id = os.getenv('GOOGLE_SHEETS_SPREADSHEET_ID')
    worksheet_name = os.getenv('GOOGLE_SHEETS_WORKSHEET_NAME', 'Users')

    if not sa_path or not spreadsheet_id:
        return Response({'error': 'Missing Google Sheets config'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    try:
        gc = gspread.service_account(filename=sa_path)
        sh = gc.open_by_key(spreadsheet_id)
        try:
            ws = sh.worksheet(worksheet_name)
        except gspread.exceptions.WorksheetNotFound:
            ws = sh.add_worksheet(title=worksheet_name, rows=1000, cols=20)

        # Desired header order per request
        headers = [
            'Имя',
            'Фамилия',
            'Место работы',
            'Направление',
            'ТГ',
            'Почта',
            'Вакансии (Да/нет)',
            'Прошел тест (Да/нет)',
            'Прошел квиз (Да/нет)',
            'Имя эксперта',
            'Оценка от пользователя',
        ]

        rows = []
        for u in TelegramUser.objects.all().order_by('id'):
            # Determine expert name from user's booked consultations, if any
            expert_name = ''
            try:
                slot = u.consultations.order_by('-start_time').first()
                if slot and slot.expert:
                    expert_first = slot.expert.first_name or ''
                    expert_last = slot.expert.last_name or ''
                    expert_name = (expert_first + ' ' + expert_last).strip()
            except Exception:
                expert_name = ''

            rows.append([
                u.first_name,
                u.last_name or '',
                u.workplace or '',
                u.position or '',
                f"@{u.username}" if u.username else '',
                u.email or '',
                'Да' if False else 'Нет',  # нет отдельного поля под "Вакансии"
                'Да' if u.has_completed_test() else 'Нет',
                'Да' if u.has_completed_quiz() else 'Нет',
                expert_name,
                '',  # Оценка от пользователя — поле отсутствует
            ])

        ws.clear()
        ws.update('A1', [headers] + rows)

        return Response({'success': True, 'exported': len(rows)})
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

