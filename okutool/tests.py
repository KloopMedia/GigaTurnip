from django.test import TestCase

from okutool.serializers import VolumeSerializer
from .models import Volume, Stage, Task, Question, QuestionAttachment
from okutool.constants import QuestionAttachmentType, StageType
from api.models import CustomUser
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class VolumeModelTest(TestCase):
    def test_create_volume(self):
        volume = Volume.objects.create(
            title="Sample Volume", description="This is a sample volume."
        )
        self.assertEqual(volume.title, "Sample Volume")
        self.assertEqual(volume.description, "This is a sample volume.")


class StageModelTest(TestCase):
    def setUp(self):
        self.volume = Volume.objects.create(
            title="Sample Volume",
            description="This is a sample volume.",
        )

    def test_create_stage(self):
        stage = Stage.objects.create(
            volume=self.volume,
            type=StageType.THEORY,
            richtext="This is some rich text.",
            json_form="",
        )
        self.assertEqual(stage.volume, self.volume)
        self.assertEqual(stage.type, StageType.THEORY)
        self.assertEqual(stage.richtext, "This is some rich text.")
        self.assertEqual(stage.json_form, "")


class TaskModelTest(TestCase):
    def setUp(self):
        self.volume = Volume.objects.create(
            title="Sample Volume", description="This is a sample volume."
        )
        self.stage = Stage.objects.create(volume=self.volume, type=StageType.PRACTICE)
        self.user = CustomUser.objects.create_user(
            username="testuser", password="password"
        )

    def test_create_task(self):
        task = Task.objects.create(
            assignee=self.user,
            stage=self.stage,
            complete=True,
            total_count=10,
            successful_count=8,
            last_score=80,
        )
        self.assertEqual(task.assignee, self.user)
        self.assertEqual(task.stage, self.stage)
        self.assertTrue(task.complete)
        self.assertEqual(task.total_count, 10)
        self.assertEqual(task.successful_count, 8)
        self.assertEqual(task.last_score, 80)


class QuestionModelTest(TestCase):
    def setUp(self):
        self.volume = Volume.objects.create(
            title="Sample Volume", description="This is a sample volume."
        )
        self.stage = Stage.objects.create(volume=self.volume, type=StageType.TEST)

    def test_create_question(self):
        question = Question.objects.create(
            stage=self.stage,
            index=0,
            title="Sample Question",
            form={"question": "What is 2+2?"},
            correct_answer={"answer": 4},
        )
        self.assertEqual(question.stage, self.stage)
        self.assertEqual(question.title, "Sample Question")
        self.assertEqual(question.form, {"question": "What is 2+2?"})
        self.assertEqual(question.correct_answer, {"answer": 4})


class QuestionAttachmentModelTest(TestCase):
    def setUp(self):
        self.volume = Volume.objects.create(
            title="Sample Volume", description="This is a sample volume."
        )
        self.stage = Stage.objects.create(volume=self.volume, type=StageType.TEST)
        self.question = Question.objects.create(
            stage=self.stage,
            index=0,
            title="Sample Question",
            form={"question": "What is 2+2?"},
            correct_answer={"answer": 4},
        )

    def test_create_question_attachment(self):
        attachment = QuestionAttachment.objects.create(
            question=self.question,
            type=QuestionAttachmentType.OTHER,
        )
        self.assertEqual(attachment.question, self.question)
        self.assertEqual(attachment.type, QuestionAttachmentType.OTHER)


class VolumeSerializerTest(TestCase):
    def setUp(self):
        # Create a Volume instance
        self.volume = Volume.objects.create(
            title="Test Volume", description="Test Description"
        )

        # Create stages associated with the volume
        self.theory_stage = Stage.objects.create(
            volume=self.volume, type=StageType.THEORY
        )
        self.test_stage = Stage.objects.create(volume=self.volume, type=StageType.TEST)

        # Create tasks for the theory stage
        self.task1 = Task.objects.create(
            stage=self.theory_stage, complete=True
        )  # Completed task
        self.task2 = Task.objects.create(
            stage=self.theory_stage, complete=True
        )  # Incomplete task

        # Create tasks for the test stage
        self.task3 = Task.objects.create(
            stage=self.test_stage, complete=True
        )  # Completed task

    def test_volume_serializer_progress(self):
        # Serialize the volume
        serializer = VolumeSerializer(self.volume)

        # Get the expected progress
        expected_total_tasks = 2  # 1 completed + 1 incomplete in theory stage
        expected_completed_tasks = 2  # 2 completed (1 from theory + 1 from test)
        expected_progress = (
            (expected_completed_tasks / expected_total_tasks) * 100
            if expected_total_tasks > 0
            else 0
        )

        # Assert that the progress in the serialized data matches the expected value
        self.assertEqual(serializer.data["progress"], expected_progress)


class TaskViewSetTests(APITestCase):

    def setUp(self):
        # Create necessary objects for testing
        self.volume = Volume.objects.create(
            title="Volume 1", description="Description of Volume 1"
        )
        self.stage = Stage.objects.create(
            volume=self.volume, type="TH", richtext="", json_form={}
        )

        self.user1 = CustomUser.objects.create_user(
            username="user1", password="password1"
        )
        self.user2 = CustomUser.objects.create_user(
            username="user2", password="password2"
        )

        self.task = Task.objects.create(
            stage=self.stage,
            assignee=self.user1,
            complete=False,
            total_count=10,
            successful_count=5,
            last_score=75,  # Initial score
        )
        self.url = reverse("okutool-task-submit", kwargs={"pk": self.task.pk})

    def test_other_user_cannot_submit_task(self):
        self.client.login(username="user2", password="password2")  # Log in as user2
        response = self.client.post(self.url, {"new_score": 85})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["detail"], "Not allowed to submit this task.")
        self.client.logout()

    def test_assignee_can_submit_task_with_high_score(self):
        self.client.login(username="user1", password="password1")  # Log in as user1
        response = self.client.post(self.url, {"new_score": 85})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.task.refresh_from_db()
        self.assertTrue(self.task.complete)
        self.assertEqual(self.task.total_count, 11)  # Incremented by 1
        self.assertEqual(self.task.successful_count, 6)  # Incremented by 1
        self.assertEqual(self.task.last_score, 85)  # Updated to new_score
        self.client.logout()

    def test_assignee_can_submit_task_with_low_score(self):
        self.client.login(username="user1", password="password1")  # Log in as user1
        response = self.client.post(self.url, {"new_score": 75})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.task.refresh_from_db()
        self.assertFalse(self.task.complete)
        self.assertEqual(self.task.total_count, 11)  # Incremented by 1
        self.assertEqual(self.task.successful_count, 5)  # Remains the same
        self.assertEqual(self.task.last_score, 75)  # Updated to new_score
        self.client.logout()

    def test_task_already_submitted(self):
        self.task.complete = True
        self.task.save()
        self.client.login(username="user1", password="password1")  # Log in as user1
        response = self.client.post(self.url, {"new_score": 85})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "task-already-submitted")
        self.client.logout()

    def test_submit_task_without_new_score(self):
        self.client.login(username="user1", password="password1")  # Log in as user1
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "new_score is required.")
        self.client.logout()
