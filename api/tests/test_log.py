import json

from rest_framework import status
from rest_framework.reverse import reverse

from api.constans import AutoNotificationConstants, TaskStageConstants, \
    CopyFieldConstants
from api.models import *
from api.tests import GigaTurnipTestHelper, to_json


class LogTest(GigaTurnipTestHelper):
    def test_logs_for_task_stages(self):
        old_count = Log.objects.count()
        self.user.managed_campaigns.add(self.campaign)

        update_js = {"name": "Rename stage"}
        url = reverse("taskstage-detail", kwargs={"pk": self.initial_stage.id})
        response = self.client.patch(url, update_js)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(old_count, 0)
        self.assertEqual(Log.objects.count(), 1)
