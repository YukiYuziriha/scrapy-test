0. What this repo is

This repository is a small, focused Scrapy project for a single purpose:

> Parse products from several category URLs on alkoteka.com, using region Краснодар, and output JSON that strictly matches the given schema.


1. Global Principles

1. Correctness over cleverness

The spider must reliably produce data that matches the required schema.
If you’re unsure about something, leave a short # TODO: and implement the simplest safe behavior.


2. Minimal surface area

Do the least amount of work needed to solve this task well.
No new frameworks, no extra technologies, no big “architecture” unless it clearly improves clarity.


3. Maintainability & clarity

Code must be easy to read and understand for a human Python dev.
Prefer small clear helpers over huge functions.
Avoid magic numbers and string litter; add short comments where non-obvious.


4. Defensive mindset

Expect missing fields, changed markup, or edge cases on pages.
Always handle “not found” cases gracefully with defaults.
Avoid raising unexpected exceptions while crawling.


5. Stay in scope

Only work on this Scrapy project.
Do not modify unrelated system configs, shells, dotfiles, etc.
Do not add business logic unrelated to scraping.


2. Tech & Constraints

1. Allowed stack

Python (standard library)
Scrapy only
Simple file I/O (categories.txt, proxies.txt)


2. Forbidden / not allowed

Selenium, Playwright, headless browsers, external HTTP clients (requests, httpx, etc.).
Async frameworks (Trio, asyncio web clients, etc.).
Heavy third-party deps (Pydantic, SQLAlchemy, etc.).
Any external network calls except:
Requests done by Scrapy to alkoteka.com (and optional proxies).


3. Output format

Spider must be runnable as:

scrapy crawl alkoteka -O result.json

result.json must be a list of product objects matching the exact schema from the task.


3. Files & Responsibilities

Assume the project structure like:

scrapy.cfg
alkoteka/
    __init__.py
    settings.py
    items.py
    pipelines.py
    middlewares.py
    utils/           # optional helper modules
        __init__.py
        parsing.py   # optional
    spiders/
        alkoteka_spider.py
categories.txt       # optional list of category URLs
proxies.txt          # optional list of proxies
README.md
agents.md

3.1. items.py

Defines one main item: ProductItem.

Fields must mirror the required output schema, including nested structures represented as scrapy.Field().


3.2. spiders/alkoteka_spider.py

The only spider for this assignment.

Responsibilities:

Take category URLs (from constant list or categories.txt).
Parse category pages & pagination.
Parse product pages and populate ProductItem.
Enforce the region Краснодар (via cookies/headers/meta).


No business unrelated to scraping.


3.3. middlewares.py

Place optional:

ProxyMiddleware

(if needed) RegionMiddleware to enforce region city.


Keep them simple and explicit.


3.4. pipelines.py

Optional. Use only if you really need post-processing.

Avoid building full DB pipelines etc. Unless explicitly requested, JSON feed export is enough.


3.5. settings.py

Configure:

Basic Scrapy settings (BOT_NAME, SPIDER_MODULES, NEWSPIDER_MODULE).
FEED_EXPORT_ENCODING = "utf-8".
ROBOTSTXT_OBEY = False.
Reasonable headers (User-Agent, Accept-Language).
Enable middlewares if used.


4. Data Schema Contract

4.1. Top-level object format

Each product must have all fields:

{
    "timestamp": int,
    "RPC": str,
    "url": str,
    "title": str,
    "marketing_tags": list[str],
    "brand": str,
    "section": list[str],
    "price_data": {
        "current": float,
        "original": float,
        "sale_tag": str,
    },
    "stock": {
        "in_stock": bool,
        "count": int,
    },
    "assets": {
        "main_image": str,
        "set_images": list[str],
        "view360": list[str],
        "video": list[str],
    },
    "metadata": dict,  # includes "__description" and other attributes
    "variants": int,
}

4.2. Default values

If something cannot be found:

timestamp: int(time.time()) at parse time.

RPC: "" (empty string).

url: response.url (always present).

title: "" if truly missing (but try hard to extract).

marketing_tags: [].

brand: "".

section: [].

price_data:

current: 0.0 if price cannot be parsed.

original: equal to current if no discount.

sale_tag: "" if no discount.


stock:

in_stock: False if unclear.

count: 0.


assets:

main_image: "".

set_images: [].

view360: [].

video: [].


metadata:

must at least contain "__description" key.

If no description, "__description": "".


variants:

0 if no variants selector is visible or parsable.


4.3. Price rules

If both original and discounted prices are available:

original = original (higher) price

current = discounted (actual) price

sale_tag = "Скидка X%"
where X is the integer percentage discount:
X = int(round(100 - current / original * 100))


If only one price is visible:

original = current = that_price

sale_tag = ""


4.4. Title rules

If product card has volume/color not present in the title but visible elsewhere on page, append it:

