import json
import re

from api.constans import ReplaceConstants as RC
from api.constans import ReplaceSourceConstants as RSC
from api.constans import ReplaceOptionsConstants as ROC
from api.models import Task


def inject(text, task):
    is_dict = False
    if isinstance(text, dict):
        is_dict = True
    if is_dict:
        text = json.dumps(text)

    if RC.REPLACE_HINT not in text:
        if is_dict:
            text = json.loads(text)
        return text

    pattern = r"\{\s*\"" + re.escape(RC.REPLACE_HINT) + r"[^\}]*\:\s\{[^\}]*\}\s*\}"
    injections = re.findall(pattern, text)

    for injection in set(injections):
        data = _get_injection_data(injection, task)
        if is_dict:
            if isinstance(data, dict):
                text = text.replace(injection, json.dumps(data))
            else:
                text = text.replace(injection, '"' + data + '"')
        else:
            if isinstance(data, dict):
                text = text.replace(injection, json.dumps(data))
            else:
                text = text.replace(injection, data)

    if is_dict:
        text = json.loads(text)

    return text


def _get_injection_data(injection, task):
    stage = _get_param(RSC.STAGE, injection, task)
    field = _get_param(RSC.FIELD, injection, task)

    task = _get_task(task, stage)

    if RC.USER_ID in injection:
        data = task.assignee.id
    elif RC.INTERNAL_META in injection:
        data = task.internal_metadata
    elif RC.RESPONSES in injection:
        data = task.responses
    else:
        data = None

    if field is not None and data is not None:
        data = data.get(field, None)

    if not isinstance(data, dict):
        data = str(data)

    return data


def _get_param(param, injection, task=None):
    try:
        data = json.loads(injection)
    except json.decoder.JSONDecodeError:
        return None
    data = data[list(data.keys())[0]]

    if not data:
        return None
    return data.get(param, None)


def _get_task(task, stage=None):
    if stage == ROC.IN_TASK:
        return task.in_tasks.get()
    if stage is not None:
        return Task.objects.get(case=task.case, stage__pk=stage)
    return task


def _extract_json(injection):
    return
    pass





# import json
# import re
#
# from api.constans import ReplaceConstants as RC
# from api.constans import ReplaceSourceConstants as RSC
# from api.constans import ReplaceOptionsConstants as ROC
#
#
# def text_inject(text, task):
#     if RC.REPLACE_HINT not in text:
#         return text
#     pattern = r"\[\s*" + re.escape(RC.REPLACE_HINT) + r".*\]"
#     injections = re.findall(pattern, text)
#     for injection in injections:
#         if RC.INTERNAL_META in injection:
#             text = text.replace(injection, _get_internal_meta_field(injection, task))
#         elif RC.USER_ID in injection:
#             text = text.replace(injection, _get_user_id(injection, task))
#
#     return text
#
#
# def _get_internal_meta_field(injection, task):
#     stage = _get_param(RSC.STAGE, injection, task)
#     field = _get_param(RSC.FIELD, injection, task)
#
#     if field is None:
#         return None
#
#     internal_meta = _get_task(stage, task).internal_metadata
#
#     if internal_meta is None:
#         return None
#
#     return internal_meta.get(field, None)
#
#
# def _get_user_id(injection, task):
#     stage = _get_param(RSC.STAGE, injection, task)
#     return _get_task(stage, task).assignee.id
#
#
# def _get_param(param, injection, task):
#     pattern = r"\{.*\}"
#     data = re.findall(pattern, injection)
#     if not data:
#         return None
#     data = json.loads(data[0])
#     return data.get(param, None)
#
#
# def _get_task(stage, task):
#     if stage == ROC.IN_TASK:
#         return task.in_tasks.get()
#     return task
#
#
# def _extract_json(injection):
#     return
#     pass
