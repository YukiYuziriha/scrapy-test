## 1. Goal & Constraints

**Goal**
Implement a Scrapy project that:

* Parses products from **3+ category URLs** on `alkoteka.com`.
* Forces **region = Краснодар** for all requests.
* Outputs **JSON** in the exact format from the task.
* Runs via:

  ```bash
  scrapy crawl alkoteka -O result.json
  ```
* Optionally:

  * Uses **proxies** (bonus).
  * Uses **middleware/OOP structuring** (bonus).

**Hard constraints**

* Only **Scrapy**. No Playwright, Selenium, etc.
* All fields from the schema must be present (even if values are empty/zero).

---

## 2. High-Level Architecture

Design it as a **small but “professional-looking” Scrapy project**:

1. **Project root**

   * `scrapy.cfg`
   * `alkoteka/` (project package)

     * `settings.py`
     * `items.py`
     * `middlewares.py`
     * `pipelines.py`
     * `spiders/alkoteka_spider.py`
     * `utils/` (optional: helpers for parsing / config)
   * `categories.txt` (optional input)
   * `README.md` (short, for humans / reviewers)

2. **Single spider** `AlkotekaSpider`:

   * Reads category URLs (constant list or file).
   * Navigates pagination.
   * Visits product pages.
   * Yields `ProductItem` strictly matching the required schema.

3. **Item** (`ProductItem`):

   * Fields mirror the JSON spec 1:1, including nested dicts and lists.

4. **Optional**

   * `ProxyMiddleware` in `middlewares.py`.
   * Small helper functions in `utils/` for:

     * cleaning prices
     * parsing breadcrumbs
     * normalizing text

---

## 3. Data Model & Schema Mapping

First thing to do (for you or the agent): **define the data model** in `items.py`, mirroring the output format.

### 3.1. Top-level fields

From spec:

* `timestamp: int`
* `RPC: str`
* `url: str`
* `title: str`
* `marketing_tags: list[str]`
* `brand: str`
* `section: list[str]`
* `price_data: dict`
* `stock: dict`
* `assets: dict`
* `metadata: dict`
* `variants: int`

Guidelines:

* **Always yield all keys**, even if empty:

  * strings → `""`
  * ints → `0`
  * floats → `0.0`
  * lists → `[]`
  * dicts → with all required keys filled with defaults.

### 3.2. `price_data` structure

* `current: float`
* `original: float`
* `sale_tag: str` (either `""` or `"Скидка X%"`)

Rules:

* If **no discount**:

  * `current = original`.
  * `sale_tag = ""`.
* If discount exists:

  * Compute percentage: `round(100 - current/original * 100)` (or int).
  * Format exactly `"Скидка {x}%"`.

### 3.3. `stock`

* `in_stock: bool`
* `count: int` (0 if unknown)

Rules:

* Use presence/absence or text on “Add to cart” / “Нет в наличии”.
* If the site doesn’t expose quantity → `count = 0`.

### 3.4. `assets`

* `main_image: str`
* `set_images: list[str]`
* `view360: list[str]`
* `video: list[str]`

Rules:

* `main_image` = first image if any, otherwise `""`.
* `set_images` = all images (absolute URLs).
* `view360` and `video` = `[]` if not found.

### 3.5. `metadata`

* Must contain:

  * `"__description": str`
  * Plus **all product characteristics from the page** as `key: value`.

Examples:

* `"Артикул"`, `"Объем"`, `"Страна"`, `"Крепость"`, etc.

Rules:

* Strip whitespace from keys and values.
* If description not found → `"__description": ""`.

### 3.6. `variants`

* Integer: **count of product variants (color or volume/mass)**.
* For this site, likely **different volumes**.
* If no variants on the page → `0` or `1` (choose one rule and use it consistently; I’d set `0` if no variant selector is visible).

---

## 4. Spider Flow Design

Define one clear flow in `spiders/alkoteka_spider.py`.

### 4.1. Inputs: category URLs

Two supported modes (pick one, or support both):

1. **Constant** in the spider:

   ```python
   start_urls = [
       "https://alkoteka.com/catalog/slaboalkogolnye-napitki-2",
       "https://alkoteka.com/catalog/...2",
       "https://alkoteka.com/catalog/...3",
   ]
   ```
2. **From file `categories.txt`**:

   * One URL per line.
   * Override `start_requests()` to read the file and yield `scrapy.Request`.

For an AI agent, tell it explicitly which option to implement.

---

### 4.2. `parse` (category page)

Responsibilities:

* Extract product URLs.
* Follow to `parse_product`.
* Handle pagination and continue with `parse`.

Guidelines:

* Use CSS/XPath selectors stable across categories.
* **Normalize URLs** with `response.follow`.
* Avoid mixing list and detail logic.

Flow:

