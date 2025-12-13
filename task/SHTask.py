from crewai import Task
import json
from agent.SHAgent import payment_assistant, user_info_json_assistant, register_order_json_assistant, \
    create_json_need_buy_assistant, set_service_support_assistant, question_service_support_assistant, help, \
    unknown_assistant, user_info_collector_assistant, register_order_assistant, answer_assistant, suggest_assistant, \
    express_need_buy_assistant, greeting_assistant, conversation_assistant, FIELDS, askable, prompt_functionTools
from general.tools import extract_unique_values, chat_create, chat_stream, client

with open("assets/json/data.json", "r", encoding="utf-8") as f:
    data = json.load(f)
with open("assets/json/details_plan.json", "r", encoding="utf-8") as f:
    details_plan = json.load(f)
keys_list = [list(item["plans"][0].keys()) for item in data if item.get("plans")]
details_data = sorted(set().union(*keys_list))
typeService = extract_unique_values("assets/json/data.json", "category")

category_description = [f"{item['category']}: {item['general_description']}" for item in data]

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

async def get_assistant_help(state: dict) -> str:
    user_message = state["input"]
    user_feature = state.get("user_feature", {})
    last_ai_message = None
    for msg in reversed(state.get("messages", [])):
        if msg.get("role") == "assistant":
            last_ai_message = msg.get("content")
            break
    fields = [key for key in FIELDS if user_feature.get(key) in (None, "-", "")]
    print("askable", fields)

    context_message = (
        f"User message: {user_message}\n"
        f"user_feature: {user_feature}\n"
        f"last_ai_message: {last_ai_message}\n"
        f"FIELDS is: {', '.join(str(x) for x in fields)}"
    )
    messages = [
        {
            "role": "system",
            "content": f"""
    ### CONTEXT INFORMATION
    {context_message}

   ### ASSISTANT INSTRUCTIONS
    {help}

(Use all the data above for a better answer.)
"""
        },
        {
            "role": "user",
            "content": user_message
        }
    ]
    search = []
    if user_feature and any(value is not None for value in user_feature.values()):
        search = ["درخواست جست و جو"]
    final_text = await chat_stream(messages, state, search)
    return final_text


def call_model(state=None):
    current_json = state.get("user_feature", {})
    user_message = state.get("input", "")
    last_ai_message = None
    for msg in reversed(state.get("messages", [])):
        if msg.get("role") == "assistant":
            last_ai_message = msg.get("content")
            break
    messages = [
        {"role": "system", "content": (
            " ### CONTEXT INFORMATION (JSON):\n"
            f"current JSON = {current_json}\n"
            f"FIELDS =  {', '.join(FIELDS)}\n"
            "### MAIN ASSISTANT INSTRUCTIONS:"

            f"{prompt_functionTools}"
        )}
    ]
    messages.append({"role": "user", "content": f"user message :{user_message}"})
    # messages.append({"role": "system", "content": f"extra_feature :{user_message}"})
    messages.append({
        "role": "system",
        "content": f"last_ai_message : {last_ai_message}"
    })
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "extract_plan",
                    "description": "Information Extraction",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            field: {"type": ["string", "number", "null"]} for field in FIELDS
                        },
                        "extra_feature": {
                            "type": ["string", "null"],
                            "description": "Other product constraints not covered by predefined 'FIELDS'"
                        },
                        "required": FIELDS
                    }
                }
            }
        ],
        tool_choice="auto"
    )
    msg = response.choices[0].message

    # ---------------------- TOOL CALL ----------------------
    if msg.tool_calls:
        args = json.loads(msg.tool_calls[0].function.arguments)

        result = {}
        for field in FIELDS:
            value = args.get(field)
            if value is None:
                if field in current_json:
                    value = current_json[field]
                else:
                    value = None

            result[field] = value
        # extra_feature: model is source of truth
        result["extra_feature"] = args.get("extra_feature")
        print("feat>>>", result)
        return result

    return current_json


# ============================================= end new method =========================================


