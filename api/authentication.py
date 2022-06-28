from drf_firebase_auth.authentication import (
    FirebaseAuthentication,
    User,
    log)
from drf_firebase_auth.models import (
    FirebaseUser,
    FirebaseUserProvider
)
from django.utils import timezone
from firebase_admin import auth as firebase_auth
from drf_firebase_auth.utils import get_firebase_user_email
from drf_firebase_auth.settings import api_settings
from firebase_admin import auth


def get_firebase_user_phone_number(firebase_user: auth.UserRecord) -> str:
    try:
        return (
            firebase_user.phone_number
            if firebase_user.phone_number
            else firebase_user.provider_data[0].phone_number
        )
    except Exception as e:
        raise Exception(e)


class FirebaseAuthentication(FirebaseAuthentication):
    def _get_or_create_local_user(
        self,
        firebase_user: firebase_auth.UserRecord
    ) -> User:
        """
        Attempts to return or create a local User from Firebase user data
        """
        email = get_firebase_user_email(firebase_user)
        phone_number = get_firebase_user_phone_number(firebase_user)
        if email:
            log.info(f'_get_or_create_local_user - email: {email}')
        elif phone_number:
            log.info(f'_get_or_create_local_user - phone: {phone_number}')
        user = None
        try:
            if email:
                user = User.objects.get(email=email)
            elif phone_number:
                user = User.objects.get(phone_number=phone_number)
            log.info(
                f'_get_or_create_local_user - user.is_active: {user.is_active}'
            )
            if not user.is_active:
                raise Exception(
                    'User account is not currently active.'
                )
            user.last_login = timezone.now()
            user.save()
        except User.DoesNotExist as e:
            login_data = email if email else phone_number
            log.error(
                f'_get_or_create_local_user - User.DoesNotExist: {login_data}'
            )
            if not api_settings.FIREBASE_CREATE_LOCAL_USER:
                raise Exception('User is not registered to the application.')
            username = \
                api_settings.FIREBASE_USERNAME_MAPPING_FUNC(firebase_user)
            log.info(
                f'_get_or_create_local_user - username: {username}'
            )
            try:
                if email:
                    user = User.objects.create_user(
                        username=username,
                        email=email
                    )
                elif phone_number:
                    user = User.objects.create_user(
                        username=username,
                        phone_number=phone_number,

                    )
                user.last_login = timezone.now()
                if (
                        api_settings.FIREBASE_ATTEMPT_CREATE_WITH_DISPLAY_NAME
                        and firebase_user.display_name is not None
                ):
                    display_name = firebase_user.display_name.split(' ')
                    if len(display_name) == 2:
                        user.first_name = display_name[0]
                        user.last_name = display_name[1]
                user.save()
            except Exception as e:
                raise Exception(e)
        return user
