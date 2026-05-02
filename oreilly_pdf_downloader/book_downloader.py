import json
import logging
import re
from pathlib import Path

import requests
import tqdm
from playwright.async_api import async_playwright

from .book import Asset, Book
from .config import DownloaderConfig
from .log_utils import log_step, with_log
from .pdf_printer import PDFPrinter

logger = logging.getLogger(__name__)


class BookDownloader:
    CSS_FONT_URL_PAT = re.compile(r"""src:url\(['"]?(.*?\.(otf|woff2|woff|ttf))['"]?\)""")

    def __init__(self, config: DownloaderConfig) -> None:
        logger.debug(f'Initializing BookDownloader with config: {config}')

        self._config = config
        self._working_book: Book | None = None

        self.session = requests.Session()
        self._setup_session()

    @property
    def book(self) -> Book:
        if self._working_book is None:
            logger.warning('No book is currently being worked on.')
            raise ValueError('No book is currently being worked on.')
        return self._working_book

    def _get(self, *args, **kwargs) -> requests.Response:
        logger.debug(f'GET {args[0]} with params {kwargs.get("params", {})}')
        resp = self.session.get(*args, **kwargs)
        if resp.ok:
            logger.debug(f'Got successful response from {resp.url}. Status: {resp.status_code}')
        else:
            logger.error(f'HTTP request failed: {resp.status_code} {resp.reason} for {resp.url}')
        resp.raise_for_status()
        return resp

    @with_log(logger, 'Setting up HTTP session', level=logging.INFO)
    def _setup_session(self) -> None:
        with log_step(logger, 'Setting HTTP headers', level=logging.DEBUG):
            self.session.headers.update(
                {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:149.0) Gecko/20100101 Firefox/149.0',
                    'Origin': 'https://learning.oreilly.com',
                    'Referer': 'https://learning.oreilly.com/',
                }
            )

        with log_step(logger, 'Setting cookies', level=logging.DEBUG):
            if Path('cookie.json').exists():
                logger.info('Loading cookies from cookie.json')
                with open('cookie.json', 'r') as f:
                    cookies = json.load(f)
            else:
                logger.info('cookie.json not found. Try to get cookies from stdin.')
                cookies = json.loads(input('Enter your cookies as a JSON string: '))
            self.session.cookies.update(cookies)

    @with_log(logger, 'Downloading book [{isbn}] (test run = {self._config.test_run})', level=logging.INFO)
    async def download_book(self, isbn: str) -> None:
        self._setup_book(isbn)

        print(f'Start downloading the book: {self.book.title}')
        batch_url = self.book.startpoint_url
        with (
            log_step(logger, f'Downloading chapters. Total: {self.book.pages}', level=logging.INFO),
            tqdm.tqdm(total=self.book.pages, desc='Downloading Chapters') as pbar,
        ):
            while batch_url is not None:
                batch_url = self._fetch_chapter_by_batch(batch_url, pbar, test_run=self._config.test_run)

        async with async_playwright() as pw, PDFPrinter(pw, self._config.page_size) as printer:
            await printer.print_book(self.book)

        print(f'Book "{self.book.title}" downloaded successfully.')
        self._working_book = None

    @with_log(logger, 'Setting up book metadata for [{isbn}]', level=logging.DEBUG)
    def _setup_book(self, isbn: str) -> None:
        book = Book(isbn)

        with log_step(logger, f'Fetching metadata for [{isbn}]', level=logging.DEBUG):
            metadata = self._get(book.meta_url).json()
            spine_metadata = self._get(metadata['spine']).json()

        book.set_metadata(metadata['title'], spine_metadata['count'])
        book.setup_dirs()
        self._working_book = book

    @with_log(logger, 'Fetching batch of chapters from {url}', level=logging.DEBUG)
    def _fetch_chapter_by_batch(self, url: str, pbar: tqdm.tqdm, test_run=False) -> str | None:
        metadata = self._get(url).json()

        for chapter in metadata['results']:
            self._fetch_one_chapter(chapter)
            pbar.update(1)

            if test_run and pbar.n >= 8:
                logger.info('Test run limit reached (8 chapters). Stopping download.')
                return None

        return metadata['next']

    @with_log(logger, 'Fetching chapter from {metadata[content_url]}', level=logging.DEBUG)
    def _fetch_one_chapter(self, metadata: dict) -> None:
        chapter_num = metadata['indexed_position']
        org_fname = Path(metadata['content_url'].rsplit('/', 1)[1]).with_suffix('.html')
        file = self.book.src_dir / f'{chapter_num:03d}_{org_fname}'
        if file.exists():
            logger.debug(f'Chapter {file} already exists. Skipping download.')
            return

        assets = self._fetch_related_assets(metadata['related_assets'])

        title = metadata['title']
        content = self._get(metadata['content_url']).text
        rendered_html = self.book.render_chapter(title, content, assets)

        with open(file, 'w') as f:
            f.write(rendered_html)

    @with_log(logger, 'Fetching related assets for chapter', level=logging.DEBUG)
    def _fetch_related_assets(self, related_assets: dict[str, list[str]]) -> Asset:
        stylesheets = self._fetch_css(related_assets['stylesheets'])
        self._fetch_images(related_assets['images'])
        # [TODO] fetch svgs
        return Asset(stylesheets=stylesheets)

    def _fetch_css(self, stylesheets: list[str]) -> list[str]:
        fetched_css = []

        for css_link in tqdm.tqdm(stylesheets, desc='Fetching CSS & Fonts', leave=False):
            base_url, css_fname = css_link.rsplit('/', 1)
            saved_filename = self.book.asset_dir / css_fname

            self._download(css_link, saved_filename, 'w')
            with open(saved_filename, 'r') as f:
                css_content = f.read()
            self._download_fonts_from_css(css_content, base_url)

            rel_path = str(saved_filename.relative_to(self.book.src_dir))
            fetched_css.append(rel_path)

        return fetched_css

    def _fetch_images(self, images: list[str]) -> None:
        for img in tqdm.tqdm(images, desc='Fetching Images', leave=False):
            self._download(img, self.book.asset_dir / img.rsplit('/', 1)[1], 'wb')

    @with_log(logger, 'Downloading {url} to {filename}', level=logging.DEBUG)
    def _download(self, url: str, filename: Path, mode: str, overwrite=False) -> None:
        # [TODO] cache in set() -> new class for cache
        if filename.exists() and not overwrite:
            logger.debug(f'File {filename} already exists. Skipping download.')
            return

        with open(filename, mode) as f:
            resp = self._get(url)
            content = resp.content if 'b' in mode else resp.text
            f.write(content)

    def _download_fonts_from_css(self, css: str, base_url: str) -> None:
        font_urls = self.CSS_FONT_URL_PAT.finditer(css)
        for font in tqdm.tqdm(font_urls, desc='Fetching Fonts', total=40, leave=False):
            self._download(f'{base_url}/{font[1]}', self.book.asset_dir / font[1], 'wb')
