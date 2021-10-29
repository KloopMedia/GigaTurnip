from django.db.models.signals import pre_save
from django.dispatch import receiver

from api.models import Task, Log


@receiver(pre_save, sender=Task)
def log_empty_task_response(sender, instance, **kwargs):
    #print(f"Signal received, INSTANCE RESPONSES: {instance.responses}")
    if instance.id is None or instance.responses:
        pass
    else:
        previous = Task.objects.get(id=instance.id)
        if previous.responses:
            reason = "wrong"
            if instance.responses is None:
                reason = "null"
            elif not instance.responses:
                reason = "empty"
            name = f"Task responses seem {reason}."
            #print(f"Signal received, EMPTY DETECTED")
            log = Log(
                name=name,
                description="Overwritten responses are inside JSON field",
                json=previous.responses,
                task=instance,
                campaign=instance.get_campaign(),
                stage=instance.stage,
                chain=instance.stage.chain,
                user=instance.assignee,
            )
            log.save()
