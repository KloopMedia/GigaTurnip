from rest_framework.views import exception_handler
from rest_framework.exceptions import APIException


class CustomApiException(APIException):

    detail = None
    status_code = None

    def __init__(self, status_code, message):
        CustomApiException.status_code = status_code
        CustomApiException.detail = message


def custom_exception_handler(exc, context):

    response = exception_handler(exc, context)

    if response is not None:
        response.data['status_code'] = response.status_code

        response.data['message'] = response.data['detail']
        del response.data['detail']

    return response
