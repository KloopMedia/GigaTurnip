import json

import requests
from django.db.models import Q, F, Count

from api.models import Stage, TaskStage, ConditionalStage, Task, Case, TaskAward, DynamicJson


def process_completed_task(task):
    current_stage = task.stage

    # Check if task is a quiz, and if so, score and save result inside
    # responses as meta_quiz_score. If quiz threshold is set, quiz with
    # score lower than threshold will be opened and returned without
    # chain propagation.
    quiz = current_stage.get_quiz()
    if quiz and quiz.is_ready():
        quiz_score, incorrect_questions = quiz.check_score(task)
        task.responses["meta_quiz_score"] = quiz_score
        task.responses["meta_quiz_incorrect_questions"] = incorrect_questions
        task.save()
        if quiz.threshold is not None and quiz_score < quiz.threshold:
            task.complete = False
            task.reopened = True
            task.save()
            return task

    next_direct_task = task.get_direct_next()
    if next_direct_task is not None:
        next_direct_task.complete = False
        next_direct_task.reopened = True
        next_direct_task.save()
        if next_direct_task.assignee == task.assignee:
            return next_direct_task
        else:
            return None
    in_conditional_pingpong_stages = ConditionalStage.objects \
        .filter(out_stages=current_stage) \
        .filter(pingpong=True)
    if len(in_conditional_pingpong_stages) > 0:
        for stage in in_conditional_pingpong_stages:
            if evaluate_conditional_stage(stage, task):
                in_tasks = Task.objects.filter(out_tasks=task)
                for in_task in in_tasks:
                    in_task.complete = False
                    in_task.reopened = True
                    in_task.save()
            else:
                process_out_stages(current_stage, task)
    else:
        process_out_stages(current_stage, task)
    next_direct_task = task.get_direct_next()
    task_awards = TaskAward.objects.filter(task_stage_verified=task.stage)
    if next_direct_task is not None:
        if next_direct_task.assignee == task.assignee:
            return next_direct_task
        else:
            return None
    elif (next_direct_task is None) and task_awards:
        for task_award in task_awards:
            rank_record = task_award.connect_user_with_rank(task)
    return None


def process_out_stages(current_stage, task):
    out_task_stages = TaskStage.objects \
        .filter(in_stages=current_stage)
    out_conditional_stages = ConditionalStage.objects \
        .filter(in_stages=current_stage)
    for stage in out_conditional_stages:
        process_conditional(stage, task)
    for stage in out_task_stages:
        create_new_task(stage, task)


def process_webhook(stage, in_task):
    params = {}
    if stage.webhook_payload_field:
        params[stage.webhook_payload_field] = json.dumps(in_task.responses)
    else:
        params = in_task.responses
    if stage.webhook_params:
        params.update(stage.webhook_params)
    params["in_task_id"] = in_task.id
    response = requests.get(stage.webhook_address, params=params)
    if stage.webhook_response_field:
        response = response.json()[stage.webhook_response_field]
    else:
        response = response.json()
    return response


