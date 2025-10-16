from django.db import models
import uuid

# Create your models here.

class TelegramUser(models.Model):
    telegram_id = models.BigIntegerField(unique=True)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    username = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    workplace = models.CharField(max_length=255, blank=True, null=True)
    position = models.CharField(max_length=255, blank=True, null=True)
    data_processing_agreement = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    auth_token = models.CharField(max_length=64, blank=True, null=True, unique=True)
    is_expert = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.first_name} {self.last_name} (@{self.username})"

    def generate_auth_token(self):
        self.auth_token = uuid.uuid4().hex
        self.save()
        return self.auth_token

    def has_completed_test(self):
        return hasattr(self, 'testresult')


class TestResult(models.Model):
    ANALYST_TYPES = [
        ('EP', 'Аналитик-решала'),
        ('EJ', 'Аналитик-суетолог'),
        ('IP', 'Аналитик-вайбик'),
        ('IJ', 'Аналитик-стратег'),
    ]
    
    user = models.OneToOneField(TelegramUser, on_delete=models.CASCADE, related_name='testresult')
    analyst_type = models.CharField(max_length=2, choices=ANALYST_TYPES)
    analyst_name = models.CharField(max_length=255)
    animal = models.CharField(max_length=255)
    description = models.TextField()
    tags = models.JSONField(default=list)
    ei_score = models.IntegerField()
    pj_score = models.IntegerField()
    gift_received = models.BooleanField(default=False)
    completed_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.first_name} - {self.analyst_name}"


class Workshop(models.Model):
    title = models.CharField(max_length=255)
    tag = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.start_time} - {self.end_time})"


class WorkshopRegistration(models.Model):
    user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE, related_name='workshop_registrations')
    workshop = models.ForeignKey(Workshop, on_delete=models.CASCADE, related_name='registrations')
    registered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'workshop')

    def __str__(self):
        return f"{self.user} -> {self.workshop}"
