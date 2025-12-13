import asyncio
from fastapi import FastAPI, Request
import socketio
from agent.SHAgent import description_data
from pydantic import BaseModel
from general.tools import (extract_min_max, filter_by_date, clean_and_load_json, execute_stored_procedure,
                           create_message, load_latest_state)
from general.tools import (read_json_file, extract_min_max, filter_by_date, clean_and_load_json,
                           execute_stored_procedure,add_item_to_json,
                           create_message, load_latest_state)
from apis.apis import customer_search, customer_info, ask_rag,execute_stored_procedure_support
from graph.SHGraph import build_graph, handle_follow_up_buy, handle_service_suggestion_buy, handle_user_info_collector
from socket_instance import sio
from general.State import ChatState
from general.state_manager import save_state, load_latest_state
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import sys
import os
import json
from langchain_core.documents import Document
from RAG.tools import json_to_docs_internet, answer_with_ai, ask_faiss_question, set_faiss_db_from_json, \
    flatten_plans_dynamic, flatten_services_dynamic,set_chroma_db_from_json,json_to_docs_universal,ask_chroma_question
import uuid
import shutil
import requests
from dotenv import load_dotenv
from openai import OpenAI
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

app = FastAPI(title="پشتیبانی اتوماسیون شبکیه")
app.mount("/assets", StaticFiles(directory="assets"), name="assets")


class Message(BaseModel):
    content: str


views = Jinja2Templates(directory="views")
sio_app = socketio.ASGIApp(sio, other_asgi_app=app)

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)
@app.get("/", response_class=HTMLResponse)
def read_root():
    # تولید UUID و تبدیل به رشته
    user_uuid = str(uuid.uuid4())

    # مسیرهای پوشه و فایل‌ها
    base_dir = "data"
    sample_file = os.path.join(base_dir, "sample.json")
    user_dir = os.path.join(base_dir, "users")
    os.makedirs(user_dir, exist_ok=True)

    # مسیر فایل جدید
    new_file_path = os.path.join(user_dir, f"{user_uuid}.json")

    # اگر فایل نمونه وجود نداشت، خطای واضح بده
    if not os.path.exists(sample_file):
        raise FileNotFoundError(f"فایل نمونه در مسیر '{sample_file}' پیدا نشد.")

    # کپی فایل نمونه به فایل جدید
    shutil.copy(sample_file, new_file_path)

    # باز کردن و تغییر مقدار token
    with open(new_file_path, "r+", encoding="utf-8") as f:
        data = json.load(f)

        # اطمینان از اینکه ساختار JSON درست خوانده شده
        if not isinstance(data, dict):
            raise ValueError("محتوای sample.json باید یک شیء (object) JSON باشد.")

        # اضافه یا جایگزین کردن token
        data["token"] = user_uuid

        thread = client.beta.threads.create()

        data["thread_id"] = thread.id


        # بازنویسی فایل
        f.seek(0)
        json.dump(data, f, ensure_ascii=False, indent=4)
        f.truncate()

    # ریدایرکت به مسیر بعدی
    return RedirectResponse(url=f"/user/{user_uuid}")


@app.get("/user/{user_uuid}", response_class=HTMLResponse)
def user_page(request: Request, user_uuid: str):
    base_dir = "data/users"
    user_file = os.path.join(base_dir, f"{user_uuid}.json")

    # ✅ اگر فایل وجود نداشت → ریدایرکت به صفحه اصلی
    if not os.path.exists(user_file):
        return RedirectResponse(url="/")

    # ✅ باز کردن فایل و خواندن محتوا
    with open(user_file, "r", encoding="utf-8") as f:
        # content = (
        #     "<p>خوش آمدید! من اینجا هستم تا در زمینه خدمات شرکت شبکیه به شما کمک کنم. "
        #     "شبکیه یک شرکت معتبر در زمینه فناوری اطلاعات است که خدماتی مانند ارائه اینترنت، "
        #     "میزبانی وب، ثبت دامنه، طراحی وب‌سایت و پشتیبانی فنی ۲۴ ساعته را با تمرکز بر "
        #     "قابلیت اطمینان، سرعت و امنیت ارائه می‌دهد. اگر سوالی دارید یا به راهنمایی نیاز "
        #     "دارید، خوشحال می‌شوم که کمک کنم! 😊</p>"
        # )
