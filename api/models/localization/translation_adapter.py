import json

from django.apps import apps
from django.db import models
from django.db.models import F

from api.models import BaseDatesModel


class TranslationAdapter(BaseDatesModel):
    stage = models.ForeignKey(
        "TaskStage",
        on_delete=models.CASCADE,
        related_name="translation_adapters",
        null=False,
        blank=False,
        help_text="Which stage modifier."
    )
    source = models.ForeignKey(
        "Language",
        on_delete=models.CASCADE,
        related_name="source_translations",
        blank=False,
        null=False,
        help_text="From what language text must be translated."
    )
    target = models.ForeignKey(
        "Language",
        on_delete=models.CASCADE,
        related_name="target_translations",
        blank=False,
        null=False,
        help_text="On what language text mus be translated."
    )

    @classmethod
    def generate_translation_tasks(cls, stage, in_tasks=None):
        in_tasks = in_tasks if in_tasks else []
        texts_by_stage = dict()
        all_keys = dict()
        TranslateKey = apps.get_model("api.translatekey")
        Translation = apps.get_model("api.translation")
        stages = stage.get_campaign().chains.values(
            **{"stage_id": F("stages__taskstage"),
             "schema": F("stages__taskstage__json_schema")}
        )
        for st in stages:
            if st.get("schema") is None:
                continue
            new_phrases = TranslateKey.get_keys_from_schema(
                json.loads(st.get("schema"))
            )

            all_keys.update(new_phrases)
            texts_by_stage[st.get("stage_id")] = new_phrases

        created_objects = {i.id for i in TranslateKey.create_from_list(
                    stage.get_campaign(), all_keys)}
        all_translations = Translation.objects.filter(
            key__campaign=stage.get_campaign()
        ).select_related("language").prefetch_related("key")
        Task = apps.get_model("api.task")
        Case = apps.get_model("api.case")
        tasks_to_create = []
        # print(all_keys)
        # print(texts_by_stage)
        for adapter in stage.translation_adapters.select_related("source",
                                                                 "target").all():

            translations_to_create = [
                Translation(key_id=i, language=adapter.target) for i in
                 created_objects if
                 not all_translations.filter(key_id=i, language=adapter.target, text__isnull=False)]

            if translations_to_create:
                Translation.objects.bulk_create(translations_to_create)
                all_translations = Translation.objects.filter(
                    key__campaign=stage.get_campaign()
                ).select_related("language").prefetch_related("key")

            for st, texts in texts_by_stage.items():
                available_translations = all_translations.filter(
                    language=adapter.target,
                    status=Translation.Status.FREE,
                    key__key__in=list(texts.keys())
                )

                available_keys = {k: v for k, v in texts.items() if
                                  k in available_translations.values_list(
                                      "key__key", flat=True)
                                  }
                if available_keys:
                    c = Case.objects.create()
                    tasks_to_create.append(
                        Task(
                            stage=stage,
                            case=c,
                            schema=TranslateKey.generate_schema_by_fields(
                                available_keys, adapter.target.name)

                        )
                    )
                    available_translations.update(
                        status=Translation.Status.PENDING)

                # print()

        Task.objects.bulk_create(tasks_to_create)

    def __str__(self):
        return f"{self.source.code} - {self.target.code}. {self.stage.id}"
