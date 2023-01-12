import json
import sys
import traceback

from django.utils import timezone
import requests
from django.db.models import Q, F, Count
from rest_framework import status
import math
from api.api_exceptions import CustomApiException
from api.constans import TaskStageConstants, AutoNotificationConstants, FieldsJsonConstants, ErrorConstants, \
    ConditionalStageConstants
from api.models import Stage, TaskStage, ConditionalStage, Task, Case, TaskAward, PreviousManual, RankLimit, \
    AutoNotification, DatetimeSort, ErrorItem
from api.utils import find_user, value_from_json, reopen_task, get_ranks_where_user_have_parent_ranks, \
    connect_user_with_ranks, give_task_awards, process_auto_completed_task, get_conditional_limit_count


def evaluate_quiz(quiz, task):
    if quiz and quiz.is_ready():
        quiz_score, incorrect_questions = quiz.check_score(task)
        task.responses[FieldsJsonConstants.META_QUIZ_SCORE] = quiz_score
        task.responses[FieldsJsonConstants.META_QUIZ_INCORRECT_QUESTIONS] = incorrect_questions
        task.save()
        if quiz.threshold is not None and quiz_score < quiz.threshold:
            task.complete = False
            task.reopened = True
            task.save()
            return task


def get_next_direct_task(next_direct_task, task):
    if next_direct_task is not None:
        next_direct_task.complete = False
        next_direct_task.reopened = True
        next_direct_task.save()
        if next_direct_task.assignee == task.assignee:
            return next_direct_task
        else:
            return None


def process_on_chain(current_stage, task):
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


def process_completed_task(task):
    current_stage = task.stage

    # Check if task is a quiz, and if so, score and save result inside
    # responses as meta_quiz_score. If quiz threshold is set, quiz with
    # score lower than threshold will be opened and returned without
    # chain propagation.
    quiz_evaluated_task = current_stage.get_quiz()
    if quiz_evaluated_task:
        quiz_evaluated_task = evaluate_quiz(quiz_evaluated_task, task)
        if quiz_evaluated_task:
            return quiz_evaluated_task
        else:
            del quiz_evaluated_task

    next_direct_task = task.get_direct_next()
    if next_direct_task is not None:
        return get_next_direct_task(next_direct_task, task)

    process_on_chain(current_stage, task)
    detecting_auto_notifications(current_stage, task)

    give_task_awards(current_stage, task)

    next_direct_task = task.get_next_demo()
    if next_direct_task is not None:
        if next_direct_task.assignee == task.assignee:
            return next_direct_task
    return None


def process_out_stages(current_stage, task):
    out_task_stages = TaskStage.objects \
        .filter(in_stages=current_stage)
    out_conditional_stages = ConditionalStage.objects \
        .filter(in_stages=current_stage).exclude(
        conditional_limit__isnull=False
    )
    out_conditional_limit_stages = ConditionalStage.objects.filter(
        in_stages=current_stage,
        conditional_limit__isnull=False
    ).order_by('conditional_limit__order', 'conditional_limit__created_at')
    for stage in out_conditional_stages:
        process_conditional(stage, task)
    for stage in out_conditional_limit_stages:
        is_conditional_limit_created = process_conditional_limit(stage, task)
        if is_conditional_limit_created:
            break
    for stage in out_task_stages:
        create_new_task(stage, task)


def process_conditional_limit(stage, in_task):
    if evaluate_conditional_stage(stage, in_task, is_limited=True):
        process_out_stages(stage, in_task)
        return True
    return False

