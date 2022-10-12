class TaskStageConstants:
    RANK = 'RA'
    STAGE = 'ST'
    INTEGRATOR = 'IN'
    AUTO_COMPLETE = 'AU'
    PREVIOUS_MANUAL = 'PA'


class ConditionalStageConstants:
    from api.functions_utils import eq, ne, gt, lt, ge, le, contains, not_contains

    OPERATORS = {
        "==": eq,
        "!=": ne,
        ">": gt,
        "<": lt,
        ">=": ge,
        "<=": le,
        "ARRAY-CONTAINS": contains,
        "ARRAY-CONTAINS-NOT": not_contains
    }

    SUPPORTED_TYPES = {
        "boolean": bool,
        "number": float,
        "integer": int,
        "string": str
    }

    VALIDATION_SCHEMA = {
        "type": "object",
        "properties": {
            "field": {"type": "string"},
            "value": {"type": "string"},
            "condition": {"type": "string", "enum": list(OPERATORS.keys())},
            "type": {"type": "string", "enum": list(SUPPORTED_TYPES.keys())},
            "system": {"type": "boolean", "default": False}
        },
        "required": ["field", "value", "condition", "type"]
    }


class CopyFieldConstants:
    USER = 'US'
    CASE = 'CA'


class NotificationConstants:
    READ_ONLY_FIELDS = ['target_user', 'sender_task', 'receiver_task', 'trigger_go']


class AutoNotificationConstants:
    FORWARD = 'FW'
    BACKWARD = 'BW'
    LAST_ONE = 'LO'


class FieldsJsonConstants:
    META_QUIZ_SCORE = 'meta_quiz_score'
    META_QUIZ_INCORRECT_QUESTIONS = 'meta_quiz_incorrect_questions'


class ErrorConstants:
    CANNOT_SUBMIT = 'You may not submit this task!'
    TASK_COMPLETED = 'Task is being completed!'
    TASK_ALREADY_COMPLETED = 'Task is already complete!'
    IMPOSSIBLE_ACTION = 'It is impossible to %s task.'
    UNSUPPORTED_TYPE = 'Unsupported \'%s\'.'
    SEND_TO_MODERATORS = 'Please send this message to your moderators.'
    ENTITY_DOESNT_EXIST = '%s %s doesn\'t exist.'
    ENTITY_IS_NOT_IN_CAMPAIGN = '%s is not in the campaign.'
