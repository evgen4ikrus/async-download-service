import argparse
import asyncio
import logging
import os

import aiofiles
from aiohttp import web

logger = logging.getLogger(__name__)


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--logs', default=False, action='store_true', help='включить логирование;')
    parser.add_argument(
        '-d',
        '--delay',
        type=float,
        default=0,
        help='включить задержку скачивание (значение в секундах). '
             'Архив будет скачиваться частями по 100kb с заданной задержкой;'
    )
    parser.add_argument('-p', '--path', default='test_photos', help='путь к каталогу с фотографиями.')
    args = parser.parse_args()
    return args.logs, args.delay, args.path


async def archive(request):
    archive_hash = request.match_info.get('archive_hash')
    archive_path = os.path.join(folder_path, archive_hash)
    if not os.path.exists(archive_path):
        raise web.HTTPNotFound(text='Архив не существует или был удален')
    response = web.StreamResponse()
    response.headers['Content-Type'] = 'text/html'
    response.headers['Content-Disposition'] = 'attachment; filename="photos.zip"'
    await response.prepare(request)
    process = await asyncio.create_subprocess_exec(
        'zip', '-r', '-', '.',
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=archive_path
    )
    try:
        while not process.stdout.at_eof():
            chunk_size = 102400
            chunk = await process.stdout.read(chunk_size)
            logging.info('Sending archive chunk ...')
            await response.write(chunk)
            await asyncio.sleep(download_delay)
    except asyncio.CancelledError:
        logging.debug('Download was interrupted')
        raise
    finally:
        if process.returncode is None:
            process.kill()
            await process.communicate()
    return response


async def handle_index_page(request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


if __name__ == '__main__':
    enabled_logging, download_delay, folder_path = get_args()
    if not enabled_logging:
        logging.disable()
    logging.basicConfig(format=u'%(filename)s[LINE:%(lineno)d]# %(levelname)-8s [%(asctime)s]  %(message)s',
                        level=logging.DEBUG)
    app = web.Application()
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', archive),
    ])
    web.run_app(app)
