import json

from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from api.models import *
from api.tests import GigaTurnipTestHelper, to_json


class CampaignTest(GigaTurnipTestHelper):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.unauth_client = APIClient()

    def test_list_open_campaigns_unauth(self):
        self.campaign.open = True
        self.campaign.save()
        self.generate_new_basic_campaign("Pepsi")

        response = self.get_objects("campaign-list", client=self.unauth_client)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_campaign_detail_open_unauth(self):
        self.campaign.open = True
        self.campaign.sms_phone = "+996123123123"
        self.campaign.save()

        response = self.get_objects("campaign-detail", client=self.unauth_client,
                                    pk=self.campaign.id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("sms_phone", response.data)
        self.assertEqual(response.data["sms_phone"], "+996123123123")

    def test_campaign_detail_closed_unauth(self):
        response = self.get_objects("campaign-detail", client=self.unauth_client,
                                    pk=self.campaign.id)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_campaign_list_open_auth(self):
        self.campaign.open = True
        self.campaign.save()
        self.generate_new_basic_campaign("Pepsi")
        self.assertEqual(Campaign.objects.count(), 2)

        response = self.get_objects("campaign-list")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_campaign_list_detail_auth(self):
        self.campaign.open = True
        self.campaign.save()
        self.generate_new_basic_campaign("Pepsi")
        self.assertEqual(Campaign.objects.count(), 2)

        response = self.get_objects("campaign-detail", pk=self.campaign.id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], self.campaign.name)

    def test_campaign_list_managers_campaigns(self):
        [i.delete() for i in self.user.ranks.all()]
        self.assertEqual(Campaign.objects.count(), 1)
        self.user.managed_campaigns.add(self.campaign)

        response = self.get_objects("campaign-list", client=self.client)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_list(self):
        pepsi_data = self.generate_new_basic_campaign(name="Pepsi")
        pepsi_data["campaign"].visible = False
        pepsi_data["campaign"].open = True
        pepsi_data["campaign"].save()

        response = self.get_objects("campaign-list")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], self.campaign.id)

    def test_join_invisible_and_open_campaign(self):
        pepsi_data = self.generate_new_basic_campaign(name="Pepsi")
        pepsi_data["campaign"].visible = False
        pepsi_data["campaign"].open = True
        pepsi_data["campaign"].save()


        response = self.employee_client.get(
            reverse("campaign-join-campaign", kwargs={"pk": pepsi_data["campaign"].id})
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_join_invisible_and_not_open_campaign(self):
        pepsi_data = self.generate_new_basic_campaign(name="Pepsi")
        pepsi_data["campaign"].visible = False
        pepsi_data["campaign"].open = False
        pepsi_data["campaign"].save()


        response = self.employee_client.get(
            reverse("campaign-join-campaign", kwargs={"pk": pepsi_data["campaign"].id})
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_campaign_serializer(self):
        # join employee to campaign
        self.campaign.open = True
        self.campaign.save()
        response = self.employee_client.get(
            reverse("campaign-join-campaign", kwargs={"pk": self.campaign.id})
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        Notification.objects.create(
            title="title",
            campaign=self.campaign,
            target_user=self.employee
        )
        Notification.objects.create(
            title="title",
            campaign=self.campaign,
            rank=self.default_rank
        )
        Notification.objects.create(
            title="title",
            campaign=self.campaign,
        )
        response = self.get_objects("campaign-list",
                                    client=self.employee_client)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            to_json(response.content)["results"][0]["notifications_count"], 2)

        response = self.client.get(
            reverse("campaign-join-campaign", kwargs={"pk": self.campaign.id})
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response = self.get_objects("campaign-list")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            to_json(response.content)["results"][0]["notifications_count"], 1)

        new_user = CustomUser.objects.create_user(username="new_new",
                                                  email='new_new@email.com',
                                                  password='123')
        new_user_client = self.create_client(new_user)
        response = self.get_objects("campaign-list", client=new_user_client)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            to_json(response.content)["results"][0]["notifications_count"], 0)

        # Add employee to management
        self.employee.managed_campaigns.add(self.campaign)
        response = self.get_objects("campaign-list",
                                    client=self.employee_client)
        # Employee must be a manager
        self.assertEqual(
            to_json(response.content)["results"][0]["is_manager"], True)
        response = self.get_objects("campaign-list",
                                    client=new_user_client)
        # New user must not be a manager
        self.assertEqual(
            to_json(response.content)["results"][0]["is_manager"], False)

    def test_campaign_filters_by_language(self):
        campaign_en_data = self.generate_new_basic_campaign(name="Pepsi")
        campaign_ru_data = self.generate_new_basic_campaign(name="Добрый Кола")
        campaign_ky_data = self.generate_new_basic_campaign(name="Джакшы Кола")

        lang_ru = Language.objects.create(
            name="Russian",
            code="ru"
        )
        lang_ky = Language.objects.create(
            name="Kyrgyz",
            code="ky"
        )

        campaign_ru_data["campaign"].languages.add(lang_ru)
        campaign_ky_data["campaign"].languages.add(lang_ky)

        campaign_ru_data["campaign"].open = True
        campaign_ky_data["campaign"].open = True

        campaign_ru_data["campaign"].save()
        campaign_ky_data["campaign"].save()

        response = self.get_objects("campaign-list")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(to_json(response.content)['count'], 3)

        response = self.get_objects("campaign-list",
                                    params={"languages__code": "ru"}
                                    )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(to_json(response.content)['count'], 1)
        self.assertEqual(to_json(response.content)['results'][0]['id'],
                         campaign_ru_data['campaign'].id)

        response = self.get_objects("campaign-list",
                                    params={"languages__code": "ky"}
                                    )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'],
                         campaign_ky_data['campaign'].id)

        response = self.get_objects("campaign-list",
                                    params={"languages__code": "en"}
                                    )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 3)
        for i in Campaign.objects.filter(open=True).values_list("id", flat=True):
            self.assertIn(i, [_['id'] for _ in
                              response.data['results']])

    def test_filter_campaign_by_categories_in(self):
        products_category = Category.objects.create(
            name="Producs"
        )

        e_commerce_category = Category.objects.create(
            name="E-Commerce"
        )
        e_commerce_category.parents.add(self.category)

        electronics_category = Category.objects.create(
            name="Electronics"
        )
        pcs_category = Category.objects.create(
            name="Personal computers"
        )
        pcs_devices_category = Category.objects.create(
            name="Personal computers attributes."
        )
        pcs_mouses_category = Category.objects.create(
            name="Mouses"
        )

        electronics_category.out_categories.add(pcs_category)
        electronics_category.out_categories.add(pcs_devices_category)
        pcs_devices_category.out_categories.add(pcs_mouses_category)

        answer = [
            {
                'id': self.category.id,
                'name': self.category.name,
                'out_categories': [
                    e_commerce_category.id
                ]},
            {
                'id': e_commerce_category.id,
                'name': e_commerce_category.name,
                'out_categories': []},
            {
                'id': electronics_category.id,
                'name': electronics_category.name,
                'out_categories': [
                    pcs_category.id,
                    pcs_devices_category.id
                ]
            },
            {
                'id': pcs_mouses_category.id,
                'name': pcs_mouses_category.name,
                'out_categories': []},
            {
                'id': pcs_category.id,
                'name': pcs_category.name,
                'out_categories': []
            },
            {
                'id': pcs_devices_category.id,
                'name': pcs_devices_category.name,
                'out_categories': [pcs_mouses_category.id]
            },
            {
                'id': products_category.id,
                'name': products_category.name,
                'out_categories': []
            }
        ]
        response = self.get_objects("category-list")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = to_json(response.content)
        self.assertEqual(content["count"], Category.objects.count())
        self.assertEqual(content["results"], answer)

        campaign_e_commerce = self.generate_new_basic_campaign(name="ElPay")
        campaign_products = self.generate_new_basic_campaign(name="Pepsi")
        campaign_electronics = self.generate_new_basic_campaign(name="Techno")
        campaign_pcs = self.generate_new_basic_campaign(name="Personal droid")
        campaign_pcs_attributes = self.generate_new_basic_campaign(
            name="Techno mouse")

        campaign_e_commerce["campaign"].categories.add(e_commerce_category)
        campaign_products["campaign"].categories.add(products_category)
        campaign_electronics["campaign"].categories.add(electronics_category)
        campaign_pcs["campaign"].categories.add(pcs_category)
        campaign_pcs["campaign"].categories.add(pcs_devices_category)
        campaign_pcs_attributes["campaign"].categories.add(
            pcs_devices_category)

        campaign_e_commerce['campaign'].open = True
        campaign_products['campaign'].open = True
        campaign_electronics['campaign'].open = True
        campaign_pcs['campaign'].open = True
        campaign_pcs_attributes['campaign'].open = True

        campaign_e_commerce['campaign'].save()
        campaign_products['campaign'].save()
        campaign_electronics['campaign'].save()
        campaign_pcs['campaign'].save()
        campaign_pcs_attributes['campaign'].save()

        response = self.get_objects("campaign-list",
                                    params={})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = to_json(response.content)
        self.assertEqual(content["count"], 6)

        response = self.get_objects("campaign-list",
                                    params={
                                        "categories": electronics_category.id
                                    })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = to_json(response.content)
        self.assertEqual(content["count"], 1)

        response = self.get_objects("campaign-list",
                                    params={
                                        "category_in": electronics_category.id
                                    })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = to_json(response.content)
        self.assertEqual(content["count"], 2)
        ids = [i["id"] for i in content["results"]]
        self.assertIn(campaign_pcs["campaign"].id, ids)
        self.assertIn(campaign_pcs_attributes["campaign"].id, ids)

    def test_filter_campaigns_by_country_name(self):
        rus_country = Country.objects.create(
            name="Russian"
        )
        kyz_country = Country.objects.create(
            name="Kyrgyzstan"
        )

        pepsi = self.generate_new_basic_campaign("Pepsi",
                                                 countries=[rus_country,
                                                            kyz_country])
        fanta = self.generate_new_basic_campaign("Fanta",
                                                 countries=[rus_country])
        pepsi["campaign"].open = True
        fanta["campaign"].open = True
        pepsi["campaign"].save()
        fanta["campaign"].save()

        response = self.get_objects("campaign-list", params={
            "countries__name": self.country.name}
                                    )
        # print([i.countries.all() for i in Campaign.objects.all()])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = to_json(response.content)
        # print(content)
        self.assertEqual(content["count"], 1)
        self.assertEqual(self.campaign.id, content["results"][0]["id"])

        response = self.get_objects("campaign-list", params={
            "countries__name": rus_country.name}
                                    )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = to_json(response.content)
        self.assertEqual(content["count"], 2)
        for i in [pepsi["campaign"].id, fanta["campaign"].id]:
            self.assertIn(i, [_["id"] for _ in content["results"]])
