from uuid import uuid4

from .contracts import ErrorBody


class PlatformError(Exception):
    def __init__(self, status: int, code: str, message: str, *, retryable: bool = False):
        super().__init__(code)
        self.status = status
        self.code = code
        self.message = message
        self.retryable = retryable

    def body(self) -> ErrorBody:
        return ErrorBody(
            code=self.code, message=self.message, request_id=str(uuid4()), retryable=self.retryable,
        )


def not_found() -> PlatformError:
    return PlatformError(404, "NOT_FOUND", "El recurso no está disponible.")


def state_conflict() -> PlatformError:
    return PlatformError(409, "STATE_CONFLICT", "La práctica cambió. Consulta su estado actual.")
