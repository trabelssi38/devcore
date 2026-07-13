"""IPv6 loopback proxy for Repowise on Windows.

Repowise API binds to 127.0.0.1:7337. The bundled Next.js UI and browser
settings may still call http://localhost:7337, which Windows/Node can resolve
to ::1 first. This proxy makes ::1:7337 forward to 127.0.0.1:7337.
"""

from __future__ import annotations

import asyncio
import contextlib
import signal

LISTEN_HOST = "::1"
LISTEN_PORT = 7337
TARGET_HOST = "127.0.0.1"
TARGET_PORT = 7337


async def pipe(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        while data := await reader.read(65536):
            writer.write(data)
            await writer.drain()
    except (ConnectionError, asyncio.CancelledError):
        pass
    finally:
        writer.close()
        with contextlib.suppress(Exception):
            await writer.wait_closed()


async def handle_client(
    client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter
) -> None:
    try:
        target_reader, target_writer = await asyncio.open_connection(
            TARGET_HOST, TARGET_PORT
        )
    except Exception:
        client_writer.close()
        with contextlib.suppress(Exception):
            await client_writer.wait_closed()
        return

    left = asyncio.create_task(pipe(client_reader, target_writer))
    right = asyncio.create_task(pipe(target_reader, client_writer))
    done, pending = await asyncio.wait(
        {left, right}, return_when=asyncio.FIRST_COMPLETED
    )
    for task in pending:
        task.cancel()
    for task in done:
        with contextlib.suppress(Exception):
            task.result()


async def main() -> None:
    server = await asyncio.start_server(
        handle_client,
        LISTEN_HOST,
        LISTEN_PORT,
        family=__import__("socket").AF_INET6,
    )

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, stop.set)

    async with server:
        await stop.wait()


if __name__ == "__main__":
    asyncio.run(main())
