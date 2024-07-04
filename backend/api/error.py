from rest_framework.exceptions import APIException
from rest_framework.status import HTTP_404_NOT_FOUND


class ValidationError404(APIException):
    status_code = HTTP_404_NOT_FOUND
