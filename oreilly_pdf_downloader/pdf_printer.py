import asyncio
from pathlib import Path

from playwright.async_api import Browser, Playwright
from pypdf import PdfWriter

from .book import Book


class PDFPrinter:
    def __init__(self, pw: Playwright) -> None:
        self.chromium = pw.chromium
        self.browser: Browser | None = None
        self.sem = asyncio.Semaphore(10)

    async def __aenter__(self):
        self.browser = await self.chromium.launch()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.browser:
            await self.browser.close()

    async def print_book(self, book: Book):
        results = await asyncio.gather(
            *(self._print_one_chapter(chapter, book.pdf_dir) for chapter in book.src_dir.glob('*.html')),
            return_exceptions=True,
        )
        self._check_for_exception(results)
        self._collect_to_book(book)

    def _collect_to_book(self, book: Book):
        merger = PdfWriter()
        chapter_pdfs = sorted(book.pdf_dir.glob('chapters/*.pdf'), key=lambda p: int(p.stem.split('-')[-1]))
        for pdf in chapter_pdfs:
            merger.append(pdf)
        merger.write(book.pdf_dir / f'{book.title}.pdf')

    async def _print_one_chapter(self, html_path: Path, pdf_dir: Path):
        if not self.browser:
            raise RuntimeError('Browser is not initialized.')

        async with self.sem:
            context = await self.browser.new_context()
            page = await context.new_page()
            await page.goto(f'file://{html_path.absolute()}')
            pdf_path = pdf_dir / 'chapters' / html_path.with_suffix('.pdf').name
            await page.pdf(path=pdf_path, width='125mm', height='158mm')
            await context.close()

    def _check_for_exception(self, results: list[BaseException | None]) -> None:
        for i, result in enumerate(results, 1):
            if isinstance(result, Exception):
                print(f'Error printing chapter {i}: {result}')
