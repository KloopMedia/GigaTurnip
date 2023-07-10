import json

from rest_framework import status
from rest_framework.reverse import reverse

from api.constans import AutoNotificationConstants, TaskStageConstants
from api.models import *
from api.tests import GigaTurnipTestHelper


class SmsTaskTest(GigaTurnipTestHelper):
    def test_smstask_creation(self):
        data = {
            "phone": "799002345",
            "sms_text": "flasdjflvlkcjl3jkl4j32l243kl"
        }
        response = self.client.post(reverse("smstask-list"), data=data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.user.sms_relay = True
        self.user.save()

        response = self.client.post(reverse("smstask-list"), data=data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(SMSTask.objects.count(), 1)

        response = self.client.post(reverse("smstask-list"), data={"phone": "12"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(SMSTask.objects.count(), 1)