#         content="""LTE شبکیه:
# این سرویس اینترنت پرسرعت FD-LTE بدون نیاز به خط تلفن است که با مودم جیبی یا رومیزی و سیم‌کارت ارائه می‌شود. سرعت آن تا ۴۰ مگابیت بر ثانیه است و پوشش کشوری دارد (مناطق دارای 4G، 5G و LTE). این سرویس برای کاربران خانگی و تجاری مناسب بوده و امکان استفاده از IP ثابت و انتخاب بسته‌های متنوع بر اساس نیاز مشتری فراهم است. لطفا ویژگی های مور نظر خود را بگویید تا سرویس اختصاصی شما معرفی شود."""
        content=description_data
        data = json.load(f)
        data["messages"].append({
            "role": "assistant",
            "content": content
        })

        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    # ✅ استخراج قسمت messages از داده‌ها
    messages = data.get("messages", [])

    # ✅ ارسال اطلاعات به قالب HTML
    return views.TemplateResponse(
        "index.html",
        {
            "request": request,
            "uuid": user_uuid,
            "messages": messages,  # 👈 ارسال لیست پیام‌ها
        },
    )


@app.get("/ask_rag")
async def api_ask_rag():
    # data = read_json_file(f"{token}.json")
    # state: ChatState = dict(data)
    # feature=state.get("user_feature",{})
    # query= ", ".join(f"{k}: {v}" for k, v in feature.items() if v not in (None, "", "-"))

    query=" قیمت زیر 890000"
    # query از URL گرفته می‌شود
    faiss_results = ask_chroma_question(
        db_name="services",
        query=query
    )
    return faiss_results
    # answer = answer_with_ai(faiss_results, query)
    # page_contents =  [doc.page_content for doc in faiss_results]
    # return page_contents

@app.get("/set_rag")
async def set_rag():
    with open("assets/json/main.json", "r", encoding="utf-8") as f:
        json_data = json.load(f)
    docs = json_to_docs_universal(json_data)
    # ساخت یا افزودن داده‌ها به chroma
    set_chroma_db_from_json(
        db_name="services",
        docs=docs,
        mode="overwrite"  # 'append' اگر بخواهی به دیتابیس موجود اضافه شود
    )
    return {"response": docs}


@app.get("/set_rag_plans")
async def set_rag():
    with open("assets/json/data.json", "r", encoding="utf-8") as f:
        json_data = json.load(f)
    docs = flatten_plans_dynamic(json_data)
    # ساخت یا افزودن داده‌ها به FAISS
    set_faiss_db_from_json(
        db_name="internet_plans",
        docs=docs,
        mode="overwrite"  # 'append' اگر بخواهی به دیتابیس موجود اضافه شود
    )
    return {"response": docs}


@app.get("/set_rag_services")
async def set_rag():
    with open("assets/json/data.json", "r", encoding="utf-8") as f:
        json_data = json.load(f)
    docs = flatten_services_dynamic(json_data)
    # ساخت یا افزودن داده‌ها به FAISS
    set_faiss_db_from_json(
        db_name="internet_services",
        docs=docs,
        mode="overwrite"  # 'append' اگر بخواهی به دیتابیس موجود اضافه شود
    )
    return {"response": docs}

@app.get("/supportadsl")
async def supportadsl():
    #3132685653
    result = execute_stored_procedure_support('Robo_User', '3135677735')

    return {"response": result}


