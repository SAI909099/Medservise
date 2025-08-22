from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.models import Doctor, TurnNumber


# or wherever your TurnNumber model is

@receiver(post_save, sender=Doctor)
def create_turn_number(sender, instance, created, **kwargs):
    if created and not TurnNumber.objects.filter(doctor=instance).exists():
        existing_letters = TurnNumber.objects.values_list('letter', flat=True)
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            if letter not in existing_letters:
                TurnNumber.objects.create(doctor=instance, letter=letter)
                break
