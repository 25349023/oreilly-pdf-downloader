import dataclasses

from jinja2 import Environment, PackageLoader, select_autoescape

_env = Environment(
    loader=PackageLoader('oreilly_pdf_downloader'),
    autoescape=select_autoescape(),
)


@dataclasses.dataclass
class Asset:
    stylesheets: list[str] = dataclasses.field(default_factory=list)
    # images: list[str] = dataclasses.field(default_factory=list)


def render_chapter(title: str, chapter_content: str, assets: Asset) -> str:
    template = _env.get_template('chapter.html')
    return template.render(title=title, chapter_content=chapter_content, stylesheets=assets.stylesheets)