async def get_assistant_intent(state: dict):
    threadId = state.get("thread_id")
    user_message = state["input"]
    last_ai_message = None
    print("msg reversed", state.get("messages", []))
    for msg in reversed(state.get("messages", [])):
        print("role assistant>>", msg.get("role"))
        if msg.get("role") == "assistant":
            print("last_ai_message iss>>>", msg.get("content"))
            last_ai_message = msg.get("content")
            break

    # بخش 3: history_suggestion
    history_suggestion = state.get("history_suggestion")
    history_suggestion = history_suggestion[-1] if history_suggestion and len(history_suggestion) > 0 else None

    previous_intents = state.get('intents', [])
    next_node = state.get('next_node', 'none')
    info = state.get('userInfo', {}).get('info')
    accountInfo = state.get('userInfo', {}).get('accountInfo')
    acc = state.get('userInfo', {}).get('accounts', [])
    fields = ["pppoe_username", "name", "lastname", "Traffic", "service_title",
              "date_service_start_fa", "date_service_expire_fa"]
    print("intents list state>>", state.get("intents"))

    accounts = []
    for account_list in acc:
        for a in account_list:
            filtered = {key: a[key] for key in fields if key in a}
            accounts.append(filtered)

    # بخش 6: آماده‌سازی پیام

    context_message = json.dumps({

        "UserMessage": user_message,
        "intents": INTENTS,
        "previousIntents": previous_intents,
        "nextNode": next_node,
        "userInfo": info,
        "accountInfo": accountInfo,
        "lastAIMessage": last_ai_message or "none",
        "suggestedServices": history_suggestion,
        "UserRequiredValues": state.get("userInfo", {}).get("needs", {}),
        "UserAccounts": accounts,
    })
    print(f"last ai is >>{last_ai_message}")

    messages = [
        {
            "role": "system",
            "content": f"""
    ### CONTEXT INFORMATION (JSON):
    {context_message}
    ### MAIN ASSISTANT INSTRUCTIONS:
    {conversation_assistant}



(The model should use the information above. The answer should only be generated based on the assistant's rules.)
"""
        },
        {
            "role": "user",
            "content": user_message
        }
    ]

    response = chat_create(messages, )

    return response


