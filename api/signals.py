from django.db.models.signals import pre_save
from django.dispatch import receiver
from rest_framework import serializers

from api.models import Task, Log


class TaskDebugSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = '__all__'


@receiver(pre_save, sender=Task)
def log_empty_task_response(sender, instance, **kwargs):
    #print(f"Signal received, INSTANCE RESPONSES: {instance.responses}")
    if instance.id is None:
        pass
    else:
        previous = Task.objects.get(id=instance.id)
        data = {"previous": TaskDebugSerializer(previous).data,
                "current": TaskDebugSerializer(instance).data}
        # log = Log(
        #     name="Task edited",
        #     description="Overwritten responses are inside JSON field",
        #     json=data,
        #     task=instance,
        #     campaign=instance.get_campaign(),
        #     stage=instance.stage,
        #     chain=instance.stage.chain,
        #     user=instance.assignee,
        # )
        # log.save()
        if previous.responses and not instance.responses:
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
                json=data,
                task=instance,
                campaign=instance.get_campaign(),
                stage=instance.stage,
                chain=instance.stage.chain,
                user=instance.assignee,
            )
            log.save()
