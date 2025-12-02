import configparser
from pathlib import Path
from typing import Any, Generator

import scrapy
import scrapy.http


class AlkotekaSpider(scrapy.Spider):
    name = "alkoteka"
    allowed_domains = ["alkoteka.com"]

    def start_requests(self) -> Generator[scrapy.Request, None, None]:
        """
        Read configuration from config.ini or CLI args.
        CLI args: -a categories=my_list.txt -a base_url=https://...
        """
        # 1. Defaults
        config = configparser.ConfigParser()
        config.read("config.ini")

        default_cat_file = config.get(
            "spider", "categories_file", fallback="categories.txt"
        )
        default_base_url = config.get(
            "spider", "base_url", fallback="https://alkoteka.com"
        )

        # 2. CLI overrides (getattr checks for -a arguments)
        cat_filename = getattr(self, "categories", default_cat_file)
        self.base_url = getattr(self, "base_url", default_base_url)

        # 3. Load URLs
        cat_file = Path(cat_filename)
        start_urls: list[str] = []

        if cat_file.exists():
            content = cat_file.read_text(encoding="utf-8")
            for raw_line in content.splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                # Handle relative paths if they occur
                if line.startswith("http"):
                    start_urls.append(line)
                else:
                    start_urls.append(f"{self.base_url.rstrip('/')}/{line.lstrip('/')}")
        else:
            self.logger.warning(
                f"Category file '{cat_filename}' not found. Using default."
            )
            start_urls = [f"{self.base_url}/catalog/vino"]

        region_cookies = {"current_city_id": "2"}

        for url in start_urls:
            yield scrapy.Request(
                url=url,
                # Scrapy expects Any, but we strictly return a Generator
                callback=self.parse,  # type: ignore[arg-type]
                cookies=region_cookies,
            )

    def parse(
        self, response: scrapy.http.Response, *args: Any, **kwargs: Any
    ) -> Generator[scrapy.Request | dict[str, Any], None, None]:
        """
        Parse the category page:
        1. Extract product links -> yield request to parse_product
        2. Extract pagination -> yield request to self.parse
        """
        self.logger.info(f"Parsing category: {response.url}")
        # TODO: Extract product links and pagination
        yield from ()

    def parse_product(self, response: scrapy.http.Response) -> Any:
        # TODO: parse product details into ProductItem
        pass