def send_webhook_request(stage, in_task):
    params = {}
    if stage.webhook_payload_field:
        params[stage.webhook_payload_field] = json.dumps(in_task.responses)
    else:
        params = in_task.responses if in_task.responses else {}
    if stage.webhook_params:
        params.update(stage.webhook_params)
    params["in_task_id"] = in_task.id
    response = requests.get(stage.webhook_address, params=params)
    if response:
        if stage.webhook_response_field:
            response = response.json()[stage.webhook_response_field]
        else:
            response = response.json()
        return response
    else:
        stage.generate_error(
            type(KeyError),
            "Error on the webhook side: {0}".format(stage.webhook),
            tb_info=traceback.format_exc(),
            data=f"{params}\nStage: {stage}"
        )
        raise CustomApiException(503,
                                 "Service can't handle this request due to unforeseen behaviour of another service.")


def process_webhook(stage, in_task, data=None):
    data = data if data else dict()
    data['stage'], data['case'] = stage, in_task.case
    response = send_webhook_request(stage, in_task)
    data["responses"] = response
    data["complete"] = True
    new_task = Task.objects.create(**data)
    new_task.in_tasks.set([in_task])
    return new_task


def process_integration(stage, in_task):
    if not (in_task.complete and in_task.stage.assign_user_by == TaskStageConstants.INTEGRATOR):
        integration = stage.get_integration()
        (integrator_task, created) = integration.get_or_create_integrator_task(in_task)
        if created:
            case = Case.objects.create()
            integrator_task.case = case
        if integrator_task.assignee is not None and \
                in_task.stage.assign_user_by == TaskStageConstants.INTEGRATOR:
            in_task.assignee = integrator_task.assignee
            in_task.save()
        integrator_task.in_tasks.add(in_task)
        integrator_task.save()
        return in_task


def process_stage_assign_by_ST(stage, data, in_task):
    if stage.assign_user_by == TaskStageConstants.STAGE:
        if stage.assign_user_from_stage is not None:
            assignee_task = Task.objects \
                .filter(stage=stage.assign_user_from_stage) \
                .filter(case=in_task.case)
            data["assignee"] = assignee_task[0].assignee
    new_task = Task.objects.create(**data)
    new_task.in_tasks.set([in_task])
    return new_task


def trigger_on_copy_input(stage, new_task, in_task):
    if stage.copy_input:
        new_task.responses = in_task.responses
    return new_task


def trigger_on_webhook(stage, new_task):
    webhook = stage.get_webhook()
    if webhook and webhook.is_triggered:
        webhook.trigger(new_task)


def set_copied_fields(stage, new_task, responses=None):
    responses = responses if responses else {}
    for copy_field in stage.copy_fields.all():
        responses.update(copy_field.copy_response(new_task))

    if new_task.responses:
        new_task.responses.update(responses)
    else:
        new_task.responses = responses

    new_task.save()

    return new_task


def process_previous_manual_assign(stage, new_task, in_task):
    if stage.assign_user_by == TaskStageConstants.PREVIOUS_MANUAL:
        new_task = assign_by_previous_manual(stage, new_task, in_task)
    return new_task


def process_create_new_task_based_and_stage_assign(stage, new_task, in_task):
    if stage.webhook_address or stage.assign_user_by in [TaskStageConstants.AUTO_COMPLETE, TaskStageConstants.INTEGRATOR]:
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


def create_new_task(stage, in_task):
    data = {"stage": stage, "case": in_task.case}
    new_task = None
    if stage.webhook_address:
        for copy_field in stage.copy_fields.all():
            in_task.responses = copy_field.copy_response(in_task)
        new_task = process_webhook(stage, in_task, data)
    elif stage.get_integration():
        in_task = process_integration(stage, in_task)
    else:
        new_task = process_stage_assign_by_ST(stage, data, in_task)
        new_task = trigger_on_copy_input(stage, new_task, in_task)
        trigger_on_webhook(stage, new_task)
        set_period(stage, new_task)
        new_task = set_copied_fields(stage, new_task)
        process_auto_completed_task(stage, new_task)
        new_task = process_previous_manual_assign(stage, new_task, in_task)

    process_create_new_task_based_and_stage_assign(stage, new_task, in_task)


