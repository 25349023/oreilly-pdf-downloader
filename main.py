import asyncio

from oreilly_pdf_downloader.book_downloader import BookDownloader


async def main():
    downloader = BookDownloader()

    target_isbn = input('Enter the ISBN of the book you want to download: ')
    await downloader.download_book(target_isbn)


if __name__ == '__main__':
    asyncio.run(main())
