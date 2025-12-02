# Alkoteka Scraper Scaffold

This repository contains a Scrapy project scaffold for parsing products from alkoteka.com.

## Requirements
- Python 3.10+
- Scrapy 2.11+

## Running the spider
```
scrapy crawl alkoteka -O result.json
```

## Notes
- Category URLs should be placed in `categories.txt` (one per line) or defined inside the spider.
- Proxy support and region handling are left as TODOs in `middlewares.py` and the spider stub.
