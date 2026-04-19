import itertools
import json
import re
from pathlib import Path

from playwright.async_api import async_playwright
import requests
import tqdm

from oreilly_pdf_downloader.pdf_printer import PDFPrinter

from .book import Book, Asset


class BookDownloader:
    CSS_FONT_URL_PAT = re.compile(r"""src:url\(['"]?(.*?\.(otf|woff2|woff|ttf))['"]?\)""")

    def __init__(self) -> None:
        self.session = requests.Session()
        self._setup_session()

        self._working_book: Book | None = None

    @property
    def book(self) -> Book:
        if self._working_book is None:
            raise ValueError('No book is currently being worked on.')
        return self._working_book

    def _get(self, *args, **kwargs) -> requests.Response:
        resp = self.session.get(*args, **kwargs)
        resp.raise_for_status()
        return resp

    def _setup_session(self) -> None:
        self.session.headers.update(
            {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:149.0) Gecko/20100101 Firefox/149.0',
                'Origin': 'https://learning.oreilly.com',
                'Referer': 'https://learning.oreilly.com/',
            }
        )

        if Path('cookie.json').exists():
            with open('cookie.json', 'r') as f:
                cookies = json.load(f)
        else:
            cookies = json.loads(input('Enter your cookies as a JSON string: '))

        self.session.cookies.update(cookies)

    async def download_book(self, isbn: str) -> None:
        self._setup_book(isbn)

        # [TODO] use logger
        print(f'Start downloading the book: {self.book.title}')

        for i in tqdm.tqdm(itertools.count(1), total=self.book.pages, desc='Downloading Chapters'):
            chapter_url = self.book.get_chapter_url(i)
            has_next = self._fetch_chapter(chapter_url)
            if not has_next:
                break

        async with async_playwright() as pw, PDFPrinter(pw) as printer:
            await printer.print_book(self.book)

        print(f'Book "{self.book.title}" downloaded successfully.')
        self._working_book = None

    def _setup_book(self, isbn: str) -> None:
        book = Book(isbn)
        try:
            metadata = self._get(book.meta_url).json()
            spine_metadata = self._get(metadata['spine']).json()
        except requests.exceptions.HTTPError as e:
            raise ValueError(f'Failed to fetch the metadata of the book {isbn}: {e}')

        book.set_metadata(metadata['title'], spine_metadata['count'])
        book.setup_dirs()
        self._working_book = book

    def _fetch_chapter(self, url: str) -> bool:
        metadata = self._get(url).json()

        file = self.book.src_dir / metadata['content_url'].rsplit('/', 1)[1]
        has_next = metadata['related_assets']['next_chapter'] is not None
        if file.exists():
            # print(f'Chapter already exists: {file}')
            return has_next

        assets = self._fetch_related_assets(metadata['related_assets'])

        title = metadata['title']
        content = self._get(metadata['content_url']).text
        rendered_html = self.book.render_chapter(title, content, assets)

        with open(file, 'w') as f:
            f.write(rendered_html)

        return has_next

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

    def _download(self, url: str, filename: Path, mode: str, overwrite=False) -> None:
        if filename.exists() and not overwrite:
            return

        with open(filename, mode) as f:
            resp = self._get(url)
            content = resp.content if 'b' in mode else resp.text
            f.write(content)

        # print('downloaded', filename)

    def _download_fonts_from_css(self, css: str, base_url: str) -> None:
        font_urls = self.CSS_FONT_URL_PAT.finditer(css)
        for font in tqdm.tqdm(font_urls, desc='Fetching Fonts', total=40, leave=False):
            self._download(f'{base_url}/{font[1]}', self.book.asset_dir / font[1], 'wb')
