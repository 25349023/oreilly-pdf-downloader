import argparse
import asyncio
import logging.config

from oreilly_pdf_downloader.book_downloader import BookDownloader


def setup_logging():
    LOGGING_CONFIG = {
        'version': 1,
        'disable_existing_loggers': False,  # avoid disabling loggers from other libraries
        'formatters': {
            'simple': {'format': '[%(levelname)s] %(message)s'},
            'detailed': {
                'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S',
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': 'WARNING',
                'formatter': 'simple',
                'stream': 'ext://sys.stdout',
            },
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'DEBUG',
                'formatter': 'detailed',
                'filename': 'downloader.log',
                'mode': 'a',
                'encoding': 'utf-8',
                'maxBytes': 5 * 1024 * 1024,  # 5 MB
                'backupCount': 4,
            },
        },
        'loggers': {
            '': {  # Root Logger
                'handlers': ['console', 'file'],
                'level': 'DEBUG',
            },
        },
    }

    logging.config.dictConfig(LOGGING_CONFIG)
    logger = logging.getLogger(__name__)

    logger.info('Logging is set up.')


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="O'Reilly PDF Downloader")
    parser.add_argument('--test-run', action='store_true', help='Run a test download that only fetches 8 pages')
    parser.add_argument(
        '--page-size', nargs=2, type=int, default=(185, 230),
        metavar=('width', 'height'), help='Set the page size (unit: mm) for the PDF',
    )  # fmt: skip
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    downloader = BookDownloader(page_size=args.page_size)

    target_isbn = input('Enter the ISBN of the book you want to download: ')
    await downloader.download_book(target_isbn, test_run=args.test_run)


if __name__ == '__main__':
    setup_logging()
    asyncio.run(main())
