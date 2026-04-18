from pathlib import Path


class Book:
    URL_TEMPLATE = 'https://learning.oreilly.com/api/v2/epub-chapters/urn:orm:book:{isbn}:chapter:chapter-{chapter:02d}.html/'

    def __init__(self, isbn):
        self.isbn = isbn
        self.src_dir = Path('books_src') / self.isbn
        self.asset_dir = self.src_dir / 'assets'
        self._setup_dirs()
        
        self.cover_url = self.get_chapter_url(1)

    def _setup_dirs(self):
        self.src_dir.mkdir(parents=True, exist_ok=True)
        self.asset_dir.mkdir(parents=True, exist_ok=True)

    def get_chapter_url(self, chapter):
        return self.URL_TEMPLATE.format(isbn=self.isbn, chapter=chapter)
