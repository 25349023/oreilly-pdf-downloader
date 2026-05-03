import argparse
import asyncio
import logging.config

import dacite

from oreilly_pdf_downloader.book_downloader import BookDownloader
from oreilly_pdf_downloader.config import Config, preprocess_args


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
        '--page-size', nargs=2, type=int, metavar=('width', 'height'), 
        help='Set the page size (unit: mm) for the PDF',
    )  # fmt: skip
    parser.add_argument(
        '--compress-pdf', action='store_true',
        help='Compress the final PDF to reduce file size (may cause higher CPU usage and longer processing time)',
    )  # fmt: skip
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    clean_args = preprocess_args(args)
    config = dacite.from_dict(Config, data=clean_args, config=dacite.Config(cast=[tuple]))

    downloader = BookDownloader(config=config)
    target_isbn = input('Enter the ISBN of the book you want to download: ')
    await downloader.download_book(target_isbn)


if __name__ == '__main__':
    setup_logging()
    asyncio.run(main())
