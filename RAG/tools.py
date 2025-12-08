import os
import json
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from openai import OpenAI
from langchain_huggingface import HuggingFaceEmbeddings


def set_faiss_db_from_json(db_name: str, docs: Document, mode: str = "overwrite"):
    save_path = os.path.join("faiss_dbs", db_name)
    os.makedirs(save_path, exist_ok=True)

    # --- Embeddings ---

    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/LaBSE")

    faiss_index_path = os.path.join(save_path, "index.faiss")
    faiss_pkl_path = os.path.join(save_path, "index.pkl")

    if os.path.exists(faiss_index_path) and os.path.exists(faiss_pkl_path):
        if mode == "append":
            print(f"🟢 دیتابیس '{db_name}' پیدا شد — در حال افزودن داده‌های جدید...")
            vectorstore = FAISS.load_local(save_path, embeddings, allow_dangerous_deserialization=True)
            vectorstore.add_documents(docs)
            vectorstore.save_local(save_path)
            print(f"✅ داده‌های جدید به '{db_name}' اضافه شد.")
        elif mode == "overwrite":
            print(f"🟠 دیتابیس '{db_name}' بازنویسی می‌شود...")
            vectorstore = FAISS.from_documents(docs, embeddings)
            vectorstore.save_local(save_path)
            print(f"✅ دیتابیس '{db_name}' با داده‌های جدید جایگزین شد.")
        else:
            raise ValueError("mode باید یکی از 'append' یا 'overwrite' باشد.")
    else:
        print(f"🔹 دیتابیس '{db_name}' وجود ندارد — در حال ساخت جدید...")
        vectorstore = FAISS.from_documents(docs, embeddings)
        vectorstore.save_local(save_path)
        print(f"✅ دیتابیس جدید '{db_name}' ساخته شد.")


#
def ask_faiss_question(db_name: str, query: str, k: int = 7):
    """
    یک سوال از دیتابیس FAISS می‌پرسد و نتایج نزدیک‌ترین متون را برمی‌گرداند.

    پارامترها:
    db_name : str : نام دیتابیس در پوشه faiss_dbs
    query   : str : سوالی که می‌خواهی بپرسی
    k       : int : تعداد نتایج نزدیک که می‌خواهی نمایش داده شود
    """
    # آماده‌سازی embedding
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/LaBSE")

    # لود دیتابیس
    vectorstore_path = f"faiss_dbs/{db_name}"
    vectorstore = FAISS.load_local(vectorstore_path, embeddings, allow_dangerous_deserialization=True)

    # جستجو
    results = vectorstore.similarity_search(query, k=k)

    # نمایش نتایج
    for i, doc in enumerate(results):
        print(f"🔹 نتیجه {i + 1}:\n{doc.page_content}\n{'-' * 50}")
    return results


def answer_with_ai(faiss_results, user_query):
    client = OpenAI()
    context = "\n\n".join([doc.page_content for doc in faiss_results])

    prompt = f"""
شما یک دستیار هوشمند هستید. با توجه به اطلاعات زیر، به سوال کاربر پاسخ کامل:

اطلاعات:
{context}

سوال کاربر:
{user_query}

پاسخ:
"""

    print("ai", prompt)
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,  # پاسخ دقیق و واقعی
        max_tokens=500
    )

    answer = response.choices[0].message.content
    return answer


def json_to_docs_internet(json_data: dict) -> list:
    docs = []

    for service in json_data.get("internet_services", []):
        service_type = service.get("type", "")
        service_desc = service.get("description", "")

        for plan in service.get("plans", []):

            # --- ساخت متن ---
            text = f"""
                سرویس: {str(service_type)}
                توضیحات: {str(service_desc)}
                نام پلن: {str(plan.get('name', ''))}
                حداقل سرعت: {str(plan.get('min_speed', ''))}
                حداکثر سرعت: {str(plan.get('max_speed', ''))}
                سرعت آپلود: {str(plan.get('upload_speed', ''))}
                قابل جابه‌جایی: {plan.get('movable', '')}
                پوشش: {str(plan.get('coverage', ''))}
                مودم: {plan.get('movable', '')}
                ترافیک شبانه: {plan.get('night_traffic', '')}
                حجم ترافیک: {str(plan.get('traffic', ''))}
                مدت زمان: {str(plan.get('duration', ''))}
                IP: {str(plan.get('ip', ''))}
                قیمت: {str(plan.get('price', ''))}
                """

            # --- تقسیم متن به chunk ---
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=500,
                chunk_overlap=100
            )
            chunks = splitter.split_text(text)

            # --- ساخت Document ---
            for chunk in chunks:
                docs.append(Document(page_content=chunk))

    return docs


