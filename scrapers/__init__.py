"""Scrapers module - connettori alle piattaforme finanziarie."""
from scrapers.base import BaseDataSource
from scrapers.justetf_scraper import JustETFScraper
from scrapers.morningstar_scraper import MorningstarScraper
from scrapers.investiny_scraper import InvestinyScraper

__all__ = [
    "BaseDataSource",
    "JustETFScraper",
    "MorningstarScraper",
    "InvestinyScraper",
]
