from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase, APIClient

from api.tests import GigaTurnipTestHelper


class AuthTest(GigaTurnipTestHelper):

    def test_generate_token(self):
        response = self.client.get(reverse("auth-my-token"))

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        key = Token.objects.get(user=self.user).key
        self.assertEqual(response.data["token"], key)

    def test_retrieve_token(self):
        token, _ = Token.objects.get_or_create(user=self.user)

        response = self.client.get(reverse("auth-my-token"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["token"], token.key)

    def test_unauth_user(self):
        client = APIClient()
        token, _ = Token.objects.get_or_create(user=self.user)

        response = client.get(reverse("auth-my-token"))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
