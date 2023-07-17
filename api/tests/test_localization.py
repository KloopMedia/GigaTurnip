import hashlib
import json

from rest_framework import status

from api.constans import AutoNotificationConstants, TaskStageConstants, \
    CopyFieldConstants
from api.models import *
from api.tests import GigaTurnipTestHelper, to_json, get_schema


class LocalizationTest(GigaTurnipTestHelper):
    def test_create_translate_keys_from_stage(self):
        schema = {
            "type": "object",
            "properties": {
                "answer": {
                    "title": "Question 1",
                    "type": "string"
                },
                "answer2": {
                    "title": "Question 2",
                    "type": "string"
                },
                "answer3": {
                    "title": "Question 3",
                    "type": "string"
                },
                "answer4": {
                    "title": "Question 4",
                    "type": "string"
                }
            },
            "required": ["answer","answer2","answer3","answer4"]
        }
        self.initial_stage.json_schema = schema
        self.initial_stage.save()

        result = TranslateKey.generate_keys_from_stage(self.initial_stage)
        self.assertEqual(len(result), 4)
        self.assertEqual(
            TranslateKey.objects.filter(campaign=self.campaign).count(), 4)

        result2 = TranslateKey.generate_keys_from_stage(self.initial_stage)
        self.assertEqual(len(result2), 0)
        self.assertEqual(
            TranslateKey.objects.filter(campaign=self.campaign).count(), 4)

        local_lang = Language.objects.create(
            name="Russia",
            code="ru"
        )
        translations = {
            "Question 1": "Вопрос 1",
            "Question 2": "Вопрос 2",
            "Question 3": "Вопрос 3",
            "Question 4": "Вопрос 4"
        }
        translated = [(i.id, translations.get(i.text)) for i in result]
        translated_values = Translation.create_from_list(local_lang, translated)
        self.assertEqual(Translation.objects.count(), 4)

        translated_values = Translation.create_from_list(local_lang, translated)
        self.assertEqual(Translation.objects.count(), 4)

    def test_translation_key_create_keys_from_schema(self):
        schema = {
            "type": "object",
            "properties": {
                "answer": {
                    "title": "Question 1",
                    "type": "string"
                },
                "answer2": {
                    "title": "Question 2",
                    "type": "string"
                },
                "answer3": {
                    "title": "Question 3",
                    "type": "string"
                },
                "answer4": {
                    "title": "Question 4",
                    "type": "string"
                }
            },
            "required": ["answer", "answer2", "answer3", "answer4"]
        }
        result_answer = {
            '02ecd63e4f1632ff673d8ebfb0709c5e520a2a64a77644369eab86c5c833a796': 'Question 1',
            '6f6cb2379d5b20df39599b65ae7501a6f4c565e7913217e30b492f871872eabd': 'Question 2',
            '0382a3d975fd041572a308838480b07e9a789989dbfb34d12152f93c03644225': 'Question 3',
            '2b71f00b126e10636fbb133ecc57bd6df85ba5c08cd8534bc8cfe1467e903a06': 'Question 4'
        }
        self.assertEqual(result_answer,
                         TranslateKey.get_keys_from_schema(schema))

    def test_translation_create_from_dict_of_texts(self):
        local_lang = Language.objects.create(
            name="Russian",
            code="ru"
        )
        texts = ["Artur", "Karim", "Rinat", "Xakim", "Atai", "Atai"]
        texts = {hashlib.sha256(i.encode()).hexdigest(): i for i in texts}
        objs = TranslateKey.create_from_list(self.campaign, texts)
        self.assertEqual(len(objs), 5)

        texts = ["Artur", "Atai", "Atai", "Artem"]
        texts = {hashlib.sha256(i.encode()).hexdigest(): i for i in texts}
        objs = TranslateKey.create_from_list(self.campaign, texts)
        self.assertEqual(len(objs), 1)


        translations = {
            "Artur": "Артур",
            "Karim": "Карим",
            "Rinat": "Ринат",
            "Xakim": "Хаким",
            "Atai": "Атай",
            "Artem": "Артем"
        }
        self.assertEqual(TranslateKey.objects.count(), len(translations.keys()))

        for i in TranslateKey.objects.filter(campaign=self.campaign):
            Translation.objects.create(key=i, language=local_lang, text=translations.get(i.text))

        self.assertEqual(Translation.objects.count(),
                         TranslateKey.objects.count())

    def test_translate_key_generate_translation_schema(self):
        schema = {
            "type": "object",
            "properties": {
                "answer": {
                    "title": "Question 1",
                    "type": "string"
                },
                "answer2": {
                    "title": "Question 2",
                    "type": "string"
                },
                "answer3": {
                    "title": "Question 3",
                    "type": "string"
                },
                "answer4": {
                    "title": "Question 4",
                    "type": "string"
                }
            },
            "required": ["answer", "answer2", "answer3", "answer4"]
        }
        result_schema = {'title': 'Translate this phrases on Russia', 'type': 'object',
                         'properties': {
                             '02ecd63e4f1632ff673d8ebfb0709c5e520a2a64a77644369eab86c5c833a796': {
                                 'title': 'Question 1', 'type': 'string'},
                             '6f6cb2379d5b20df39599b65ae7501a6f4c565e7913217e30b492f871872eabd': {
                                 'title': 'Question 2', 'type': 'string'},
                             '0382a3d975fd041572a308838480b07e9a789989dbfb34d12152f93c03644225': {
                                 'title': 'Question 3', 'type': 'string'},
                             '2b71f00b126e10636fbb133ecc57bd6df85ba5c08cd8534bc8cfe1467e903a06': {
                                 'title': 'Question 4', 'type': 'string'}}}
        self.assertEqual(result_schema,
                         TranslateKey.generate_schema_to_translate_by_schema(
                             schema, "Russia"))

    def test_task_translation_schema(self):
        schema = {
            "title": "Schema for english people",
            "description": "Description",
            "type": "object",
            "properties": {
                "firstName": {
                    "title": "Provide your name",
                    "type": "string"
                },
                "lastName": {
                    "title": "Provide your last name",
                    "type": "string"
                },
                "surname": {
                    "title": "Provide your surname(optional).",
                    "type": "string"
                }
            },
            "required": ["firstName", "lastName"]
        }
        self.initial_stage.json_schema =  schema
        self.initial_stage.save()

        second_stage = self.initial_stage.add_stage(TaskStage(
            name="Second ts.",
            assign_user_by=TaskStageConstants.STAGE,
            assign_user_from_stage=self.initial_stage,
            json_schema=self.initial_stage.json_schema
        ))

        # verification stage
        rank_verifier = Rank.objects.create(name='verifier rank')
        RankRecord.objects.create(rank=rank_verifier, user=self.employee)

        verifier_stage = second_stage.add_stage(TaskStage(
            name="Get on verification",
            assign_user_by=TaskStageConstants.RANK,
            json_schema=self.initial_stage.json_schema
        ))
        # conditional stage
        conditional_stage = verifier_stage.add_stage(ConditionalStage(
                name='Checker',
                conditions=[
                    {"type": "string", "field": "firstName", "value": "",
                     "condition": "!="}
                ]
        ))

        # final user stage
        third_stage = conditional_stage.add_stage(TaskStage(
            name="Third ts.",
            assign_user_by=TaskStageConstants.STAGE,
            assign_user_from_stage=second_stage,
            json_schema=self.initial_stage.json_schema
        ))

        response = self.get_objects("taskstage-available-stages")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Stage.objects.count(), 5)
        self.assertEqual(response.data["count"], 3)
        all_stage = [self.initial_stage.id, second_stage.id, third_stage.id]
        response_stages = [i["id"] for i in response.data["results"]]
        self.assertEqual(all_stage, response_stages)

    def test_translation_schema_substitution_by_lang(self):
        schema = {
            "type": "object",
            "properties": {
                "answer": {
                    "title": "Question 1",
                    "type": "string"
                },
                "answer2": {
                    "title": "Question 2",
                    "type": "string"
                },
                "answer3": {
                    "title": "Question 3",
                    "type": "string"
                },
                "answer4": {
                    "title": "Question 4",
                    "type": "string"
                }
            },
            "required": ["answer", "answer2", "answer3", "answer4"]
        }
        self.initial_stage.json_schema = schema
        self.initial_stage.save()
        objects = TranslateKey.generate_keys_from_stage(self.initial_stage)
        self.assertEqual(len(objects), 4)

        translations = {
            "Question 1": "Вопрос 1",
            "Question 2": "Вопрос 2",
            "Question 3": "Вопрос 3",
            "Question 4": "Вопрос 4"
        }
        local_lang = Language.objects.create(
            name="Russia",
            code="ru"
        )
        [Translation.objects.create(key=i, language=local_lang, text=translations[i.text])
         for i in objects]

        translated = TranslateKey.get_translated_schema_by_stage(
            self.initial_stage, "ru"
        )
        translated_schema = {'type': 'object',
         'properties': {'answer': {'title': 'Вопрос 1', 'type': 'string'},
                        'answer2': {'title': 'Вопрос 2', 'type': 'string'},
                        'answer3': {'title': 'Вопрос 3', 'type': 'string'},
                        'answer4': {'title': 'Вопрос 4', 'type': 'string'}},
         'required': ['answer', 'answer2', 'answer3', 'answer4']}
        self.assertEqual(translated_schema, translated)

        response = self.get_objects("taskstage-list", params={"lang": "ru"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["json_schema"],
                         translated_schema)

        response = self.get_objects("taskstage-list", params={"lang": "ky"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["json_schema"],
                         schema)

    def test_translation_schema_substitution_by_lang_through_task(self):
        schema = {
            "type": "object",
            "properties": {
                "answer": {
                    "title": "Question 1",
                    "type": "string"
                },
                "answer2": {
                    "title": "Question 2",
                    "type": "string"
                },
                "answer3": {
                    "title": "Question 3",
                    "type": "string"
                },
                "answer4": {
                    "title": "Question 4",
                    "type": "string"
                }
            },
            "required": ["answer", "answer2", "answer3", "answer4"]
        }
        self.initial_stage.json_schema = schema
        self.initial_stage.save()
        objects = TranslateKey.generate_keys_from_stage(self.initial_stage)
        self.assertEqual(len(objects), 4)

        translations = {
            "Question 1": "Вопрос 1",
            "Question 2": "Вопрос 2",
            "Question 3": "Вопрос 3",
            "Question 4": "Вопрос 4"
        }
        local_lang = Language.objects.create(
            name="Russia",
            code="ru"
        )
        [Translation.objects.create(key=i, language=local_lang,
                                    text=translations[i.text])
         for i in objects]

        translated = TranslateKey.get_translated_schema_by_stage(
            self.initial_stage, "ru"
        )
        translated_schema = {'type': 'object',
                             'properties': {'answer': {'title': 'Вопрос 1',
                                                       'type': 'string'},
                                            'answer2': {'title': 'Вопрос 2',
                                                        'type': 'string'},
                                            'answer3': {'title': 'Вопрос 3',
                                                        'type': 'string'},
                                            'answer4': {'title': 'Вопрос 4',
                                                        'type': 'string'}},
                             'required': ['answer', 'answer2', 'answer3',
                                          'answer4']}
        self.assertEqual(translated_schema, translated)

        # task
        task = self.create_initial_task()

        params = {"lang": "ru"}
        response = self.get_objects("task-detail", pk=task.id, params=params)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["stage"]["json_schema"],
                         translated_schema)

    def test_translation_update_from_dict(self):
        schema = get_schema()
        self.initial_stage.json_schema = schema
        self.initial_stage.save()
        objects = TranslateKey.generate_keys_from_stage(self.initial_stage)
        self.assertEqual(len(objects), 4)

        translations = {
            "Question 1": "Вопрос 1",
            "Question 2": "Вопрос 2",
            "Question 3": "Вопрос 3",
            "Question 4": "Вопрос 4"
        }
        translations = {hashlib.sha256(k.encode()).hexdigest(): v
                        for k, v in translations.items()}
        local_lang = Language.objects.create(
            name="Russia",
            code="ru"
        )
        Translation.objects.bulk_create(
            [Translation(key=i, language=local_lang) for i in objects]
        )

        self.assertEqual(Translation.objects.count(), 4)
        self.assertEqual(Translation.objects.exclude(
            status=Translation.Status.ANSWERED).count(), 4
            )

        Translation.update_from_dict(self.campaign, local_lang, translations)
        self.assertEqual(Translation.objects.count(), 4)
        all_translations = Translation.objects.all()
        self.assertEqual(all_translations.exclude(
            status=Translation.Status.ANSWERED).count(), 0)
        self.assertEqual(
            all_translations.filter(
                status=Translation.Status.ANSWERED).count(), 4)
        translated_texts = [i[0].split()[1] == i[1].split()[1] for i in
                            all_translations.values_list("key__text", "text")]
        self.assertTrue(all(translated_texts))