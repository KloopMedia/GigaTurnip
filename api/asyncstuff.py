from django.db.models import Q

from api.models import Case, Stage, TaskStage, ConditionalStage, Task



def process_completed_task(task):
    current_stage = Stage.objects.get(id=task.stage.id)
    in_conditional_pingpong_stages = ConditionalStage.objects \
        .filter(out_stages=current_stage) \
        .filter(pingpong=True)
    if len(in_conditional_pingpong_stages) > 0:
        for stage in in_conditional_pingpong_stages:
            if evaluate_conditional_stage(stage, task):
                in_tasks = Task.objects.filter(out_tasks=task)
                for in_task in in_tasks:
                    in_task.complete = False
                    in_task.save()
        pass
    else:
        out_task_stages = TaskStage.objects \
            .filter(in_stages=current_stage)
        out_conditional_stages = ConditionalStage.objects \
            .filter(in_stages=current_stage) \
            .filter(Q(instance_of=ConditionalStage))
        for stage in out_task_stages:
            create_new_task(stage, task)


def create_new_task(stage, in_task):
    data = {"stage": stage, "case": in_task.case}
    if stage.assign_user_by == "ST":
        if stage.assign_user_from_stage is not None:
            assignee_task = Task.objects \
                .filter(stage=stage.assign_user_from_stage) \
                .filter(case=in_task.case)
            data["assignee"] = assignee_task[0].assignee
    new_task = Task.objects.create(**data)
    new_task.in_tasks.set([in_task])


def evaluate_conditional_stage(stage, task):
    return True