def set_period(stage, new_task):
    datetime_task = DatetimeSort.objects.filter(stage_id=stage.id)
    if datetime_task:
        datetime_task = datetime_task[0]
        if datetime_task.how_much and datetime_task.after_how_much:
            start_period = timezone.now() + \
                           timezone.timedelta(hours=datetime_task.after_how_much)
            end_period = start_period + timezone.timedelta(hours=datetime_task.how_much)
            new_task.start_period = start_period
            new_task.end_period = end_period


def process_conditional(stage, in_task):
    if evaluate_conditional_stage(stage, in_task) and not stage.pingpong:
        process_out_stages(stage, in_task)
    elif stage.pingpong:
        out_task_stages = TaskStage.objects \
            .filter(in_stages=stage)
        for stage in out_task_stages:
            out_tasks = in_task.out_tasks.filter(stage=stage)
            if len(out_tasks) > 0:
                for out_task in out_tasks:
                    if out_task.stage.webhook_address:
                        for copy_field in stage.copy_fields.all():
                            in_task.responses = copy_field.copy_response(in_task)
                        response = send_webhook_request(out_task.stage, in_task)
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


def evaluate_conditional_stage(stage, task, is_limited=False):
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
        control_value = rule.get("value")
        condition = rule.get("condition")
        type_ = rule.get("type") if rule.get("type") else "string"

        if not ConditionalStageConstants.SUPPORTED_TYPES.get(type_):
            stage.generate_error(
                exc_type=ValueError,
                details=f"Invalid type {type_} provided on conditional stage {stage.id}",
                tb=traceback.format_tb,
                data=f"{rules}\n{rule}"
            )
            raise CustomApiException(status.HTTP_400_BAD_REQUEST,
                                     f'{ErrorConstants.UNSUPPORTED_TYPE % type_} {ErrorConstants.SEND_TO_MODERATORS}')

        actual_value = None
        if not is_limited:
            actual_value = get_value_from_dotted(rule["field"], responses)
        elif is_limited:
            actual_value = get_conditional_limit_count(stage, rule)

        try:
            control_value = ConditionalStageConstants.SUPPORTED_TYPES.get(type_)(control_value)
            f = ConditionalStageConstants.OPERATORS.get(condition)
            results.append(f(control_value, actual_value))
        except Exception as e:
            exc_type, value, tb = sys.exc_info()
            stage.generate_error(
                exc_type=exc_type,
                details=f"Invalid conditions in conditional stage {stage.id}",
                tb=tb, tb_info=traceback.format_exc(),
                data=json.dumps({"responses": responses, "conditions": rules})
                )
            raise CustomApiException(status.HTTP_400_BAD_REQUEST,
                                     f'{ErrorConstants.UNSUPPORTED_TYPE % type_} {ErrorConstants.SEND_TO_MODERATORS}')

    return all(results)


def evaluate_conditional_logic_stage(stage: ConditionalStage, task: Task):
    rules = stage.conditions
    rules = rules if rules else []
    responses = task.responses
    results = list()

    if responses is None:
        return False

    for rule in rules:
        control_value = rule.get("value")
        condition = rule.get("condition")
        actual_value = stage.out_stages.get().tasks.count()

        f = ConditionalStageConstants.OPERATORS.get(condition)
        results.append(f(control_value, actual_value))

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
        raise CustomApiException(status.HTTP_400_BAD_REQUEST, ErrorConstants.ENTITY_DOESNT_EXIST % ('User', value))

    if not user.ranks.filter(ranklimit__in=RankLimit.objects.filter(stage__chain__campaign_id=stage.get_campaign())):
        reopen_task(task_with_email)
        new_task.delete()
        raise CustomApiException(status.HTTP_400_BAD_REQUEST, ErrorConstants.ENTITY_IS_NOT_IN_CAMPAIGN % 'User')

    new_task.assignee = user
    new_task.save()

    return new_task


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