async def get_assistant_greeting(state: dict) -> str:
    # audio_buffer = []
    # user_message = state["input"]
    # url = "wss://api.openai.com/v1/realtime?model=gpt-4o-mini-realtime-preview"
    #
    # async with websockets.connect(
    #         url,
    #         extra_headers=[
    #             ("Authorization", f"Bearer {api_key}"),
    #             ("OpenAI-Beta", "realtime=v1")
    #         ]
    # ) as ws:
    #
    #     print("Connected!")
    #
    #     # ---- 1) تنظیم Agent (دستورالعمل‌ها) ----
    #     await ws.send(json.dumps({
    #         "type": "session.update",
    #         "session": {
    #             "instructions": (
    #                 "Generate warm, friendly,human and context-aware welcome responses in Persian."
    #                 "Avoid repeating past AI messages and maintain a natural flow of conversation."
    #                 "Introduce the “شبکیه” brand and give the user a sense of trust."
    #                 "You are the Customer Greeting & Brand Introduction Assistant.\n"
    #                 "Your role is to generate warm, friendly, natural, and context-aware greeting responses in Persian (Farsi).\n"
    #                 "You maintain a semi-formal, respectful, and trustworthy tone, using limited professional emojis when appropriate.\n"
    #                 # "You are a helpful AI assistant and must clearly communicate that you are an AI.\n"
    #                 "You help build trust and guide the user smoothly through the early stages of interaction.\n"
    #                 "You introduce the brand 'شبکیه' .\n"
    #                 "\n. شبکیه is an IT company providing internet services, web hosting, domain registration, website design, and 24/7 technical support, with a strong focus on reliability, speed, security, and customer satisfaction."
    #                 "You can only talk about the services of the 'شبکیه' company."
    #                 "1. All responses must be written only in Persian (Farsi).\n"
    #                 "2. Maintain a natural, warm, and semi-formal tone without sounding robotic.\n"
    #                 "3. Avoid any repetition of previous AI messages, including greetings or brand introductions.\n"
    #                 "5. If the user's name is available, use it naturally for personalization.\n"
    #                 "6. Do not repeat greetings such as 'سلام'  if already used earlier; respond based on context.\n"
    #                 "7. Keep the conversation flowing naturally and engagingly.\n"
    #                 "8. Use professional emojis sparingly and appropriately.\n"
    #                 "9.End every message by expressing readiness to assist the user.\n"
    #                 "10. Avoid mechanical, repetitive, or template-like phrasing.\n"
    #                 "11.If someone asks whether you are truly an AI, respond affirmatively. Say that you are an AI trained in the field of retina-related studies and that you are currently continuing your education and learning in this area."
    #
    #             ),
    #             "temperature": 0.7,
    #             "voice": 'alloy',
    #             "output_audio_format": "pcm16"
    #         }
    #     }))
    #
    #     # ---- 2) قرار دادن پیام کاربر در گفتگو ----
    #     await ws.send(json.dumps({
    #         "type": "conversation.item.create",
    #         "item": {
    #             "type": "message",
    #             "role": "user",
    #             "content": [
    #                 {"type": "input_text", "text": user_message}
    #             ]
    #         }
    #     }))
    #
    #     # ---- 3) دستور تولید پاسخ (gent) ----
    #     await ws.send(json.dumps({"type": "response.create"}))
    #
    #     # ---- 4) دریافت پاسخ مدل به صورت قطعه‌قطعه ----
    #     async for raw in ws:
    #         data = json.loads(raw)
    #         print("ws is>>>",data)
    #         if data.get("type") == "response.audio_transcript.delta":
    #             print(data['delta'])
    #         if data.get("type") == "response.audio.delta":
    #             pcm_bytes = base64.b64decode(data["delta"])
    #             audio_array = np.frombuffer(pcm_bytes, dtype=np.int16)
    #             audio_buffer.append(audio_array)
    #
    #
    #         if data.get("type") == "response.content_part.done":
    #             print("\n--- DONE ---")
    #             break
    #     # ذخیره تمام صوت‌ها در یک فایل WAV
    #     if audio_buffer:
    #         all_audio = np.concatenate(audio_buffer)
    #         write("output2.mp3", 24000, all_audio)  # نرخ نمونه‌برداری 24kHz
    #         print(f"Audio saved to output.wav")
    # url = "wss://api.openai.com/v1/realtime?model=gpt-4o-mini-realtime-preview"
    #
    # async with websockets.connect(
    #     url,
    #     extra_headers=[
    #         ("Authorization", f"Bearer {api_key}"),
    #         ("OpenAI-Beta", "realtime=v1")
    #     ]
    # ) as ws:
    #
    #     print("Connected to OpenAI Realtime API!")
    #
    #     # ---- 1) ارسال پیام ورودی ----
    #     await ws.send(json.dumps({
    #         "type": "conversation.item.create",
    #         "item": {
    #             "type": "message",
    #             "role": "user",
    #             "content": [
    #                 { "type": "input_text", "text": user_message }
    #             ]
    #         }
    #     }))
    #
    #     # ---- 2) درخواست پاسخ ----
    #     await ws.send(json.dumps({
    #         "type": "response.create"
    #     }))
    #
    #     # ---- 3) دریافت استریمی پاسخ ----
    #     async for raw in ws:
    #         data = json.loads(raw)
    #
    #         if data.get("type") == "response.text.delta":
    #             print(data["text"], end="", flush=True)
    #
    #         if data.get("type") == "response.completed":
    #             print("\n\n--- Response Completed ---")
    #             break

    threadId = state.get("thread_id")
    user_message = state["input"]
    last_ai_message = None
    for msg in reversed(state.get("messages", [])):
        if msg.get("role") == "assistant":
            last_ai_message = msg.get("content")
            break
    info = state.get('userInfo', {}).get('info')
    # آماده‌سازی پیام کامل برای Assistant
    # context_message = (
    #     f"New user message: {user_message}\n"
    #     f"User info: {info}\n"
    #     f"Last AI message: {last_ai_message if last_ai_message else 'none'}\n"
    # )
    # final = await thread_message(context_message, threadId, greeting_assistant.id)
    messages = [
        {"role": "system", "content": greeting_assistant},
        {
            "role": "system",
            "content": f"last ai message: {last_ai_message or 'none'}"
        },
        {
            "role": "system",
            "content": f"user info : {info or 'none'}"
        },
        {"role": "user", "content": f"{user_message}"},
    ]
    final_text = chat_stream(messages, state)

    return final_text


def get_assistant_express_need_buy(state: dict) -> str:
    user_message = state["input"]
    context_message = (
        f"User message: {user_message}\n"
        f"User info: {state.get('userInfo', {})}\n"
        f"User needs: {state.get('userInfo', {}).get('needs', {})}\n\n"
        f"Available service types: {', '.join(category_description)}\n\n"
    )
    messages = [
        {
            "role": "system",
            "content": f"""
    ### CONTEXT INFORMATION
    {context_message}
    
   ### ASSISTANT INSTRUCTIONS
    {express_need_buy_assistant}
    
(Use all the data above for a better answer.)
"""
        },
        {
            "role": "user",
            "content": user_message
        }
    ]
    final_text = chat_stream(messages, state, typeService)
    return final_text


