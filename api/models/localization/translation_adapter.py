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

    @staticmethod
    def get_phrases_by_stages(chains):
        TranslateKey = apps.get_model("api.translatekey")

        stages = chains.values(
            **{"stage_id": F("stages__taskstage"),
             "schema": F("stages__taskstage__json_schema")}
        )

        texts_by_stage = dict()
        all_keys = dict()

        for st in stages:
            if st.get("schema") is None:
                continue
            new_phrases = TranslateKey.get_keys_from_schema(
                json.loads(st.get("schema"))
            )

            all_keys.update(new_phrases)
            texts_by_stage[st.get("stage_id")] = new_phrases

        return texts_by_stage, all_keys

    @classmethod
    def generate_translation_tasks(cls, stage, in_tasks=None):
        """
        Generating tasks for users who will translate phrases.
        If any phrase have been already translated - so this phrase will not be shown again.
        Every stage will have phrases only from its schema.

        :param stage: TaskStage
        :param in_tasks: In tasks for Task instances
        :return:
        """
        TranslateKey = apps.get_model("api.translatekey")
        Translation = apps.get_model("api.translation")
        Task = apps.get_model("api.task")
        Case = apps.get_model("api.case")


        in_tasks = in_tasks if in_tasks else []
        # geenreate new TranslateKey for new phrases
        texts_by_stage, all_keys = cls.get_phrases_by_stages(stage.get_campaign().chains)
        created_objects = {i.id for i in TranslateKey.create_from_list(
                    stage.get_campaign(), all_keys)}

        # all translations for our campaign
        all_translations = Translation.objects.filter(
            key__campaign=stage.get_campaign()
        ).select_related("language").prefetch_related("key")

        # array to store created tasks
        tasks_to_create = []
        for adapter in stage.translation_adapters.select_related("source",
                                                                 "target").all():
            # create translation class instances if they aren't exists in DB, if there is any new instance then create instances
            translations_to_create = [
                Translation(key_id=i, language=adapter.target) for i in
                 created_objects if
                 not all_translations.filter(key_id=i, language=adapter.target, text__isnull=False)]

            if translations_to_create:
                Translation.objects.bulk_create(translations_to_create)
                all_translations = Translation.objects.filter(
                    key__campaign=stage.get_campaign()
                ).select_related("language").prefetch_related("key")

            # create tasks with schema that will show phrases that must be translated
            for st, texts in texts_by_stage.items():
                # phrases that haven't been translated yet
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

        created_objects = Task.objects.bulk_create(tasks_to_create)
        [i.in_tasks.add(*in_tasks) for i in created_objects]


    def __str__(self):
        return f"{self.source.code} - {self.target.code}. {self.stage.id}"
