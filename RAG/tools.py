import os
import json
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from openai import OpenAI
from langchain_huggingface import HuggingFaceEmbeddings
import chromadb
from typing import Any
from general.state_manager import save_state
import uuid


def normalize_value(value):
    if isinstance(value, list):
        return ", ".join(map(str, value))

    if isinstance(value, dict):
        return value['title'].strip()
        # return " | ".join(f"{k}: {v}" for k, v in value.items())

    if isinstance(value, bool):
        return "بله" if value else "خیر"

    if value is None:
        return "—"

    return str(value)


def humanize_key(key: str) -> str:
    return key.replace("_", " ").strip()


def json_to_docs_universal(json_data: dict) -> list:
    docs = []

    services = json_data
    for service in services:
        name = service.get("name", "")
        #
        # for plan in service.get("products", []):
        #
        #     lines = [
        #         "مشخصات:"
        #     ]
        #     metadata = {}
        #     for key, value in plan.items():
        #         readable_key = humanize_key(key)
        #         readable_value = normalize_value(value)
        #         lines.append(f"- {readable_key}: {readable_value}")
        #         # if key in askable:
        #         metadata[key] = f"{readable_value}"
        for plan in service.get("products", []):

            # --- خلاصه‌ی معنایی برای embedding ---
            summary = (
                f"نام محصول: {plan.get('title', 'نامشخص')} | "
                f"توضیحات محصول: {plan.get('description', 'نامشخص')} | "
                f"دسته‌بندی: {(plan.get('category') or {}).get('title', 'نامشخص').strip()} | "
                f"ویژگی محصول: {plan.get('extra_feature', 'نامشخص')} | "
                f"قیمت: {plan.get('price', 'نامشخص')} تومان"
            )

            # summary = ( f"""
            #
            #                 نام پلن: {str(plan.get('name', ''))}
            #                 حداقل سرعت: {str(plan.get('min_speed', ''))}مگابیت،
            #                 حداکثر سرعت: {str(plan.get('max_speed', ''))}مگابیت،
            #                 سرعت آپلود: {str(plan.get('upload_speed', ''))}مگابیت،
            #                 f"{'قابل حمل' if plan.get('movable') == 'دارد' else 'ثابت'}، "
            #                 پوشش: {str(plan.get('coverage', ''))}
            #                 f"{'مودم دارد' if plan.get('modem') == 'دارد' else 'بدون مودم'}، "
            #                 ترافیک شبانه: {plan.get('night_traffic', '')}
            #                 حجم ترافیک: {str(plan.get('traffic', ''))}مگابیت،
            #                 مدت زمان: {str(plan.get('duration_days', ''))}روزه،
            #                 IP: {str(plan.get('ip', ''))}
            #                 قیمت: {str(plan.get('price', ''))} تومان
            #                 """
            # )

            lines = [
                summary,
                "",
                "مشخصات کامل:"
            ]

            metadata = {}

            for key, value in plan.items():
                lines.append(f"- {humanize_key(key)}: {normalize_value(value)}")

                # --- متادیتا عددی واقعی ---
                if isinstance(value, (int, float)):
                    metadata[key] = value
                else:
                    metadata[key] = normalize_value(value)

            # یک Document کامل برای هر محصول
            docs.append(
                Document(
                    page_content="\n".join(lines),
                    metadata=metadata
                )
            )
    return docs
def json_to_docs_question_answer(json_data: list) -> list:
    docs = []

    for service in json_data:
        # --- خلاصه‌ی معنایی برای embedding ---
        summary = f"{service['question']}\n{service['answer']}"

        # summary = (
        #     f"پرسش: {service.get('question', 'نامشخص')} | "
        #     f"پاسخ: {service.get('answer', 'نامشخص')}"
        # )

        # --- متادیتا ---
        metadata = {}
        for key, value in service.items():
            if isinstance(value, (int, float)):
                metadata[key] = value
            else:
                metadata[key] = normalize_value(value)  # یا همان value اگر نیازی به تغییر نیست

        # --- ایجاد Document ---
        docs.append(
            Document(
                page_content=summary,
                metadata=metadata
            )
        )

    return docs# def json_to_docs_qestion_answer(json_data: dict) -> list:
