from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from .models import TelegramUser, TestResult, QuizResult, Workshop, WorkshopRegistration, ConsultationTopic, ConsultationSlot
from .telegram_auth import verify_telegram_webapp_data, get_user_from_telegram_data
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import os

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_API_BASE = 'https://api.telegram.org'

def _send_telegram_message(chat_id: int, text: str) -> None:
    try:
        import urllib.parse
        import urllib.request
        payload = urllib.parse.urlencode({
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML',
        }).encode()
        url = f"{TELEGRAM_API_BASE}/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        req = urllib.request.Request(url, data=payload)
        with urllib.request.urlopen(req, timeout=5) as _:
            pass
    except Exception:
        # Silent fail: notifications should not break API
        pass

@csrf_exempt
@require_http_methods(["POST"])
@swagger_auto_schema(
    operation_description="Проверяет авторизацию пользователя через Telegram WebApp initData",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'initData': openapi.Schema(type=openapi.TYPE_STRING, description='Telegram WebApp initData'),
        },
        required=['initData']
    ),
    responses={
        200: openapi.Response('Успешная авторизация', openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                'user_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                'is_expert': openapi.Schema(type=openapi.TYPE_BOOLEAN),
            }
        )),
        400: openapi.Response('Ошибка запроса'),
        401: openapi.Response('Неверная подпись Telegram'),
    },
    tags=['Authentication']
)
def verify_user(request):
    """
    Проверяет авторизацию пользователя через Telegram WebApp initData
    """
    try:
        # Debug: print masked token tail to ensure env consistency (remove in production)
        try:
            _tt = TELEGRAM_BOT_TOKEN or ''
            print(f"[API] TELEGRAM_BOT_TOKEN len={len(_tt)} tail={_tt[-6:]}")
        except Exception:
            pass
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
@swagger_auto_schema(
    operation_description="Проверяет, проходил ли пользователь тест",
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


@csrf_exempt
@require_http_methods(["POST"])
@swagger_auto_schema(
    operation_description="Проверяет, проходил ли пользователь квиз",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'initData': openapi.Schema(type=openapi.TYPE_STRING, description='Telegram WebApp initData'),
        },
        required=['initData']
    ),
    responses={
        200: openapi.Response('Статус квиза', openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                'has_completed': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                'quiz_result': openapi.Schema(type=openapi.TYPE_OBJECT, description='Результат квиза (если пройден)'),
            }
        )),
        400: openapi.Response('Ошибка запроса'),
        401: openapi.Response('Неверная подпись Telegram'),
    },
    tags=['Quiz']
)
def get_quiz_status(request):
    """
    Проверяет, проходил ли пользователь квиз
    """
    try:
        data = json.loads(request.body)
        init_data = data.get('initData')
        
        print(f"Quiz status check - initData: {init_data[:50] if init_data else 'None'}...")
        
        if not init_data:
            return JsonResponse({'error': 'No initData provided'}, status=400)
        
        # Проверяем подпись Telegram
        telegram_data = verify_telegram_webapp_data(init_data, TELEGRAM_BOT_TOKEN)
        
        if not telegram_data:
            print("Quiz status check - Invalid Telegram signature")
            return JsonResponse({'error': 'Invalid Telegram signature'}, status=401)
        
        # Извлекаем telegram_id
        telegram_id = get_user_from_telegram_data(telegram_data)
        
        if not telegram_id:
            print("Quiz status check - No telegram_id in data")
            return JsonResponse({'error': 'No telegram_id in data'}, status=400)
        
        print(f"Quiz status check - telegram_id: {telegram_id}")
        
        try:
            user = TelegramUser.objects.get(telegram_id=telegram_id)
            print(f"Quiz status check - user found: {user.first_name}")
            
            if user.has_completed_quiz():
                quiz_result = user.quizresult
                print(f"Quiz status check - quiz completed: {quiz_result.correct_answers}/{quiz_result.total_questions}")
                return JsonResponse({
                    'success': True,
                    'has_completed': True,
                    'quiz_result': {
                        'correct_answers': quiz_result.correct_answers,
                        'total_questions': quiz_result.total_questions,
                        'answers': quiz_result.answers,
                        'completed_at': quiz_result.completed_at.isoformat(),
                    }
                })
            else:
                print("Quiz status check - quiz not completed")
                return JsonResponse({
                    'success': True,
                    'has_completed': False
                })
                
        except TelegramUser.DoesNotExist:
            print("Quiz status check - User not registered")
            return JsonResponse({'error': 'User not registered'}, status=403)
            
    except json.JSONDecodeError:
        print("Quiz status check - Invalid JSON")
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        print(f"Quiz status check - Exception: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def save_quiz_result(request):
    """
    Сохраняет результат квиза
    """
    try:
        data = json.loads(request.body)
        init_data = data.get('initData')
        quiz_data = data.get('quizResult')
        
        print(f"Save quiz result - initData: {init_data[:50] if init_data else 'None'}...")
        print(f"Save quiz result - quizData: {quiz_data}")
        
        if not init_data:
            return JsonResponse({'error': 'No initData provided'}, status=400)
        
        # Проверяем подпись Telegram
        telegram_data = verify_telegram_webapp_data(init_data, TELEGRAM_BOT_TOKEN)
        
        if not telegram_data:
            print("Save quiz result - Invalid Telegram signature")
            return JsonResponse({'error': 'Invalid Telegram signature'}, status=401)
        
        # Извлекаем telegram_id
        telegram_id = get_user_from_telegram_data(telegram_data)
        
        if not telegram_id:
            print("Save quiz result - No telegram_id in data")
            return JsonResponse({'error': 'No telegram_id in data'}, status=400)
        
        print(f"Save quiz result - telegram_id: {telegram_id}")
        
        try:
            user = TelegramUser.objects.get(telegram_id=telegram_id)
            print(f"Save quiz result - user found: {user.first_name}")
            
            # Проверяем, не проходил ли уже квиз
            if user.has_completed_quiz():
                print("Save quiz result - Quiz already completed")
                return JsonResponse({'error': 'Quiz already completed'}, status=400)
            
            # Получаем данные результата
            if not quiz_data:
                print("Save quiz result - No quiz result data provided")
                return JsonResponse({'error': 'No quiz result data provided'}, status=400)
            
            # Создаем результат квиза
            quiz_result = QuizResult.objects.create(
                user=user,
                correct_answers=quiz_data['correct_answers'],
                total_questions=quiz_data['total_questions'],
                answers=quiz_data['answers']
            )
            
            print(f"Save quiz result - Quiz result created: {quiz_result}")
            
            return JsonResponse({
                'success': True,
                'message': 'Quiz result saved successfully'
            })
                
        except TelegramUser.DoesNotExist:
            print("Save quiz result - User not registered")
            return JsonResponse({'error': 'User not registered'}, status=403)
            
    except json.JSONDecodeError:
        print("Save quiz result - Invalid JSON")
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        print(f"Save quiz result - Exception: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


# -------- SPECIAL: Workshops --------

def _get_user_by_init_data(request):
    data = json.loads(request.body)
    init_data = data.get('initData')
    if not init_data:
        return None, JsonResponse({'error': 'No initData provided'}, status=400)
    telegram_data = verify_telegram_webapp_data(init_data, TELEGRAM_BOT_TOKEN)
    if not telegram_data:
        return None, JsonResponse({'error': 'Invalid Telegram signature'}, status=401)
    telegram_id = get_user_from_telegram_data(telegram_data)
    if not telegram_id:
        return None, JsonResponse({'error': 'No telegram_id in data'}, status=400)
    try:
        user = TelegramUser.objects.get(telegram_id=telegram_id)
        return user, None
    except TelegramUser.DoesNotExist:
        return None, JsonResponse({'error': 'User not registered'}, status=403)


@csrf_exempt
@require_http_methods(["GET"])
def list_workshops(request):
    workshops = Workshop.objects.all().order_by('start_time')
    def fmt(w):
        try:
            # HH:MM - HH:MM
            st = w.start_time.strftime('%H:%M')
            et = w.end_time.strftime('%H:%M')
            return f"{st} - {et}"
        except Exception:
            return ""

    data = [{
        'id': w.id,
        'title': w.title,
        'tag': w.tag,
        'description': w.description,
        'time': fmt(w),
    } for w in workshops]
    return JsonResponse({'success': True, 'workshops': data})


@csrf_exempt
@require_http_methods(["POST"])
def my_workshop_status(request):
    try:
        user, err = _get_user_by_init_data(request)
        if err:
            return err
        regs = WorkshopRegistration.objects.filter(user=user).select_related('workshop')
        data = []
        for r in regs:
            # Build time string like in list_workshops()
            try:
                st = r.workshop.start_time.strftime('%H:%M') if r.workshop.start_time else ""
                et = r.workshop.end_time.strftime('%H:%M') if r.workshop.end_time else ""
                time_str = f"{st} - {et}" if st and et else ""
            except Exception:
                time_str = ""
            data.append({
                'id': r.workshop.id,
                'title': r.workshop.title,
                'time': time_str,
            })
        return JsonResponse({'success': True, 'registrations': data, 'count': regs.count()})
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def register_workshop(request, workshop_id):
    try:
        user, err = _get_user_by_init_data(request)
        if err:
            return err
        # limit 2
        current_count = WorkshopRegistration.objects.filter(user=user).count()
        if current_count >= 2:
            return JsonResponse({'error': 'Registration limit reached (2)'}, status=400)
        try:
            workshop = Workshop.objects.get(id=workshop_id)
        except Workshop.DoesNotExist:
            return JsonResponse({'error': 'Workshop not found'}, status=404)
        reg, created = WorkshopRegistration.objects.get_or_create(user=user, workshop=workshop)
        if not created:
            return JsonResponse({'error': 'Already registered'}, status=400)
        return JsonResponse({'success': True})
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def cancel_workshop(request, workshop_id):
    try:
        user, err = _get_user_by_init_data(request)
        if err:
            return err
        try:
            reg = WorkshopRegistration.objects.get(user=user, workshop_id=workshop_id)
        except WorkshopRegistration.DoesNotExist:
            return JsonResponse({'error': 'Registration not found'}, status=404)
        reg.delete()
        return JsonResponse({'success': True})
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# -------- Consultations --------

@csrf_exempt
@require_http_methods(["GET"])
def consultations_topics(request):
    topics = ConsultationTopic.objects.all().order_by('name')
    return JsonResponse({'success': True, 'topics': [{ 'id': t.id, 'name': t.name } for t in topics]})


def _fmt_time(dt):
    try:
        return dt.strftime('%H:%M')
    except Exception:
        return ""


@csrf_exempt
@require_http_methods(["GET"])
def consultations_slots(request):
    try:
        from datetime import datetime, date, time, timedelta
        topic_id = request.GET.get('topic_id')
        if not topic_id:
            return JsonResponse({'success': True, 'slots': []})
        try:
            topic = ConsultationTopic.objects.get(id=topic_id)
        except ConsultationTopic.DoesNotExist:
            return JsonResponse({'success': True, 'slots': []})

        raw_slots = [
            (11, 0), (11, 30), (12, 0), (12, 30), (13, 0), (13, 30),
            (14, 0), (14, 30), (15, 0), (15, 30), (16, 0), (16, 30),
            (17, 0), (17, 30),
        ]
        today = date.today()
        generated = []
        expert_ids = list(topic.experts.values_list('id', flat=True))
        start_day = datetime.combine(today, time(0, 0))
        end_day = datetime.combine(today, time(23, 59))
        bookings = ConsultationSlot.objects.select_related('expert').filter(
            expert_id__in=expert_ids,
            start_time__gte=start_day,
            end_time__lte=end_day,
            is_booked=True,
        )
        booked_map = {}
        for b in bookings:
            booked_map.setdefault(b.expert_id, set()).add((b.start_time, b.end_time))

        for expert_id in expert_ids:
            try:
                expert = TelegramUser.objects.get(id=expert_id)
            except TelegramUser.DoesNotExist:
                continue
            for (hh, mm) in raw_slots:
                st = datetime.combine(today, time(hh, mm))
                et = st + timedelta(minutes=30)
                if (st, et) in booked_map.get(expert_id, set()):
                    continue
                generated.append({
                    'id': int(f"{expert_id}{hh:02d}{mm:02d}"),
                    'expert': {
                        'id': expert.id,
                        'first_name': expert.first_name,
                        'last_name': expert.last_name,
                    },
                    'topic': { 'id': topic.id, 'name': topic.name },
                    'time': f"{_fmt_time(st)} - {_fmt_time(et)}",
                    'st_iso': st.isoformat(),
                    'et_iso': et.isoformat(),
                })
        return JsonResponse({'success': True, 'slots': generated})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def consultations_book(request, slot_id):
    try:
        user, err = _get_user_by_init_data(request)
        if err:
            return err
        data = json.loads(request.body)
        st_iso = data.get('st_iso')
        et_iso = data.get('et_iso')
        expert_id = data.get('expert_id')
        topic_id = data.get('topic_id')
        from datetime import datetime
        if not (st_iso and et_iso and expert_id and topic_id):
            return JsonResponse({'error': 'Missing slot payload'}, status=400)
        try:
            expert = TelegramUser.objects.get(id=expert_id, is_expert=True)
            topic = ConsultationTopic.objects.get(id=topic_id)
        except Exception:
            return JsonResponse({'error': 'Invalid expert/topic'}, status=400)
        st = datetime.fromisoformat(st_iso)
        et = datetime.fromisoformat(et_iso)
        # Prevent double booking for the same topic by the same user
        already = ConsultationSlot.objects.filter(booked_by=user, topic=topic, is_booked=True).exists()
        if already:
            return JsonResponse({'error': 'Already booked this topic'}, status=400)
        # Reuse existing unbooked slot record to avoid unique constraint conflicts
        existing_slot = ConsultationSlot.objects.filter(expert=expert, start_time=st, end_time=et).first()
        if existing_slot:
            if existing_slot.is_booked:
                return JsonResponse({'error': 'Slot already booked'}, status=400)
            # Update and book existing slot
            existing_slot.topic = topic
            existing_slot.is_booked = True
            existing_slot.booked_by = user
            existing_slot.save()
            slot = existing_slot
        else:
            # Create a new record if none exists yet
            slot = ConsultationSlot.objects.create(
                expert=expert,
                topic=topic,
                start_time=st,
                end_time=et,
                is_booked=True,
                booked_by=user,
            )
        # Notify expert
        try:
            expert_name = f"{slot.expert.first_name} {slot.expert.last_name or ''}".strip()
            user_name = f"{user.first_name} {user.last_name or ''}".strip()
            text = (
                f"Новая запись на консультацию\n"
                f"Тема: <b>{slot.topic.name}</b>\n"
                f"Время: <b>{_fmt_time(slot.start_time)} - {_fmt_time(slot.end_time)}</b>\n"
                f"Пользователь: <b>{user_name}</b> (@{user.username or '-'})\n"
                f"Место встречи: <b>стойка информации на стенде Яндекса, 1 этаж</b>\n"
            )
            _send_telegram_message(slot.expert.telegram_id, text)
        except Exception:
            pass
        return JsonResponse({'success': True, 'id': slot.id})
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def consultations_cancel(request, slot_id):
    try:
        user, err = _get_user_by_init_data(request)
        if err:
            return err
        try:
            slot = ConsultationSlot.objects.select_related('expert', 'topic', 'booked_by').get(id=slot_id, booked_by=user)
        except ConsultationSlot.DoesNotExist:
            return JsonResponse({'error': 'Booking not found'}, status=404)
        # Notify expert before clearing booking
        try:
            user_name = f"{user.first_name} {user.last_name or ''}".strip()
            text = (
                f"Отмена записи на консультацию\n"
                f"Тема: <b>{slot.topic.name}</b>\n"
                f"Время: <b>{_fmt_time(slot.start_time)} - {_fmt_time(slot.end_time)}</b>\n"
                f"Пользователь: <b>{user_name}</b> (@{user.username or '-'})\n"
            )
            _send_telegram_message(slot.expert.telegram_id, text)
        except Exception:
            pass
        # Delete the slot entirely so the same expert/time can be booked again later
        slot.delete()
        return JsonResponse({'success': True})
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def consultations_my(request):
    try:
        user, err = _get_user_by_init_data(request)
        if err:
            return err
        qs = ConsultationSlot.objects.select_related('expert', 'topic').filter(booked_by=user).order_by('start_time')
        data = [{
            'id': s.id,
            'topic_id': s.topic.id,
            'topic': s.topic.name,
            'expert': f"{s.expert.first_name} {s.expert.last_name or ''}".strip(),
            'time': f"{_fmt_time(s.start_time)} - { _fmt_time(s.end_time)}",
            'meeting_location': 'стойка информации на стенде Яндекса, 1 этаж',
        } for s in qs]
        return JsonResponse({'success': True, 'consultations': data})
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def expert_schedule(request):
    try:
        expert, err = _get_user_by_init_data(request)
        if err:
            return err
        if not expert.is_expert:
            return JsonResponse({'error': 'Only experts allowed'}, status=403)
        qs = ConsultationSlot.objects.select_related('topic', 'booked_by').filter(expert=expert).order_by('start_time')
        data = [{
            'id': s.id,
            'topic': s.topic.name,
            'time': f"{_fmt_time(s.start_time)} - { _fmt_time(s.end_time)}",
            'booked': s.is_booked,
            'user': (
                {
                    'id': s.booked_by.id,
                    'first_name': s.booked_by.first_name,
                    'last_name': s.booked_by.last_name,
                    'username': s.booked_by.username,
                } if s.booked_by else None
            ),
            'meeting_location': 'стойка информации на стенде Яндекса, 1 этаж',
        } for s in qs]
        return JsonResponse({'success': True, 'schedule': data})
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def expert_set_location(request, slot_id):
    try:
        expert, err = _get_user_by_init_data(request)
        if err:
            return err
        if not expert.is_expert:
            return JsonResponse({'error': 'Only experts allowed'}, status=403)
        data = json.loads(request.body)
        location = data.get('location', '').strip()
        try:
            slot = ConsultationSlot.objects.get(id=slot_id, expert=expert)
        except ConsultationSlot.DoesNotExist:
            return JsonResponse({'error': 'Slot not found'}, status=404)
        slot.meeting_location = location or None
        slot.save()
        return JsonResponse({'success': True})
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)