from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from general.constants import products,split_query_by_required
from task.SHTask import get_assistant_suggest, register_order_json_task, get_assistant_express_need_buy, \
    get_assistant_user_info_collector, get_assistant_register_order, get_assistant_answer, \
    user_info_json_task, get_assistant_unknown, create_json_need_buy_response_task, \
    payment_task, get_assistant_intent, get_assistant_greeting, get_assistant_help,get_assistant_user_info, call_model, \
    get_assistant_question_service_support, get_assistant_set_service_support,get_assistant_question_answer
from LTE.graph.LTEGraph import handle_problem_list, handle_get_account_user, handle_json_account, \
    handle_ask_witch_account, handle_extract_select_account, handle_ask_problem, handle_LTE_detect, \
    handle_update_json_support_task

from general.state_manager import save_state, load_latest_state
from general.State import ChatState, ChatStateManager
from general.tools import emit_message, run_task_as_crew, create_message, parse_json5, missing_fields, \
    extract_unique_values, get_last_intent, add_item_to_json
from apis.apis import ask_rag
import asyncio
from socket_instance import sio
import re
import random
from RAG.tools import ask_chroma_question
import json
import time

typeService = extract_unique_values("assets/json/data.json", "category")
INTENTS = [
    "greeting",
    "express_need_buy",
    "extract_json_buy",
    "service_suggestion_buy",
    "answer_question_service_suggestion",
    "register_order",
    "extract_user_info_json",
    "payment",
    "follow_up_buy",
    "support",
    "question_service_support",
    "set_service_support",
    "ask_problem",
    "set_problem",
    "get_info_account",
    "extract_json_account",
    "ask_witch_account",
    "extract_select_account",
    "LTE_detect",
    "unknown"
]

# ============================================= start new method =========================================
def clean_features(features: dict) -> dict:
    return {k: v for k, v in features.items() if v not in (None, "-", "")}

def get_chroma_results(state):
    check_interval = 0.5
    # search_history = state.get("search_history", [])
    # if search_history:
    #     return {"result": search_history, "status": "main"}
    status_search = state.get("status_search", 1)
    print("status_search>>>",status_search)
    if status_search == 0:
        max_attempts = 50  # تعداد حداکثر تلاش
        attempts = 0
        while attempts < max_attempts:
            search_history = state.get("search_history", [])
            if search_history:
                return {"result": search_history, "status": "main"}
            time.sleep(check_interval)
            attempts += 1
        return {"result": [], "status": "timeout"}
    else:
        query,orQuery = split_query_by_required(clean_features(state.get("user_feature", {})))
        print('query items is>>>>',query)
        print('orQuery items is>>>>',orQuery)
        result = ask_chroma_question(
                db_name="services",
                query=query,
                orQuery=orQuery,
                state=state
            )
        state["search_history"] = result["result"]
        return result

