from argparse import Namespace
from dataclasses import dataclass


def preprocess_args(args: Namespace) -> dict:
    return {k: v for k, v in vars(args).items() if v is not None}


@dataclass
class Config:
    # Default page size in mm (width, height)
    page_size: tuple[int, int] = (185, 230)

    # If True, only fetches a limited number of pages for testing purposes
    test_run: bool = False

    # Whether to compress the final PDF to reduce file size
    compress_pdf: bool = False

    # [TODO] For future: add sub config class for each component (e.g., printer), but keep simple for now