"Name" + ", Volume" → "Name, 0.5 л" etc.


Never drop important parts of the original name.


5. Scrapy Spider Behavior

5.1. Category input

Support at least one of:

1. Hard-coded list:

start_urls = [...] with 3+ category URLs.


2. From file categories.txt:

One URL per line.

Implement start_requests() to read and yield scrapy.Request.


When in doubt, prioritize simplicity and robustness.

5.2. parse (category pages)

Responsibilities:

Extract product URLs (link to product pages).

Yield response.follow(product_url, callback=self.parse_product).

Handle pagination:

Find next page link.

If exists, response.follow(next_page, callback=self.parse).


Guidelines:

Use stable selectors (CSS or XPath) robust against minor layout changes.

Do not mix product parsing logic into parse; keep it in parse_product.


5.3. parse_product (product pages)

Responsibilities:

Fully populate a ProductItem.

Use small helper methods when logic becomes long.

Always ensure all fields of the schema are present before yielding.


Pattern:

1. Initialize item with safe defaults.


2. Fill:

timestamp, url, RPC, title.


3. Fill:

marketing_tags, brand, section.


4. Fill:

price_data.


5. Fill:

stock.


6. Fill:

assets.


7. Fill:

metadata.


8. Fill:

variants.


9. Yield item.


When HTML doesn’t match expectations, do not crash. Use get(default="") and similar patterns.


6. Region Handling (Краснодар)

The assignment explicitly requires using region Краснодар.

Rules:

1. Prefer a simple, explicit mechanism:

Set a cookie or parameter that selects Краснодар.

Or, if known, set current_city_id to the ID corresponding to Краснодар.


2. Implementation options:

Option A: set cookies in start_requests():

For every initial request, attach cookies selecting Краснодар.


Option B: middleware:

Add/override a specific cookie for every outgoing request.



3. Document the approach with a comment, e.g.:



# Force region: Краснодар via city cookie

If the exact ID or mechanism is uncertain, pick the most reasonable one and leave a # TODO note explaining the assumption instead of inventing fake behavior.


7. Proxy Handling (Optional but Nice)

Goal: basic proxy support, not a full proxy manager.

Rules:

1. If proxies.txt exists:

Read it as a list of proxy URLs (one per line).

On each request, randomly choose a proxy.


2. ProxyMiddleware in middlewares.py:

On process_request, if there are proxies:

Set request.meta["proxy"] = chosen_proxy.


If proxies.txt missing or empty: do nothing, don’t crash.


3. Keep it small:

No need for health checks, rotation strategies, or statistics.


8. Coding Style & Quality

1. PEP8-ish, but don’t obsess:

Reasonable max line length.

Clear variable names.

Functions not too long.


2. Small helpers:

Extract parsing utilities (price, breadcrumbs, attributes) into small functions or utils/parsing.py if it improves readability.


3. Comments

Use comments sparingly, only where behavior is not obvious.

Example: region enforcement, title tweak with volume.


4. No pointless abstractions

Don’t build a framework inside the project.

No abstract spiders or inheritance hierarchies unless actually useful.



9. Safety & Error Handling

1. Never intentionally crash the crawl because of an unexpected HTML variation.

Use .get(default=""), .getall() + safe indexing.

Wrap fragile parsing in small helper functions that handle missing values.


2. Log, don’t break:

If something important cannot be parsed, consider logging a warning via self.logger.warning(...) but still yield the item with defaults.


3. Defensive against type issues:

Always cast numeric fields (float, int) after cleaning.

Strip all string fields.



10. Workflow per Change (How You Should Work)

Whenever you change/add something as an agent:

1. Read & understand the immediate context:

Open the relevant file(s).

Understand what the code is already doing.


2. Restate goal (internally):

“I am implementing X in this spider / middleware / utils”.


3. Make a small plan:

Max 3–5 steps for this change.

Implement incrementally.


4. Write code with defaults & safety:

Prefer simple, explicit logic over clever one-liners.

Always think about “what if this selector returns nothing?”.


5. Self-check:

Reread your diff.

Check that all required fields in the schema are still produced.


6. Optionally run / pseudo-run:

Ensure the spider entry point is still:

scrapy crawl alkoteka -O result.json


7. No scope creep:

Do not refactor unrelated parts just because you “see improvements”.

Only touch what’s needed to satisfy this assignment.



11. Things You Must NOT Do

Do not:

Introduce Selenium, Playwright, or other browser tools.

Add random third-party libraries.

Change the output JSON structure.

Remove required fields from items.

Implement complex CLI, config systems, or UIs.

Touch user environment files (shell configs, git configs, etc.).

Generalize the project into a “universal scraping framework”.


If a requirement seems ambiguous:

Choose the simplest reasonable interpretation.

Leave a # TODO comment explaining the assumption.


End of agents.md.
