"""
foo
"""
import argparse
import sys

import scrapy
import scrapy.crawler
import scrapy.utils.project

from ..config import ConfigurationFile
from ..db import DatabaseConfiguration
from ..exceptions import SmuttyException
from ..filetools import IntegerStateFile

import smutty.scraper.settings

from .spiders import SmuttySpider


class App:
    """
    foo
    """

    def __init__(self):
        # analyze commande line arguments
        parser = argparse.ArgumentParser(description="Smutty metadata scrapper")
        parser.add_argument("-s", "--start-page", metavar="START_PAGE", type=int)
        parser.add_argument("-c", "--page-count", metavar="PAGE_COUNT", type=int)
        parser.add_argument("-m", "--min-id", metavar="MIN_ID", type=int)
        parser.add_argument("-b", "--blacklist-tag-file", metavar="BLACKLIST_FILE")
        parser.add_argument("config", metavar="CONFIG", nargs='?', default=ConfigurationFile.DEFAULT_CONFIG_FILE)
        args = parser.parse_args()

        # exit early if nothing will be done
        if args.page_count is not None and int(args.page_count) == 0:
            sys.exit(0)

        # load configuration
        self._config = ConfigurationFile(args.config)

        # process configuration
        self._current_scraper_page_state = IntegerStateFile(self._config.get('scraper', 'current_scraper_page'))
        self._highest_scraper_id_state = IntegerStateFile(self._config.get('scraper', 'highest_scraper_id'))
        self._lowest_scraper_id_state = IntegerStateFile(self._config.get('scraper', 'lowest_scraper_id'))
        self._database_url = DatabaseConfiguration(self._config.get('database')).url

        # manage start page :
        # - start based on state file
        # - override if necessary
        # - persist to make sure it exists
        current_scraper_page = self._current_scraper_page_state.get()
        if args.start_page is not None:
            current_scraper_page = args.start_page
        if current_scraper_page is None or current_scraper_page == 0:
            current_scraper_page = 1
        self._current_scraper_page_state.set(current_scraper_page)

        # manage min id
        # - start based on state file
        # - override if necessary
        # - if defined, make sure state file exists
        min_id = self._lowest_scraper_id_state.get()
        if args.min_id is not None:
            min_id = args.min_id
        if min_id is not None:
            self._lowest_scraper_id_state.set(min_id)

        # load blacklist tags
        blacklisted_tags = set()
        if args.blacklist_tag_file:
            try:
                with open(args.blacklist_tag_file) as file_obj:
                    blacklisted_tags = {tag.lower() for line in file_obj for tag in line.split()}
            except FileNotFoundError as exc:
                raise SmuttyException(exc)

        # manage settings
        self._settings = scrapy.utils.project.get_project_settings()
        self._settings.setmodule(smutty.scraper.settings)

        self._settings.set("SMUTTY_PAGE_COUNT", args.page_count)
        self._settings.set("SMUTTY_BLACKLIST_TAGS", blacklisted_tags)
        self._settings.set("SMUTTY_DATABASE_CONFIGURATION_URL", self._database_url)
        self._settings.set("SMUTTY_STATE_FILE_CURRENT_SCRAPER_PAGE", self._current_scraper_page_state.file_name)
        self._settings.set("SMUTTY_STATE_FILE_HIGHEST_SCRAPER_ID", self._highest_scraper_id_state.file_name)
        self._settings.set("SMUTTY_STATE_FILE_LOWEST_SCRAPER_ID", self._lowest_scraper_id_state.file_name)

    def run(self):
        """
        foo
        """
        process = scrapy.crawler.CrawlerProcess(self._settings)
        process.crawl(SmuttySpider)
        process.start()  # it blocks here until finished