async def handle_help(state: ChatState):
    print("handle help")
    print('changed_part is>>', state["changed_part"])
    user_input = state.get("input")

    if 'درخواست جست و جو' in user_input:
        state['status_order'] = 'pending'
        save_state(state)
        chroma_results = get_chroma_results(state)
        plans = chroma_results.get("result")
        print(chroma_results.get("result"))
        if plans:
            if chroma_results.get("status") == "main":
                text = "تمامی محصولات مشابه درخواست شما یافت شد که عبارتند از:"
            else:
                text = (
                    "متأسفانه در حال حاضر محصولی دقیقاً مطابق با نیاز شما موجود نیست.\n"
                    "با این حال، چند گزینه‌ی جایگزین برای شما در نظر گرفته‌ایم:"
                )
        else:
            plans = None
            text = (
                "متأسفانه هیچ محصولی مطابق با جستجوی شما پیدا نشد 😔\n"
                "می‌خواید ویژگی‌های جدیدی اضافه کنید تا دوباره جستجو کنیم؟"
            )

        emit_message(state,1, text, plans=plans)


    elif 'شروع پرسش' in user_input:
        state['status_order'] = ''
        save_state(state)
        response = await get_assistant_help(state)
        response = re.sub(r"^```html\s*|\s*```$", "", response).strip()
        state["messages"].append(create_message("assistant", response))
        save_state(state)


    elif 'نمایش همه محصولات' in user_input:

        emit_message(
            state,1,
            "«لیست تمامی محصولات: »",
            plans=products
        )


    elif 'مرحله بعد' in user_input:
        user_info=state["user_info"]
        state['status_order'] = 'confirmed'
        save_state(state)
        all_not_null = all(value is not None and value != "" for value in user_info.values())
        if all_not_null :
            text = (
                "سبد خرید شما با موفقیت تکمیل و ذخیره شد 🎉\n"
                "از انتخاب و اعتماد شما سپاسگزاریم 💙\n"
                " اگر ویژگی جدیدی مدنظر دارید بفرمایید."

            )

            emit_message(
                state, 1,
                text,
               )
        else:
            state['status_order'] = 'pending'
            response = await get_assistant_user_info(state)
            response = re.sub(r"^```html\s*|\s*```$", "", response).strip()
            state["messages"].append(create_message("assistant", response))
            save_state(state)


    else:

        features = call_model(state)
        state["user_feature"] = features['user_feature']
        state["user_info"] = features['user_info']
        state["question"] = features['question']
        state["changed_part"] = features['changed_part']
        state['status_order'] = 'pending'
        save_state(state)

        miss_fields = missing_fields(features['user_feature'])

        if not miss_fields and state["changed_part"] in ("user_feature", "none"):

            values = [str(v) for v in features['user_feature'].values() if v]
            text = (
                "عالی! درخواست های شما دریافت شد، "
                # + "، ".join(values)
                + ".\n"
                ". اگه دوست دارید نتایج رو ببینید، روی دکمه «درخواست جست‌وجو» بزنید یا اگر مورد دیگه‌ای مدنظر دارید، بهم بگید."
            )
            btn = ["درخواست جست و جو"] if state["changed_part"] in ("user_feature", "none") else None
            emit_message(
                state,1,
                text,
                buttons=btn
            )
        elif  all(value is not None and value != "" for value in state["user_info"].values()) and state["changed_part"]=='user_info':
            state["status_order"] = "confirmed"
            save_state(state)
            text = (
                "سبد خرید شما با موفقیت تکمیل و ذخیره شد 🎉\n"
                 "از انتخاب و اعتماد شما سپاسگزاریم 💙\n"
                 "برای نهایی کردن خرید لطفا روی دکمه پرداخت کلیک کنید \n"
                " ویا اگر ویژگی جدیدی مدنظر دارید بفرمایید."
            )


            emit_message(
                state,
                1,
                text,

            )
        elif  state["changed_part"]=='question':
                chroma_results = ask_chroma_question(db_name="question_answer", query={}, orQuery=state.get("question",''), state=state,k=1)
                response = await get_assistant_question_answer(state, chroma_results['result'][0])
                response = re.sub(r"^```html\s*|\s*```$", "", response).strip()
                state["messages"].append(create_message("assistant", response))
                state['status_order'] = 'pending'
                save_state(state)
        else:
            response = await get_assistant_help(state)
            response = re.sub(r"^```html\s*|\s*```$", "", response).strip()
            state["messages"].append(create_message("assistant", response))
            state["search_history"]=[]
            state['status_order'] = 'pending'
            save_state(state)
            print("clean_features>>>",clean_features(features['user_feature']))
            if any(v not in (None, "-") for v in features['user_feature'].values()):
                query, orQuery = split_query_by_required(clean_features(state.get("user_feature", {})))
                print('query items is>>>>', query)
                print('orQuery items is>>>>', orQuery)
                chroma_results = ask_chroma_question(db_name="services",query=query, orQuery=orQuery,state=state,k=7)
                state["search_history"] = chroma_results["result"]

    if state.get("intents"):
        state["intents"].pop()

    state["next_node"] = ""
    save_state(state)
    return state

# ============================================= end new method =========================================

async def analyze_message(state: ChatState) -> ChatState:
    # user_input = state["input"]
    # last_ai_message = None
    # for msg in reversed(state.get("messages", [])):
    #     if msg.get("role") == "assistant":
    #         last_ai_message = msg.get("content")
    #         break
    #
    # task = context_switch_task(user_input, state, last_ai_message)
    # result = run_task_as_crew(task)

    response = await get_assistant_intent(state)
    print("response type:>>>", type(response))
    # response=json.loads(response)
    if isinstance(response, str):
        response = json.loads(response)
    print("response intent is", get_last_intent(state))
    state["intents"].extend(response)
    state["next_node"] = get_last_intent(state)
    save_state(state)
    return state


def detect_intent(state: ChatState):
    # print("detect_intent")
    # # intent = get_last_intent(state)
    # # if intent=="extract_json_buy":
    # #     if user_need['type']==[] :
    # #         state['next_node'] = "express_need_buy"
    # # if intent == "unknown":
    # #     state['next_node'] = "unknown"
    # # elif intent == "register_order":
    # #     state['next_node'] = ""
    # # elif intent == "service_suggestion_buy":
    # #     state['next_node'] = "service_suggestion_buy"
    # 
    # # save_state(state)
    return state