1. Extract all product links.
2. `yield response.follow(url, callback=self.parse_product)` for each.
3. Find “next page” link.
4. If exists → `yield response.follow(next_url, callback=self.parse)`.

---

### 4.3. `parse_product` (product page)

Responsibilities:

* Build the `ProductItem` fully.
* Fill **every field** according to mapping.
* Handle missing data gracefully (fallbacks / defaults).

Implementation approach:

1. Initialize empty `ProductItem` with defaults.
2. Fill simple primitives (`timestamp`, `url`, `RPC`, `title`).
3. Parse structured data (`section`, `price_data`, `stock`).
4. Parse media (`assets`).
5. Parse metadata (description + characteristics).
6. Determine `variants`.
7. `yield item`.

For the agent: separate out helper methods if needed:

* `_parse_price_data(response)`
* `_parse_stock(response)`
* `_parse_assets(response)`
* `_parse_metadata(response)`
* `_parse_variants(response)`

This makes the spider look more “senior” and keeps code readable.

---

## 5. Region Handling (Краснодар)

This is important, they explicitly mention it.

Plan:

1. **Use cookies or headers in `DEFAULT_REQUEST_HEADERS` / `COOKIES`**:

   * Find how region is stored (usually cookie like `current_city_id`).
   * For the assignment, you can hardcode `"Краснодар"` region cookie/value once.

2. Implementation options:

   * **Option A: settings-level cookies**:

     * If Scrapy version supports `COOKIES_ENABLED` & `DEFAULT_REQUEST_HEADERS`, you can:

       * Use `Cookie` header or custom `request.cookies` in `start_requests()`.
   * **Option B: middleware**:

     * Implement a downloader middleware that:

       * Adds a specific cookie / query parameter to each request to enforce region.

3. Keep it simple but explicit:

   * In code comments, write:

     > `# Force region: Краснодар via cookie current_city_id=...`

Even if the exact ID is guessed, the important part is: you show awareness and attempt.

---

## 6. Proxy Support (Optional, but Good Bonus)

Target: **basic support for HTTP proxies**, not a full rotation engine.

Plan:

1. Add setting, e.g. in `settings.py`:

   * `PROXY_LIST_FILE = "proxies.txt"` (or inline list).

2. Create `ProxyMiddleware` in `middlewares.py`:

   * Read proxies from file at startup.
   * On each request, assign random proxy:

     ```python
     request.meta["proxy"] = choice(self.proxies)
     ```

3. Enable middleware in settings:

   ```python
   DOWNLOADER_MIDDLEWARES = {
       "alkoteka.middlewares.ProxyMiddleware": 350,
   }
   ```

Guidelines for agent:

* Simple, deterministic behavior is enough.
* Do **not** overcomplicate with async verification, etc.
* If `proxies.txt` missing, middleware falls back to “no proxy”.

---

## 7. Settings & Config

Within `alkoteka/settings.py`:

1. **Core Scrapy settings:**

   * `BOT_NAME = "alkoteka"`
   * `ROBOTSTXT_OBEY = False`
   * `FEED_EXPORT_ENCODING = "utf-8"`

2. **User-Agent & headers:**

   * Realistic browser UA.
   * `Accept-Language: "ru-RU,ru;q=0.9"`.

3. **Concurrency & delays:**

   * For test assignment, keep it polite:

     * `DOWNLOAD_DELAY = 0.5` – `1`
     * Concurrency default is fine.

4. **Export format** is handled by Scrapy command:

   ```bash
   scrapy crawl alkoteka -O result.json
   ```

---

## 8. Validation Strategy (So Result Isn’t Garbage)

You want the AI to build something that **actually matches the spec**, not just “runs”.

Plan:

1. **Manual sanity check**:

   * Run spider on 1–2 pages.
   * Open `result.json` and verify:

     * Every object has all required keys.
     * `price_data`, `stock`, `assets`, `metadata` have correct nested keys.
     * Types: ints, floats, bool, lists, strings.

2. **Spot-check known fields**:

   * Compare:

     * Product name on site vs `title`.
     * Price on site vs `price_data.current/original`.
     * Marketing tags vs visible labels.
     * Brand vs what site shows.
     * Section vs breadcrumbs.

3. **Edge cases**:

   * Product without discount.
   * Product “out of stock”.
   * Product with several volumes (variants).

4. **Consistency**:

   * `timestamp` changes on runs, okay.
   * `RPC` stable per product (e.g. from article / URL ID).

---

## 9. CLI & Deliverables

Make sure final usage is as they require:

```bash
scrapy crawl alkoteka -O result.json
```

Deliverables:

* Full Scrapy project folder.
* `README.md` with:

  * How to install deps (`pip install scrapy`).
  * How to run spider.
  * Optional: how to change categories or proxies.

Optional:

* `categories.txt` with 3+ category URLs.
* `proxies.txt` (even if empty, just for structure).

---
