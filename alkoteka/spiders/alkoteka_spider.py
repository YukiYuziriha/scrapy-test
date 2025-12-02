import configparser
import json
import time
from collections.abc import Generator
from pathlib import Path
from typing import Any, cast

import scrapy
import scrapy.http

from alkoteka.items import ProductItem


class AlkotekaSpider(scrapy.Spider):
    name = "alkoteka"
    allowed_domains = ["alkoteka.com"]

    # API Endpoints
    API_LIST_URL = "https://alkoteka.com/api/v1/product"
    API_DETAIL_URL = "https://alkoteka.com/api/v1/product/{uuid}"

    def start_requests(self) -> Generator[scrapy.Request, None, None]:
        """
        1. Load config/CLI args.
        2. Resolve City UUID.
        3. Load Category URLs -> Extract Slugs.
        4. Yield API Requests.
        """
        # --- Configuration Loading ---
        config = configparser.ConfigParser()
        config.read("config.ini")

        # 1. City Handling
        # Priority: CLI arg > Config 'default_city' > 'krasnodar'
        cli_city = getattr(self, "city", None)
        config_city = config.get("spider", "default_city", fallback="krasnodar")
        target_city_key = cli_city or config_city

        # Fetch UUID from [cities] section
        city_uuid = config.get("cities", target_city_key.lower(), fallback=None)

        if not city_uuid:
            self.logger.error(
                f"City '{target_city_key}' not found in config.ini [cities]. "
                "Using Krasnodar fallback."
            )
            # Fallback to known Krasnodar UUID if config fails
            city_uuid = "4a70f9e0-46ae-11e7-83ff-00155d026416"

        self.logger.info(f"Scraping for city: {target_city_key} (UUID: {city_uuid})")

        # 2. Category Loading
        cat_filename = getattr(
            self,
            "categories",
            config.get("spider", "categories_file", fallback="categories.txt"),
        )
        cat_file = Path(cat_filename)

        if not cat_file.exists():
            self.logger.error(f"Category file '{cat_filename}' not found.")
            return

        content = cat_file.read_text(encoding="utf-8")

        for raw_line in content.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            # Extract slug from URL
            # URL: https://alkoteka.com/catalog/vino -> slug: vino
            # Path: /catalog/krepkiy-alkogol -> slug: krepkiy-alkogol
            slug = self._extract_slug(line)
            if not slug:
                self.logger.warning(f"Could not extract slug from: {line}")
                continue

            # Construct List API Request
            url = (
                f"{self.API_LIST_URL}?city_uuid={city_uuid}"
                f"&root_category_slug={slug}&page=1&per_page=20"
            )

            # Max items limit (default 100 items per category)
            # Convert items to pages (20 items per page)
            max_items = int(getattr(self, "max_items", 100))
            # Equivalent to ceil(max_items / 20) without importing math
            max_pages = (max_items + 19) // 20

            # mypy's Request callback signature doesn't account for generator callbacks.
            # Scrapy supports them at runtime, so we ignore this arg-type here.
            yield scrapy.Request(
                url=url,
                callback=self.parse,  # type: ignore[arg-type]
                meta={
                    "city_uuid": city_uuid,
                    "slug": slug,
                    "page": 1,
                    "max_pages": max_pages,
                },
            )

    def _extract_slug(self, url_or_path: str) -> str | None:
        """Helper to extract 'vino' from '.../catalog/vino'."""
        # Remove trailing slash
        clean = url_or_path.rstrip("/")
        # Get last segment
        return clean.split("/")[-1]

    def parse(
        self, response: scrapy.http.Response, *args: object, **kwargs: object
    ) -> Generator[scrapy.Request, None, None]:
        """
        Handle List API response.
        1. Yield Detail requests for products.
        2. Yield Next Page request.
        """
        try:
            data = json.loads(response.text)
        except json.JSONDecodeError:
            self.logger.error(f"Failed to decode JSON from {response.url}")
            return

        if not data.get("success"):
            self.logger.error(f"API Error: {data.get('error')}")
            return

        results = data.get("results", {})

        # Handle structure variations
        if isinstance(results, list):
            products = results
            pagination_source = data
        else:
            products = results.get("products", [])
            pagination_source = results

        # 1. Yield Product Details
        city_uuid = response.meta["city_uuid"]

        for prod in products:
            # Use UUID for detail request if available
            p_uuid = prod.get("uuid")
            if not p_uuid:
                self.logger.warning("Product missing UUID, skipping detail fetch")
                continue

            # Detail API URL
            detail_url = (
                self.API_DETAIL_URL.format(uuid=p_uuid) + f"?city_uuid={city_uuid}"
            )

            # See note above: Scrapy allows generator callbacks; mypy does not.
            yield scrapy.Request(
                url=detail_url,
                callback=self.parse_product,  # type: ignore[arg-type]
                meta={"list_data": prod},  # Pass basic data just in case
            )

        # 2. Pagination
        # Pagination info is usually in 'meta' key or top level
        meta_info = data.get("meta", {})

        # Try 'meta' first, then fallback to pagination_source
        current_page = meta_info.get("current_page") or pagination_source.get(
            "current_page", 1
        )

        # 'total_pages' might not be present, calculate it if 'total' exists
        total_pages = (
            meta_info.get("last_page")
            or meta_info.get("total_pages")
            or pagination_source.get("total_pages")
        )

        if not total_pages:
            # If explicit total_pages missing, try calculating from total / per_page
            total_items = meta_info.get("total") or pagination_source.get("total", 0)
            per_page = meta_info.get("per_page") or pagination_source.get(
                "per_page", 20
            )
            if total_items and per_page:
                total_pages = (total_items + per_page - 1) // per_page
            else:
                total_pages = 1

        max_pages = response.meta.get("max_pages", 5)

        # Check both Total Pages and User Limit
        if current_page < total_pages and current_page < max_pages:
            next_page = current_page + 1
            root_slug = response.meta["slug"]

            next_url = (
                f"{self.API_LIST_URL}?"
                f"city_uuid={city_uuid}&"
                f"root_category_slug={root_slug}&"
                f"page={next_page}&"
                f"per_page=20"
            )

            # Same callback-type mismatch explanation as above.
            yield scrapy.Request(
                url=next_url,
                callback=self.parse,  # type: ignore[arg-type]
                meta={
                    "city_uuid": city_uuid,
                    "slug": root_slug,
                    "page": next_page,
                    "max_pages": max_pages,
                },
            )

    def parse_product(
        self, response: scrapy.http.Response
    ) -> Generator[ProductItem, None, None]:
        """
        Handle Detail API response and map JSON fields to ProductItem.
        """
        product = self._get_product_data(response)
        if not product:
            return

        list_data = response.meta.get("list_data", {})
        slug = self._resolve_slug(product, list_data)

        item = ProductItem()
        item["timestamp"] = int(time.time())
        item["RPC"] = str(product.get("vendor_code", "") or "")
        item["url"] = f"https://alkoteka.com/product/{slug}"
        item["brand"] = self._parse_brand(product)
        item["title"] = self._parse_title(product)
        item["section"] = self._parse_section(product)
        item["price_data"] = self._parse_price_data(product)
        item["stock"] = self._parse_stock(product)
        item["assets"] = self._parse_assets(product)
        item["metadata"] = self._parse_metadata(product)
        item["marketing_tags"] = self._parse_marketing_tags(product)
        item["variants"] = 0

        yield item

    def _get_product_data(
        self, response: scrapy.http.Response
    ) -> dict[str, Any] | None:
        try:
            raw_data = json.loads(response.text)
        except json.JSONDecodeError:
            self.logger.error("Failed to decode JSON from %s", response.url)
            return None

        if not isinstance(raw_data, dict):
            self.logger.error("Unexpected product payload at %s", response.url)
            return None

        data = cast(dict[str, Any], raw_data)

        if not data.get("success"):
            self.logger.error("Product API error at %s", response.url)
            return None

        product = data.get("results")
        if not isinstance(product, dict) or not product:
            self.logger.warning("Product payload missing for %s", response.url)
            return None

        return cast(dict[str, Any], product)

    def _resolve_slug(self, product: dict[str, Any], list_data: dict[str, Any]) -> str:
        slug = product.get("slug") or list_data.get("slug") or ""
        return str(slug)

    def _parse_brand(self, product: dict[str, Any]) -> str:
        brand_info = product.get("brand")
        if isinstance(brand_info, dict):
            name = brand_info.get("name")
            if isinstance(name, str):
                return name
        return ""

    def _parse_title(self, product: dict[str, Any]) -> str:
        name_raw = product.get("name")
        name = str(name_raw).strip() if name_raw else ""
        volume_raw = product.get("volume")
        volume = str(volume_raw).strip() if volume_raw else ""
        if volume and volume not in name and name:
            return f"{name}, {volume}"
        if name:
            return name
        return volume

    def _parse_section(self, product: dict[str, Any]) -> list[str]:
        section: list[str] = []
        category = product.get("category")
        while isinstance(category, dict):
            name = category.get("name")
            if isinstance(name, str):
                section.insert(0, name)
            category = category.get("parent")
        return [part for part in section if part]

    def _parse_price_data(self, product: dict[str, Any]) -> dict[str, Any]:
        current = self._to_float(product.get("price"))
        original = self._to_float(product.get("prev_price"))
        if original == 0:
            original = current

        sale_tag = ""
        if original > current and original > 0:
            discount = int(round(100 - (current / original * 100)))
            sale_tag = f"Скидка {discount}%"

        return {"current": current, "original": original, "sale_tag": sale_tag}

    def _parse_stock(self, product: dict[str, Any]) -> dict[str, Any]:
        count = 0
        count_raw = product.get("quantity_total", 0)
        if isinstance(count_raw, (int, float)):
            count = int(count_raw)
        elif isinstance(count_raw, str):
            try:
                count = int(count_raw)
            except ValueError:
                count = 0
        return {"in_stock": count > 0, "count": count}

    def _parse_assets(self, product: dict[str, Any]) -> dict[str, Any]:
        main_img_raw = product.get("image_url")
        main_img = str(main_img_raw) if main_img_raw else ""
        set_images = [main_img] if main_img else []
        return {
            "main_image": main_img,
            "set_images": set_images,
            "view360": [],
            "video": [],
        }

    def _parse_metadata(self, product: dict[str, Any]) -> dict[str, Any]:
        description = product.get("description")
        desc_text = str(description) if isinstance(description, str) else ""

        if not desc_text:
            blocks = product.get("description_blocks")
            if isinstance(blocks, list):
                desc_text = " ".join(str(block) for block in blocks if block)

        metadata: dict[str, Any] = {"__description": desc_text}

        known_specs = ["country", "region", "strength", "sugar", "grape", "color"]
        for spec in known_specs:
            parsed = self._parse_spec_value(product.get(spec))
            if parsed:
                metadata[spec] = parsed

        props = product.get("properties")
        if isinstance(props, dict):
            for key, val in props.items():
                parsed_prop = self._parse_spec_value(val)
                if parsed_prop:
                    metadata[key] = parsed_prop

        return metadata

    def _parse_marketing_tags(self, product: dict[str, Any]) -> list[str]:
        tags = []
        if product.get("is_new"):
            tags.append("Новинка")
        if product.get("is_gift"):
            tags.append("Подарок")
        return tags

    def _parse_spec_value(self, value: object) -> str:
        if isinstance(value, dict) and "name" in value:
            return str(value.get("name", ""))
        if isinstance(value, (str, int, float)):
            return str(value)
        return ""

    def _to_float(self, value: object) -> float:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return 0.0
        return 0.0
