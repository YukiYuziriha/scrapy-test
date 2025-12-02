# Alkoteka Scraper Scaffold

This repository contains a Scrapy project for parsing products from alkoteka.com.

## Requirements
- Python 3.10+
- Scrapy 2.11+

## Setup

1.  **Create and activate a virtual environment:**

    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

2.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

3.  **Install pre-commit hooks:**

    ```bash
    pre-commit install
    ```

## Configuration

The spider can be configured via `config.ini` or Command Line Interface (CLI) arguments.

### `config.ini`
The default configuration is stored in `config.ini`. You can add new cities by adding their UUIDs to the `[cities]` section.

```ini
[spider]
base_url = https://alkoteka.com
categories_file = categories.txt
default_city = krasnodar

[cities]
krasnodar = 4a70f9e0-46ae-11e7-83ff-00155d026416
sochi = 985b3eea-46b4-11e7-83ff-00155d026416
```

### Category File Format
The category file (default: `categories.txt`) should contain one URL or path per line.
- **Full URLs:** `https://alkoteka.com/catalog/vino`
- **Relative Paths:** `/catalog/vino` (will be appended to `base_url`)

Example:
```text
https://alkoteka.com/catalog/krepkiy-alkogol
/catalog/vino
/catalog/shampanskoe-i-igristye-vina
```

## Running the Spider

### 1. Simplest Way (Default)
Just run this. It will scrape **100 items per category** (from `categories.txt`) using the default city (**Krasnodar**).
```bash
scrapy crawl alkoteka -O result.json
```

### 2. Customizing the Number of Items
Want fewer or more items? Use the `max_items` argument.
*Note: This sets the limit **PER CATEGORY**.*

**Get only 10 items per category:**
```bash
scrapy crawl alkoteka -a max_items=10 -O result.json
```

**Get 500 items per category:**
```bash
scrapy crawl alkoteka -a max_items=500 -O result.json
```

### 3. Other Customizations (Advanced)
You can mix and match these arguments:

**Select a specific city:**
```bash
scrapy crawl alkoteka -a city=sochi -O result.json
```

**Use a different category file:**
```bash
scrapy crawl alkoteka -a categories=my_custom_list.txt -O result.json
```

**Combine everything:**
"I want 50 items per category, from Sochi, using my custom list."
```bash
scrapy crawl alkoteka -a city=sochi -a categories=my_custom_list.txt -a max_items=50 -O result.json
```

## Managing Cities
To use a different city as the default:
1.  Find the city's UUID (e.g., from the API request `city_uuid` parameter).
2.  Add it to `[cities]` in `config.ini`.
3.  Change `default_city` in the `[spider]` section to your new city key.

## Validation

### 1. Sanity check helper
To verify that `result.json` matches the required schema and contains data, use the bundled helper:

```bash
python3 sanity_check.py
```

Or specify a different file:
```bash
python3 sanity_check.py my_results.json
```

`sanity_check.py` will:
- ensure the file exists and is valid JSON
- confirm the root is a list and print the total number of items
- check the first item against the required top-level keys
- validate nested `price_data`, `stock`, and `metadata.__description`

### 2. Quick manual JSON reading
To quickly inspect the pretty-printed JSON (first few lines):

```bash
python3 -m json.tool result.json | head
```

Or inspect basic stats and the first item:

```bash
python3 - << 'PY'
import json
from pathlib import Path

data = json.loads(Path("result.json").read_text(encoding="utf-8"))
print("Total products:", len(data))
print("First product:", data[0] if data else None)
PY
```

## Proxy support

Proxy support is enabled via a downloader middleware and configured through `proxies.txt` in the project root.

- One proxy URL per line, e.g.:

  ```text
  # HTTP proxies
  http://user:pass@host1:port1
  http://host2:port2
  ```

- Empty or commented lines (`# ...`) are ignored.
- If `proxies.txt` is missing or empty, the spider runs without a proxy.

To quickly confirm that proxies are being applied, you can put a dummy entry like `http://127.0.0.1:9999` into `proxies.txt` and run the spider; connection-refused errors indicate that Scrapy is attempting to use the proxy.

## Notes
- Region (city) is controlled via `config.ini` / `-a city=...` and passed as `city_uuid` to all API calls.
