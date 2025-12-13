import requests
from RAG.tools import json_to_docs_internet,answer_with_ai, ask_faiss_question, set_faiss_db_from_json,ask_chroma_question
import json
import pyodbc
from typing import Any
async  def customer_search(info,
        # username: str | None = None,
        # mobile: str | None = None,
        # melicode: str | None = None,
        # lastname: str | None = None,
    timeout: float = 10.0
) -> dict:
    print(info)
    url = "https://lte.shabakieh.com/webservice/rest/customer_search"
    headers = {
        "accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    data = {
        "login_username": "aeye",
        "login_password": "Dehdar123!@#",
    }

    if info["username"]:
        data["username"] = info["username"]
    if info["mobile"]:
        data["mobile"] = info["mobile"]
    if info["melicode"]:
        data["melicode"] = info["melicode"]
    # if info["name"]:
    #     data["name"] =  info["name"]
    if info["lastname"]:
        data["lastname"] =  info["lastname"]

    try:
        resp = requests.post(url, data=data, headers=headers, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        return {"error": "request_failed", "detail": str(e)}
    except ValueError:
        return {"error": "invalid_json", "text": resp.text}


async def customer_info(
        username: str,
        mokhtasar: bool | str = True,
        online: bool | str = True,
        timeout: float = 10.0
) -> dict:
    url = "https://lte.shabakieh.com/webservice/rest/customer_info"
    headers = {
        "accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    data = {
        "username": username,
        "mokhtasar": "true" if mokhtasar in [True, "true", "True", 1] else "false",
        "online": "true" if online in [True, "true", "True", 1] else "false",
    }

    try:
        resp = requests.post(url, data=data, headers=headers, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        return {"error": "request_failed", "detail": str(e)}
    except ValueError:
        return {"error": "invalid_json", "text": resp.text}

#api for adsl support
def execute_stored_procedure_support(procedure_name, params=None):
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
            'DRIVER={ODBC Driver 18 for SQL Server};'
            f'SERVER={server};'
            f'DATABASE={database};'
            f'UID={username};'
            f'PWD={password};'
            'Encrypt=no;'

        )
        cursor = conn.cursor()
        print(cursor)
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

async def ask_rag( needs: list[str],k: int = 10, max_distance: float =0.34):
    query= ', '.join(needs)
    print('query>>>',query)
    # query از URL گرفته می‌شود
    chroma_results = ask_chroma_question(
        db_name="services",
        query=query,
        k=k,
        max_distance=max_distance
    )
    # answer = answer_with_ai(faiss_results, query)
    print("page_contents is>>", chroma_results)
    # page_contents =  [doc.page_content for doc in chroma_results]
    return chroma_results
