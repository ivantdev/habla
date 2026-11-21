import asyncio
import re

from fastapi import Request
from python_multipart.exceptions import MultipartParseError
from starlette.datastructures import UploadFile
from starlette.formparsers import MultiPartException, MultiPartParser
from starlette.requests import ClientDisconnect

from .audio import INPUT_RATE
from .config import Settings
from .errors import PlatformError


async def read_anchor(request: Request, settings: Settings) -> tuple[int, str, bytes, str]:
    if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() != "multipart/form-data":
        raise PlatformError(415, "UNSUPPORTED_MEDIA_TYPE", "Envía la grabación como multipart/form-data.")
    body = bytearray()
    limit = settings.max_anchor_seconds * INPUT_RATE * 2 + 8192
    try:
        async with asyncio.timeout(settings.upload_seconds):
            async for chunk in request.stream():
                if len(body) + len(chunk) > limit:
                    raise PlatformError(413, "AUDIO_TOO_LARGE", "La grabación excede el límite permitido.")
                body.extend(chunk)
    except TimeoutError as error:
        raise PlatformError(504, "UPLOAD_TIMEOUT", "La grabación no llegó a tiempo.", retryable=True) from error
    except ClientDisconnect as error:
        raise PlatformError(400, "UPLOAD_INTERRUPTED", "Se interrumpió la subida.") from error

    async def chunks():
        yield bytes(body)

    parser = MultiPartParser(request.headers, chunks(), max_files=1, max_fields=2, max_part_size=2048)
    try:
        form = await parser.parse()
    except (MultiPartException, MultipartParseError) as error:
        raise PlatformError(400, "INVALID_MULTIPART", "La grabación no tiene un formulario válido.") from error
    try:
        names = {key for key, _ in form.multi_items()}
        version, phrase, recording = form.get("state_version"), form.get("phrase_id"), form.get("audio")
        if (
            len(form.multi_items()) != 3 or names != {"state_version", "phrase_id", "audio"}
            or not isinstance(version, str) or not re.fullmatch(r"[1-9][0-9]{0,17}", version)
            or not isinstance(phrase, str) or not 1 <= len(phrase) <= 128
            or not isinstance(recording, UploadFile)
        ):
            raise PlatformError(422, "INVALID_UPLOAD", "Envía la versión, la frase y un archivo de audio.")
        return int(version), phrase, await recording.read(), recording.content_type or ""
    finally:
        await form.close()
