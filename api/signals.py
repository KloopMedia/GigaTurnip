from django.db.models.signals import pre_save
from django.dispatch import receiver
from rest_framework import serializers

from api.models import Task, Log, TaskStage


class TaskDebugSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = '__all__'


class TaskStageDebugSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskStage
        fields = '__all__'


@receiver(pre_save, sender=Task)
def log_empty_task_response(sender, instance, **kwargs):
    # print(f"Signal received, INSTANCE RESPONSES: {instance.responses}")
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
            # print(f"Signal received, EMPTY DETECTED")
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


@receiver(pre_save, sender=TaskStage)
def log_task_stage_changing(sender, instance, **kwargs):
    if instance.id is None:
        pass
    else:
        previous = TaskStage.objects.get(id=instance.id)
        data = {"previous": TaskStageDebugSerializer(previous).data,
                "current": TaskStageDebugSerializer(instance).data, }
        differences = []
        for key, value in data['current'].items():
            current_value = data.get('previous').get(key)
            if value != current_value:
                difference = f"{key}: {current_value} -> {value}"
                differences.append(difference)
        if differences:
            name = "Task Stage was changed"
            description = "\n".join(differences)
            log = Log(
                name=name,
                description=description,
                json=data,
                campaign=previous.get_campaign(),
                stage=previous,
            )
            log.save()