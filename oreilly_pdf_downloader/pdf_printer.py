import asyncio
import logging
from pathlib import Path

import tqdm
from playwright.async_api import Browser, Playwright
from pypdf import PdfWriter

from .book import Book
from .config import Config
from .log_utils import log_step, with_log
from .utils import tqdm_gather, wrap_sync

logger = logging.getLogger(__name__)


class PDFPrinter:
    def __init__(self, pw: Playwright, config: Config) -> None:
        self.chromium = pw.chromium
        self.browser: Browser | None = None
        self.sem = asyncio.Semaphore(10)
        logger.debug(f'Initializing PDFPrinter with config: {config}')
        self.config = config

    @with_log(logger, 'Launching Playwright Chromium browser', level=logging.DEBUG)
    async def __aenter__(self):
        self.browser = await self.chromium.launch()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.browser:
            with log_step(logger, 'Closing Playwright Chromium browser', level=logging.DEBUG):
                await self.browser.close()

    async def print_book(self, book: Book):
        with log_step(logger, f'Printing chapters for book [{book.isbn}]', level=logging.INFO):
            all_chapters = (ch for ch in book.src_dir.iterdir() if ch.is_file())
            results = await tqdm_gather(
                *(self._print_one_chapter(chapter, book.pdf_dir) for chapter in all_chapters),
                return_exceptions=True,
                desc='Printing Chapters',
            )
            self._check_for_exception(results)

        self._collect_to_book(book)

    @with_log(logger, 'Merging chapters into final book PDF for [{book.isbn}]', level=logging.INFO)
    def _collect_to_book(self, book: Book):
        merger = PdfWriter()
        chapter_pdfs = sorted(book.pdf_dir.glob('chapters/*.pdf'), key=lambda p: int(p.stem.split('_')[0]))
        for pdf in tqdm.tqdm(chapter_pdfs, desc='Merging Chapters'):
            merger.append(pdf)
        merger.write(book.pdf_dir / f'{book.title}.pdf')

    async def _print_one_chapter(self, html_path: Path, pdf_dir: Path):
        if not self.browser:
            logger.error('Browser instance is not available. Cannot print chapter.')
            raise RuntimeError('Browser is not initialized.')

        pdf_path = pdf_dir / 'chapters' / html_path.with_suffix('.pdf').name
        async with (
            self.sem,
            wrap_sync(log_step(logger, f'Printing chapter from {html_path} to {pdf_path}', level=logging.DEBUG)),
        ):
            context = await self.browser.new_context()
            page = await context.new_page()
            await page.goto(f'file://{html_path.absolute()}')
            w, h = self.config.page_size
            await page.pdf(path=pdf_path, width=f'{w}mm', height=f'{h}mm')
            await context.close()

    def _check_for_exception(self, results: list[BaseException | None]) -> None:
        for i, result in enumerate(results, 1):
            if isinstance(result, Exception):
                logger.error(f'Error printing chapter {i}: {result}')