@app.get("/pay", response_class=HTMLResponse)
async def pay():
    latest_state = load_latest_state()
    state: ChatState = dict(latest_state)
    user_info = state.setdefault('userInfo', {})
    orders = user_info.setdefault('orders', [])

    if not orders:
        # اگر orders خالی بود، یه سفارش جدید می‌سازیم
        orders.append({'status': 'پرداخت موفق'})
    else:
        first_order = orders[-1]

        if isinstance(first_order, dict):
            # اگر دیکشنری بود
            first_order['status'] = 'پرداخت موفق'
        elif isinstance(first_order, str):
            # اگر متن بود، تبدیلش کن به دیکشنری
            orders[-1] = {
                'description': first_order,
                'status': 'پرداخت موفق'
            }
        else:
            # اگر نوع ناشناخته بود، یه دیکشنری جدید بساز
            orders[-1] = {'status': 'پرداخت موفق'}
    # state['userInfo']['orders'][0]['status'] = 'پرداخت موفق'
    user_info['needs'] = {
        "type": [
        ],
        "details": [
        ]
    },
    state['next_node'] = ""
    save_state(state)

    await  handle_follow_up_buy(state)
    return """
        <html>
            <body>
                <h2>پرداخت موفق! سفارش با موفقیت ثبت شد.</h2>

            </body>
        </html>
    """


@app.get("/register_plan")
async def register_plan(need: str, token: str):
    print('register_plan>>', need, token)
    data = read_json_file(f"{token}.json")
    state: ChatState = dict(data)

    # message = create_message("user", need)
    # await sio.emit(f"room_{token}", message, room=token)
    # save_state(state)

    orders = await ask_rag([need], 1)

    if (len(orders) == 0):
        state['next_node'] = ""
        save_state(state)
        await handle_service_suggestion_buy(state)
    else:
        state.setdefault("userInfo", {}).setdefault("orders", []).extend(orders)
        print('orders is>>', state["userInfo"]['orders'])
        if (state["userInfo"]['info']['name'] != "" and state["userInfo"]['info']['phone'] != ""):
            orders = state.get("userInfo", {}).get("orders", [])
            info = state.get("userInfo", {}).get("info", {})

            item = {
                "token": state.get("token", ""),
                "info": info,
                "orders": orders,
                "user_message": state.get("input", "")
            }
            add_item_to_json('output/orders.json', item)
        print('orders len is>>', state['intents'])
        if len(state['intents']) != 0:
            state['intents'].pop()
        info = state['userInfo']['info']
        if (info['name'] == "" or info['phone'] == ""):
            state['next_node'] = ""
            save_state(state)
            await handle_user_info_collector(state)
            # state['next_node'] = "user_info_collector"
        else:
            state['next_node'] = ""
            save_state(state)
            await handle_follow_up_buy(state)
            # state['next_node'] = "follow_up_buy"

        state['next_node'] = ""
        save_state(state)
    return {"success": True}


@app.get("/getUser")
async def getUser():
    result = await  customer_info('989559001349')
    return result


# @app.get("/sendMessage")
# async def sendMessage(state: ChatState):
#     return  state

@ app.get("/showMessage")
async def showMessage(message: str):
    s={"message": message}
    with open("assets/json/messagetest.json", "w", encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False, indent=2)
    return {"message": message}

@ app.get("/showMessage")
async def showMessage(message: str):
    s={"message": message}
    with open("assets/json/messagetest.json", "w", encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False, indent=2)
    return {"message": message}


@app.get("/build")
async def build():
    # return 1
    graph = build_graph()
    result = await graph.get_graph().draw_png("graph.png")
    return result


@app.post("/langchain-sample4/")
async def process_message(request: Request, message: Message):
    print("coll sample4", message)


