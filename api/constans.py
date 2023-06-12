from django.db import models


class TaskStageConstants:
    RANK = 'RA'
    STAGE = 'ST'
    INTEGRATOR = 'IN'
    AUTO_COMPLETE = 'AU'
    PREVIOUS_MANUAL = 'PA'


class TaskStageSchemaSourceConstants:
    STAGE = 'ST'
    TASK = 'TA'


class ConditionalStageConstants:
    from api.functions_utils import eq, ne, gt, lt, ge, le, contains, not_contains

    OPERATORS = {
        "==": eq,
        "!=": ne,
        ">": gt,
        "<": lt,
        ">=": ge,
        "<=": le,
        "in": contains,
        "nin": not_contains
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


class DynamicJsonConstants:
    DYNAMIC_FIELDS = {
        "main": "main_key",
        "foreign": ["foreign_fields"],
        "count": "optional | int()",
        "constants": {
            "main": "str",
            "foreign": {
                "<field_#1_name>": ["constant val #1", "constant val #n"],
                # ....
                "<field_#k_name>": ["constant val #1", "constant val #n"],

            }
        }
    }


class CopyFieldConstants:
    USER = 'US'
    CASE = 'CA'


class WebhookConstants:
    IN_RESPONSES = 'in'
    CURRENT_TASK_RESPONSES = 'cu'
    MODIFIER_FIELD = "mf"


class WebhookTargetConstants:
    RESPONSES = "RE"
    SCHEMA = "SC"


class NotificationConstants:
    READ_ONLY_FIELDS = ['target_user', 'sender_task', 'receiver_task', 'trigger_go']


class AutoNotificationConstants:
    FORWARD = 'FW'
    BACKWARD = 'BW'
    LAST_ONE = 'LO'


class ErrorConstants:
    ERROR_CAMPAIGN = "09A09E345A3634A86002ACB5CAFE1C10"
    ERROR_CHAIN = "09A09E345A3634A86002ACB5CAFE1C10"
    ERROR_STAGE = "731774739328AE88A97FA984CA7ED16F"
    CANNOT_SUBMIT = 'You may not submit this task!'
    TASK_COMPLETED = 'Task is being completed!'
    TASK_ALREADY_COMPLETED = 'Task is already complete!'
    IMPOSSIBLE_ACTION = 'It is impossible to %s task.'
    UNSUPPORTED_TYPE = 'Unsupported \'%s\'.'
    SEND_TO_MODERATORS = 'Please send this message to your moderators.'
    ENTITY_DOESNT_EXIST = '%s %s doesn\'t exist.'
    ENTITY_IS_NOT_IN_CAMPAIGN = '%s is not in the campaign.'


class DjangoORMConstants:
    LOOKUP_SEP = '__'
    LOOKUP_PREFIXES = {
        '^': 'istartswith',
        '@': 'search',
        '$': 'iregex',
        '==': 'iexact',
        '!=': 'ne',
        '>': 'gt',
        '<': 'lt',
        '>=': 'gte',
        '<=': 'lte',
        'in': 'icontains',
    }
    CAST_PAIRS = {
        "boolean": models.BooleanField,
        "number": models.FloatField,
        "integer": models.IntegerField,
        "string": models.CharField
    }


class JSONFilterConstants:
    JSON_Filter_Validation_Schema = {
        "type": "array",
        "items": {
            "type": "object",
            "required": ["field", "type"],
            "properties": {
                "field": {
                    "type": "string",
                    "enum": []  # вставить поля которые у меня есть
                },
                "type": {
                    "type": "string",
                    "enum": list(ConditionalStageConstants.SUPPORTED_TYPES.keys()),  # вставить возможные типы
                },
                "conditions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "operator": {
                                "type": "string",
                                "enum": list(DjangoORMConstants.LOOKUP_PREFIXES.keys()),  # вставить возможные операторы
                            },
                            "value": {  # сюда пишутся значения с которыми будут сравнивать
                                "type": "string"
                            }
                        }
                    }
                }
            }
        }
    }


class ReplaceConstants:
    REPLACE_HINT = "@TURNIP_"
    USER_ID = REPLACE_HINT + "USER_ID"
    INTERNAL_META = REPLACE_HINT + "INTERNAL_META"


class ReplaceSourceConstants:
    STAGE = "stage"
    FIELD = "field"


class ReplaceOptionsConstants:
    IN_TASK = "in_task"
