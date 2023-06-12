import json
import re

from api.constans import ReplaceConstants as RC
from api.constans import ReplaceSourceConstants as RSC
from api.constans import ReplaceOptionsConstants as ROC


def text_inject(text, task):
    if RC.REPLACE_HINT not in text:
        return text
    pattern = r"\[\s*" + re.escape(RC.REPLACE_HINT) + r".*\]"
    injections = re.findall(pattern, text)
    for injection in injections:
        if RC.INTERNAL_META in injection:
            text = text.replace(injection, _get_internal_meta_field(injection, task))
        elif RC.USER_ID in injection:
            text = text.replace(injection, _get_user_id(injection, task))

    return text


def _get_internal_meta_field(injection, task):
    stage = _get_param(RSC.STAGE, injection, task)
    field = _get_param(RSC.FIELD, injection, task)

    if field is None:
        return None

    internal_meta = _get_task(stage, task).internal_metadata

    if internal_meta is None:
        return None

    return internal_meta.get(field, None)


def _get_user_id(injection, task):
    stage = _get_param(RSC.STAGE, injection, task)
    return _get_task(stage, task).assignee.id


def _get_param(param, injection, task):
    pattern = r"\{.*\}"
    data = re.findall(pattern, injection)
    if not data:
        return None
    data = json.loads(data[0])
    return data.get(param, None)


def _get_task(stage, task):
    if stage == ROC.IN_TASK:
        return task.in_tasks.get()
    return task


def _extract_json(injection):
    return
    pass
