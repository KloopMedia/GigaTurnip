import base64
import json
from base64 import b64encode, b64decode
from unittest.mock import patch

from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.reverse import reverse

from api.constans import TaskStageConstants
from api.models import *
from api.tests import GigaTurnipTestHelper
from api.utils import cryptography as crypto_utils


class SmsTaskTest(GigaTurnipTestHelper):

    def setUp(self):
        super(SmsTaskTest, self).setUp()
        self.user.sms_relay = True
        self.user.save()

        self.public_key, self.private_key = crypto_utils.generate_keys()

        self.initial_stage.json_schema = json.dumps({
            "type": "object",
            "properties": {
                "answer": {
                    "title": "Question 1",
                    "type": "string"
                }
            },
            "required": [
                "answer"
            ]
        })
        self.initial_stage.save()

    @patch('api.utils.cryptography.get_private_key')
    def test_sms_task_creation(self, get_private_key):
        get_private_key.return_value = self.private_key

        self.initial_stage.sms_complete_task_allow = True
        self.initial_stage.save()

        data = {
            "responses": {"answer": "hello world!"},
             "complete": False,
             "stage_id": self.initial_stage.id,
             "user_token": Token.objects.create(user=self.employee).key,
         }
        encrypted_aes_key, ciphertext = crypto_utils.encrypt_large_text(json.dumps(data), self.public_key)

        payload = {
            "ciphertext": base64.b64encode(ciphertext),
            "encrypted_aes_key": base64.b64encode(encrypted_aes_key),
            "phone": "+996555000000"
        }

        response = self.client.post(reverse("smstask-list"), data=payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(SMSTask.objects.count(), 1)
        sms_task = SMSTask.objects.first()
        self.assertEqual(sms_task.phone, payload["phone"])
        self.assertEqual(sms_task.sms_text, str(base64.b64decode(payload["ciphertext"])))
        self.assertEqual(sms_task.sms_text, str(base64.b64decode(payload["ciphertext"])))
        # self.assertEqual(sms_task.source, json.dumps(payload))
        # self.assertEqual(json.dumps(sms_task.decrypted), json.dumps(data))
        self.assertEqual(sms_task.decompressed, json.dumps(data))

        employee_tasks = self.employee.tasks.all()
        self.assertEqual(employee_tasks.count(), 1)
        self.assertTrue(employee_tasks.filter(stage=self.initial_stage))
        self.assertEqual(employee_tasks.filter(stage=self.initial_stage).first().responses, data["responses"])
        self.assertTrue(SMSTask.objects.filter(task=employee_tasks.first()))

    @patch('api.utils.cryptography.get_private_key')
    def test_sms_task_update(self, get_private_key):
        get_private_key.return_value = self.private_key

        self.initial_stage.sms_complete_task_allow = True
        self.initial_stage.save()

        case = Case.objects.create()
        task = Task.objects.create(
            assignee=self.employee,
            case=case,
            stage=self.initial_stage,
            responses={"answer": "hello world!"},
            complete=False,
        )

        data = {
            "id": task.id,
            "responses": {"answer": "updated"},
            "complete": True,
            "stage_id": self.initial_stage.id,
            "user_token": Token.objects.create(user=self.employee).key,
         }
        encrypted_aes_key, ciphertext = crypto_utils.encrypt_large_text(json.dumps(data), self.public_key)

        payload = {
            "ciphertext": base64.b64encode(ciphertext),
            "encrypted_aes_key": base64.b64encode(encrypted_aes_key),
            "phone": "+996555000000"
        }

        response = self.client.post(reverse("smstask-list"), data=payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(SMSTask.objects.count(), 1)
        sms_task = SMSTask.objects.first()
        self.assertEqual(sms_task.phone, payload["phone"])
        self.assertEqual(sms_task.sms_text, str(base64.b64decode(payload["ciphertext"])))
        self.assertEqual(sms_task.sms_text, str(base64.b64decode(payload["ciphertext"])))
        # self.assertEqual(sms_task.source, json.dumps(payload))
        # self.assertEqual(json.dumps(sms_task.decrypted), json.dumps(data))
        self.assertEqual(sms_task.decompressed, json.dumps(data))

        employee_tasks = self.employee.tasks.all()
        self.assertEqual(employee_tasks.count(), 1)
        self.assertTrue(employee_tasks.filter(stage=self.initial_stage))

        employee_task = employee_tasks.first()
        self.assertEqual(employee_task.responses, data["responses"])
        self.assertTrue(employee_task.complete)
        self.assertTrue(SMSTask.objects.filter(task=employee_tasks.first()))

    @patch('api.utils.cryptography.get_private_key')
    def test_sms_task_chain_flow(self, get_private_key):
        get_private_key.return_value = self.private_key

        self.initial_stage.sms_complete_task_allow = True
        self.initial_stage.save()

        second_stage = self.initial_stage.add_stage(
            TaskStage(
                name="new online stage",
                json_schema=self.initial_stage.json_schema,
                assign_user_from_stage=self.initial_stage,
                assign_user_by=TaskStageConstants.STAGE,
            )
        )

        token = Token.objects.create(user=self.employee)

        data_1 = {
            "responses": {"answer": "hello world!"},
             "complete": False,
             "stage_id": self.initial_stage.id,
             "user_token": token.key,
         }
        encrypted_aes_key_1, ciphertext_1 = crypto_utils.encrypt_large_text(json.dumps(data_1), self.public_key)

        payload_1 = {
            "ciphertext": base64.b64encode(ciphertext_1),
            "encrypted_aes_key": base64.b64encode(encrypted_aes_key_1),
            "phone": "+996555000000"
        }

        response_1 = self.client.post(reverse("smstask-list"), data=payload_1, format="json")

        self.assertEqual(response_1.status_code, status.HTTP_201_CREATED)
        self.assertEqual(SMSTask.objects.count(), 1)
        sms_task = SMSTask.objects.first()
        self.assertEqual(sms_task.phone, payload_1["phone"])
        self.assertEqual(sms_task.sms_text, str(base64.b64decode(payload_1["ciphertext"])))
        self.assertEqual(sms_task.sms_text, str(base64.b64decode(payload_1["ciphertext"])))
        # self.assertEqual(sms_task.source, json.dumps(payload))
        # self.assertEqual(json.dumps(sms_task.decrypted), json.dumps(data))
        self.assertEqual(sms_task.decompressed, json.dumps(data_1))

        employee_tasks = self.employee.tasks.all()
        self.assertEqual(employee_tasks.count(), 1)
        self.assertTrue(employee_tasks.filter(stage=self.initial_stage))
        self.assertEqual(employee_tasks.filter(stage=self.initial_stage).first().responses, data_1["responses"])
        self.assertTrue(SMSTask.objects.filter(task=employee_tasks.first()))

        data_2 = {
            "id": employee_tasks.first().id,
            "responses": {"answer": "updated text"},
             "complete": True,
             "stage_id": self.initial_stage.id,
             "user_token": token.key,
         }
        encrypted_aes_key_2, ciphertext_2 = crypto_utils.encrypt_large_text(json.dumps(data_2), self.public_key)

        payload_2 = {
            "ciphertext": base64.b64encode(ciphertext_2),
            "encrypted_aes_key": base64.b64encode(encrypted_aes_key_2),
            "phone": "+996555000000"
        }
        response_update = self.client.post(reverse("smstask-list"), data=payload_2, format="json")

        self.assertEqual(response_update.status_code, status.HTTP_201_CREATED)
        self.assertEqual(SMSTask.objects.count(), 2)
        sms_task = SMSTask.objects.order_by("-created_at").first()
        self.assertEqual(sms_task.phone, payload_1["phone"])
        self.assertEqual(sms_task.sms_text, str(base64.b64decode(payload_2["ciphertext"])))
        self.assertEqual(sms_task.sms_text, str(base64.b64decode(payload_2["ciphertext"])))
        # self.assertEqual(sms_task.source, json.dumps(payload))
        # self.assertEqual(json.dumps(sms_task.decrypted), json.dumps(data))
        self.assertEqual(sms_task.decompressed, json.dumps(data_2))


        employee_tasks = self.employee.tasks.all()
        self.assertEqual(employee_tasks.count(), 2)
        first_task = self.employee.tasks.filter(stage=self.initial_stage).first()
        self.assertTrue(first_task.complete)
        self.assertEqual(first_task.responses, data_2["responses"])
        self.assertTrue(SMSTask.objects.filter(task=first_task))

        second_task = employee_tasks.filter(stage=second_stage).first()
        self.assertFalse(second_task.complete)

        self.assertEqual(first_task.case.id, second_task.case.id)
