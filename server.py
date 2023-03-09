import asyncio
import logging
import os

import aiofiles
from aiohttp import web

logger = logging.getLogger(__name__)


async def archive(request):
    archive_hash = request.match_info.get('archive_hash')
    archive_path = os.path.join('test_photos', archive_hash)
    if not os.path.exists(archive_path):
        raise web.HTTPNotFound(text='Архив не существует или был удален')
    response = web.StreamResponse()

    # Большинство браузеров не отрисовывают частично загруженный контент, только если это не HTML.
    # Поэтому отправляем клиенту именно HTML, указываем это в Content-Type.
    response.headers['Content-Type'] = 'text/html'
    response.headers['Content-Disposition'] = 'attachment; filename="photos.zip"'

    # Отправляет клиенту HTTP заголовки
    await response.prepare(request)

    process = await asyncio.create_subprocess_exec(
        'zip', '-r', '-', '.',
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=archive_path
    )
    try:
        while not process.stdout.at_eof():
            stdout_part = await process.stdout.read(100 * 1024)
            logging.info('Sending archive chunk ...')
            await response.write(stdout_part)
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        logging.debug('Download was interrupted')
        raise
    finally:
        pass
    return response


async def handle_index_page(request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


if __name__ == '__main__':
    logging.basicConfig(format=u'%(filename)s[LINE:%(lineno)d]# %(levelname)-8s [%(asctime)s]  %(message)s',
                        level=logging.DEBUG)
    app = web.Application()
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', archive),
    ])
    web.run_app(app)
