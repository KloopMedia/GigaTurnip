import json

import requests
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
            else:
                process_out_stages(current_stage, task)
    else:
        process_out_stages(current_stage, task)


def process_out_stages(current_stage, task):
    out_task_stages = TaskStage.objects \
        .filter(in_stages=current_stage)
    out_conditional_stages = ConditionalStage.objects \
        .filter(in_stages=current_stage)
    for stage in out_conditional_stages:
        process_conditional(stage, task)
    for stage in out_task_stages:
        create_new_task(stage, task)


def create_new_task(stage, in_task):
    data = {"stage": stage, "case": in_task.case}
    if stage.webhook_address:
        params = {}
        if stage.webhook_payload_field:
            params[stage.webhook_payload_field] = json.dumps(in_task.responses)
        else:
            params = in_task.responses
        if stage.webhook_params:
            params.update(stage.webhook_params)
        response = requests.get(stage.webhook_address, params=params)
        if stage.webhook_response_field:
            response = response.json()[stage.webhook_response_field]
        else:
            response = response.json()
        data["responses"] = response
        data["complete"] = True
        new_task = Task.objects.create(**data)
        new_task.in_tasks.set([in_task])
        process_completed_task(new_task)
    else:
        if stage.assign_user_by == "ST":
            if stage.assign_user_from_stage is not None:
                assignee_task = Task.objects \
                    .filter(stage=stage.assign_user_from_stage) \
                    .filter(case=in_task.case)
                data["assignee"] = assignee_task[0].assignee
        new_task = Task.objects.create(**data)
        new_task.in_tasks.set([in_task])


def process_conditional(stage, in_task):
    if evaluate_conditional_stage(stage, in_task) and not stage.pingpong:
        process_out_stages(stage, in_task)
    elif stage.pingpong:
        out_task_stages = TaskStage.objects \
            .filter(in_stages=stage)
        for stage in out_task_stages:
            out_tasks = Task.objects.filter(in_tasks=in_task).filter(stage=stage)
            if len(out_tasks) > 0:
                for out_task in out_tasks:
                    out_task.complete = False
                    out_task.save()
            else:
                create_new_task(stage, in_task)


def evaluate_conditional_stage(stage, task):
    """Checks each response
       Returns True if all responses exist and fit to the conditions
    """
    rules = stage.conditions
    responses = task.responses
    results = list()

    if responses is None:
        return False

    for rule in rules:

        control_value = rule["value"]
        condition = rule["condition"]
        actual_value = get_value_from_dotted(rule["field"], responses)

        if condition == "==":
            results.append(control_value == actual_value)
        elif condition == "!=":
            results.append(control_value != actual_value)
        elif condition == ">":
            results.append(control_value > actual_value)
        elif condition == "<":
            results.append(control_value < actual_value)
        elif condition == ">=":
            results.append(control_value >= actual_value)
        elif condition == "<=":
            results.append(control_value <= actual_value)
        elif condition == "ARRAY-CONTAINS":
            results.append(control_value in actual_value)
        elif condition == "ARRAY-CONTAINS-NOT":
            results.append(control_value not in actual_value)

    return all(results)


def get_value_from_dotted(dotted_path, source_dict):
    """Turns dotted_path into regular dict keys and returns the value.
    """
    fields = dotted_path.split(".")
    result = source_dict
    for field in fields:
        try:
            result = result[field]
        except KeyError:
            return None
    return result