def process_updating_schema_answers(task_stage, case=None, responses=dict()):
    if case:
        case = Case.objects.get(id=case)

    schema = json.loads(task_stage.get_json_schema())
    dynamic_properties = task_stage.dynamic_jsons_target.all()

    if dynamic_properties and task_stage.json_schema:
        for dynamic_json in dynamic_properties:
            previous_responses = {}
            if not case and dynamic_json.source:
                raise CustomApiException(
                    status.HTTP_400_BAD_REQUEST,
                    "You may not update this task until you haven't pass task id in attributes query. "
                    + ErrorConstants.SEND_TO_MODERATORS
                )

            if case and dynamic_json.source:
                previous_tasks = case.tasks.filter(stage_id=dynamic_json.source.id)
                previous_responses = previous_tasks[0].responses if previous_tasks.count() else dict()

            kwargs = {"dynamic_json": dynamic_json, "schema": schema, "responses": responses}
            if not dynamic_json.webhook and not dynamic_json.obtain_options_from_stage:
                kwargs['previous_responses'] = previous_responses
                schema = update_schema_dynamic_answers(**kwargs)
            elif dynamic_json.webhook and not dynamic_json.obtain_options_from_stage:
                schema = update_schema_dynamic_answers_webhook(**kwargs)
            else:
                schema = dynamic_answers_obtain_options(dynamic_json, schema)
        return schema
    else:
        return schema


def update_schema_dynamic_answers(dynamic_json, schema, responses=dict(), previous_responses=dict()):
    main_key, foreign_fields, constants_values, count = get_dynamic_dict_fields(dynamic_json.dynamic_fields)

    to_delete = dict()
    all_fields = [] + foreign_fields
    available_by_main = []

    by_main_filter = 'responses__'
    c = 'pk'
    if dynamic_json.source:
        available_by_main.append(len(json.loads(dynamic_json.source.json_schema)['properties'][main_key]['enum']))
        by_main_filter = 'in_tasks__' + by_main_filter
        c = 'in_tasks'
    elif not dynamic_json.source:
        all_fields = [main_key] + all_fields
        to_delete = {'responses__' + main_key: []}
        available_by_main.append(len(schema['properties'][main_key]['enum']))

    tasks = dynamic_json.target.tasks.filter(
        complete=True,
        force_complete=False
    )

    if foreign_fields:
        for i in foreign_fields:
            to_delete['responses__' + i] = []
            available_by_main.append(len(schema['properties'][i]['enum']))

    total_available_answers = math.prod(available_by_main)
    filtered_by_main = tasks.values(
        **{'responses__'+main_key: F(by_main_filter + main_key)}
    ).annotate(count=Count(c)).order_by()

    for i in filtered_by_main:
        if i['count'] > total_available_answers or (not foreign_fields and count >= i['count']):
            to_delete['responses__' + main_key].append(i['responses__' + main_key])

    if not foreign_fields:
        schema = remove_unavailable_enums_from_answers(schema, to_delete)
        return schema

    if main_key in responses.keys() or main_key in previous_responses.keys():
        if main_key in responses.keys():
            searched_main = responses[main_key]
        else:
            searched_main = previous_responses[main_key]
        filtered_by_main = filtered_by_main.filter(**{'responses__' + main_key: searched_main})

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

    to_delete = remove_constants_vals(constants_values, to_delete) if constants_values else to_delete
    schema = remove_unavailable_enums_from_answers(schema, to_delete)
    schema = remove_answers_in_turn(schema, all_fields, responses)
    return schema