#     docs = []
#
#     services = json_data
#     for service in services:
#             # --- خلاصه‌ی معنایی برای embedding ---
#             summary = (
#                 f"پرسش: {service.get('question', 'نامشخص')} | "
#                 f"پاسخ {service.get('answer', 'نامشخص')} | "
#
#             )
#
#             lines = [
#                 summary,
#                 "",
#             ]
#
#             metadata = {}
#
#             for key, value in service.items():
#                 lines.append(f"- {humanize_key(key)}: {normalize_value(value)}")
#
#                 # --- متادیتا عددی واقعی ---
#                 if isinstance(value, (int, float)):
#                     metadata[key] = value
#                 else:
#                     metadata[key] = normalize_value(value)
#
#             # یک Document کامل برای هر محصول
#             docs.append(
#                 Document(
#                     page_content="\n".join(lines),
#                     metadata=metadata
#                 )
#             )
#     return docs


def set_chroma_db_from_json(db_name: str, docs: list[Document], mode: str = "overwrite"):
    """
    docs: لیستی از Documentهای langchain
    mode: "overwrite" یا "append"
    """
    save_path = os.path.join("chroma_dbs", db_name)
    os.makedirs(save_path, exist_ok=True)

    # --- Embeddings ---
    # embeddings = HuggingFaceEmbeddings(model_name="intfloat/e5-large")
    embeddings = HuggingFaceEmbeddings(model_name="intfloat/multilingual-e5-base")

    # --- اتصال به Chroma ---
    client = chromadb.PersistentClient(path=save_path)

    # بررسی اینکه collection وجود دارد یا نه
    existing_collections = [c.name for c in client.list_collections()]

    if db_name in existing_collections:
        collection = client.get_collection(db_name)
        if mode == "append":
            print(f"🟢 دیتابیس '{db_name}' پیدا شد — در حال افزودن داده‌های جدید...")
            # for doc in docs:
            #     embedding_vector = embeddings.embed_query(doc.page_content)
            for doc in docs:
                embedding_vector = embeddings.embed_documents(
                    [f"passage: {doc.page_content}"]
                )[0]
                collection.add(
                    ids=[doc.metadata.get("id", str(uuid.uuid4()))],
                    documents=[doc.page_content],
                    embeddings=[embedding_vector],
                    metadatas=[doc.metadata]

                )
            print(f"✅ داده‌های جدید به '{db_name}' اضافه شد.")
        elif mode == "overwrite":
            print(f"🟠 دیتابیس '{db_name}' بازنویسی می‌شود...")
            client.delete_collection(db_name)
            collection = client.create_collection(db_name)
            for doc in docs:
                embedding_vector = embeddings.embed_documents(
                    [f"passage: {doc.page_content}"]
                )[0]
                collection.add(
                    ids=[doc.metadata.get("id", str(uuid.uuid4()))],
                    documents=[doc.page_content],
                    embeddings=[embedding_vector],
                    metadatas=[doc.metadata]
                )
            print(f"✅ دیتابیس '{db_name}' با داده‌های جدید جایگزین شد.")
        else:
            raise ValueError("mode باید یکی از 'append' یا 'overwrite' باشد.")
    else:
        print(f"🔹 دیتابیس '{db_name}' وجود ندارد — در حال ساخت جدید...")
        collection = client.create_collection(db_name)
        for doc in docs:
            embedding_vector = embeddings.embed_documents(
                [f"passage: {doc.page_content}"]
            )[0]            # embedding_vector = embeddings.embed_documents([f"passage: {doc.page_content}"])[0]

            collection.add(
                ids=[doc.metadata.get("id", str(uuid.uuid4()))],
                documents=[doc.page_content],
                embeddings=[embedding_vector],
                metadatas=[doc.metadata]
            )
        print(f"✅ دیتابیس جدید '{db_name}' ساخته شد.")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "models", "multilingual-e5-base")
def build_extra_query(optional_data):
    parts = []
    for k, v in optional_data.items():
        parts.append(f"{k} {v}")

    return ", ".join(parts)