async def unknown(state: ChatState) -> ChatState:
    print("handle unknown")
    user_input = state["input"]
    response = get_assistant_unknown(state)
    response = re.sub(r"^```html\s*|\s*```$", "", response).strip()
    message = create_message('assistant', response)
    state["messages"].append(message)
    if (state['intents'] != []):
        state['intents'].pop()

    state['next_node'] = get_last_intent(state)
    save_state(state)
    return state


async def handle_greeting(state: ChatState):
    print("handle greeting")
    response = await get_assistant_greeting(state)
    response = re.sub(r"^```html\s*|\s*```$", "", response).strip()
    message = create_message('assistant', response)
    state["messages"].append(message)

    if (len(state['intents']) > 0):
        state['intents'].pop()

    state['next_node'] = get_last_intent(state)
    save_state(state)
    return state


async def handle_express_need_buy(state: ChatState):
    print("handle express need buy")
    response = get_assistant_express_need_buy(state)
    response = re.sub(r"^```html\s*|\s*```$", "", response).strip()
    message = create_message('assistant', response, typeService)
    state["messages"].append(message)
    # room = state["token"]
    # asyncio.create_task(sio.emit(f"room_{room}", message, room=room))

    if (len(state['intents']) > 0):
        state['intents'].pop()

    state['next_node'] = get_last_intent(state)
    save_state(state)
    return state


async def handle_extract_json_buy(state: ChatState):
    response = create_json_need_buy_response_task(state)
    # response = re.sub(r"^```html\s*|\s*```$", "", response).strip()
    needs = parse_json5(response)
    state["userInfo"]['needs'] = needs
    if (len(state['intents']) > 0):
        state['intents'].pop()

    if len(needs['type']) == 0:
        state['next_node'] = "express_need_buy"
    elif len(needs['type']) != 0:
        state['next_node'] = "service_suggestion_buy"
    save_state(state)
    return state


async def handle_service_suggestion_buy(state: ChatState):
    print("handle service suggestion buy")
    user_info = state["userInfo"]
    needs = user_info['needs']['type'] + user_info['needs']['details'][::-1]
    searchList = await ask_rag(needs)
    sList = searchList[:3]
    index = len(state["history_suggestion"])
    state["history_suggestion"].append({index: sList})
    response = get_assistant_suggest(state, sList, searchList)
    response = re.sub(r"^```html\s*|\s*```$", "", response).strip()
    message = create_message('assistant', response, None, searchList)
    state["messages"].append(message)
    if len(state['intents']) != 0:
        state['intents'].pop()
    state['next_node'] = get_last_intent(state)
    save_state(state)
    return state


async def handle_create_answer_service_suggestion(state: ChatState):
    print("handle answer service suggestion")

    response = get_assistant_answer(state)
    response = re.sub(r"^```html\s*|\s*```$", "", response).strip()
    message = create_message('assistant', response)
    state["messages"].append(message)
    if len(state['intents']) != 0:
        state['intents'].pop()
    state['next_node'] = get_last_intent(state)
    save_state(state)
    return state


async def handle_register_order_json_buy(state: ChatState):
    print("handle register_order json_buy")
    if (len(state["history_suggestion"]) < 1):
        state['next_node'] = "extract_json_buy"
        save_state(state)
    else:
        task = register_order_json_task(state)
        result = run_task_as_crew(task)
        response = result.raw.strip()
        response = re.sub(r"^```html\s*|\s*```$", "", response).strip()
        orders = parse_json5(response)
        print('orders json is>>', orders)
        if (len(orders) == 0):
            state['next_node'] = "service_suggestion_buy"
            save_state(state)
        else:
            state["userInfo"]['orders'].extend(orders)
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
                state['next_node'] = "user_info_collector"
            else:
                state['next_node'] = "follow_up_buy"
                # state['next_node'] = "payment"

        save_state(state)
    return state


async def handle_user_info_collector(state: ChatState):
    print("handle user info collector")

    response = get_assistant_user_info_collector(state)
    response = re.sub(r"^```html\s*|\s*```$", "", response).strip()
    message = create_message('assistant', response)
    state["messages"].append(message)
    # room = state["token"]
    # asyncio.create_task(sio.emit(f"room_{room}", message, room=room))
    if (state['intents'] != []):
        state['intents'].pop()
    state['next_node'] = get_last_intent(state)
    save_state(state)
    return state