def create_new_task(stage, in_task):
    data = {"stage": stage, "case": in_task.case}
    if stage.webhook_address:
        # params = {}
        # if stage.webhook_payload_field:
        #     params[stage.webhook_payload_field] = json.dumps(in_task.responses)
        # else:
        #     params = in_task.responses
        # if stage.webhook_params:
        #     params.update(stage.webhook_params)
        # params["in_task_id"] = in_task.id
        # response = requests.get(stage.webhook_address, params=params)
        # if stage.webhook_response_field:
        #     response = response.json()[stage.webhook_response_field]
        # else:
        #     response = response.json()
        response = process_webhook(stage, in_task)
        data["responses"] = response
        data["complete"] = True
        new_task = Task.objects.create(**data)
        new_task.in_tasks.set([in_task])
        process_completed_task(new_task)
    elif stage.get_integration():
        if not (in_task.complete and in_task.stage.assign_user_by == "IN"):
            integration = stage.get_integration()
            (integrator_task, created) = integration.get_or_create_integrator_task(in_task)
            # integration_status = IntegrationStatus(
            #     integrated_task=in_task,
            #     integrator=integrator_task)
            # integration_status.save()
            if created:
                case = Case.objects.create()
                integrator_task.case = case
            if integrator_task.assignee is not None and \
                    in_task.stage.assign_user_by == "IN":
                in_task.assignee = integrator_task.assignee
                in_task.save()
            integrator_task.in_tasks.add(in_task)
            integrator_task.save()
    else:
        if stage.assign_user_by == "ST":
            if stage.assign_user_from_stage is not None:
                assignee_task = Task.objects \
                    .filter(stage=stage.assign_user_from_stage) \
                    .filter(case=in_task.case)
                data["assignee"] = assignee_task[0].assignee
        new_task = Task.objects.create(**data)
        new_task.in_tasks.set([in_task])
        if stage.copy_input:
            new_task.responses = in_task.responses
        webhook = stage.get_webhook()
        if webhook:
            webhook.trigger(new_task)
        for copy_field in stage.copy_fields.all():
            new_task.responses = copy_field.copy_response(new_task)
        new_task.save()
        if stage.assign_user_by == "IN":
            process_completed_task(new_task)
        if stage.assign_user_by == "AU":
            new_task.complete = True
            new_task.save()
            process_completed_task(new_task)


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
                    if out_task.stage.webhook_address:
                        response = process_webhook(out_task.stage, in_task)
                        out_task.responses = response
                        out_task.complete = True
                        out_task.save()
                        process_completed_task(out_task)
                    else:
                        out_task.complete = False
                        out_task.reopened = True
                        if stage.copy_input:
                            out_task.responses = update_responses(out_task.responses,
                                                                  in_task.responses)
                        for copy_field in stage.copy_fields.all():
                            out_task.responses = copy_field.copy_response(out_task)
                        out_task.save()
            else:
                create_new_task(stage, in_task)


def evaluate_conditional_stage(stage, task):
    """Checks each response
       Returns True if all responses exist and fit to the conditions
    """
    rules = stage.conditions
    rules = rules if rules else []
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


def update_responses(responses_to_update, responses):
    for k in responses.keys():
        responses_to_update[k] = responses.get(k)
    return responses_to_update


def process_updating_schema_answers(task_stage, responses):
    schema = task_stage.json_schema if task_stage.json_schema else '{}'
    schema = json.loads(schema)
    dynamic_properties = DynamicJson.objects.filter(task_stage=task_stage)
    if dynamic_properties and task_stage.json_schema and responses:
        for dynamic_json in dynamic_properties:
            schema = update_schema_dynamic_answers(dynamic_json, responses, schema)
        return schema
    else:
        return schema


def update_schema_dynamic_answers(dynamic_json, responses, schema):
    tasks = dynamic_json.task_stage.tasks.all()
    tasks = tasks.filter(complete=True, force_complete=False).order_by('updated_at')

    main_key = dynamic_json.dynamic_fields['main']
    main_filter = {'responses__' + main_key: responses[main_key]}

    foreign_fields = dynamic_json.dynamic_fields['foreign']
    foreign_fields = ['responses__' + i for i in foreign_fields]
    if not foreign_fields:
        parsing_fields = ['responses__' + main_key]
    else:
        parsing_fields = foreign_fields

    if foreign_fields:
        taken_values_info = tasks.filter(**main_filter)
    else:
        taken_values_info = tasks

    taken_values_info = taken_values_info.values(
                    *parsing_fields
                ).annotate(count=Count('pk')).order_by()
    unavailable = taken_values_info.filter(
        count__gte=dynamic_json.dynamic_fields['count']
    )

    new_schema = remove_unavailable_items_from_answers(schema, dynamic_json.dynamic_fields, unavailable)

    return new_schema


def remove_unavailable_items_from_answers(schema, dynamic_fields, unavailable):
    if dynamic_fields['foreign']:
        answers = dynamic_fields['foreign']
    else:
        answers = [dynamic_fields['main']]

    for i in answers:
        key = 'responses__' + i
        for answer in unavailable:
            idx = schema['properties'][i]['enum'].index(answer[key])
            del schema['properties'][i]['enum'][idx]
            if schema['properties'][i].get('enumNames'):
                del schema['properties'][i]['enumNames'][idx]

    return schema
