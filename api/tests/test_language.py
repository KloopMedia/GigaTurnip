from rest_framework import status
from rest_framework.test import APIClient

from api.models import *
from api.tests import GigaTurnipTestHelper, to_json


class LanguageTest(GigaTurnipTestHelper):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.lang_ru = Language.objects.create(
            code="ru",
            name="Russian"
        )
        cls.lang_ky = Language.objects.create(
            code="ky",
            name="Kyrgyz"
        )

        cls.lang_fr = Language.objects.create(
            code="fr",
            name="French"
        )

    def test_list_languages_api_auth(self):
        response = self.get_objects("language-list")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = to_json(response.content)
        self.assertEqual(content["count"], 4)
        langs_en_data = {
            "id": self.lang.id,
            "name": self.lang.name,
            "code": self.lang.code
        }
        self.assertIn(langs_en_data, content["results"])

    def test_list_languages_api_unauth(self):
        unauth_client = APIClient()
        response = self.get_objects("language-list", client=unauth_client)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = to_json(response.content)
        self.assertEqual(content["count"], 4)
        langs_en_data = {
            "id": self.lang.id,
            "name": self.lang.name,
            "code": self.lang.code
        }
        self.assertIn(langs_en_data, content["results"])