# FIELDS = { "service_type": "string", "min_speed": "number", "max_download": "number", "max_upload": "number", "portable": "bool", "coverage": "string", "modem": "string", "night_traffic": "bool", "traffic": "number", "duration": "number", "ip": "bool", "price": "number", "region": "string", }


def get_assistant_question_service_support(state: dict) -> str:
    user_message = state["input"]
    buttons = ['به پشتیبانی ADSL نیاز دارم', 'به پشتیبانی LTE نیاز دارم']

    context_message = (
        f"User message: {user_message}\n"
    )
    messages = [
        {
            "role": "system",
            "content": f"""
        ### CONTEXT INFORMATION
        {context_message}

       ### ASSISTANT INSTRUCTIONS
        {question_service_support_assistant}

    (Use all the data above for a better answer.)
    """
        },
        {
            "role": "user",
            "content": user_message
        }
    ]
    final_text = chat_stream(messages, state, buttons)

    return final_text


def get_assistant_set_service_support(state: dict) -> str:
    user_message = state["input"]
    context_message = (
        f"User message: {user_message}\n"
    )
    messages = [
        {
            "role": "system",
            "content": f"""
        ### CONTEXT INFORMATION
        {context_message}

       ### ASSISTANT INSTRUCTIONS
        {set_service_support_assistant}

    (Use all the data above for a better answer.)
    """
        },
        {
            "role": "user",
            "content": user_message
        }
    ]
    final_text = chat_create(messages)
    return final_text


def get_assistant_suggest(state: dict, searchList=None, allSearch=None) -> str:
    user_message = state["input"]
    user_needs = state.get("userInfo", {}).get("needs", {})
    context_message = (
        f"User message: {user_message}\n"
        f"User needs: {user_needs}\n"
        f"Available services: {','.join(searchList)}\n"
    )
    messages = [
        {
            "role": "system",
            "content": f"""
        ### CONTEXT INFORMATION
        {context_message}

       ### ASSISTANT INSTRUCTIONS
        {suggest_assistant}

    (Use all the data above for a better answer.)
    """
        },
        {
            "role": "user",
            "content": user_message
        }
    ]
    final_text = chat_stream(messages, state, None, allSearch)

    return final_text


def get_assistant_answer(state: dict) -> str:
    user_message = state["input"]
    nameUser = None
    phoneUser = None
    user_info = state.get("userInfo", None)
    if user_info is not None:
        nameUser = user_info["info"]['name']
        phoneUser = user_info["info"]['phone']
    context_message = (
        f"User message: {user_message}\n"
        f" categories description: {category_description}\n"
        f" name user: {nameUser}\n"
        f" phone user: {phoneUser}\n"
    )
    messages = [
        {
            "role": "system",
            "content": f"""
        ### CONTEXT INFORMATION
        {context_message}

       ### ASSISTANT INSTRUCTIONS
        {answer_assistant}

    (Use all the data above for a better answer.)
    """
        },
        {
            "role": "user",
            "content": user_message
        }
    ]
    final_text = chat_stream(messages, state)

    return final_text


def get_assistant_register_order(state: dict) -> str:
    user_message = state["input"]
    orders = state.get('userInfo', {}).get('orders', {})

    if (len(orders) < 1):
        order = []
    else:
        order = state.get('userInfo', {}).get('orders', {})[-1]
    context_message = (
        f"User message: {user_message}\n"
        f"User name: {state.get('userInfo').get('info').get('name')}\n"
        f"Registered services: {order}\n"
    )
    messages = [
        {
            "role": "system",
            "content": f"""
        ### CONTEXT INFORMATION
        {context_message}

       ### ASSISTANT INSTRUCTIONS
        {register_order_assistant}

    (Use all the data above for a better answer.)
    """
        },
        {
            "role": "user",
            "content": user_message
        }
    ]
    final_text = chat_stream(messages, state)

    return final_text


