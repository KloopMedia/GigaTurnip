import json

from rest_framework import status
from rest_framework.reverse import reverse

from api.constans import AutoNotificationConstants, TaskStageConstants, \
    CopyFieldConstants
from api.models import *
from api.tests import GigaTurnipTestHelper, to_json


class CampaignTest(GigaTurnipTestHelper):

    def test_list_campaign_serializer(self):
        # join employee to campaign
        self.campaign.open = True
        self.campaign.save()
        response = self.employee_client.get(
            reverse("campaign-join-campaign", kwargs={"pk": self.campaign.id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

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
        self.assertEqual(response.status_code, status.HTTP_200_OK)

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

        campaign_ru_data["campaign"].language = lang_ru
        campaign_ky_data["campaign"].language = lang_ky

        campaign_ru_data["campaign"].open = True
        campaign_ky_data["campaign"].open = True

        campaign_ru_data["campaign"].save()
        campaign_ky_data["campaign"].save()

        response = self.get_objects("campaign-list")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(to_json(response.content)['count'], 4)

        response = self.get_objects("campaign-list",
                                    params={"language__code": "ru"}
                                    )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(to_json(response.content)['count'], 1)
        self.assertEqual(to_json(response.content)['results'][0]['id'],
                         campaign_ru_data['campaign'].id)

        response = self.get_objects("campaign-list",
                                    params={"language__code": "ky"}
                                    )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(to_json(response.content)['count'], 1)
        self.assertEqual(to_json(response.content)['results'][0]['id'],
                         campaign_ky_data['campaign'].id)

        response = self.get_objects("campaign-list",
                                    params={"language__code": "en"}
                                    )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(to_json(response.content)['count'], 2)
        for i in [campaign_en_data['campaign'].id, self.campaign.id]:
            self.assertIn(i, [_['id'] for _ in
                              to_json(response.content)['results']])

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
