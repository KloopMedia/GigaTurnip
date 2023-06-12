from api.tests import GigaTurnipTestHelper

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
