"""
Management command to import consultations from consultations.json
"""
import json
import os
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from users.models import TelegramUser, ConsultationTopic, TopicTimeSlot


class Command(BaseCommand):
    help = 'Import consultations from consultations.json file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='consultations.json',
            help='Path to consultations.json file (relative to server directory)',
        )

    def handle(self, *args, **options):
        file_path = options['file']
        if not os.path.isabs(file_path):
            # Relative to server directory
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            file_path = os.path.join(base_dir, file_path)
        
        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f'File not found: {file_path}'))
            return

        self.stdout.write(f'Reading consultations from: {file_path}')
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Map Russian month names to month numbers
        month_map = {
            'ноября': 11,
            'декабря': 12,
            'января': 1,
            'февраля': 2,
            'марта': 3,
            'апреля': 4,
            'мая': 5,
            'июня': 6,
            'июля': 7,
            'августа': 8,
            'сентября': 9,
            'октября': 10,
        }

        # Step 1: Extract unique experts
        experts_dict = {}
        for date_str, time_slots in data.items():
            for time_slot, experts_list in time_slots.items():
                for expert_data in experts_list:
                    username = expert_data.get('username', '').lstrip('@')
                    if not username:
                        continue
                    if username not in experts_dict:
                        experts_dict[username] = {
                            'first_name': expert_data.get('first_name', ''),
                            'last_name': expert_data.get('last_name', ''),
                            'position': expert_data.get('position_full', ''),
                            'username': username,
                        }

        self.stdout.write(f'Found {len(experts_dict)} unique experts')

        # Step 2: Extract unique topics
        topics_set = set()
        for date_str, time_slots in data.items():
            for time_slot, experts_list in time_slots.items():
                for expert_data in experts_list:
                    topics = expert_data.get('topics', [])
                    topics_set.update(topics)

        self.stdout.write(f'Found {len(topics_set)} unique topics: {", ".join(sorted(topics_set))}')

        with transaction.atomic():
            # Step 3: Create/update experts
            created_experts = 0
            updated_experts = 0
            for username, expert_info in experts_dict.items():
                user, created = TelegramUser.objects.get_or_create(
                    username=username,
                    defaults={
                        'first_name': expert_info['first_name'],
                        'last_name': expert_info['last_name'],
                        'position': expert_info['position'],
                        'is_expert': True,
                        'data_processing_agreement': True,
                    }
                )
                if created:
                    created_experts += 1
                else:
                    # Update existing user
                    user.first_name = expert_info['first_name']
                    user.last_name = expert_info['last_name']
                    user.position = expert_info['position']
                    user.is_expert = True
                    user.save()
                    updated_experts += 1

            self.stdout.write(
                self.style.SUCCESS(
                    f'Experts: {created_experts} created, {updated_experts} updated'
                )
            )

            # Step 4: Create topics
            topics_dict = {}
            for topic_name in topics_set:
                topic, created = ConsultationTopic.objects.get_or_create(name=topic_name)
                topics_dict[topic_name] = topic
                if created:
                    self.stdout.write(f'Created topic: {topic_name}')

            # Step 5: Parse dates and create time slots
            slots_created = 0
            slots_updated = 0

            for date_str, time_slots in data.items():
                # Parse date: "20 ноября" -> 2025-11-20
                parts = date_str.strip().split()
                if len(parts) != 2:
                    self.stdout.write(self.style.WARNING(f'Invalid date format: {date_str}'))
                    continue
                
                day = int(parts[0])
                month_name = parts[1].lower()
                month = month_map.get(month_name)
                if not month:
                    self.stdout.write(self.style.WARNING(f'Unknown month: {month_name}'))
                    continue

                # Assume year 2025 (or current year if needed)
                year = 2025
                date_obj = datetime(year, month, day).date()

                for time_range, experts_list in time_slots.items():
                    # Parse time: "11:00-11:30" -> start_time and end_time
                    if '-' not in time_range:
                        self.stdout.write(self.style.WARNING(f'Invalid time format: {time_range}'))
                        continue
                    
                    start_str, end_str = time_range.split('-', 1)
                    try:
                        start_hour, start_min = map(int, start_str.split(':'))
                        end_hour, end_min = map(int, end_str.split(':'))
                        start_datetime = timezone.make_aware(
                            datetime.combine(date_obj, datetime.min.time().replace(hour=start_hour, minute=start_min))
                        )
                        end_datetime = timezone.make_aware(
                            datetime.combine(date_obj, datetime.min.time().replace(hour=end_hour, minute=end_min))
                        )
                    except ValueError:
                        self.stdout.write(self.style.WARNING(f'Invalid time format: {time_range}'))
                        continue

                    # Group experts by topics
                    experts_by_topic = {}
                    for expert_data in experts_list:
                        username = expert_data.get('username', '').lstrip('@')
                        if not username:
                            continue
                        try:
                            expert_user = TelegramUser.objects.get(username=username, is_expert=True)
                        except TelegramUser.DoesNotExist:
                            self.stdout.write(self.style.WARNING(f'Expert not found: {username}'))
                            continue
                        
                        topics = expert_data.get('topics', [])
                        for topic_name in topics:
                            if topic_name not in experts_by_topic:
                                experts_by_topic[topic_name] = []
                            if expert_user not in experts_by_topic[topic_name]:
                                experts_by_topic[topic_name].append(expert_user)

                    # Create TopicTimeSlot for each topic
                    for topic_name, experts in experts_by_topic.items():
                        topic = topics_dict[topic_name]
                        
                        # Check if slot already exists
                        slot, created = TopicTimeSlot.objects.get_or_create(
                            topic=topic,
                            start_time=start_datetime,
                            end_time=end_datetime,
                        )
                        
                        # Add experts to the slot
                        for expert in experts:
                            slot.experts.add(expert)
                        
                        if created:
                            slots_created += 1
                        else:
                            slots_updated += 1

            self.stdout.write(
                self.style.SUCCESS(
                    f'Time slots: {slots_created} created, {slots_updated} updated'
                )
            )

        self.stdout.write(self.style.SUCCESS('Import completed successfully!'))

