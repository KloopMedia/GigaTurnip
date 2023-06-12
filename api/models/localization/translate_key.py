import hashlib
import json
from typing import Any

from django.apps import apps
from django.db import models
from django.db.models import QuerySet
from rest_framework.request import Request


class TranslateKey(models.Model):
    campaign = models.ForeignKey(
        "Campaign",
        on_delete=models.CASCADE,
        blank=False,
        null=False,
        help_text="Campaign that translate text."
    )
    key = models.CharField(
        max_length=64,
        null=False,
        blank=False,
        help_text="Hash text for text."
    )
    text = models.TextField(
        blank=False,
        null=False,
        help_text="Text to translation."
    )

    FIELDS_TO_COLLECT = ["title", "description", "enumNames"]

    @staticmethod
    def extract_titles(storage, val):
        storage[hashlib.sha256(val.encode()).hexdigest()] = val

    @staticmethod
    def extract_enums(storage, val):
        for enum in val:
            storage[hashlib.sha256(val.encode()).hexdigest()] = enum

    @classmethod
    def extract_fields_to_translate(cls, data, storage, path=None):
        p = path if path else ""
        if isinstance(data, dict):
            for i in range(len(cls.FIELDS_TO_COLLECT)):
                key = cls.FIELDS_TO_COLLECT[i]
                val = data.get(key)
                if isinstance(val, (str, list)):
                    full_path = f"{p}__{key}" if p else key
                    if key == "enumNames":
                        cls.extract_enums(storage, val)
                    else:
                        cls.extract_titles(storage, val)
            for k, v in data.items():
                full_path = f"{p}__{k}" if p else k
                cls.extract_fields_to_translate(v, storage, full_path)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                if not isinstance(i, (dict, list)):
                    break
                full_path = f"{p}__{i}" if p else i
                cls.extract_enums(storage, item)

    @staticmethod
    def generate_fields(fields: dict):
        """
        Generate array of dictionaries.

        :param fields: schema
        :return:
        """
        result = []
        for k, v in fields.items():
            result.append({k: {
                "title": v,
                "type": "string"
            }})
        return result

    @classmethod
    def generate_schema_to_translate(cls, schema: dict) -> dict[str, str]:
        """
        Method generates new schema with fields from schema that must be translated.

        :param schema: source scheme which fields must be renamed
        :return:
        """
        translated_schema: dict[str, str | dict[Any, Any]] = {
            "title": "JSON SCHEMA TRANSLATE",
            "type": "object",
            "properties": {}

        }
        for item in cls.generate_fields(cls.get_keys_from_schema(schema)):
            translated_schema["properties"].update(item)
        return translated_schema

    @classmethod
    def get_keys_from_schema(cls, schema: dict) -> dict[str, str]:
        """
        Generate schema with a texts of the fields FIELDS_TO_COLLECT.

        :param schema: schema of the TaskStage
        :return: schema where key is a hashed hexdigset of the value, value is a text
        """
        paths_to_text = dict()
        cls.extract_fields_to_translate(schema, paths_to_text)
        return paths_to_text

    @classmethod
    def create_from_list(cls, campaign, texts: dict) -> QuerySet:
        """
        Create many instances in the database in one query based on schema.

        :param campaign: Campaign that want to translate texts.
        :param texts: Key is a hashed code, value - is a text
        :return: Queryset of TranslateKey
        """
        exists = set(
            cls.objects.filter(
                campaign=campaign, key__in=list(texts.keys())
            ).values_list("key", flat=True)
        )

        data_to_create = [cls(campaign=campaign, key=k, text=v) for k, v
                          in texts.items() if k not in exists]

        return cls.objects.bulk_create(data_to_create)

    @classmethod
    def generate_keys_from_stage(cls, stage):
        texts = cls.get_keys_from_schema(json.loads(stage.get_json_schema()))
        return cls.create_from_list(stage.get_campaign(), texts)

    @classmethod
    def substitute_values(cls, schema: dict,
                          translations):
        """
        Method substitute schema values of FIELDS_TO_COLLECT fields with 'translations' values in order to translate schema on traget language.

        :param schema: Schema where method will substitute values
        :param translations: Translation QuerySet - available translations.
        :return:
        """
        if isinstance(schema, dict):
            for k, v in schema.items():
                if k in cls.FIELDS_TO_COLLECT and isinstance(v, str):
                    translation = translations.filter(
                        key__key=hashlib.sha256(v.encode()).hexdigest()
                    ).first()
                    schema[k] = translation.text if translation else v
                elif isinstance(v, dict):
                    cls.substitute_values(v, translations)

    @classmethod
    def get_translated_schema_by_stage(cls, stage,
                                            lang_code: str) -> dict:
        """
        This method gets json schema of the stage and creates new based on the language.

        :param stage: TaskStage which schema must be used as source schema
        :param lang_code: Language code
        :return: translated schema
        """

        schema = json.loads(stage.get_json_schema())
        all_fields = cls.get_keys_from_schema(schema)
        translations = apps.get_model("api.translation").objects.filter(
            key__key__in=list(all_fields.keys()),
            language__code=lang_code
        )

        cls.substitute_values(schema, translations)
        return schema

    @classmethod
    def to_representation(cls, instance,
                          request: Request):
        """
        Change instance json schema based on accept language.

        :param instance: TaskStage instance
        :param request: Request to get language query param
        :return: instance with substituted language
        """
        lang = apps.get_model("api.language").objects.filter(
            code=request.query_params.get("lang")
        ).first()
        if lang:
            json_schema = cls.get_translated_schema_by_stage(
                instance, lang.code)
            instance.json_schema = json.dumps(json_schema, ensure_ascii=False)

        return instance


    def __str__(self):
        return f"{self.campaign}: {self.key}"

    class Meta:
        unique_together = ("campaign", "key")
