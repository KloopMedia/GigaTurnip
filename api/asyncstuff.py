import json

import requests
from django.db.models import Q, F, Count
from rest_framework import status
import math
from api.api_exceptions import CustomApiException
from api.models import Stage, TaskStage, ConditionalStage, Task, Case, TaskAward, PreviousManual, RankLimit, \
    AutoNotification
from api.utils import find_user, value_from_json, reopen_task, get_ranks_where_user_have_parent_ranks, \
    connect_user_with_ranks


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
    detecting_auto_notifications(current_stage, task)
    next_direct_task = task.get_next_demo()
    task_awards = TaskAward.objects.filter(task_stage_verified=task.stage)
    for task_award in task_awards:
        rank_record = task_award.connect_user_with_rank(task)
        if rank_record:
            ranks = get_ranks_where_user_have_parent_ranks(rank_record.user, rank_record.rank)
            connect_user_with_ranks(rank_record.user, ranks)
    if next_direct_task is not None:
        if next_direct_task.assignee == task.assignee:
            return next_direct_task
        else:
            return None
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
        params = in_task.responses if in_task.responses else {}
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
    new_task = None
    if stage.webhook_address:
        for copy_field in stage.copy_fields.all():
            in_task.responses = copy_field.copy_response(in_task)
        response = process_webhook(stage, in_task)
        data["responses"] = response
        data["complete"] = True
        new_task = Task.objects.create(**data)
        new_task.in_tasks.set([in_task])
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
        if stage.assign_user_by == TaskStage.STAGE:
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
        if webhook and webhook.is_triggered:
            webhook.trigger(new_task)
        for copy_field in stage.copy_fields.all():
            new_task.responses = copy_field.copy_response(new_task)
        new_task.save()
        if stage.assign_user_by == TaskStage.AUTO_COMPLETE:
            new_task.complete = True
            new_task.save()
        if stage.assign_user_by == TaskStage.PREVIOUS_MANUAL:
            assign_by_previous_manual(stage, new_task, in_task)
    if stage.webhook_address or stage.assign_user_by in [TaskStage.AUTO_COMPLETE, TaskStage.INTEGRATOR]:
        task_award = stage.task_stage_verified.all()
        if not task_award:
            process_completed_task(new_task)
        if task_award:
            rank_record = task_award[0].connect_user_with_rank(in_task)
            if rank_record:
                ranks = get_ranks_where_user_have_parent_ranks(rank_record.user, rank_record.rank)
                connect_user_with_ranks(rank_record.user, ranks)
            if task_award[0].stop_chain and rank_record:
                pass
            else:
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
                        for copy_field in stage.copy_fields.all():
                            in_task.responses = copy_field.copy_response(in_task)
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
                            out_task.responses.update(copy_field.copy_response(out_task))
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
        js_schema = json.loads(task.stage.json_schema) if task.stage.json_schema else {}
        type_to_convert = get_value_from_dotted('properties.' + rule["field"], js_schema)

        if type_to_convert:
            type_to_convert = type_to_convert.get('type')
            if type_to_convert == "string":
                control_value = str(control_value)
                actual_value = str(actual_value)
            elif type_to_convert == "integer":
                control_value = int(control_value)
                actual_value = int(actual_value)
            elif type_to_convert == "number":
                control_value = float(control_value)
                actual_value = float(actual_value)
        else:
            control_value = str(control_value)
            actual_value = str(actual_value)

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


def assign_by_previous_manual(stage, new_task, in_task):
    previous_manual_to_assign = stage.get_previous_manual_to_assign()
    task_with_email = Task.objects.filter(case=in_task.case,
                                          stage=previous_manual_to_assign.task_stage_email
                                          ).order_by('updated_at')[0]
    value = value_from_json(previous_manual_to_assign.field, task_with_email.responses)
    if previous_manual_to_assign.is_id:
        user = find_user(id=int(value))
    else:
        user = find_user(email=value)

    if not user:
        reopen_task(task_with_email)
        new_task.delete()
        raise CustomApiException(400, f"User {value} doesn't exist")

    if not user.ranks.filter(ranklimit__in=RankLimit.objects.filter(stage__chain__campaign_id=stage.get_campaign())):
        reopen_task(task_with_email)
        new_task.delete()
        raise CustomApiException(400, f"User is not in the campaign.")

    new_task.assignee = user
    new_task.save()


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


def process_updating_schema_answers(task_stage, responses={}):
    schema = task_stage.json_schema if task_stage.json_schema else '{}'
    schema = json.loads(schema)
    dynamic_properties = task_stage.dynamic_jsons.all()
    if dynamic_properties and task_stage.json_schema:
        for dynamic_json in dynamic_properties:
            if not dynamic_json.webhook:
                schema = update_schema_dynamic_answers(dynamic_json, responses, schema)
            else:
                schema = update_schema_dynamic_answers_webhook(dynamic_json, schema, responses)
        return schema
    else:
        return schema


