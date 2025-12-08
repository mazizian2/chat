import os
from datetime import datetime
import json
from typing import Optional, Any
import re
import uuid



def save_state(data: dict, folder_path: str = "data/users"):

    os.makedirs(folder_path, exist_ok=True)


    file_path = os.path.join(folder_path, f"{data['token']}.json")

    print(">>>>",file_path)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    return file_path
# def save_state(state: dict, folder: str = "states", history_limit: int = 5):
#     """
#     ذخیره‌سازی ChatState به دو صورت:
#     1. فایل latest.json (آخرین وضعیت)
#     2. فایل با timestamp برای تاریخچه (محدود به history_limit)
#     """
#
#     # اطمینان از وجود پوشه
#     os.makedirs(folder, exist_ok=True)
#
#     # مسیر فایل آخرین وضعیت
#     latest_path = os.path.join(folder, "latest.json")
#
#     # مسیر فایل تاریخچه با timestamp
#     timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#     history_path = os.path.join(folder, f"{timestamp}.json")
#
#     # ذخیره در latest.json
#     with open(latest_path, "w", encoding="utf-8") as f:
#         json.dump(state, f, ensure_ascii=False, indent=2)
#
#     # ذخیره نسخه تاریخچه
#     with open(history_path, "w", encoding="utf-8") as f:
#         json.dump(state, f, ensure_ascii=False, indent=2)
#
#     # مدیریت محدودیت تعداد نسخه‌های تاریخچه
#     _cleanup_history(folder, history_limit)
#
#     print(f"✅ ChatState ذخیره شد: {latest_path} و {history_path}")
#
#     return {"latest": latest_path, "history": history_path}

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



def load_latest_state(folder: str = "states"):
    """
    خواندن آخرین ChatState از latest.json
    """
    latest_path = os.path.join(folder, "latest.json")
    print(latest_path)
    if not os.path.exists(latest_path):
        print("⚠️ فایل latest.json پیدا نشد.")
        return None

    with open(latest_path, "r", encoding="utf-8") as f:
        state = json.load(f)

    print(f"📂 آخرین ChatState از {latest_path} خوانده شد.")
    return state