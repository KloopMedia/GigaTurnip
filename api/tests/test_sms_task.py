import json
from base64 import b64encode, b64decode

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

    def test_smstask_creation(self):
        self.initial_stage.sms_complete_task_allow = True
        self.initial_stage.save()

        data = {
            "responses": {"answer": "hello world!"},
             "complete": False,
             "stage_id": self.initial_stage.id,
             "user_token": Token.objects.create(user=self.employee).key,
         }

        payload = {
            "sms_text": crypto_utils.rsa_encrypt(self.public_key, json.dumps(data).encode()),
            "phone": "+996555000000"
        }

        response = self.client.post(reverse("smstask-list"), data=payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(SMSTask.objects.count(), 1)
