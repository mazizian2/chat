from crewai import Crew, Task
from typing import Optional, Any, Dict, List
from typing import Optional, Any
import re
import uuid
import pyodbc
import json5
import json
import os
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
import asyncio
from socket_instance import sio
from general.state_manager import save_state

def extract_unique_values(filename, key):
    with open(filename, "r", encoding="utf-8") as file:
        data = json.load(file)
    return list(dict.fromkeys(item.get(key) for item in data if key in item))

with open("assets/json/data.json", "r", encoding="utf-8") as f:
    data = json.load(f)
with open("assets/json/details_plan.json", "r", encoding="utf-8") as f:
    details_plan = json.load(f)
keys_list = [list(item["plans"][0].keys()) for item in data if item.get("plans")]
details_data = sorted(set().union(*keys_list))
typeService = extract_unique_values("assets/json/data.json", "category")

category_description = [f"{item['category']}: {item['general_description']}" for item in data]

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)





def add_item_to_json(filename, item):
    """
    اگر شماره تلفن تکراری باشد، سفارش جدید به orders قبلی اضافه می‌شود.
    اگر جدید باشد، آیتم تازه ساخته می‌شود.
    """

    # فایل رو بخون
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                if not isinstance(data, list):
                    data = [data]
            except json.JSONDecodeError:
                data = []
    else:
        data = []

    phone = item["info"].get("phone")
    user_message = item.get("user_message", "")

    # پیدا کردن کاربر با شماره تلفن
    existing_user = None
    for entry in data:
        if entry.get("info", {}).get("phone") == phone:
            existing_user = entry
            break

    # اگر کاربر قبلاً وجود داشت → اضافه کردن سفارش جدید
    if existing_user:
        if "orders" not in existing_user:
            existing_user["orders"] = []
        if "user_messages" not in existing_user:
            existing_user["user_messages"] = []
        # اضافه کردن سفارش‌های جدید به لیست قدیمی
        existing_user["orders"].extend(item.get("orders", []))
        if user_message:
            existing_user["user_messages"].append(user_message)
        existing_user["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"🔄 سفارش جدید به کاربر با شماره {phone} اضافه شد.")

    else:
        # ساخت آیتم جدید
        new_id = data[-1]["id"] + 1 if data else 1
        item["id"] = new_id
        item["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if "user_message" in item:
            item["user_messages"] = [item.pop("user_message")]
        data.append(item)
        print(f"✅ کاربر جدید با شماره {phone} ثبت شد.")

    # ذخیره مجدد در فایل
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def add_item_to_support_json(filename, item):
    """
    ذخیره یا به‌روزرسانی اطلاعات پشتیبانی بر اساس PPPoE username.
    ساختار نهایی شامل:
      - selectAccount
      - problems
      - user_messages
      - token (اختیاری)
    """

    # خواندن فایل JSON (در صورت وجود)
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                if not isinstance(data, list):
                    data = [data]
            except json.JSONDecodeError:
                data = []
    else:
        data = []

    # استخراج فیلدها از داده ورودی
    selectAccount = item.get("selectAccount", {})
    pppoe_username = selectAccount.get("info", {}).get("pppoe_username")
    problems = item.get("problems", [])
    user_message = item.get("user_message", "")
    token = item.get("token", None)  # ← اضافه شد

    if not pppoe_username:
        print("⚠️ خطا: فیلد pppoe_username یافت نشد.")
        return

    # جستجوی کاربر بر اساس PPPoE
    existing_user = next(
        (entry for entry in data if entry.get("pppoe_username") == pppoe_username),
        None
    )

    if existing_user:
        # اگر کاربر قبلاً ثبت شده
        if "problems" not in existing_user:
            existing_user["problems"] = []
        if "user_messages" not in existing_user:
            existing_user["user_messages"] = []

        existing_user["problems"].extend(problems)
        if user_message:
            existing_user["user_messages"].append(user_message)

        # بروزرسانی توکن (در صورت تغییر)
        if token:
            existing_user["token"] = token

        existing_user["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"🔄 بروزرسانی برای PPPoE {pppoe_username}")

    else:
        # اگر کاربر جدید است
        new_id = max((entry.get("id", 0) for entry in data), default=0) + 1
        new_entry = {
            "id": new_id,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "pppoe_username": pppoe_username,
            "selectAccount": selectAccount,
            "problems": problems,
            "user_messages": [user_message] if user_message else [],
        }
        if token:
            new_entry["token"] = token  # ← اضافه شد

        data.append(new_entry)
        print(f"✅ کاربر جدید با PPPoE {pppoe_username} ثبت شد.")

    # ذخیره در فایل
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


# def add_item_to_support_json(filename, item):
#     """
#     ذخیره یا به‌روزرسانی اطلاعات پشتیبانی کاربر بر اساس PPPoE username.
#     ساختار نهایی شامل:
#     - selectAccount
#     - problems
#     - user_messages
#     """
#
#     # خواندن فایل (اگر وجود داشته باشد)
#     if os.path.exists(filename):
#         with open(filename, "r", encoding="utf-8") as f:
#             try:
#                 data = json.load(f)
#                 if not isinstance(data, list):
#                     data = [data]
#             except json.JSONDecodeError:
#                 data = []
#     else:
#         data = []
#
#     # استخراج فیلدها از ورودی
#     selectAccount = item.get("selectAccount", {})
#     pppoe_username = selectAccount.get("info", {}).get("pppoe_username")
#     problems = item.get("problems", [])
#     user_message = item.get("user_message", "")
#
#     if not pppoe_username:
#         print("⚠️ خطا: فیلد pppoe_username در داده ورودی یافت نشد.")
#         return
#
#     # بررسی وجود کاربر قبلی
#     existing_user = next(
#         (entry for entry in data if entry.get("pppoe_username") == pppoe_username),
#         None
#     )
#
#     if existing_user:
#         # اگر کاربر از قبل وجود دارد، فقط problems و message اضافه می‌کنیم
#         if "problems" not in existing_user:
#             existing_user["problems"] = []
#         if "user_messages" not in existing_user:
#             existing_user["user_messages"] = []
#
#         existing_user["problems"].extend(problems)
#         if user_message:
#             existing_user["user_messages"].append(user_message)
#
#         existing_user["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#
#         print(f"🔄 بروزرسانی: مشکل جدید برای PPPoE {pppoe_username} اضافه شد.")
#
#     else:
#         # ساخت کاربر جدید
#         new_id = max((entry.get("id", 0) for entry in data), default=0) + 1
#         new_entry = {
#             "id": new_id,
#             "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
#             "pppoe_username": pppoe_username,
#             "selectAccount": selectAccount,
#             "problems": problems,
#             "user_messages": [user_message] if user_message else []
#         }
#         data.append(new_entry)
#
#         print(f"✅ کاربر جدید با PPPoE {pppoe_username} ثبت شد.")
#
#     # ذخیره در فایل
#     with open(filename, "w", encoding="utf-8") as f:
#         json.dump(data, f, indent=4, ensure_ascii=False)

OUTPUT_HTML = (
    " خروجی را به صورت HTML تولید کن، بدون هیچگونه style، CSS یا inline style. "
    "فقط از تگ‌های HTML استاندارد استفاده کن مانند <p>, <ul>, <li>, <strong> و غیره. "
    "متن باید خوانا و ساده باشد و در صورت نیاز برای بهتر شدن پیام می‌توانی از ایموجی استفاده کنی. "
    "هیچ Markdown یا code block اضافه نکن. "
    "خروجی فقط HTML باشد و هیچ توضیح اضافی نده."
)


def get_last_intent(state: dict) -> str:
    """
    آخرین intent ذخیره‌شده را برمی‌گرداند.
    - اگر لیست intent خالی بود یا وجود نداشت → رشته خالی برگردانده می‌شود.
    """
    intents = state.get("intents", [])
    if intents:
        return intents[-1]
    return ""


def load_file(folder: str = "states", nameFile: str = ''):
    """
    خواندن آخرین ChatState از latest.json
    """
    path = os.path.join(folder, nameFile)
    print(path)
    if not os.path.exists(path):
        print("⚠️ فایل پیدا نشد.")
        return None

    with open(path, "r", encoding="utf-8") as f:
        state = json.load(f)

    print(f" از {path} خوانده شد.")
    return state


def get_country_by_city(city: str) -> str:
    city = city.strip().lower()
    data = {
        "tehran": "Iran",
        "paris": "France",
        "berlin": "Germany",
        "tokyo": "Japan",
        "cairo": "Egypt",
        "new york": "USA",
    }
    return data.get(city, "اطلاعاتی ندارم 😅")


def create_message(role: str, message: str, buttons: Optional[Any] = None, plans: Optional[Any] = None) -> Dict[
    str, Any]:
    """
    ساخت یک پیام با فرمت LangChain / ChatState

    Args:
        role (str): نقش پیام دهنده، مثلا "user" یا "bot"
        message (str): محتوای پیام

    Returns:
        Dict[str, str]: دیکشنری با کلیدهای "role" و "content"
    """
    # return {
    #     "role": role,
    #     "content": message,
    # }
    message_dict = {
        "role": role,
        "content": message
    }
    if buttons is not None:
        message_dict["buttons"] = buttons
    if plans is not None:
        message_dict["plans"] = plans
    return message_dict


def create_message_stream(role: str, message: str, buttons: Optional[Any] = None, plans: Optional[Any] = None) -> Dict[
    str, Any]:
    message_dict = {
        "role": role,
        "content": message
    }
    if buttons is not None:
        message_dict["buttons"] = buttons
    if plans is not None:
        message_dict["plans"] = plans
    return message_dict


# create message and run stream
def thread_message_stream(state: dict, context_message: str, threadId: str, assistantId: str, ):
    client.beta.threads.messages.create(
        role="user",
        content=context_message,
        thread_id=threadId,
    )
    steam_text = ""
    final = ""
    counter = 1
    unique_id = str(uuid.uuid4())

    with client.beta.threads.runs.stream(
            thread_id=threadId, assistant_id=assistantId
    ) as stream:
        for delta in stream.text_deltas:
            print(delta, end="", flush=True)  # چاپ زنده
            steam_text = delta
            final += steam_text
            counter += 1
            id = counter
            message_dict = {
                "uuid": unique_id,
                "counter": id,
                "role": "assistant",
                "content": steam_text
            }
            room = state["token"]
            asyncio.create_task(sio.emit(f"room_{room}", message_dict, room=room))

        final += stream.until_done() or ""
        print("\nassistant_response:", final)
    return final


# create message and run
def chat_create(messages: List[Any]):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        messages=messages
    )
    return response.choices[0].message.content
def thread_message_stream(state:dict,context_message:str,threadId:str,assistantId:str,):
    client.beta.threads.messages.create(
        role="user",
        content=context_message,
        thread_id=threadId,
    )
    steam_text = ""
    final = ""
    counter = 1
    unique_id = str(uuid.uuid4())

    with client.beta.threads.runs.stream(
            thread_id=threadId, assistant_id=assistantId
    ) as stream:
        for delta in stream.text_deltas:
            print(delta, end="", flush=True)  # چاپ زنده
            steam_text = delta
            final += steam_text
            counter += 1
            id = counter
            message_dict = {
                "uuid": unique_id,
                "counter": id,
                "role": "assistant",
                "content": steam_text
            }
            room = state["token"]
            asyncio.create_task(sio.emit(f"room_{room}", message_dict, room=room))

        final += stream.until_done() or ""
        print("\nassistant_response:", final)
    return final

#create message and run
async def thread_message(context_message:str,threadId:str,assistantId:str):
    client.beta.threads.messages.create(
        role="user",
        content=context_message,
        thread_id=threadId,
    )
    run = client.beta.threads.runs.create(
        assistant_id=assistantId,
        thread_id=threadId,
    )
    while run.status in ("queued", "in_progress"):
        await asyncio.sleep(1)
        run = client.beta.threads.runs.retrieve(thread_id=threadId, run_id=run.id)
    messages_page = client.beta.threads.messages.list(
        order="desc",
        limit=1,
        thread_id=threadId,
    )
    messages = messages_page.data  # → این یک list است
    last_msg = messages[0]  # چون limit=1
    value = last_msg.content[0].text.value
    print("intent res>>", value)
    return value

# create message and run stream
def chat_stream(messages: List[Any], state=None, buttons=None, plans=None):
    room = state["token"]
    unique_id = str(uuid.uuid4())
    stream_text = ""
    final_text = ""
    counter = 1
    with  client.chat.completions.stream(
            model="gpt-4o-mini",
            temperature=0.7,
            messages=messages,
    ) as stream:
        for event in stream:
            if event.type == 'content.delta':
                id = counter + 1
                stream_text = event.delta
                message_dict = {
                    "uuid": unique_id,
                    "counter": id,
                    "role": "assistant",
                    "content": stream_text,
                    "buttons": buttons,
                    "plans": plans,
                }
                asyncio.create_task(sio.emit(f"room_{room}", message_dict, room=room))


            elif event.type == "content.done":
                final_text = event.content
                # items={
                #     "uuid": unique_id,
                #     "buttons":buttons,
                # }
                # asyncio.create_task(sio.emit(f"room_{room}", items, room=room))

    return final_text


def parse_json5(text):
    """
        ورودی می‌تونه:
          - آبجکت پایتونی (dict یا list)
          - رشته JSON یا JSON5
          - رشته‌ای با بلاک کد مارک‌داون ```json ... ```
        باشه

        خروجی: همیشه آبجکت پایتونی (dict یا list)
        """
    # اگر خودش dict یا list باشه → مستقیم برگردون
    if isinstance(text, (dict, list)):
        return text

    # اگر رشته باشه
    if isinstance(text, str):
        # پاک کردن بلاک مارک‌داون ```json ... ```
        clean_text = re.sub(r"```(?:json|python)?\s*", "", text)
        clean_text = clean_text.replace("```", "").strip()

        try:
            return json5.loads(clean_text)
        except Exception as e:
            print("❌ خطا در parse:", e)
            return None

    print("❌ نوع ورودی پشتیبانی نمی‌شود:", type(text))
    return None


def run_task_as_crew(task: Task) -> str:
    crew = Crew(agents=[task.agent], tasks=[task], verbose=False)
    result = crew.kickoff()
    return result


async def run_async_task_as_crew(task: Task) -> str:
    crew = Crew(agents=[task.agent], tasks=[task], verbose=False)
    result = crew.ainvoke()
    return result


def _cleanup_history(folder: str, limit: int):
    """
    حذف فایل‌های تاریخچه قدیمی‌تر از limit
    """
    files = [
        f for f in os.listdir(folder)
        if f.endswith(".json") and f != "latest.json"
    ]
    files.sort()  # مرتب‌سازی بر اساس نام که timestamp هم هست

    # اگر تعداد فایل‌ها بیشتر از limit بود، حذف قدیمی‌ها
    if len(files) > limit:
        old_files = files[:-limit]
        for f in old_files:
            os.remove(os.path.join(folder, f))
            print(f"🗑 حذف نسخه قدیمی: {f}")


def load_latest_state(folder: str = "mehdi"):
    """
    خواندن آخرین ChatState از latest.json
    """
    latest_path = os.path.join(folder, "latest.json")

    if not os.path.exists(latest_path):
        print("⚠️ فایل latest.json پیدا نشد.")
        return None

    with open(latest_path, "r", encoding="utf-8") as f:
        state = json.load(f)

    print(f"📂 آخرین ChatState از {latest_path} خوانده شد.")
    return state


def extract_json_from_text(text: str) -> Optional[Any]:
    """
    تلاش می‌کند از متن داده شده اولین شیء JSON معتبر را استخراج و به دیکشنری پایتون تبدیل کند.
    اگر نتواند، None برمی‌گرداند.

    Args:
        text (str): متنی که ممکن است شامل JSON باشد.

    Returns:
        dict یا list یا None: شیء JSON تبدیل شده یا None اگر JSON معتبر نبود.
    """
    # جستجوی اولین بلاک {...}
    match = re.search(r"\{[^{}]*\}", text)

    if match:
        json_text = match.group(0)
        try:
            return json.loads(json_text)
        except json.JSONDecodeError:
            return None
    return None


def make_message(role: str, content: str) -> dict:
    """
    یک پیام با id و timestamp خودکار می‌سازد.

    :param role: نقش پیام ('assistant' یا 'user')
    :param content: محتوای پیام
    :return: دیکشنری پیام کامل
    """
    return {
        "id": str(uuid.uuid4()),
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat()
    }


def getIntent(intents: Dict[str, Any], intent_label):
    for intent in intents:
        if intent['intent'] == intent_label:
            return intent

    return None


def execute_stored_procedure(procedure_name, params=None):
    """
    اجرای یک Stored Procedure در SQL Server و بازگرداندن نتایج.

    :param server: آدرس سرور (IP یا hostname)
    :param database: نام دیتابیس
    :param username: نام کاربری
    :param password: پسورد
    :param procedure_name: نام Stored Procedure
    :param params: لیستی از پارامترها (در صورت وجود)
    :return: لیست نتایج
    """
    server = '185.237.85.3'
    database = 'ICA_DatacenterNew'
    username = 'sa'
    password = 'data3755'
    conn = None
    results = []
    try:
        # ساخت کانکشن
        conn = pyodbc.connect(
            'DRIVER={ODBC Driver 17 for SQL Server};'
            f'SERVER={server};'
            f'DATABASE={database};'
            f'UID={username};'
            f'PWD={password};'
            'Encrypt=yes;'
            'TrustServerCertificate=yes;'
        )
        cursor = conn.cursor()

        # اجرای Stored Procedure
        if params:
            # اگر پارامتر داشت
            placeholders = ','.join('?' for _ in params)
            query = f"EXEC {procedure_name} {placeholders}"
            cursor.execute(query, params)
        else:
            # بدون پارامتر
            query = f"EXEC {procedure_name}"
            cursor.execute(query)

        # گرفتن تمام نتایج
        results = cursor.fetchall()

        cursor.close()
    except Exception as e:
        print("Error:", e)
    finally:
        if conn:
            conn.close()
    rows_as_dict = [dict(zip([column[0] for column in row.cursor_description], row)) for row in results]

    # تبدیل به JSON
    json_result = json.dumps(rows_as_dict, default=str, ensure_ascii=False, indent=2)

    return json_result


def clean_and_load_json(response):
    # اگر CrewOutput داری
    if hasattr(response, "raw"):
        response = response.raw

    # اگر از قبل dict بود
    if isinstance(response, dict):
        return response

    s = str(response).strip()

    # حذف ```json ... ``` یا ``` ... ```
    s = re.sub(r'^```[a-zA-Z]*\s*', '', s)
    s = re.sub(r'\s*```$', '', s)

    # نرمال‌سازی نقل‌قول‌های هوشمند (اگر بود)
    s = s.replace('“', '"').replace('”', '"').replace('’', "'")

    try:
        return json.loads(s)
    except json.JSONDecodeError:
        # fallback: اولین بلوک JSON را از متن بیرون بکش
        return extract_first_json_object(s)


def extract_first_json_object(text):
    import json
    start = text.find('{')
    if start == -1:
        raise ValueError("No JSON object start found")
    depth = 0
    for i, ch in enumerate(text[start:], start):
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                block = text[start:i + 1]
                return json.loads(block)
    raise ValueError("Unbalanced or incomplete JSON in text")


def filter_by_date(data_list):
    drop_fields = ["Radif", "Company", "Porsant", "UpdateUser", "Fa_CreateDate", "ScoreUntivirus"]
    today = datetime.today().date()
    filtered = []

    for item in data_list:
        show_to_date = datetime.strptime(item['ShowToDate'], "%Y-%m-%d %H:%M:%S").date()
        if item['RanjeStatus'] == True and show_to_date >= today:
            new_item = item.copy()  # کپی می‌گیریم که دیتای اصلی دست‌نخورده بمونه
            if drop_fields:
                for f in drop_fields:
                    new_item.pop(f, None)  # حذف کلید در صورت وجود

            filtered.append(new_item)

    return filtered


def extract_min_max(data_list):
    """
    دریافت min و max برای فیلدهای مشخص
    :param data_list: لیستی از دیکشنری‌ها
    :return: دیکشنری شامل min و max برای هر فیلد
    """
    # مپ بین اسم‌های اصلی و اسم‌های خروجی
    field_map = {
        "Sorat": "speed",
        "Hajm": "volume",
        "DaySefaresh": "duration_days",
        "Gheimat": "budget"
    }

    result = {}

    for source_key, target_key in field_map.items():
        values = []
        for item in data_list:
            val = item.get(source_key)
            # تلاش برای تبدیل به عدد
            try:
                val = float(val)
            except Exception:
                continue
            values.append(val)

        if values:
            result[target_key] = {
                "min": min(values),
                "max": max(values)
            }

    return result


def apply_filters(services, filters):
    """
    فیلتر کردن لیست سرویس‌ها بر اساس شرایط داده شده
    :param services: لیستی از دیکشنری سرویس‌ها
    :param filters: دیکشنری فیلترها
    :return: لیست فیلتر شده
    """

    def check_range(value, f):
        """ بررسی بازه min/max """
        if f["status"] == "unset":
            return True
        if f["min"] is not None and value < f["min"]:
            return False
        if f["max"] is not None and value > f["max"]:
            return False
        return True

    def check_special(service, special):
        """ بررسی ویژگی‌های خاص """
        if special["status"] == "unset":
            return True

        # شبانه
        if special.get("night_free") is True and "شبانه" not in service.get("Shabaneh", ""):
            return False
        if special.get("night_free") is False and "شبانه" in service.get("Shabaneh", ""):
            return False

        # مودم
        if special.get("with_modem") is True and not service.get("Modem", False):
            return False
        if special.get("with_modem") is False and service.get("Modem", False):
            return False

        # سایر ویژگی‌ها (برای آینده میشه تکمیل کرد)
        return True

    # map کلیدهای سرویس به فیلتر
    field_map = {
        "Sorat": "speed",
        "Hajm": "volume",
        "DaySefaresh": "duration_days",
        "Gheimat": "budget"
    }

    filtered_services = []

    for s in services:
        ok = True
        for field, filter_name in field_map.items():
            f = filters["filters"][filter_name]
            try:
                val = float(s.get(field, 0))
            except:
                ok = False
                break
            if not check_range(val, f):
                ok = False
                break

        if ok and not check_special(s, filters["special_features"]):
            ok = False

        if ok:
            filtered_services.append(s)

    return filtered_services


def apply_filters(services, filters, limit=None):
    """
    فیلتر کردن لیست سرویس‌ها بر اساس شرایط داده شده
    :param services: لیستی از دیکشنری سرویس‌ها
    :param filters: دیکشنری فیلترها
    :param limit: تعداد آیتم خروجی (مثلا 5) - اگر None باشه همه برگردونده میشه
    :return: لیست فیلتر شده
    """

    def check_range(value, f):
        print(">>>>", value)
        print(">>>>", f)
        """ بررسی بازه min/max """
        if f["status"] == "unset":
            return True
        if f["min"] is not None and value < f["min"]:
            return False
        if f["max"] is not None and value > f["max"]:
            return False
        return True

    def check_special(service, special):
        """ بررسی ویژگی‌های خاص """
        if special["status"] == "unset":
            return True

        # شبانه
        if special.get("night_free") is True and "شبانه ندارد" not in service.get("Shabaneh", ""):
            return False
        if special.get("night_free") is False and "شبانه دارد" in service.get("Shabaneh", ""):
            return False

        # مودم
        if special.get("with_modem") is True and not service.get("Modem", False):
            return False
        if special.get("with_modem") is False and service.get("Modem", False):
            return False

        # سایر ویژگی‌ها
        return True

    # map کلیدهای سرویس به فیلتر
    field_map = {
        "Sorat": "speed",
        "Hajm": "volume",
        "DaySefaresh": "duration_days",
        "Gheimat": "budget"
    }

    filtered_services = []

    for s in services:
        ok = True
        for field, filter_name in field_map.items():
            f = filters["filters"][filter_name]
            try:
                val = float(s.get(field, 0))
            except:
                ok = False
                break
            if not check_range(val, f):
                ok = False
                break

        if ok and not check_special(s, filters["special_features"]):
            ok = False

        if ok:
            filtered_services.append(s)
            # اگر limit مشخص شده بود و پر شد، break
            if limit is not None and len(filtered_services) >= limit:
                break

    return filtered_services


def read_json_file_support(file_name: str):
    base_dir = "data/supports"  # مسیر پوشه‌ای که فایل‌ها در آن ذخیره می‌شوند
    file_path = os.path.join(base_dir, file_name)

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"فایل '{file_path}' پیدا نشد.")

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def read_json_file(file_name: str):
    base_dir = "data/users"  # مسیر پوشه‌ای که فایل‌ها در آن ذخیره می‌شوند
    file_path = os.path.join(base_dir, file_name)

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"فایل '{file_path}' پیدا نشد.")

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data
