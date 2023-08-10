import base64
import json
from base64 import b64encode, b64decode
from unittest.mock import patch

from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.reverse import reverse
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
    def test_smstask_creation(self, get_private_key):
        get_private_key.return_value = self.private_key

        self.initial_stage.sms_complete_task_allow = True
        self.initial_stage.save()

        print("creating data")
        data = {
            "responses": {"answer": "hello world!"},
             "complete": False,
             "stage_id": self.initial_stage.id,
             "user_token": Token.objects.create(user=self.employee).key,
         }
        encrypted_aes_key, ciphertext = crypto_utils.encrypt_large_text(json.dumps(data), self.public_key)
        print("encrypting data")

        payload = {
            "ciphertext": base64.b64encode(ciphertext),
            "encrypted_aes_key": base64.b64encode(encrypted_aes_key),
            "phone": "+996555000000"
        }
        print("here si payload")
        print(payload)

        print("sending request")
        response = self.client.post(reverse("smstask-list"), data=payload, format="json")

        print("print here is answer")
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
    def test_smstask_update(self, get_private_key):
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

        print("creating data")
        data = {
            "id": task.id,
            "responses": {"answer": "updated"},
            "complete": True,
            "stage_id": self.initial_stage.id,
            "user_token": Token.objects.create(user=self.employee).key,
         }
        encrypted_aes_key, ciphertext = crypto_utils.encrypt_large_text(json.dumps(data), self.public_key)
        print("encrypting data")

        payload = {
            "ciphertext": base64.b64encode(ciphertext),
            "encrypted_aes_key": base64.b64encode(encrypted_aes_key),
            "phone": "+996555000000"
        }
        print("here si payload")
        print(payload)

        print("sending request")
        response = self.client.post(reverse("smstask-list"), data=payload, format="json")

        print("print here is answer")
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