def update_schema_dynamic_answers(dynamic_json, responses, schema):
    tasks = dynamic_json.task_stage.tasks.all()
    tasks = tasks.filter(complete=True, force_complete=False).order_by('updated_at')

    main_key = dynamic_json.dynamic_fields['main']
    foreign_fields = dynamic_json.dynamic_fields['foreign']
    count = dynamic_json.dynamic_fields['count']

    to_delete = {'responses__' + main_key: []}
    available_by_main = [len(schema['properties'][main_key]['enum'])]
    all_fields = [main_key] + foreign_fields

    if foreign_fields:
        for i in foreign_fields:
            key = 'responses__' + i
            to_delete[key] = []
            available_by_main.append(len(schema['properties'][i]['enum']))

    total_available_answers = math.prod(available_by_main)

    filtered_by_main = tasks.values('responses__' + main_key).annotate(count=Count('pk')).order_by()
    for i in filtered_by_main:
        if i['count'] > total_available_answers or (not foreign_fields and count >= i['count']):
            to_delete['responses__' + main_key].append(i['responses__' + main_key])

    if not foreign_fields:
        schema = remove_unavailable_enums_from_answers(schema, to_delete)
        return schema

    if main_key in responses.keys():
        filtered_by_main = filtered_by_main.filter(**{'responses__' + main_key: responses[main_key]})
        for idx, key in enumerate(foreign_fields):

            if key in responses.keys() or key == all_fields[-1]:
                responses_key = 'responses__' + key
                available = filtered_by_main.values(responses_key).annotate(count=Count('pk'))

                arr_fixed_position = available_by_main[idx + 2:]
                for i in available:
                    if ((len(foreign_fields) >= idx + 2) and i['count'] > math.prod(arr_fixed_position)) or \
                            (len(foreign_fields) < idx + 2 and i['count'] >= count):
                        to_delete[responses_key].append(i[responses_key])
                if len(foreign_fields) >= idx + 2:
                    filtered_by_main = available.filter(**{responses_key: responses[key]}).annotate(count=Count('pk'))

    schema = remove_unavailable_enums_from_answers(schema, to_delete)
    schema = remove_answers_in_turn(schema, all_fields, responses)
    return schema


def update_schema_dynamic_answers_webhook(dynamic_json, schema, responses):
    response = dynamic_json.webhook.post({
        "fields": dynamic_json.dynamic_fields.get("foreign"),
        "schema": schema,
        "responses": responses})

    response_text = json.loads(response.text)
    if response_text.get('status') == status.HTTP_200_OK:
        return response_text.get('schema')
    else:
        raise CustomApiException(status.HTTP_500_INTERNAL_SERVER_ERROR, 'Exception on the webhook side')


def remove_unavailable_enums_from_answers(schema, to_delete):
    for key, answers in to_delete.items():
        k = key.replace('responses__', '')
        for a in answers:
            idx = schema['properties'][k]['enum'].index(a)
            del schema['properties'][k]['enum'][idx]
            if schema['properties'][k].get('enumNames'):
                del schema['properties'][k]['enumNames'][idx]

    return schema


def remove_answers_in_turn(schema, fields, responses):
    while fields[1:]:
        field = fields.pop(0)
        if field not in responses.keys():
            for i in fields:
                del schema['properties'][i]
                # if schema['properties'][i].get('enumNames'):
                #     schema['properties'][i]['enumNames'] = []
            return schema
    return schema


def detecting_auto_notifications(stage, task):
    if task.out_tasks.all():
        out_task = task.out_tasks.all()[0]
        if out_task.complete is False and out_task.reopened is False:
            send_auto_notifications(stage, task.case, {'go': AutoNotification.FORWARD})
    elif task.in_tasks.all():
        previous_task = task.in_tasks.all()[0]
        if previous_task.complete is False and previous_task.reopened is True:
            send_auto_notifications(stage, task.case, {'go': AutoNotification.BACKWARD})
        else:
            send_auto_notifications(stage, task.case, {'go': AutoNotification.LAST_ONE})
    elif not stage.in_stages.count():
        in_tasks, out_tasks = task.in_tasks.all(), task.out_tasks.all()
        if (not in_tasks or in_tasks and in_tasks[0].complete) and task.complete and not out_tasks:
            send_auto_notifications(stage, task.case, {'go': AutoNotification.LAST_ONE})


def send_auto_notifications(trigger, case, filters=None):
    for auto_notification in trigger.auto_notification_trigger_stages.filter(**filters):
        user = case.tasks.get(stage=auto_notification.recipient_stage).assignee
        auto_notification.create_notification(user)