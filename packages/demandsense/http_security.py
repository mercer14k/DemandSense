"""Bounded ASGI body buffering, including requests without Content-Length."""

from uuid import uuid4

from starlette.responses import JSONResponse


class BodyLimitMiddleware:
    def __init__(self, app, max_bytes=11 * 1024 * 1024):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] in {"GET", "HEAD", "OPTIONS"}:
            return await self.app(scope, receive, send)
        chunks, size = [], 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            size += len(message.get("body", b""))
            if size > self.max_bytes:
                trace = str(uuid4())
                response = JSONResponse(
                    {
                        "error": {
                            "code": "payload_too_large",
                            "message": "Maximum request size is 11 MiB",
                            "trace_id": trace,
                            "details": None,
                        }
                    },
                    status_code=413,
                    headers={"X-Trace-ID": trace},
                )
                return await response(scope, receive, send)
            chunks.append(message)
            if not message.get("more_body", False):
                break
        index = 0

        async def bounded_receive():
            nonlocal index
            if index < len(chunks):
                result = chunks[index]
                index += 1
                return result
            return await receive()

        await self.app(scope, bounded_receive, send)
