import json

from rest_framework import status

from api.constans import AutoNotificationConstants, TaskStageConstants, \
    CopyFieldConstants
from api.models import *
from api.tests import GigaTurnipTestHelper, to_json


class QuizTest(GigaTurnipTestHelper):

    def test_quiz(self):
        task_correct_responses = self.create_initial_task()
        correct_responses = {"1": "a", "2": "b", "3": "a", "4": "c", "5": "d"}
        self.initial_stage.json_schema = {
            "type": "object",
            "properties": {
                "1": {
                    "enum": ["a", "b", "c", "d"], "title": "Question 1", "type": "string"
                },
                "2": {
                    "enum": ["a", "b", "c", "d"], "title": "Question 2", "type": "string"
                },
                "3": {
                    "enum": ["a", "b", "c", "d"], "title": "Question 3", "type": "string"
                },
                "4": {
                    "enum": ["a", "b", "c", "d"], "title": "Question 4", "type": "string"
                },
                "5": {
                    "enum": ["a", "b", "c", "d"], "title": "Question 5", "type": "string"
                }
            },
            "dependencies": {},
            "required": ["1", "2", "3", "4", "5"]
        }
        self.initial_stage.json_schema = json.dumps(self.initial_stage.json_schema)
        self.initial_stage.save()
        task_correct_responses = self.complete_task(
            task_correct_responses,
            responses=correct_responses)
        Quiz.objects.create(
            task_stage=self.initial_stage,
            correct_responses_task=task_correct_responses
        )
        task = self.create_initial_task()
        responses = {"1": "a", "2": "b", "3": "a", "4": "c", "5": "b"}
        task = self.complete_task(task, responses=responses)

        self.assertEqual(task.responses[Quiz.SCORE], 80)
        self.assertEqual(Task.objects.count(), 2)
        self.assertTrue(task.complete)

    def test_quiz_correctly_answers(self):
        task_correct_responses = self.create_initial_task()

        self.initial_stage.json_schema = {
            "type": "object",
            "properties": {
                "q_1": {
                    "enum": ["a", "b", "c"],
                    "title": "Question 1",
                    "type": "string"
                },
                "q_2": {
                    "enum": ["a", "b", "c"],
                    "title": "Question 2",
                    "type": "string"
                },
                "q_3": {
                    "enum": ["a", "b", "c"],
                    "title": "Question 3",
                    "type": "string"
                }
            },
            "dependencies": {},
            "required": [
                "q_1",
                "q_2",
                "q_3"
            ]
        }
        self.initial_stage.json_schema = json.dumps(self.initial_stage.json_schema)
        self.initial_stage.save()

        correct_responses = {"q_1": "a", "q_2": "b", "q_3": "a"}
        task_correct_responses = self.complete_task(
            task_correct_responses,
            responses=correct_responses)
        Quiz.objects.create(
            task_stage=self.initial_stage,
            correct_responses_task=task_correct_responses,
            show_answer=Quiz.ShowAnswers.ALWAYS
        )
        task = self.create_initial_task()
        responses = {"q_1": "a", "q_2": "c", "q_3": "c"}
        task = self.complete_task(task, responses=responses)

        self.assertEqual(task.responses[Quiz.SCORE], 33)
        self.assertEqual(task.responses[Quiz.INCORRECT_QUESTIONS], "Question 2\nQuestion 3")
        self.assertEqual(Task.objects.count(), 2)
        self.assertTrue(task.complete)

    def test_quiz_above_threshold(self):
        task_correct_responses = self.create_initial_task()
        correct_responses = {"1": "a", "2": "b", "3": "a", "4": "c", "5": "d"}
        self.initial_stage.json_schema = {
            "type": "object",
            "properties": {
                "1": {
                    "enum": ["a", "b", "c", "d"], "title": "Question 1", "type": "string"
                },
                "2": {
                    "enum": ["a", "b", "c", "d"], "title": "Question 2", "type": "string"
                },
                "3": {
                    "enum": ["a", "b", "c", "d"], "title": "Question 3", "type": "string"
                },
                "4": {
                    "enum": ["a", "b", "c", "d"], "title": "Question 4", "type": "string"
                },
                "5": {
                    "enum": ["a", "b", "c", "d"], "title": "Question 5", "type": "string"
                }
            },
            "dependencies": {},
            "required": ["1", "2", "3", "4", "5"]
        }
        self.initial_stage.json_schema = json.dumps(self.initial_stage.json_schema)
        self.initial_stage.save()

        task_correct_responses = self.complete_task(
            task_correct_responses,
            responses=correct_responses)
        Quiz.objects.create(
            task_stage=self.initial_stage,
            correct_responses_task=task_correct_responses,
            threshold=70
        )
        self.initial_stage.add_stage(
            TaskStage(
                assign_user_by="ST",
                assign_user_from_stage=self.initial_stage
            )
        )
        task = self.create_initial_task()
        responses = {"1": "a", "2": "b", "3": "a", "4": "c", "5": "b"}
        task = self.complete_task(task, responses=responses)

        self.assertEqual(task.responses[Quiz.SCORE], 80)
        self.assertEqual(Task.objects.count(), 3)
        self.assertTrue(task.complete)

    def test_quiz_below_threshold(self):
        task_correct_responses = self.create_initial_task()
        correct_responses = {"1": "a", "2": "b", "3": "a", "4": "c", "5": "d"}
        self.initial_stage.json_schema = {
            "type": "object",
            "properties": {
                "1": {
                    "enum": ["a", "b", "c", "d"], "title": "Question 1", "type": "string"
                },
                "2": {
                    "enum": ["a", "b", "c", "d"], "title": "Question 2", "type": "string"
                },
                "3": {
                    "enum": ["a", "b", "c", "d"], "title": "Question 3", "type": "string"
                },
                "4": {
                    "enum": ["a", "b", "c", "d"], "title": "Question 4", "type": "string"
                },
                "5": {
                    "enum": ["a", "b", "c", "d"], "title": "Question 5", "type": "string"
                }
            },
            "dependencies": {},
            "required": ["1", "2", "3", "4", "5"]
        }
        self.initial_stage.json_schema = json.dumps(self.initial_stage.json_schema)
        self.initial_stage.save()
        task_correct_responses = self.complete_task(
            task_correct_responses,
            responses=correct_responses)
        Quiz.objects.create(
            task_stage=self.initial_stage,
            correct_responses_task=task_correct_responses,
            threshold=90
        )
        self.initial_stage.add_stage(
            TaskStage(
                assign_user_by="ST",
                assign_user_from_stage=self.initial_stage
            )
        )
        task = self.create_initial_task()
        responses = {"1": "a", "2": "b", "3": "a", "4": "c", "5": "b"}
        task = self.complete_task(task, responses=responses)

        self.assertEqual(task.responses[Quiz.SCORE], 80)
        self.assertEqual(Task.objects.count(), 2)
        self.assertFalse(task.complete)

    def test_quiz_show_answers_never(self):
        task_correct_responses = self.create_initial_task()

        js_schema = {
            "type": "object",
            "properties": {
                "q_1": {
                    "enum": ["a", "b", "c"],
                    "title": "Question 1",
                    "type": "string"
                },
                "q_2": {
                    "enum": ["a", "b", "c"],
                    "title": "Question 2",
                    "type": "string"
                },
                "q_3": {
                    "enum": ["a", "b", "c"],
                    "title": "Question 3",
                    "type": "string"
                }
            },
            "dependencies": {},
            "required": [
                "q_1",
                "q_2",
                "q_3"
            ]
        }
        self.initial_stage.json_schema = json.dumps(js_schema)
        self.initial_stage.save()

        correct_responses = {"q_1": "a", "q_2": "b", "q_3": "a"}
        task_correct_responses = self.complete_task(
            task_correct_responses,
            responses=correct_responses)
        task_correct_responses.assignee = None
        task_correct_responses.save()
        quiz = Quiz.objects.create(
            task_stage=self.initial_stage,
            correct_responses_task=task_correct_responses,
            show_answer=Quiz.ShowAnswers.NEVER
        )
        # Test answers if no threshold
        task = self.create_initial_task()
        responses = {"q_1": "a", "q_2": "c", "q_3": "c"}
        task = self.complete_task(task, responses=responses)
        self.assertEqual(task.responses[Quiz.SCORE], 33)
        self.assertEqual(task.responses[Quiz.INCORRECT_QUESTIONS], [])
        self.assertTrue(task.complete)
        self.assertEqual(self.user.tasks.count(), 1)

        # Test answers if below threshold
        quiz.threshold = 50
        quiz.save()
        task = self.create_initial_task()
        responses = {"q_1": "a", "q_2": "c", "q_3": "c"}
        task = self.complete_task(task, responses=responses)
        self.assertEqual(task.responses[Quiz.SCORE], 33)
        self.assertEqual(task.responses[Quiz.INCORRECT_QUESTIONS], [])
        self.assertFalse(task.complete)
        self.assertEqual(self.user.tasks.count(), 2)

        # Test answers if above threshold
        task = self.create_initial_task()
        responses = correct_responses
        task = self.complete_task(task, responses=responses)
        self.assertEqual(task.responses[Quiz.SCORE], 100)
        self.assertEqual(task.responses[Quiz.INCORRECT_QUESTIONS], [])
        self.assertTrue(task.complete)
        self.assertEqual(self.user.tasks.count(), 3)

        # Test answers if above threshold
        quiz.provide_answers = True
        quiz.save()
        task = self.create_initial_task()
        responses = correct_responses
        task = self.complete_task(task, responses=responses)
        self.assertEqual(task.responses[Quiz.SCORE], 100)
        self.assertEqual(task.responses[Quiz.INCORRECT_QUESTIONS], [])
        self.assertTrue(task.complete)
        self.assertEqual(self.user.tasks.count(), 4)

    def test_quiz_show_answers_always(self):
        task_correct_responses = self.create_initial_task()

        js_schema = {
            "type": "object",
            "properties": {
                "q_1": {
                    "enum": ["a", "b", "c"],
                    "title": "Question 1",
                    "type": "string"
                },
                "q_2": {
                    "enum": ["a", "b", "c"],
                    "title": "Question 2",
                    "type": "string"
                },
                "q_3": {
                    "enum": ["a", "b", "c"],
                    "title": "Question 3",
                    "type": "string"
                }
            },
            "dependencies": {},
            "required": [
                "q_1",
                "q_2",
                "q_3"
            ]
        }
        self.initial_stage.json_schema = json.dumps(js_schema)
        self.initial_stage.save()

        correct_responses = {"q_1": "a", "q_2": "b", "q_3": "a"}
        task_correct_responses = self.complete_task(
            task_correct_responses,
            responses=correct_responses)
        task_correct_responses.assignee = None
        task_correct_responses.save()
        quiz = Quiz.objects.create(
            task_stage=self.initial_stage,
            correct_responses_task=task_correct_responses,
            show_answer=Quiz.ShowAnswers.ALWAYS
        )
        # Test answers if no threshold
        task = self.create_initial_task()
        responses = {"q_1": "a", "q_2": "c", "q_3": "c"}
        task = self.complete_task(task, responses=responses)
        self.assertEqual(task.responses[Quiz.SCORE], 33)
        self.assertEqual(task.responses[Quiz.INCORRECT_QUESTIONS],
                         'Question 2\nQuestion 3')
        self.assertTrue(task.complete)
        self.assertEqual(self.user.tasks.count(), 1)

        # Test answers if below threshold
        quiz.provide_answers = True
        quiz.threshold = 50
        quiz.save()
        task = self.create_initial_task()
        task = self.complete_task(task, responses=responses)
        self.assertEqual(task.responses[Quiz.SCORE], 33)
        self.assertEqual(task.responses[Quiz.INCORRECT_QUESTIONS],
                         'Question 2: b\nQuestion 3: a')
        self.assertFalse(task.complete)
        self.assertEqual(self.user.tasks.count(), 2)

        # Test answers if above threshold
        task = self.create_initial_task()
        responses = correct_responses
        task = self.complete_task(task, responses=responses)
        self.assertEqual(task.responses[Quiz.SCORE], 100)
        self.assertEqual(task.responses[Quiz.INCORRECT_QUESTIONS], '')
        self.assertTrue(task.complete)

    def test_quiz_show_answers_on_pass(self):
        task_correct_responses = self.create_initial_task()

        js_schema = {
            "type": "object",
            "properties": {
                "q_1": {
                    "enum": ["a", "b", "c"],
                    "title": "Question 1",
                    "type": "string"
                },
                "q_2": {
                    "enum": ["a", "b", "c"],
                    "title": "Question 2",
                    "type": "string"
                },
                "q_3": {
                    "enum": ["a", "b", "c"],
                    "title": "Question 3",
                    "type": "string"
                }
            },
            "dependencies": {},
            "required": [
                "q_1",
                "q_2",
                "q_3"
            ]
        }
        self.initial_stage.json_schema = json.dumps(js_schema)
        self.initial_stage.save()

        correct_responses = {"q_1": "a", "q_2": "b", "q_3": "a"}
        task_correct_responses = self.complete_task(
            task_correct_responses,
            responses=correct_responses)
        task_correct_responses.assignee = None
        task_correct_responses.save()
        quiz = Quiz.objects.create(
            task_stage=self.initial_stage,
            correct_responses_task=task_correct_responses,
            show_answer=Quiz.ShowAnswers.ON_PASS
        )
        # Test answers if no threshold
        task = self.create_initial_task()
        responses = {"q_1": "a", "q_2": "c", "q_3": "c"}
        task = self.complete_task(task, responses=responses)
        self.assertEqual(task.responses[Quiz.SCORE], 33)
        self.assertEqual(task.responses[Quiz.INCORRECT_QUESTIONS], [])
        self.assertTrue(task.complete)
        self.assertEqual(self.user.tasks.count(), 1)

        # Test answers if below threshold
        quiz.threshold = 50
        quiz.save()
        task = self.create_initial_task()
        task = self.complete_task(task, responses=responses)
        self.assertEqual(task.responses[Quiz.SCORE], 33)
        self.assertEqual(task.responses[Quiz.INCORRECT_QUESTIONS], [])
        self.assertFalse(task.complete)
        self.assertEqual(self.user.tasks.count(), 2)

        # Test answers if above threshold
        quiz.provide_answers = True
        quiz.save()
        task = self.create_initial_task()
        responses = {"q_1": "a", "q_2": "b", "q_3": "c"}
        task = self.complete_task(task, responses=responses)
        self.assertEqual(task.responses[Quiz.SCORE], 66)
        self.assertEqual(task.responses[Quiz.INCORRECT_QUESTIONS], 'Question 3: a')
        self.assertTrue(task.complete)
        self.assertEqual(self.user.tasks.count(), 3)

        # Test answers if threshold equals 0
        quiz.provide_answers = True
        quiz.threshold = 0
        quiz.save()
        task = self.create_initial_task()
        responses = {"q_1": "a", "q_2": "b", "q_3": "c"}
        task = self.complete_task(task, responses=responses)
        self.assertEqual(task.responses[Quiz.SCORE], 66)
        self.assertEqual(task.responses[Quiz.INCORRECT_QUESTIONS], 'Question 3: a')
        self.assertTrue(task.complete)
        self.assertEqual(self.user.tasks.count(), 4)

    def test_quiz_show_answers_on_fail(self):
        task_correct_responses = self.create_initial_task()

        js_schema = {
            "type": "object",
            "properties": {
                "q_1": {
                    "enum": ["a", "b", "c"],
                    "title": "Question 1",
                    "type": "string"
                },
                "q_2": {
                    "enum": ["a", "b", "c"],
                    "title": "Question 2",
                    "type": "string"
                },
                "q_3": {
                    "enum": ["a", "b", "c"],
                    "title": "Question 3",
                    "type": "string"
                }
            },
            "dependencies": {},
            "required": [
                "q_1",
                "q_2",
                "q_3"
            ]
        }
        self.initial_stage.json_schema = json.dumps(js_schema)
        self.initial_stage.save()

        correct_responses = {"q_1": "a", "q_2": "b", "q_3": "a"}
        task_correct_responses = self.complete_task(
            task_correct_responses,
            responses=correct_responses)
        task_correct_responses.assignee = None
        task_correct_responses.save()
        quiz = Quiz.objects.create(
            task_stage=self.initial_stage,
            correct_responses_task=task_correct_responses,
            show_answer=Quiz.ShowAnswers.ON_FAIL
        )
        # Test answers if no threshold
        task = self.create_initial_task()
        responses = {"q_1": "a", "q_2": "c", "q_3": "c"}
        task = self.complete_task(task, responses=responses)
        self.assertEqual(task.responses[Quiz.SCORE], 33)
        self.assertEqual(task.responses[Quiz.INCORRECT_QUESTIONS], [])
        self.assertTrue(task.complete)
        self.assertEqual(self.user.tasks.count(), 1)

        # Test answers if below threshold
        quiz.provide_answers = True
        quiz.save()
        quiz.threshold = 50
        quiz.save()
        task = self.create_initial_task()
        task = self.complete_task(task, responses=responses)
        self.assertEqual(task.responses[Quiz.SCORE], 33)
        self.assertEqual(task.responses[Quiz.INCORRECT_QUESTIONS],
                         'Question 2: b\nQuestion 3: a')
        self.assertFalse(task.complete)
        self.assertEqual(self.user.tasks.count(), 2)

        # Test answers if above threshold
        task = self.create_initial_task()
        responses = {"q_1": "a", "q_2": "b", "q_3": "c"}
        task = self.complete_task(task, responses=responses)
        self.assertEqual(task.responses[Quiz.SCORE], 66)
        self.assertEqual(task.responses[Quiz.INCORRECT_QUESTIONS], [])
        self.assertTrue(task.complete)
        self.assertEqual(self.user.tasks.count(), 3)


    def test_quiz_with_instant_answers(self):
        task_correct_responses = self.create_initial_task()
        correct_responses = {"1": "a", "2": "b", "3": "a", "4": "c", "5": "d"}
        self.initial_stage.json_schema = {
            "type": "object",
            "properties": {
                "1": {
                    "enum": ["a", "b", "c", "d"], "title": "Question 1", "type": "string"
                },
                "2": {
                    "enum": ["a", "b", "c", "d"], "title": "Question 2", "type": "string"
                },
                "3": {
                    "enum": ["a", "b", "c", "d"], "title": "Question 3", "type": "string"
                },
                "4": {
                    "enum": ["a", "b", "c", "d"], "title": "Question 4", "type": "string"
                },
                "5": {
                    "enum": ["a", "b", "c", "d"], "title": "Question 5", "type": "string"
                }
            },
            "dependencies": {},
            "required": ["1", "2", "3", "4", "5"]
        }
        self.initial_stage.json_schema = json.dumps(self.initial_stage.json_schema)
        self.initial_stage.save()
        task_correct_responses = self.complete_task(
            task_correct_responses,
            responses=correct_responses)
        Quiz.objects.create(
            task_stage=self.initial_stage,
            correct_responses_task=task_correct_responses,
            send_answers_with_questions=True
        )
        task_creation_api_response = self.get_objects(endpoint="taskstage-create-task",
                                                      pk=self.initial_stage.pk)
        
        self.assertEqual(task_creation_api_response.data["stage"]["quiz_answers"], correct_responses)

        # task = self.create_initial_task()
        # responses = {"1": "a", "2": "b", "3": "a", "4": "c", "5": "b"}
        # task = self.complete_task(task, responses=responses)
        #
        # self.assertEqual(task.responses[Quiz.SCORE], 80)
        # self.assertEqual(Task.objects.count(), 2)
        # self.assertTrue(task.complete)
