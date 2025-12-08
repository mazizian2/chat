
from crewai import Crew,Task
import os
from datetime import datetime
import json
from typing import Optional, Any
import re
import uuid
import pyodbc

OUTPUT_HTML = (
    " خروجی را به صورت HTML تولید کن، بدون هیچگونه style، CSS یا inline style. "
    "فقط از تگ‌های HTML استاندارد استفاده کن مانند <p>, <ul>, <li>, <strong> و غیره. "
    "متن باید خوانا و ساده باشد و در صورت نیاز برای بهتر شدن پیام می‌توانی از ایموجی استفاده کنی. "
    "هیچ Markdown یا code block اضافه نکن. "
    "خروجی فقط HTML باشد و هیچ توضیح اضافی نده."
)

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


def run_task_as_crew(task: Task) -> str:
    crew = Crew(agents=[task.agent], tasks=[task], verbose=False)
    result = crew.kickoff()
    return result
async def run_async_task_as_crew(task: Task) -> str:
    crew = Crew(agents=[task.agent], tasks=[task], verbose=False)
    result = crew.ainvoke()
    return result


def save_state(state: dict, folder: str = "mehdi", history_limit: int = 5):
    """
    ذخیره‌سازی ChatState به دو صورت:
    1. فایل latest.json (آخرین وضعیت)
    2. فایل با timestamp برای تاریخچه (محدود به history_limit)
    """

    # اطمینان از وجود پوشه
    os.makedirs(folder, exist_ok=True)

    # مسیر فایل آخرین وضعیت
    latest_path = os.path.join(folder, "latest.json")

    # مسیر فایل تاریخچه با timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    history_path = os.path.join(folder, f"{timestamp}.json")

    # ذخیره در latest.json
    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    # ذخیره نسخه تاریخچه
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    # مدیریت محدودیت تعداد نسخه‌های تاریخچه
    _cleanup_history(folder, history_limit)

    print(f"✅ ChatState ذخیره شد: {latest_path} و {history_path}")

    return {"latest": latest_path, "history": history_path}

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
    match  = re.search(r"\{[^{}]*\}", text)

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
        #fallback: اولین بلوک JSON را از متن بیرون بکش
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
                block = text[start:i+1]
                return json.loads(block)
    raise ValueError("Unbalanced or incomplete JSON in text")


def filter_by_date(data_list):
    drop_fields = ["Radif","Company","Porsant","UpdateUser","Fa_CreateDate","ScoreUntivirus"]
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
        print(">>>>",value)
        print(">>>>",f)
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