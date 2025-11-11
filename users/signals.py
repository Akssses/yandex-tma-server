from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import TelegramUser
import os
import logging

logger = logging.getLogger(__name__)


def _open_or_create_worksheet():
    try:
        import gspread  # type: ignore
    except Exception as e:
        logger.warning("gspread is not installed: %s", e)
        return None

    sa_path = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE')
    spreadsheet_id = os.getenv('GOOGLE_SHEETS_SPREADSHEET_ID')
    worksheet_name = os.getenv('GOOGLE_SHEETS_WORKSHEET_NAME', 'Users')

    if not sa_path or not spreadsheet_id:
        logger.error("Google Sheets config missing: service_account=%s spreadsheet_id=%s", sa_path, spreadsheet_id)
        return None
    try:
        gc = gspread.service_account(filename=sa_path)
        sh = gc.open_by_key(spreadsheet_id)
        try:
            ws = sh.worksheet(worksheet_name)
        except gspread.exceptions.WorksheetNotFound:
            ws = sh.add_worksheet(title=worksheet_name, rows=1000, cols=20)
        return ws
    except Exception as e:
        logger.exception("Failed to open Google Sheet: %s", e)
        return None


def _user_to_row(u: TelegramUser):
    # expert name (if user has booked consultation)
    expert_name = ''
    try:
        slot = u.consultations.order_by('-start_time').first()
        if slot and slot.expert:
            expert_first = slot.expert.first_name or ''
            expert_last = slot.expert.last_name or ''
            expert_name = (expert_first + ' ' + expert_last).strip()
    except Exception:
        expert_name = ''

    return [
        u.first_name,
        u.last_name or '',
        u.workplace or '',
        u.position or '',
        f"@{u.username}" if u.username else '',
        u.email or '',
        'Да' if (u.vacancies_interest is True) else ('Нет' if (u.vacancies_interest is False) else ''),
        'Да' if u.has_completed_test() else 'Нет',
        'Да' if u.has_completed_quiz() else 'Нет',
        expert_name,
        '',  # оценка: поля нет
    ]


@receiver(post_save, sender=TelegramUser)
def append_new_user_to_sheet(sender, instance: TelegramUser, created: bool, **kwargs):
    if not created:
        return
    ws = _open_or_create_worksheet()
    if ws is None:
        return
    try:
        ws.append_row(_user_to_row(instance), value_input_option='RAW')
    except Exception as e:
        logger.exception("Failed to append row to Google Sheet: %s", e)


