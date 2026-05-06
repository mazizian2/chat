import json

with open("assets/json/main.json", "r", encoding="utf-8") as f:
    data = json.load(f)
data = data[0]
keys_list = [list(data["products"][0].keys())] if "products" in data and len(data["products"]) > 0 else []

askable = data.get("askable", [])

# استخراج فیلدهای required
required_fields = {
    item["field"] for item in askable if item["required"]
}
askable_fields = [item["field"] for item in askable] if askable else []
FIELDS = askable_fields if askable_fields != [] else sorted(set().union(*keys_list))
FIELDS_EXAMPLE = askable if askable != [] else sorted(set().union(*keys_list))

description_data = data.get("description", "")
unique_categories = list({item["category"]['title'] for item in data["products"]})
unique_product = list({item['title'] for item in data["products"]})
products = data["products"]
Personality=data.get("type", "")
extra_field='extra_feature'
def split_query_by_required(query):

    required_data = {}
    optional_data = {}

    for key, value in query.items():
        if key in required_fields:
            required_data[key] = value
        else:
            optional_data[key] = value

    return required_data, optional_data