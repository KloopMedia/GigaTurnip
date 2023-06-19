import json

from rest_framework import status

from api.constans import AutoNotificationConstants, TaskStageConstants, \
    CopyFieldConstants
from api.models import *
from api.tests import GigaTurnipTestHelper, to_json


class CountryTest(GigaTurnipTestHelper):

    def test_list_countries(self):
        Country.objects.create(
            name="Russian"
        )
        Country.objects.create(
            name="Kyrgyzstan"
        )

        response = self.get_objects("country-list")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = to_json(response.content)
        self.assertEqual(content["count"], 3)
        country_data = {
            "id": self.country.id,
            "name": self.country.name
        }
        self.assertIn(country_data, content["results"])