async def handle_user_info_json(state: ChatState):
    print("handle user info json")
    user_input = state["input"]
    task = user_info_json_task(state)
    result = run_task_as_crew(task)
    response = result.raw.strip()
    response = re.sub(r"^```html\s*|\s*```$", "", response).strip()
    message = create_message('assistant', response)
    # state["messages"].append(message)
    info = parse_json5(response)
    state["userInfo"]['info'] = info

    print("user info json is>>", state["userInfo"]['info'])
    # asyncio.create_task(sio.emit("room_mehdi", message, room="mehdi"))
    if (state['intents'] != []):
        state['intents'].pop()

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

        state['next_node'] = "follow_up_buy"
        # state['next_node'] = "payment"
    else:
        state['next_node'] = "user_info_collector"
    save_state(state)
    return state


async def handle_question_service_support(state: ChatState):
    print("handle question service support")

    response = get_assistant_question_service_support(state)
    response = re.sub(r"^```html\s*|\s*```$", "", response).strip()
    buttons = ['به پشتیبانی ADSL نیاز دارم', 'به پشتیبانی LTE نیاز دارم']
    message = create_message('assistant', response, buttons)
    state["messages"].append(message)
    if (state['intents'] != []):
        state['intents'].pop()
    state['next_node'] = get_last_intent(state)
    save_state(state)
    return state


async def handle_set_service_support(state: ChatState):
    print("handle set_service support")
    response = get_assistant_set_service_support(state)
    # message = create_message('assistant', response)
    # # state["messages"].append(message)
    # info = parse_json5(response)
    response = re.sub(r"^```html\s*|\s*```$", "", response).strip()

    state["userInfo"]['service_support'] = response
    state["userInfo"]['selectAccount'] = []
    state["userInfo"]['accountInfo'] = {}

    print("service_support is>>", state["userInfo"]['service_support'])
    # asyncio.create_task(sio.emit("room_mehdi", message, room="mehdi"))
    if (state['intents'] != []):
        state['intents'].pop()
    state['next_node'] = "get_info_account"
    save_state(state)
    return state


async def handle_payment(state: ChatState):
    user_input = state["input"]
    print("handle payment")
    task = payment_task(state)
    result = run_task_as_crew(task)
    response = result.raw.strip()
    response = re.sub(r"^```html\s*|\s*```$", "", response).strip()
    message = create_message('assistant', response)
    state["messages"].append(message)
    room = state["token"]
    asyncio.create_task(sio.emit(f"room_{room}", message, room=room))
    asyncio.create_task(sio.emit("room_e3740a54-9912-4e70-8b73-8cb23fc3c6e4", message, room=room))

    if len(state['intents']) != 0:
        state['intents'].pop()

    state['next_node'] = get_last_intent(state)
    save_state(state)
    return state


async def handle_follow_up_buy(state: ChatState):
    print("handle follow up buy")
    user_input = state["input"]
    response = await get_assistant_register_order(state)
    response = re.sub(r"^```html\s*|\s*```$", "", response).strip()
    message = create_message('assistant', response)
    state["messages"].append(message)
    room = state["token"]
    asyncio.create_task(sio.emit(f"room_{room}", message, room=room))
    if (state['intents'] != []):
        state['intents'].pop()
    state['next_node'] = get_last_intent(state)
    save_state(state)
    return state




async def handle_support(state: ChatState):
    print("handle support")
    if (state['intents'] != []):
        state['intents'].pop()
    lastIntent = get_last_intent(state)
    if (lastIntent == ""):
        userInfo = state["userInfo"]
        if (userInfo["service_support"] == ""):
            state['next_node'] = "question_service_support"
        else:
            if (userInfo['accounts'] == []):
                state['next_node'] = "get_info_account"
            elif (userInfo['selectAccount'] == []):
                state['next_node'] = "ask_witch_account"
            elif (userInfo['problems'] == []):
                state['next_node'] = "ask_problem"
            else:
                state['next_node'] = "update_json_support"
    else:
        state['next_node'] = get_last_intent(state)

    save_state(state)
    return state