def get_assistant_user_info_collector(state: dict) -> str:
    user_message = state["input"]
    name = state.get('userInfo').get("info").get('name')
    phone = state.get('userInfo').get("info").get('phone')
    orders = state.get('userInfo', {}).get('orders', {})
    order = []
    if (len(orders) > 0):
        order = orders[-1]
    last_ai_message = None
    for msg in reversed(state.get("messages", [])):
        if msg.get("role") == "assistant":
            last_ai_message = msg.get("content")
            break
    context_message = (
        f"last AI message: {last_ai_message}\n"
        f"User message: {user_message}\n"
        f"User name: {name}\n"
        f"User phone number: {phone}\n"
        f"services selected by the user: {order}\n"
    )
    messages = [
        {
            "role": "system",
            "content": f"""
        ### CONTEXT INFORMATION
        {context_message}

       ### ASSISTANT INSTRUCTIONS
        {user_info_collector_assistant}

    (Use all the data above for a better answer.)
    """
        },
        {
            "role": "user",
            "content": user_message
        }
    ]
    final_text = chat_stream(messages, state)

    return final_text


def get_assistant_unknown(state: None) -> str:
    user_message = state["input"]
    context_message = (
        f"User message: {user_message}\n"
    )
    messages = [
        {
            "role": "system",
            "content": f"""
        ### CONTEXT INFORMATION
        {context_message}

       ### ASSISTANT INSTRUCTIONS
        {unknown_assistant}

    (Use all the data above for a better answer.)
    """
        },
        {
            "role": "user",
            "content": user_message
        }
    ]
    final_text = chat_stream(messages, state)

    return final_text


def create_json_need_buy_response_task(state=None):
    last_ai_message = None
    for msg in reversed(state.get("messages", [])):
        if msg.get("role") == "assistant":
            last_ai_message = msg.get("content")
            break
    user_message = state.get("input")
    history_suggestion = state.get("history_suggestion")
    if (len(history_suggestion) > 0):
        history_suggestion = history_suggestion[-1]
    else:
        history_suggestion = None
    previous_json = state.get('userInfo', {}).get('needs', {})
    print("details_data isss>>>", details_plan)
    context_message = (
        f"""
        🔹 **User Message:** {user_message}
        🔹 **Last AI Message:** {last_ai_message or 'None'}
        🔹 **Previous Suggestions:** {history_suggestion}
        🔹 **Previous Needs:** {previous_json}
        🔹 **Available Services (typeService):** {typeService}
        🔹 **Feature Schema (details_plan):** {details_plan}
        """
    )
    messages = [
        {
            "role": "system",
            "content": f"""
    ### 🧩 Input Context
        {context_message}

       ### ASSISTANT INSTRUCTIONS
        {create_json_need_buy_assistant}

    (Use all the data above for a better answer.)
    """
        },
        {
            "role": "user",
            "content": user_message
        }
    ]
    final = chat_create(messages)
    return final


def register_order_json_task(state=None):
    history = state.get("history_suggestion")
    user_message = state.get("input")
    history_suggestion = history[-1]
    print('last of history_suggestion is>>>>', history_suggestion)
    context_message = (
        f"""
        🔹 **User Message:** {user_message}
        🔹 **f"Suggested services list:** {history_suggestion}\n\n"

        """
    )
    messages = [
        {
            "role": "system",
            "content": f"""
    ### 🧩 Input Context
        {context_message}

       ### ASSISTANT INSTRUCTIONS
        {register_order_json_assistant}

    (Use all the data above for a better answer.)
    """
        },
        {
            "role": "user",
            "content": user_message
        }
    ]
    final = chat_create(messages)
    return final


def user_info_json_task(state=None):
    user_message = state.get("input", "")
    info = state["userInfo"]['info']
    context_message = (
        f"""
       f"User message: {user_message}\n"
            f"User information: {info}\n"

        """
    )
    messages = [
        {
            "role": "system",
            "content": f"""
    ### 🧩 Input Context
        {context_message}

       ### ASSISTANT INSTRUCTIONS
        {user_info_json_assistant}

    (Use all the data above for a better answer.)
    """
        },
        {
            "role": "user",
            "content": user_message
        }
    ]
    final = chat_create(messages)
    return final


def payment_task(state=None):
    order = state["userInfo"]['orders'][-1]
    info = state["userInfo"]['info']
    user_message = state.get("input")
    context_message = (
        f"""
         f"User message: {user_message}\n"
            f"User order: {order}\n"
            f"User info: {info}\n\n"

        """
    )
    messages = [
        {
            "role": "system",
            "content": f"""
    ### 🧩 Input Context
        {context_message}

       ### ASSISTANT INSTRUCTIONS
        {payment_assistant}

    (Use all the data above for a better answer.)
    """
        },
        {
            "role": "user",
            "content": user_message
        }
    ]
    final = chat_stream(messages, state)
    return final
