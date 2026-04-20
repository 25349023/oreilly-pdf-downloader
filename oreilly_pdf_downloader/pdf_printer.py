import asyncio
import logging
from pathlib import Path

import tqdm
from playwright.async_api import Browser, Playwright
from pypdf import PdfWriter

from .book import Book
from .utils import tqdm_gather

logger = logging.getLogger(__name__)


class PDFPrinter:
    def __init__(self, pw: Playwright) -> None:
        self.chromium = pw.chromium
        self.browser: Browser | None = None
        self.sem = asyncio.Semaphore(10)

    async def __aenter__(self):
        logger.debug('Launching Playwright Chromium browser for PDF printing.')
        self.browser = await self.chromium.launch()
        logger.debug('Chromium browser launched successfully.')
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.browser:
            logger.debug('Closing Chromium browser.')
            await self.browser.close()
            logger.debug('Chromium browser closed successfully.')

    async def print_book(self, book: Book):
        logger.info(f'Starting to print the book: {book.title}')
        results = await tqdm_gather(
            *(self._print_one_chapter(chapter, book.pdf_dir) for chapter in book.src_dir.glob('*.html')),
            return_exceptions=True,
            desc='Printing Chapters',
        )
        self._check_for_exception(results)

        logger.info(f'Finished printing chapters for "{book.title}". Starting to merge into a single PDF.')
        self._collect_to_book(book)
        logger.info(f'Book "{book.title}" printed and merged successfully.')

    def _collect_to_book(self, book: Book):
        merger = PdfWriter()
        chapter_pdfs = sorted(book.pdf_dir.glob('chapters/*.pdf'), key=lambda p: int(p.stem.split('-')[-1]))
        for pdf in tqdm.tqdm(chapter_pdfs, desc='Merging Chapters'):
            merger.append(pdf)
        merger.write(book.pdf_dir / f'{book.title}.pdf')

    async def _print_one_chapter(self, html_path: Path, pdf_dir: Path):
        if not self.browser:
            logger.error('Browser instance is not available. Cannot print chapter.')
            raise RuntimeError('Browser is not initialized.')

        async with self.sem:
            logger.debug(f'Printing chapter from {html_path} to PDF.')
            context = await self.browser.new_context()
            page = await context.new_page()
            await page.goto(f'file://{html_path.absolute()}')
            pdf_path = pdf_dir / 'chapters' / html_path.with_suffix('.pdf').name
            await page.pdf(path=pdf_path, width='185mm', height='230mm')
            await context.close()
            logger.debug(f'Finished printing chapter to {pdf_path}.')

    def _check_for_exception(self, results: list[BaseException | None]) -> None:
        for i, result in enumerate(results, 1):
            if isinstance(result, Exception):
                logger.error(f'Error printing chapter {i}: {result}')