async def process_message(request: Request, message: Message):
    print("coll sample4", message)
    # print(pyodbc.drivers())
    # server = '185.237.85.3'
    # database = 'ICA_DatacenterNew'
    # username = 'sa'
    # password = 'data3755'

    # بدون پارامتر
    rows = execute_stored_procedure('B_SefareshList_Sel', [0, 0])
    rows = execute_stored_procedure('B_SefareshList_Sel', [0, 0])
    # json_result = execute_stored_procedure(server, database, username, password, 'Robo_User',[3132685653])

    # print(json_result)
    # cm = ChromaManager("user_messages3")
    #
    # print("create chroma")
    # # ثبت پیام‌ها
    # cm.add_message("سلام! می‌خوام یه سفر برنامه‌ریزی کنم.", metadata={"user_id": 1, "topic": "travel"})
    #
    # print("create message")
    # cm.add_message("بودجه حدود ۲۰ میلیون تومنه.", metadata={"user_id": 1, "topic": "budget"})
    #
    # print("create message")
    #
    # # واکشی پیام‌ها
    # results = cm.fetch_similar("بودجه")
    # print("پیام‌های واکشی شده:", results)
    # user_info = json.loads('{"name": "مهدی دهدار", "phone": "09134226929"} ')
    #
    # user = json.loads(user_info)
    # return {"response":user}
    # if os.path.exists(f"states/test.json"):
    #     with open(f"states/test.json", "r", encoding="utf-8") as f:
    #         state_data = json.load(f)
    # print("json:",state_data)
    # latest_state = load_latest_state()
    # graph=create_sh_graph()
    # graph_png = graph.get_graph().draw_mermaid_png()
    # with open("graph.png", "wb") as f:
    #     f.write(graph_png)
    # state: ChatState = dict(latest_state)
    # state = ChatState(
    #     input=message.content,
    #     messages=[],
    #     intent=""
    # )

    # state['input']=message.content
    # state["messages"].append({
    #     "id": str(uuid.uuid4()),
    #     "role": 'user',
    #     "content": message.content,
    #     "timestamp": datetime.now().isoformat()
    # })
    # sio = request.app.state.sio
    # await sio.emit("room_mehdi", {
    #     "id": str(uuid.uuid4()),
    #     "role": 'user',
    #     "content": message.content,
    #     "timestamp": datetime.now().isoformat()
    # }, room="mehdi")
    # print("state:",state)
    # result = graph.invoke(state)
    json_rows = clean_and_load_json(rows)
    filter_row_by_date = filter_by_date(json_rows)
    extract = extract_min_max(filter_row_by_date)
    print("row:", len(filter_row_by_date))
    print("row:", filter_row_by_date)
    print("row:", extract)
    return {"response": filter_row_by_date}
    json_rows = clean_and_load_json(rows)
    filter_row_by_date = filter_by_date(json_rows)
    extract = extract_min_max(filter_row_by_date)
    print("row:", len(filter_row_by_date))
    print("row:", filter_row_by_date)
    print("row:", extract)
    return {"response": filter_row_by_date}


# اتصال کاربران
@sio.event
async def connect(sid, environ):
    print(f"🔌 Client connected: {sid}")


@sio.event
async def disconnect(sid):
    print(f"❌ Client disconnected: {sid}")


# جوین شدن به Room
@sio.event
async def join(sid, data):
    print("join", data)
    print("join", data)
    room = data["room"]
    await sio.enter_room(sid, room)
    await sio.emit("message", f"🔔 A new user joined {room}", room=room)


# دریافت پیام
# @sio.event
# async def message(sid, data):
#     print("message",data)
#     room = data["room"]
#     msg = data["msg"]
#     message=make_message('user',msg)
#     await sio.emit("room_mehdi", message, room="mehdi")
#     latest_state = load_latest_state()
#     graph=create_sh_graph()
#     state: ChatState = dict(latest_state)
#     state['input']=msg
#     state["messages"].append(message)
#     print("state:",state)
#     result = await graph.ainvoke(state)
#     print("print",result)
N8N_WEBHOOK_URL = "https://n8n.shabakieh.com/webhook-test/receiveMessage"

@sio.event
async def message(sid, data):
    print("message issssssss>>", data)
    room = data["room"]
    msg = data["msg"]
    data = read_json_file(f"{room}.json")
    state: ChatState = dict(data)
    # message=create_message("user",msg)
    message = create_message("user", msg)
    await sio.emit(f"room_{room}", message, room=room)

    # sendMessage(state)

    state["messages"].append(message)
    state['input'] = msg
    state['input'] = msg
    save_state(state)
    # 2. ارسال پیام به n8n



    graph = build_graph()
    result = await graph.ainvoke(state)
    # response = requests.post(N8N_WEBHOOK_URL, json={"message": state})
    # response.raise_for_status()
    # print('webhook is:', response)


