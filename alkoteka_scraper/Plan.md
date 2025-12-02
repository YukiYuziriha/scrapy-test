# Implementation Plan

## 1. Goal & Constraints
- Build a Scrapy project that parses products from 3+ category URLs on alkoteka.com.
- Enforce region selection to Краснодар for all requests.
- Output JSON matching the required schema via `scrapy crawl alkoteka -O result.json`.
- Optional: proxy support and middleware-based structuring.

## 2. Architecture
- Project layout:
  - `scrapy.cfg`
  - `alkoteka/` with `settings.py`, `items.py`, `middlewares.py`, `pipelines.py`, `utils/`, and `spiders/alkoteka_spider.py`.
  - Optional input files: `categories.txt`, `proxies.txt`.
  - `README.md` for quickstart guidance.
- Single spider `AlkotekaSpider` handles categories, pagination, and product parsing.

## 3. Data Model
- `ProductItem` fields mirror the JSON schema exactly: `timestamp`, `RPC`, `url`, `title`, `marketing_tags`, `brand`, `section`, `price_data`, `stock`, `assets`, `metadata`, `variants`.
- Nested dicts include all required keys with safe defaults when missing.

## 4. Spider Flow
- Category URLs from constants or `categories.txt`.
- `parse`: extract product links, follow pagination.
- `parse_product`: build `ProductItem`; use helpers for price, stock, assets, metadata, variants.

## 5. Region Handling
- Force Краснодар region via cookie/header or middleware that injects the required value for every request.
- Document assumptions with TODO comments if exact identifier is uncertain.

## 6. Proxy Support (Optional)
- `ProxyMiddleware` loads proxies from `proxies.txt` and assigns one per request when available.

## 7. Settings & Defaults
- `FEED_EXPORT_ENCODING = "utf-8"`, `ROBOTSTXT_OBEY = False`, realistic headers, polite delays as needed.

## 8. Validation Checklist
- Ensure every item includes all schema keys with proper types and defaults.
- Verify price/stock/metadata parsing matches site content; handle missing data defensively.