# 🔹 ساخت گراف
def build_graph():
    builder = StateGraph(ChatState)
    # نود تحلیل پیام
    builder.add_node("analyze_message", analyze_message)
    builder.add_node("detect_intent", detect_intent)
    builder.add_node("greeting", handle_greeting)
    builder.add_node("express_need_buy", handle_express_need_buy)
    builder.add_node("extract_json_buy", handle_extract_json_buy)
    builder.add_node("service_suggestion_buy", handle_service_suggestion_buy)
    builder.add_node("answer_question_service_suggestion", handle_create_answer_service_suggestion)
    builder.add_node("register_order", handle_register_order_json_buy)
    builder.add_node("user_info_collector", handle_user_info_collector)
    builder.add_node("extract_user_info_json", handle_user_info_json)
    builder.add_node("follow_up_buy", handle_follow_up_buy)
    builder.add_node("unknown", unknown)
    builder.add_node("payment", handle_payment)
    builder.add_node("help", handle_help)

    # support node
    builder.add_node("support", handle_support)
    builder.add_node("set_problem", handle_problem_list)
    builder.add_node("LTE_detect", handle_LTE_detect)
    builder.add_node("ask_problem", handle_ask_problem)
    builder.add_node("get_info_account", handle_get_account_user)
    builder.add_node("extract_json_account", handle_json_account)
    builder.add_node("ask_witch_account", handle_ask_witch_account)
    builder.add_node("extract_select_account", handle_extract_select_account)
    builder.add_node("update_json_support", handle_update_json_support_task)
    builder.add_node("question_service_support", handle_question_service_support)
    builder.add_node("set_service_support", handle_set_service_support)
    builder.add_edge("extract_json_account", "ask_witch_account")
    builder.add_edge("set_service_support", "get_info_account")
    # builder.add_edge("update_json_support", "LTE_detect")

    builder.add_conditional_edges("extract_select_account", lambda state: state["next_node"], {
        "ask_problem": "ask_problem",
        "ask_witch_account": "ask_witch_account",
        "update_json_support": "update_json_support",
        "unknown": "unknown"
    }),
    builder.add_conditional_edges("support", lambda state: state["next_node"], {
        "ask_problem": "ask_problem",
        "set_problem": "set_problem",
        "question_service_support": "question_service_support",
        "get_info_account": "get_info_account",
        "extract_json_account": "extract_json_account",
        "ask_witch_account": "ask_witch_account",
        "extract_select_account": "extract_select_account",
        "update_json_support": "update_json_support",
        "unknown": "unknown"
    }),
    builder.add_conditional_edges("set_problem", lambda state: state["next_node"], {
        "ask_problem": "ask_problem",
        "support": "support",
        "question_service_support": "question_service_support",
        "set_service_support": "set_service_support",
        "set_problem": "set_problem",
        "ask_witch_account": "ask_witch_account",
        "get_info_account": "get_info_account",
        "update_json_support": "update_json_support",
        "unknown": "unknown"
    }),

    builder.set_entry_point("help")

    # builder.add_edge("analyze_message", "detect_intent")
    builder.add_edge("extract_json_buy", "service_suggestion_buy")
    builder.add_conditional_edges("extract_user_info_json", lambda state: state["next_node"], {
        "user_info_collector": "user_info_collector",
        # "payment": "payment",
        "follow_up_buy": "follow_up_buy",
        "unknown": "unknown"
    }),
    builder.add_conditional_edges("update_json_support", lambda state: state["next_node"], {
        "LTE_detect": "LTE_detect",
        "get_info_account": "get_info_account",
        "ask_witch_account": "ask_witch_account",
        "unknown": "unknown"
    }),

    builder.add_conditional_edges("register_order", lambda state: state["next_node"], {
        "extract_json_buy": "extract_json_buy",
        "service_suggestion_buy": "service_suggestion_buy",
        "user_info_collector": "user_info_collector",
        # "payment": "payment",
        "follow_up_buy": "follow_up_buy",
        "unknown": "unknown"
    }),
    builder.add_conditional_edges("analyze_message", lambda state: state["next_node"], {
        "greeting": "greeting",
        "express_need_buy": "express_need_buy",
        "extract_json_buy": "extract_json_buy",
        "answer_question_service_suggestion": "answer_question_service_suggestion",
        "register_order": "register_order",
        # "payment": "payment",
        "user_info_collector": "user_info_collector",
        "extract_user_info_json": "extract_user_info_json",
        "follow_up_buy": "follow_up_buy",
        "support": "support",
        "set_problem": "set_problem",
        "set_service_support": "set_service_support",
        "extract_json_account": "extract_json_account",
        "extract_select_account": "extract_select_account",
        "update_json_support": "update_json_support",
        "get_info_account": "get_info_account",
        "ask_witch_account": "ask_witch_account",
        "LTE_detect": "LTE_detect",
        "unknown": "unknown"
    })

    builder.add_edge("service_suggestion_buy", END),
    builder.add_edge("unknown", END),
    builder.add_edge("greeting", END),
    builder.add_edge("user_info_collector", END),
    builder.add_edge("follow_up_buy", END),
    builder.add_edge("express_need_buy", END),
    builder.add_edge("LTE_detect", END),
    builder.add_edge("ask_problem", END),

    return builder.compile()
