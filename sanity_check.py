import json
import sys
from pathlib import Path


# This is a small CLI helper; keeping all checks
# in one function is clearer than splitting it
# just to satisfy a complexity rule.
def sanity_check(file_path: str = "result.json") -> None:  # noqa: PLR0912
    path = Path(file_path)
    if not path.exists():
        print(f"❌ File '{file_path}' not found.")
        sys.exit(1)

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print(f"❌ File '{file_path}' is not valid JSON.")
        sys.exit(1)

    if not isinstance(data, list):
        print(f"❌ JSON root is not a list (got {type(data).__name__}).")
        sys.exit(1)

    total = len(data)
    print(f"✅ Loaded {total} items from '{file_path}'.")

    if total == 0:
        print("⚠️  Warning: List is empty.")
        return

    # Schema Check (First Item)
    item = data[0]
    required_keys = {
        "timestamp",
        "RPC",
        "url",
        "title",
        "marketing_tags",
        "brand",
        "section",
        "price_data",
        "stock",
        "assets",
        "metadata",
        "variants",
    }

    keys = set(item.keys())
    missing = required_keys - keys

    if missing:
        print(f"❌ Missing top-level keys in first item: {missing}")
        sys.exit(1)
    else:
        print("✅ Top-level schema: OK")

    # Nested Checks
    # Price
    price = item.get("price_data", {})
    if {"current", "original", "sale_tag"} <= set(price.keys()):
        print("✅ Price Data: OK")
    else:
        print(f"❌ Price Data missing keys: {set(price.keys())}")

    # Stock
    stock = item.get("stock", {})
    if {"in_stock", "count"} <= set(stock.keys()):
        print("✅ Stock Data: OK")
    else:
        print(f"❌ Stock Data missing keys: {set(stock.keys())}")

    # Metadata
    meta = item.get("metadata", {})
    if "__description" in meta:
        print("✅ Metadata (__description): OK")
        print(f"   Sample specs: {list(meta.keys())[:5]}")
    else:
        print("❌ Metadata missing '__description'")

    print("\n🎉 Sanity check passed!")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "result.json"
    sanity_check(target)
