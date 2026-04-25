import logging
from pathlib import Path

from .log_utils import with_log
from .renderer import Asset, render_chapter

logger = logging.getLogger(__name__)


class Book:
    METADATA_URL_TEMPLATE = 'https://learning.oreilly.com/api/v2/epubs/urn:orm:book:{isbn}/'
    URL_TEMPLATE = 'https://learning.oreilly.com/api/v2/epub-chapters/urn:orm:book:{isbn}:chapter:chapter-{chapter:02d}.html/'  # fmt: skip
    STARTPOINT_TEMPLATE = 'https://learning.oreilly.com/api/v2/epub-chapters/?epub_identifier=urn:orm:book:{isbn}'

    def __init__(self, isbn):
        self.isbn = isbn
        self.title = ''
        self.pages = 0

        self.meta_url = self.METADATA_URL_TEMPLATE.format(isbn=self.isbn)
        self.startpoint_url = self.STARTPOINT_TEMPLATE.format(isbn=self.isbn)

        self.src_dir = Path('books_src') / self.isbn
        self.asset_dir = self.src_dir / 'assets'
        self.pdf_dir = Path('books_pdf') / self.isbn

    def set_metadata(self, title, pages) -> None:
        self.title = title
        self.pages = pages

    @with_log(
        logger, 'Setting up directories for book [{self.isbn}] at {self.src_dir} and {self.pdf_dir}', level=logging.INFO
    )
    def setup_dirs(self):
        self.src_dir.mkdir(parents=True, exist_ok=True)
        self.asset_dir.mkdir(parents=True, exist_ok=True)
        self.pdf_dir.mkdir(parents=True, exist_ok=True)

    def get_chapter_url(self, chapter):
        return self.URL_TEMPLATE.format(isbn=self.isbn, chapter=chapter)

    def render_chapter(self, title: str, content: str, assets: Asset) -> str:
        content = self._replace_asset_srcs(content)
        return render_chapter(title, content, assets)

    def _replace_asset_srcs(self, content: str) -> str:
        content = content.replace(f'/api/v2/epubs/urn:orm:book:{self.isbn}/files',
                                  str(self.asset_dir.name))  # fmt: skip
        content = content.replace('assets/images', str(self.asset_dir.name))
        return content
