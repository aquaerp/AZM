from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from workforce.models import JobTask

from .models import JobCard
from .realtime import publish_workshop_update


def _publish_after_commit(workshop_id, entity, record_id, job_card_id=None):
    transaction.on_commit(lambda: publish_workshop_update(workshop_id, entity, record_id, job_card_id))


@receiver(post_save, sender=JobCard)
def notify_job_card_update(sender, instance, **kwargs):
    _publish_after_commit(instance.workshop_id, "job_card", instance.pk, instance.pk)


@receiver(post_save, sender=JobTask)
def notify_task_update(sender, instance, **kwargs):
    _publish_after_commit(instance.workshop_id, "task", instance.pk, instance.job_card_id)
