from rest_framework import status
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return response

    detail = response.data
    message = "Request failed."

    if isinstance(detail, dict):
        message = detail.get("message") or detail.get("detail") or detail.get("error") or message
        if message == "Request failed.":
            for value in detail.values():
                if isinstance(value, list) and value:
                    message = str(value[0])
                    break
                if isinstance(value, str) and value.strip():
                    message = value
                    break
    elif isinstance(detail, list):
        message = str(detail[0]) if detail else "Validation failed."
    elif detail:
        message = str(detail)

    if response.status_code == status.HTTP_400_BAD_REQUEST:
        error_code = "VALIDATION_ERROR"
    elif response.status_code == status.HTTP_401_UNAUTHORIZED:
        error_code = "UNAUTHORIZED"
    elif response.status_code == status.HTTP_403_FORBIDDEN:
        error_code = "FORBIDDEN"
    elif response.status_code == status.HTTP_404_NOT_FOUND:
        error_code = "NOT_FOUND"
    else:
        error_code = "REQUEST_ERROR"

    response.data = {
        "success": False,
        "message": message,
        "error": {
            "code": error_code,
            "details": detail,
        },
    }
    return response