def type_des_to_text(category, general_desc):
    """
    ورودی: دسته‌بندی، توضیحات عمومی، روش سفارش و دیتای plan
    خروجی: یک رشته متن فارسی برای embedding
    """

    def normalize_value(value):
        """تبدیل مقادیر None، False و رشته‌های خالی به 'ندارد'"""
        if value in [None, False, "", "null", "None"]:
            return "ندارد"
        if value is True:
            return "دارد"
        return str(value)

    text_parts = [
        f"دسته‌بندی: {category}",
        # f"عنوان: {plan.get('title', '---')}",
        # f"توضیحات: {normalize_value(plan.get('description'))}",
        # f"قیمت: {normalize_value(plan.get('price'))}",
        # f"مدت زمان: {normalize_value(plan.get('duration'))} روز",
    ]

    # فیلدهای ویژه در صورت وجود
    # excluded_keys = ['id', 'title', 'description', 'price', 'duration']
    # special_fields = {k: v for k, v in plan.items() if k not in excluded_keys}
    #
    # for key, value in special_fields.items():
    #     text_parts.append(f"{key}: {normalize_value(value)}")

    # اضافه کردن توضیحات عمومی سرویس
    text_parts.append(f"توضیحات کلی سرویس: {normalize_value(general_desc)}")
    text_parts.append(f"نام سرویس سرویس: {normalize_value(category)}")
    # text_parts.append(f"روش سفارش: {normalize_value(order_desc)}")

    return "\n".join(text_parts)


def plan_to_text(category, plan):
    """
    ورودی: دسته‌بندی، توضیحات عمومی، روش سفارش و دیتای plan
    خروجی: یک رشته متن فارسی برای embedding
    """

    def normalize_value(value):
        """تبدیل مقادیر None، False و رشته‌های خالی به 'ندارد'"""
        if value in [None, False, "", "null", "None"]:
            return "ندارد"
        if value is True:
            return "دارد"
        return str(value)

    text_parts = [
        f"دسته‌بندی: {category}",
        f"عنوان: {plan.get('title', '---')}",
        f"توضیحات: {normalize_value(plan.get('description'))}",
        f"قیمت: {normalize_value(plan.get('price'))}",
        f"مدت زمان: {normalize_value(plan.get('duration'))} روز",
        f"مدت زمان: {normalize_value(plan.get('duration'))} روز",
        f"پیشنهاد ویژه{normalize_value(plan.get('special_offer'))}"
        f"نوع قرارداد{normalize_value(plan.get('contract_type'))}"
        f"هزینه راه اندازی :{normalize_value(plan.get('setup_cost'))}"
        f" منطقه{normalize_value(plan.get('region'))}"
        f" ترافیک{normalize_value(plan.get('traffic'))} GB"
        f"ترافیک شب{normalize_value(plan.get('night_traffic'))}"
        f"حداقل سرعت{normalize_value(plan.get('min_speed'))}"
        f"حداکثر آپلود{normalize_value(plan.get('max_download'))}"
        f"نوع سرویس{normalize_value(plan.get('service_type'))}"


    ]

    # فیلدهای ویژه در صورت وجود
    excluded_keys = ['id', 'title', 'description', 'price', 'duration']
    special_fields = {k: v for k, v in plan.items() if k not in excluded_keys}

    for key, value in special_fields.items():
        text_parts.append(f"{key}: {normalize_value(value)}")

    # اضافه کردن توضیحات عمومی سرویس

    return "\n".join(text_parts)


def flatten_plans_dynamic(json_data):
    flat_items = []
    docs = []

    for category_item in json_data:
        category = category_item.get("category", "")
        # general_desc = category_item.get("general_description", "")
        # order_desc = category_item.get("order_description", "")

        for plan in category_item.get("plans", []):
            full_text = plan_to_text(category, plan)
            flat_items.append({
                # "id": plan.get("id"),
                # "category": category,
                "text": full_text
            })
            # --- تقسیم متن به chunk ---
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=500,
                chunk_overlap=100
            )
            chunks = splitter.split_text(full_text)

            # --- ساخت Document ---
            for chunk in chunks:
                docs.append(Document(page_content=chunk))
    return docs


def flatten_services_dynamic(json_data):
    flat_items = []
    docs = []

    for category_item in json_data:
        category = category_item.get("category", "")
        general_desc = category_item.get("general_description", "")
        order_desc = category_item.get("order_description", "")

        for plan in category_item.get("plans", []):
            full_text = type_des_to_text(category, general_desc)
            flat_items.append({
                "id": plan.get("id"),
                "category": category,
                "text": full_text
            })
            # --- تقسیم متن به chunk ---
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=500,
                chunk_overlap=100
            )
            chunks = splitter.split_text(full_text)

            # --- ساخت Document ---
            for chunk in chunks:
                docs.append(Document(page_content=chunk))
    return docs