def ask_chroma_question(db_name: str, query: dict, orQuery: Any,state=None, k: int = 10,)->dict:
    print("query is>> tools", query)
    print("or query is>> tools", orQuery)
    state['status_search']=0
    save_state(state)
    # embeddings = HuggingFaceEmbeddings(model_name="intfloat/e5-large")
    embeddings = HuggingFaceEmbeddings(model_name=r"C:\models\multilingual-e5-base\models--intfloat--multilingual-e5-base\snapshots\835193815a3936a24a0ee7dc9e3d48c1fbb19c55",model_kwargs={"local_files_only": True})
    feature = query.get("extra_feature", "")
    feature2 = build_extra_query(orQuery) if isinstance(orQuery, dict) else orQuery
    parts = [p for p in [feature, feature2] if p]
    final_query = " ".join(parts)
    query_vector = embeddings.embed_query(f"query: {final_query}")
    print('query_vector is>>>',final_query)

    persist_directory = f"chroma_dbs/{db_name}"
    client = chromadb.PersistentClient(path=persist_directory)

    if db_name not in [c.name for c in client.list_collections()]:
        raise ValueError(f"❌ دیتابیس '{db_name}' یافت نشد!")

    collection = client.get_collection(db_name)
    where_clause = None
    query.pop("extra_feature", None)
    if query:
        if len(query) == 1:
            k_, v_ = next(iter(query.items()))
            where_clause = {k_: v_}
        else:
            where_clause = {
                "$and": [{k: v} for k, v in query.items()]
            }
            print("where_clause",where_clause)

    results = collection.query(
        query_embeddings=[query_vector],
        n_results=k,
        where=where_clause
    )
    docs = results["documents"][0]
    distances = results["distances"][0]
    print("docs & distances>>",docs,distances)
    if(len(docs)>0):
      avg_dist = sum(distances) / len(distances)
      res=[doc for doc, dist in zip(docs, distances) if dist <= avg_dist]
      final_docs = {"result":res,"status":"main"}
    else:
        if query:
            if len(query) == 1:
                k_, v_ = next(iter(query.items()))
                where_clause = {k_: v_}
            else:
                where_clause = {
                    "$or": [{k: v} for k, v in query.items()]
                }
        print("where_clause is>>>", where_clause)
        results = collection.query(
            query_embeddings=[query_vector],
            n_results=4,
            where=where_clause
        )
        final_docs = {"result": results["documents"][0], "status": "alternative"}
    print("final_docs is>>>",final_docs['result'])
    state['status_search'] = 1
    save_state(state)
    return final_docs
    # for i, doc_text in enumerate(docs):

    # docs = results["documents"][0]
    # distances = results["distances"][0]
    # print("results rag is>>",results)
    # # فیلتر کردن و مرتب‌سازی
    # filtered = [(doc, dist) for doc, dist in zip(docs, distances)]
    # filtered.sort(key=lambda x: x[1])
    #
    # final_docs = filtered[:k]
    #
    # print(f"⚡ Threshold فاصله خودکار: {max_distance:.3f}")
    # for i, (doc_text, dist) in enumerate(final_docs):
    #     print(f"🔹 نتیجه {i + 1} (distance: {dist:.3f}):\n{doc_text}\n{'-'*50}")
    #
    # return [doc for doc, _ in final_docs]


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


def json_to_docs_custom(json_data: dict, root_key: str, key_map: dict, chunk_size=500, chunk_overlap=100) -> list:
    """
    json_data: دیکشنری JSON ورودی
    root_key: کلیدی که لیست اصلی در آن قرار دارد (مثل "internet_services")
    key_map: دیکشنری که mapping بین کلیدهای JSON و عنوان متن را مشخص می‌کند
             مثال:
             {
                 "type": "سرویس",
                 "description": "توضیحات",
                 "products.name": "نام پلن",
                 "products.min_speed": "حداقل سرعت",
                 "products.max_speed": "حداکثر سرعت"
             }
    """
    docs = []

    for item in json_data.get(root_key, []):
        # برای کلیدهای سطح اول
        text_parts = []
        for k, label in key_map.items():
            # بررسی اینکه key مربوط به پلن است یا خود سرویس
            if k.startswith("products."):
                continue
            value = item.get(k, "")
            text_parts.append(f"{label}: {value}")

        # پردازش پلن‌ها در صورت وجود
        for plan in item.get("products", []):
            plan_parts = text_parts.copy()
            for k, label in key_map.items():
                if k.startswith("products."):
                    plan_key = k.split(".")[1]  # مثلا 'name'
                    value = plan.get(plan_key, "")
                    plan_parts.append(f"{label}: {value}")

            full_text = "\n".join(plan_parts)

            # تقسیم متن به chunk
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
            chunks = splitter.split_text(full_text)

            # ساخت Document
            for chunk in chunks:
                docs.append(Document(page_content=chunk))

    return docs


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


def flatten_json_dynamic(json_data):
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
