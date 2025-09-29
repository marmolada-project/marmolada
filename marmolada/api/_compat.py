from starlette import status

if not hasattr(status, "HTTP_422_UNPROCESSABLE_CONTENT"):  # pragma: no cover
    # starlette < 0.48
    status.HTTP_422_UNPROCESSABLE_CONTENT = status.HTTP_422_UNPROCESSABLE_ENTITY
