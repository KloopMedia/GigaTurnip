import json

from rest_framework import status

from api.constans import AutoNotificationConstants, TaskStageConstants, \
    CopyFieldConstants
from api.models import *
from api.tests import GigaTurnipTestHelper, to_json


class CategoryTest(GigaTurnipTestHelper):

    def test_list_categories(self):
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

