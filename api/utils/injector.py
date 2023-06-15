import json
import re

from api.constans import ReplaceConstants as RC
from api.constans import ReplaceSourceConstants as RSC
from api.constans import ReplaceOptionsConstants as ROC
from api.models import Task


def inject(text, task):
    print("INJECTION TEXT IN:")
    print(str(text))
    is_dict = False
    if isinstance(text, dict):
        is_dict = True
    print(str(is_dict))
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
        print("INJECTION PART")
        print(data)
        if is_dict:
            if isinstance(data, dict):
                text = text.replace(injection, json.dumps(data))
            else:
                print("TEXT BEFORE INJECTION:")
                print(text)
                text = text.replace(injection, '"' + data + '"')
                print("TEXT AFTER INJECTION:")
                print(text)
        else:
            if isinstance(data, dict):
                text = text.replace(injection, json.dumps(data))
            else:
                text = text.replace(injection, data)

    if is_dict:
        text = json.loads(text)

    print("INJECTION TEXT OUT:")
    print(str(text))
    return text


def _get_injection_data(injection, task):
    print("INJECTION:")
    print(injection)
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
    print("GET PARAM DATA:")
    print(data)
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
