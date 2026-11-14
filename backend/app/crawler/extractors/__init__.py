"""The extractors that read a product off a shop page.

``extract`` is the entry point: it picks the right extractor for the platform
the page comes from and falls back to the generic schema.org reader.
"""

from app.crawler.extractors.base import ExtractedProduct, extract

__all__ = ["ExtractedProduct", "extract"]
