import json

with open("assets/json/main.json", "r", encoding="utf-8") as f:
    data = json.load(f)
data = data[0]
keys_list = [list(data["products"][0].keys())] if "products" in data and len(data["products"]) > 0 else []

askable = data.get("askable", [])
askable_fields = [item["field"] for item in askable] if askable else []
FIELDS = askable_fields if askable_fields != [] else sorted(set().union(*keys_list))
FIELDS_EXAMPLE = askable if askable != [] else sorted(set().union(*keys_list))

description_data = data.get("description", "")
unique_categories = list({item["category_type"] for item in data["products"]})
products = data["products"]