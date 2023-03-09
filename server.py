import asyncio
import datetime
import os.path

import aiofiles
from aiohttp import web


async def archive(request):
    response = web.StreamResponse()

    # Большинство браузеров не отрисовывают частично загруженный контент, только если это не HTML.
    # Поэтому отправляем клиенту именно HTML, указываем это в Content-Type.
    response.headers['Content-Type'] = 'text/html'
    response.headers['Content-Disposition'] = 'attachment; filename="photos.zip"'

    # Отправляет клиенту HTTP заголовки
    await response.prepare(request)
    archive_hash = request.match_info.get('archive_hash')
    archive_path = os.path.join('test_photos', archive_hash)
    process = await asyncio.create_subprocess_exec(
        'zip', '-r', '-', '.',
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=archive_path
    )
    while not process.stdout.at_eof():
        stdout_part = await process.stdout.read(100 * 1024)
        await response.write(stdout_part)
    return response


async def handle_index_page(request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


if __name__ == '__main__':
    app = web.Application()
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', archive),
    ])
    web.run_app(app)
