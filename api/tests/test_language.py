from api.tests import GigaTurnipTestHelper


class LanguageTest(GigaTurnipTestHelper):

    def test_list_languages(self):
        Language.objects.create(
            code="ru",
            name="Russian"
        )
        Language.objects.create(
            code="ky",
            name="Kyrgyz"
        )

        response = self.get_objects("language-list")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = to_json(response.content)
        self.assertEqual(content["count"], 3)
        langs_en_data = {
            "id": self.lang.id,
            "name": self.lang.name,
            "code": self.lang.code
        }
        self.assertIn(langs_en_data, content["results"])
