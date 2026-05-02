from dataclasses import dataclass


@dataclass
class DownloaderConfig:
    # Default page size in mm (width, height)
    page_size: tuple[int, int] = (185, 230)

    # If True, only fetches a limited number of pages for testing purposes
    test_run: bool = False

    # [TODO] For future: add sub config class for each component (e.g., printer), but keep simple for now