def dynamic_answers_obtain_options(dynamic_json, schema):
    main_key, foreign_fields, constants_values, count = get_dynamic_dict_fields(dynamic_json.dynamic_fields)
    all_options = list(dynamic_json.source.tasks.filter(complete=True, assignee__isnull=False).
                       exclude(**{'responses__' + main_key: None}).
                       values_list(
        'responses__' + main_key, flat=True
    ).order_by().distinct()
                       )
    for field in foreign_fields:
        previous_answers = schema['properties'][field].get('enum', [])
        result_arr = list(set(previous_answers + all_options))
        result_arr.sort()
        schema['properties'][field]['enum'] = result_arr
        if schema['properties'][field].get('enumNames', []):
            previous_answers = schema['properties'][field].get('enumNames', [])
            result_arr = list(set(previous_answers + all_options))
            result_arr.sort()
            schema['properties'][field]['enumNames'] = result_arr

    return schema


def get_dynamic_dict_fields(dynamic_fields):
    main_key = dynamic_fields.get('main')
    foreign_fields = dynamic_fields.get('foreign')
    constants_values = dynamic_fields.get('constants', dict())
    count = dynamic_fields.get('count')
    return main_key, foreign_fields, constants_values, count


def update_schema_dynamic_answers_webhook(dynamic_json, schema, responses):
    response = dynamic_json.webhook.post({
        "fields": dynamic_json.dynamic_fields.get("foreign"),
        "schema": schema,
        "responses": responses})

    if response.status_code == status.HTTP_200_OK:
        response_text = json.loads(response.text)
        updated_schema = response_text.get('schema') or schema
        return updated_schema
    else:
        raise CustomApiException(status.HTTP_500_INTERNAL_SERVER_ERROR, 'Exception on the webhook side')


def remove_unavailable_enums_from_answers(schema, to_delete):
    for key, answers in to_delete.items():
        k = key.replace('responses__', '')
        for a in answers:
            idx = schema['properties'][k]['enum'].index(a) if a in schema['properties'][k]['enum'] else None
            if idx is not None:
                del schema['properties'][k]['enum'][idx]
                if schema['properties'][k].get('enumNames'):
                    del schema['properties'][k]['enumNames'][idx]

    return schema


def remove_constants_vals(constants_vals, to_delete):
    for key, constants in constants_vals.get('foreign', {}).items():
        for c in constants:
            if c in to_delete.get('responses__'+key, []):
                idx = to_delete['responses__'+key].index(c)
                del to_delete['responses__'+key][idx]
    return to_delete


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
        if all(task.in_tasks.values_list('complete', flat=True)):
            send_auto_notifications(stage, task, task.case, {'go': AutoNotificationConstants.FORWARD})
    elif task.in_tasks.all():
        previous_task = task.in_tasks.all()[0]
        if previous_task.complete is False and previous_task.reopened is True:
            send_auto_notifications(stage, task, task.case, {'go': AutoNotificationConstants.BACKWARD})
        else:
            send_auto_notifications(stage, task, task.case, {'go': AutoNotificationConstants.LAST_ONE})
    elif not stage.in_stages.count():
        in_tasks, out_tasks = task.in_tasks.all(), task.out_tasks.all()
        if (not in_tasks or in_tasks and in_tasks[0].complete) and task.complete and not out_tasks:
            send_auto_notifications(stage, task, task.case, {'go': AutoNotificationConstants.LAST_ONE})


def send_auto_notifications(trigger, task, case, filters=None):
    for auto_notification in trigger.auto_notification_trigger_stages.filter(**filters):
        try:
            receiver_task = case.tasks.get(
                stage=auto_notification.recipient_stage
            )
            auto_notification.create_notification(task, receiver_task,
                                                  receiver_task.assignee)
        except Task.DoesNotExist:
            auto_notification.generate_error(
                type(Task.DoesNotExist),
                details="System can't access to the task that doesn't exist. " 
                "Adjust your Notification status properly.",
                tb_info=traceback.format_exc(),
                data=f"AutoNotificationId: {auto_notification.id}. "
                        f"Task: {task.id}"
            )
            raise CustomApiException(
                406, "Notification cannot be sent. "
                     "Show this message to your verifiers"
            )
