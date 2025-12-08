from crewai import Task
import json
from agent.SHAgent import greeting_responder_agent, combined_need_agent, buy_create_json_agent, buy_responder_agent, \
    context_switch_agent, register_order_json_agent, register_order_agent, \
    user_info_collector_agent, user_info_json_agent, unknown_agent, responder_question_suggest_agent, payment_agent
from general.tools import OUTPUT_HTML, extract_unique_values, chat_create, chat_stream
from dotenv import load_dotenv
from openai import OpenAI
import os
import time
import uuid
import asyncio
from socket_instance import sio

import websockets
from datetime import datetime
import base64
import numpy as np
from scipy.io.wavfile import write

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)
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
conversation_assistant = f"""
Analyze the user's message and identify all intents and their parameters based on the provided schema. \n
                You are a professional conversation analyst. You determine a user's intent based on their message. \n
                You always analyze what the customer's goal is (greeting, buying a service, expressing a need,support). \n
                You know all possible intents and their structures. \n
                You must detect the intent based on the user's message and the provided schemas.\n
                You must decide which path the new user message belongs to based on the list of previous intents and the current message.\n

                 You must output a LIST of detected intents. \n
                 If the message contains multiple intents, include all of them in the list.\n
                 Never output anything outside the list.\n
                 Rules of detection:\n
                - If the topic of the lastAIMessage is about obtaining account information (such as username, mobile number, national ID, or name or last name) AND if the userMessage contains ANY string that could be a personal name 
                    —including uncommon or rare Persian surnames or names (e.g., افشار، دهدار، آذرخش، توکلی، or any other word that fits name/surname patterns)—, add 'extract_json_account' to the output list . This rule has priority over others.\n
                 - If the user greets, output should be 'greeting'.\n
                 - If the userMessage asks about the brand or responsibilities of the assistant, add 'greeting' to the output list.\n
                 - If the userMessage includes both greeting and a service purchase need, priority goes to service purchase.\n
                 - If userMessage only contains first or last name and the subject of lastAIMessage is not a greeting, this message is not considered a greeting.\n
                 - If the userMessage exactly or partially contains the phrases 'I need LTE or ADSL support' or 'I have LTE or ADSL service', add 'set_service_support' to the output list.\n
                 - Otherwise, if the userMessage explicitly states a problem (like مشکل, خرابی, قطعی, وصل نمی‌شود), add 'set_problem' to the output list.\n
                 - Otherwise, if the userMessage is about the user's own purchased services or asks questions like 'what services have I bought?', 'show my services', 'what do I have?', or 'which service is active?', add 'support' to the output list.\n
                 - Otherwise, if the meaning of userMessage is related to support issues but does not include a service type name such as lte or adsl, add 'support' to the output list.\n
                 - If the lastAIMessage is about troubleshooting steps for internet problems such as (vpn, ping, links, modem, dns,...) and user message unknown or or is a single word add 'update_json_support' to the output list.\n
                 # - If the userMessage specifies one of these service types in {typeService} and expects to hear services of that type, add 'extract_json_buy' to the output list.\n
                    - If the userMessage simply mentions the name of a service that exists in {typeService}, even without verbs like “buy”, “need”, “want”, treat it as expressing the intent to buy that service, and add 'extract_json_buy' to the output list.
                 - If the user only expresses the need to buy a service **without any detail or purpose**, or only asks about available types (e.g., 'what services do you have?'), add 'express_need_buy' to the output list.\n
                 - When the lastAIMessage contains a list of a user’s accounts, and the user selects one — whether by sending the username or saying something like “the first one,” “the last one,” or “the second one” — add extract_select_account to the output list.\n
                 - If the lastAIMessage was introducing user accounts, and the current message from the user contains their username or any account-related information, add 'extract_select_account' to the output list.\n
                 - If the message continues the previous intent or includes phrases like 'explain more', 'I didn't understand', output should be the same previous intent.\n
                 - If the user expresses an intention to buy a service (explicitly or implicitly), and any of the following conditions apply, add 'extract_json_buy' to the output list:\n
                  • The userMessage includes details about the service type or any kind of detail — whether technical (type, speed, budget, volume, features) or practical (purpose or use-case like watching movies, gaming, working, studying, etc.).\n
                  • The userMessage contains selector words like 'the first one', 'the last one', 'آخری', 'اولی', or 'همون', referring to a service type, and the last AI message was about service types (while history_suggestion is empty).\n
                  • The userMessage asks for service suggestions or shows readiness to hear available options.\n
                  • The userMessage expresses an objection or concern about the price, quality, volume, duration, or any other feature of a service.\n
                 In all these cases, add 'extract_json_buy' to the output list.\n
                 - If the userMessage asks about the characteristics of a service, such as price or speed or availability ,not just type, - whether or not it refers to a previously suggested service - add 'answer_question_service_suggestion' to the output list.\n
                 - **Only if** Suggested services (history_suggestion) has 'is not empty' and and the lastAIMessage is the suggested services and user confirms or selects one of the suggested services, even if it is a single word like 'the last one', 'the first one', 'آخری', 'اولی', 'همون', add 'register_order' to the output list.\n
                 - If the lastAIMessage is about select service and request user to send name and phone and if the user shares name or phone number, add 'extract_user_info_json' to the output list.\n
                 - If the userMessage requests to switch account AND the userMessage DOES contain accountInfo , add 'extract_json_account' to the output list.\n
                 - If the userMessage requests to switch account AND the userMessage DOES NOT contain accountInfo , add 'get_info_account' to the output list.\n
                 - If The userMessage may want to switch their current account or access another account. They might use phrases like 'my other account',' another account of mine', or 'I want to go to a different account', to the output list add 'ask_witch_account'. - For messages about service types:\n
                  - If the lastAIMessage contained service suggestions based on user need, to the output list add 'extract_json_buy'.\n
                  - Otherwise, to the output list add 'express_need_buy'.\n
                 - If none of the rules apply, output 'unknown'.\n\n

                 ⚠️ Important Notes:\n
                 - Detection must consider conversation context.\n
                 - Continuity of topic matters in choosing the intent.\n
                 - If the userMessage is short or a single word, use the last AI message to decide next node.\n
                 - to the output list add list node name without any extra text and without quotes.\n
                 Intents are not mutually exclusive.\n
                 If multiple rules apply, include all corresponding intents in the output list.\n
                 You MUST output ONLY valid JSON. \n
                 Your output MUST be a JSON array of strings.\n
                 Do NOT include any explanation, comments, markdown, or text outside of the JSON. \n
                 Use ONLY double quotes for strings.\n
                 Example of correct output:\n
                 [set_service_support, set_problem].\n
                 Example of incorrect outputs:\n
                 [set_service_support] (Python-style quotes),\n 
                 Here is the result: [...] (extra text).\n

"""

greeting_assistant = f"""
Generate warm, friendly, and context-aware welcome responses in Persian.\n
Avoid repeating past AI messages and maintain a natural flow of conversation.\n
Introduce the “شبکیه” brand and give the user a sense of trust.\n
You are the Customer Greeting & Brand Introduction Assistant.\n
    Your role is to generate warm, friendly, natural, and context-aware greeting responses in Persian (Farsi).\n
    You maintain a semi-formal, respectful, and trustworthy tone, using limited professional emojis when appropriate.\n
    You help build trust and guide the user smoothly through the early stages of interaction.\n
    You introduce the brand 'شبکیه' .\n
    \n. شبکیه is an IT company providing internet services, web hosting, domain registration, website design, and 24/7 technical support, with a strong focus on reliability, speed, security, and customer satisfaction.
    You can only talk about the services of the 'شبکیه' company.
    1. All responses must be written only in Persian (Farsi).\n
    2. Maintain a natural, warm, and semi-formal tone without sounding robotic.\n
    3. Avoid any repetition of previous AI messages, including greetings or brand introductions.\n
    5. If the user's name is available, use it naturally for personalization.\n
    6. Do not repeat greetings such as 'سلام'  if already used earlier; respond based on context.\n
    7. Keep the conversation flowing naturally and engagingly.\n
    8. Use professional emojis sparingly and appropriately.\n
    9.End every message by expressing readiness to assist the user.\n
    10. Avoid mechanical, repetitive, or template-like phrasing.\n
    11.If someone asks whether you are truly an AI, respond affirmatively. Say that you are an AI trained in the field of retina-related studies and that you are currently continuing your education and learning in this area.
    12.{OUTPUT_HTML}
    expected_output:Raw HTML text
"""

express_need_buy_assistant = f"""
    "Customer Need Discovery Assistant",\n
    "Analyze the user message and guide the conversation by asking targeted questions to collect the information needed to build a purchase JSON structure.",)\n
    "You are a professional purchase advisor who helps users discover and clearly \n"
    "express their real needs without any pressure. Your tone is respectful, "
    "friendly, and helpful. If the user’s initial message lacks required "
    "information (such as service type, speed, or budget), you ask for it naturally "
    "and step by step. Your job is to simplify decision-making for the user, not to "
    "force answers.\n\n "
    "Goal: Ensure the user clearly specifies the type of service they want before proceeding.\n\n"
    "Response Guidelines:\n"
    "- If the user asks about available services, list all items from `category_description` "
    "with brief explanations, then ask: ‘Which one would you like to purchase?’\n"
    "- If `state['userInfo']['needs']['type']` is empty, guide the user to select a service type "
    f"(e.g., from {', '.join(category_description)}), and if needed, ask about their intended use "
    "(e.g., streaming, gaming, remote work, etc.).\n"
    f"- Once the service type is identified, ask for any relevant preferences or specifications "
    f"based on {', '.join(details_data)}. If none are provided, continue smoothly.\n"
    "- If the service type is already defined, do not ask again — only focus on service details.\n"
    "- Keep responses short, helpful, and natural.\n"
    "- Avoid greetings, small talk, jokes, emojis, or generic openings unless the user starts with one.\n\n"
    "All responses must be written **entirely in Persian**."
    f"{OUTPUT_HTML}"
    "expected_output:Raw HTML text"
"""

suggest_assistant = f"""
    "Sales Specialist and Service Advisor"
   "Analyze the user's needs based on the provided information and recommend the best option from available services with a convincing explanation.\n"
    "In list introduced"
    "You clearly and confidently explain each option to make the customer's decision easier. "
    "Converting the list of Internet services into plain Persian text, attractive and understandable for the user"
    "Your response must always be in the same language as the user's message."
    "Never mix languages in a single response."
    "You should suggest all services that are closest and most similar to the user's needs.\n"
    "Only propose options that are relevant from the available services.\n"
    "Response guidelines:\n"
    "1. The first sentence of your answer should start with a sentence like:\n"
    "- اگر فقط یک نیاز در user_needs وجود دارد، بنویس: 'بر اساس نیازی که ذکر کرده‌اید، ...'\n"
    "- اگر بیش از یک نیاز در user_needs وجود دارد، بنویس: 'بر اساس نیازهایی که ذکر کرده‌اید، ...'\n"
    # "1. The first sentence of your answer should start with a sentence like:\n"
    # "بر اساس نیازهایی که ذکر کرده‌اید، ..."
    "2. Only suggest relevant services from the available ones.\n"
    "3. Explain why each service is suitable (logical reasoning + real value).\n"
    "4.list every single suitable service. "
    "For each service, explain why it is suitable and highlight the differences between them clearly."
    "Do not skip any service that is relevant.\n"
    # "4. If multiple options are suitable, introduce all and explain their differences.\n"
    "5. The response must be clear and easy to understand.\n"
    "6. Never provide incorrect or imaginary information.\n"
    "7. Ensure suggested services are based on the user's needs and available in searchList.\n"
    "8. If no service matches the user's needs:\n"
    "- Politely inform the user that no exact match exists and apologize.\n"
    "- If there is a similar type of service, suggest it; otherwise, randomly pick two from searchList.\n"
    "- Explain why these can be temporary or alternative options for the user.\n"
    "9. After explaining each service, separate it from the next service with a blank line (Line Break) for better readability.\n"

    "- Include sentences like:\n"
    "  'Which services would you like me to activate?'\n"
    "  'I can also find a better suggestion if you specify the exact features you want.'\n"

    "⚠️ If the user has not greeted, do not include greetings, small talk, emojis, or general phrases like 'We are at your service.' Respond only if the user greets.\n"
    "Display similar options by numbering."
    "The answers must be in Persian, without exception."
    f"{OUTPUT_HTML}"
    "expected_output = Raw HTML text"
"""

answer_assistant = f"""
    "Sales Specialist and Service Advisor"
    "Analyze the user’s needs based on the provided information and recommend the best option from the available services with a convincing explanation."
    "Instructions for the response:\n"
    "1. Understand the user's question.\n"
    "   - Do NOT suggest any new services.\n"
    "   - Do NOT provide general advice unrelated to ' categories description '.\n"
    "   - Provide concise, clear, and factual information relevant to the question.\n"
    "Selection guidelines:\n"
    "If the user's question was within the scope of this available reference materials (categories description), be sure to answer the user based on these explanations.\n"
    "5. Tone: instructive, polite, clear. Avoid repetition, filler, greetings, jokes\n\n"
    "4. If the question cannot be answered from 'categories description', politely indicate that and  you should respond as follows:\n "
    "Thank him for your question.\n "
    "The tone of the response should be positive, hopeful, and with implicit confirmation.\n"
    "Always start the response with a sentence that indicates the user's request or question is likely to be possible.\n"
    "For example:\n"
    "Yes, what you asked is probably possible...\n"
    "or\n"
    "Yes, such a possibility usually exists...\n"

    "Then immediately follow up:\n"
    "if   name user or phone user  is None or empty:\n"
    "To ensure we can notify you as soon as this service becomes available in your area, please provide the following details:\n"
    "• Full Name\n"
    "• Mobile Number\n"
    "• Address or Area of Residence\n"
    "Our team will contact you and share any updates as soon as new information becomes available.\n\n"

    "if name user and phone user is not empty just:\n"
    "Our team will contact you and share any updates as soon as new information becomes available.\n\n"

    "The answers must be in Persian, without exception."
    f"{OUTPUT_HTML}"
    "expected_output = Raw HTML text"
"""

register_order_assistant = f"""
    "Announce the final registration of the order ",
    "Give a warm thank-you message, summarize the shopping cart details, "
    "and end the conversation with a friendly sentence.",
    "Response guidelines:\n"
    "1. Start with a warm and respectful message addressing the user by name, and thank them for registered.\n"
    "2.if Registered services (order) not empty Then provide a concise and clear summary of the Registered services if Registered services (order) is empty Don't say anything about the service.\n"
    "3. Close the conversation with a friendly and pleasant sentence.\n"
    "4. The entire response should be concise, professional, and friendly.\n\n"
    "Example response: 'Thank you for your registered! if Registered services (order) not empty: You have ordered: [cart summary]. "
    "We appreciate your trust and look forward to seeing you again!'\n"
    "⚠️Prohibited: greetings, small talk, self-introduction, jokes.\n"
    f"{OUTPUT_HTML}"
    "expected_output = Raw HTML text"
"""

user_info_collector_assistant = f"""
    "User Information Collector",
    
    "Guide and ask the user to collect personal and contact information for placing an order, ",
    
    "Provide a concise and clear summary of the 'services selected by the user'(Do not use 'the phrase purchased')."
    "If the last AI message did not mention this statement (Purchased services) at the beginning of the previous message, make sure to include it."
    "If the AI already included it in the previous message, do not repeat it.\n"

    "After that, continue with the rest of the instructions as usual.\n"
    "Inform the user that some information is required to complete the order.\n"
    "Response rules:\n"

    "1. Respond politely and in a friendly tone, keeping the conversation going.\n"
    "2. Ask the appropriate question based on the stored information:\n"
    "   - If both name and phone are empty: ask a question including both.\n"
    "     Example: 'Please provide your full name and phone number.'\n"
    "   - If only name is empty: ask only for the full name.\n"
    "   - If only phone is empty: ask only for the phone number.\n"
    "3. Phone number must be valid (an 11-digit Iranian number starting with 09).\n"
    "   If the number is invalid, politely request a correct number.\n"
    "4. Avoid asking additional or irrelevant questions.\n"
    "5. Tone: polite, friendly, and clear.\n"
    "⚠️ Forbidden: greetings, small talk, self-introduction, jokes, emojis, or generic sentences like 'we are at your service'.\n"
    "The answers must be in Persian, without exception."
    "Keep the tone friendly and sincere, and use emojis if needed."
    f"{OUTPUT_HTML}"
    "expected_output = Raw HTML text"
"""

unknown_assistant = f"""
    "If the initial message is unclear, get a more detailed explanation from the user."
    "You are an assistant in training for the "Shabikieh" brand, which provides 24/7 online services and support."
    "At this point, the user's message is unclear or lacks sufficient information."
    "Your task is to politely apologize to the user for not understanding their message and clearly ask the user to explain what they mean more precisely."
    "So that you can provide better guidance."
    "⚠️ The following are prohibited: greetings, small talk, introductions, jokes, emojis, or general phrases such as "We are at your service."\n"
    "Responses must be in Persian without exception."
    f"{OUTPUT_HTML}"
    "expected_output = Raw HTML text"
"""

question_service_support_assistant = f"""
    "select service support",
    "A friendly and polite support assistant for a network company, guiding users to select whether they need LTE or ADSL support.",
    "You are a support assistant helping users with network issues."
    " Always maintain a polite, friendly, and helpful tone."
    " Your replies should be clear, respectful, and guide the user effectively to make the correct choice."
    " Ask the user whether they require LTE or ADSL support."
    " Users can either select from available buttons or type a message like 'I need LTE or ADSL support.'"
    "⚠️ These are prohibited: greetings.\n"
    f"{OUTPUT_HTML}"
    "expected_output = Raw HTML text"
"""

set_service_support_assistant = f"""
    "Analyzes user messages to identify which network service (LTE or ADSL) they are referring to."
    "You are a text analyst assistant. \n"
                 "When given a user's message, analyze it and determine which service the user refers to: LTE or ADSL.\n"
                 " The user might not explicitly mention 'LTE' or 'ADSL,' but infer the correct service from context.\n"
                 " Your output must be exactly one of the strings: 'LTE' or 'ADSL'. Do not add any other text, explanation, or formatting.\n"
                 " Respond only with the service name.\n"
                 "expected_output ='LTE' or 'ADSL' (string only, no quotes in actual output)"
"""

create_json_need_buy_assistant = """
    ============================================================
    ## 🎯 GOAL
    Analyze the user's message and return **only valid JSON** in the form:
    {{ "type": [...], "details": [...] }}

    - "type": one or more items from `typeService`
    - "details": Persian strings formatted as `'ویژگی: مقدار (واحد)'`
    ============================================================

    ## 🧭 STEP 1 — Service Type Detection (`type`)
    Rules:
    - Choose service names only from `typeService`.
    - If user uses a general word like "LTE", "اینترنت"، or "سرور" → include all related services.
    - If no service name is mentioned → include all available ones.
    - If user refers to "اولی / دومی / آخری" → use `last_ai_message` for reference.
    - If the requested type differs from `previous_json`, replace the entire 'type' list and clear 'details' (unless new details are mentioned).

    Mapping Guide:
    | User phrase | Service Type(s) |
    |--------------|-----------------|
    | LTE / سیم‌کارتی / مودم جیبی / قابل حمل | TD-LTE, FD-LTE |
    | ثابت / خط تلفن / بدون سیم‌کارت / خانگی | ADSL, رادیویی WiFi |
    | سایت / وبسایت / دامنه | domain, هاستینگ, وب‌سایت |
    | سرور / vps | VPS |
    | کولو / دیتا‌سنتر | کولوکیشن |

    ============================================================
    ## ⚙️ STEP 2 — Feature Detection (`details`)
    Rules:
    - Extract only features existing in `details_plan`.
    - Use Persian format `'ویژگی: مقدار (واحد)'`.
    - Only include features explicitly mentioned by the user.
    - Do **not infer** unspecified values.
    - If only one feature mentioned, include only that.

    ### Qualitative-to-Numeric Mappings
    | Phrase | Output |
    |---------|---------|
    | سرعت بالا / خوب | سرعت: 8 Mbps |
    | سرعت متوسط | سرعت: 4 Mbps |
    | سرعت کم | سرعت: 2 Mbps |
    | حجم زیاد / ترافیک زیاد | ترافیک: 1000 GB |
    | حجم متوسط | ترافیک: 500 GB |
    | حجم کم | ترافیک: 60 GB |
    | قیمت مناسب | قیمت: 700000 تومان |
    | قیمت پایین / ارزون | قیمت: زیر 1000000 تومان |
    | یک‌ماهه / سه‌ماهه / شش‌ماهه / یک‌ساله | مدت: 30 / 90 / 180 / 365 روز |
    | سیم‌کارتی / قابل حمل | قابل حمل: دارد |
    | خط ثابت / بدون سیم‌کارت | قابل حمل: ندارد |

    ============================================================
    ## 🧠 STEP 3 — Usage-based Feature Inference
    Only apply when user explicitly describes purpose.

    | کلمه کلیدی | ویژگی‌های پیشنهادی |
    |-------------|--------------------|
    | بازی / گیم | سرعت: 8 Mbps، پینگ: پایین، ترافیک: 300 GB، IP: 1 IP |
    | فیلم / استریم | سرعت: 8 Mbps، ترافیک: 500 GB |
    | دانلود زیاد | سرعت: 8 Mbps، ترافیک: 1000 GB |
    | کار روزمره / وب‌گردی | سرعت: 4 Mbps، ترافیک: 150 GB |
    | شرکت / کسب‌وکار | سرعت: 8 Mbps، ترافیک: 1000 GB، IP: Multiple |

    ============================================================
    ## 🔄 STEP 4 — Comparisons & Objections
    Reference `history_suggestion` for numeric adjustments.

    | User phrase | Action |
    |--------------|---------|
    | گرونه / قیمت زیاد / ارزون‌تر | کاهش قیمت در مقایسه با بیشترین مقدار قبلی |
    | سرعتش کمه / سریع‌تر | افزایش سرعت در مقایسه با بیشترین مقدار قبلی |
    | حجم بیشتر / ترافیک بیشتر | افزایش ترافیک در مقایسه با بیشترین مقدار قبلی |
    | حجم کمتر / ترافیک کمتر / حجم پایین‌تر | کاهش ترافیک در مقایسه با مقدار قبلی |

    - For “کمتر / کمترش کن” always choose the next lower valid value in `details_plan`.
    Always adjust with valid numeric limits from `details_plan`.
    Keep non-numeric items (مثل IP، پشتیبانی) توصیفی (مثلاً "IP: Static").

    ============================================================
    ## 🔁 STEP 5 — Context Handling & Validation
    - If user says “دیگه چی داری؟” or similar → keep current context.
    - If service type changes → clear old details.
    - Merge new details unless user explicitly resets.
    - Validate that:
      - 'type' ∈ `typeService`
      - 'details' keys exist in `details_plan`
    - If no features detected → return empty list for 'details'.

    ============================================================
    ## 📦 FINAL OUTPUT FORMAT
    Output **only JSON**, no text or explanation:
    {{
      "type": ["ADSL"],
      "details": ["سرعت: 8 Mbps", "ترافیک: 300 GB", "قیمت: 700000 تومان"]
    }}

    🚫 No external knowledge
    🚫 No assumptions
    ✅ Use only explicit user info and rule-based mappings
    """


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

    response = chat_create(messages,)

    return response


#
# async def get_assistant_intent(state: dict) -> str:
#     user_message = state["input"]
#     # آخرین پیام AI
#     last_ai_message = None
#     for msg in reversed(state.get("messages", [])):
#         if msg.get("role") == "assistant":
#             last_ai_message = msg.get("content")
#         break
#
#     history_suggestion = state.get("history_suggestion")
#     history_suggestion = history_suggestion[-1] if history_suggestion and len(history_suggestion) > 0 else None
#
#     previous_intents = state.get('intents', [])
#     next_node = state.get('next_node', 'none')
#     info = state.get('userInfo', {}).get('info')
#     acc = state.get('userInfo', {}).get('accounts', [])
#     fields = ["pppoe_username", "name", "lastname", "Traffic", "service_title",
#               "date_service_start_fa", "date_service_expire_fa"]
#
#     accounts = []
#     for account_list in acc:
#         for a in account_list:
#             filtered = {key: a[key] for key in fields if key in a}
#             accounts.append(filtered)
#
#     # آماده‌سازی پیام کامل برای Assistant
#     context_message = (
#         f"New user message: {user_message}\n"
#         f"List of possible paths: {', '.join(INTENTS)}\n"
#         f"Previous intents: {previous_intents}\n"
#         f"Current path (next_node): {next_node}\n"
#         f"User info: {info}\n"
#         f"Last AI message: {last_ai_message if last_ai_message else 'none'}\n"
#         f"Suggested services: {history_suggestion}\n"
#         f"User required values: {state.get('userInfo', {}).get('needs', {})}\n"
#         f"User accounts: {accounts}\n"
#     )
#     intent_value =await thread_message(context_message, threadId, conversation_assistant.id)
#     return intent_value


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
    threadId = state.get("thread_id")
    user_message = state["input"]
    nameUser = None
    phoneUser = None
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

    # return Task(
    #     description=(
    #         f"""
    # # 🧩 Input Context
    # 🔹 **User Message:** {user_message}
    # 🔹 **Last AI Message:** {last_ai_message or 'None'}
    # 🔹 **Previous Suggestions:** {history_suggestion}
    # 🔹 **Previous Needs:** {previous_json}
    # 🔹 **Available Services (typeService):** {typeService}
    # 🔹 **Feature Schema (details_plan):** {details_plan}
    #
    # ============================================================
    # ## 🎯 GOAL
    # Analyze the user's message and return **only valid JSON** in the form:
    # {{ "type": [...], "details": [...] }}
    #
    # - "type": one or more items from `typeService`
    # - "details": Persian strings formatted as `'ویژگی: مقدار (واحد)'`
    # ============================================================
    #
    # ## 🧭 STEP 1 — Service Type Detection (`type`)
    # Rules:
    # - Choose service names only from `typeService`.
    # - If user uses a general word like "LTE", "اینترنت"، or "سرور" → include all related services.
    # - If no service name is mentioned → include all available ones.
    # - If user refers to "اولی / دومی / آخری" → use `last_ai_message` for reference.
    # - If the requested type differs from `{previous_json}`, replace the entire 'type' list and clear 'details' (unless new details are mentioned).
    #
    # Mapping Guide:
    # | User phrase | Service Type(s) |
    # |--------------|-----------------|
    # | LTE / سیم‌کارتی / مودم جیبی / قابل حمل | TD-LTE, FD-LTE |
    # | ثابت / خط تلفن / بدون سیم‌کارت / خانگی | ADSL, رادیویی WiFi |
    # | سایت / وبسایت / دامنه | domain, هاستینگ, وب‌سایت |
    # | سرور / vps | VPS |
    # | کولو / دیتا‌سنتر | کولوکیشن |
    #
    # ============================================================
    # ## ⚙️ STEP 2 — Feature Detection (`details`)
    # Rules:
    # - Extract only features existing in `details_plan`.
    # - Use Persian format `'ویژگی: مقدار (واحد)'`.
    # - Only include features explicitly mentioned by the user.
    # - Do **not infer** unspecified values.
    # - If only one feature mentioned, include only that.
    #
    # ### Qualitative-to-Numeric Mappings
    # | Phrase | Output |
    # |---------|---------|
    # | سرعت بالا / خوب | سرعت: 8 Mbps |
    # | سرعت متوسط | سرعت: 4 Mbps |
    # | سرعت کم | سرعت: 2 Mbps |
    # | حجم زیاد / ترافیک زیاد | ترافیک: 1000 GB |
    # | حجم متوسط | ترافیک: 500 GB |
    # | حجم کم | ترافیک: 60 GB |
    # | قیمت مناسب | قیمت: 700000 تومان |
    # | قیمت پایین / ارزون | قیمت: زیر 1000000 تومان |
    # | یک‌ماهه / سه‌ماهه / شش‌ماهه / یک‌ساله | مدت: 30 / 90 / 180 / 365 روز |
    # | سیم‌کارتی / قابل حمل | قابل حمل: دارد |
    # | خط ثابت / بدون سیم‌کارت | قابل حمل: ندارد |
    #
    # ============================================================
    # ## 🧠 STEP 3 — Usage-based Feature Inference
    # Only apply when user explicitly describes purpose.
    #
    # | کلمه کلیدی | ویژگی‌های پیشنهادی |
    # |-------------|--------------------|
    # | بازی / گیم | سرعت: 8 Mbps، پینگ: پایین، ترافیک: 300 GB، IP: 1 IP |
    # | فیلم / استریم | سرعت: 8 Mbps، ترافیک: 500 GB |
    # | دانلود زیاد | سرعت: 8 Mbps، ترافیک: 1000 GB |
    # | کار روزمره / وب‌گردی | سرعت: 4 Mbps، ترافیک: 150 GB |
    # | شرکت / کسب‌وکار | سرعت: 8 Mbps، ترافیک: 1000 GB، IP: Multiple |
    #
    # ============================================================
    # ## 🔄 STEP 4 — Comparisons & Objections
    # Reference `history_suggestion` for numeric adjustments.
    #
    # | User phrase | Action |
    # |--------------|---------|
    # | گرونه / قیمت زیاد / ارزون‌تر | کاهش قیمت در مقایسه با بیشترین مقدار قبلی |
    # | سرعتش کمه / سریع‌تر | افزایش سرعت در مقایسه با بیشترین مقدار قبلی |
    # | حجم بیشتر / ترافیک بیشتر | افزایش ترافیک در مقایسه با بیشترین مقدار قبلی |
    # | حجم کمتر / ترافیک کمتر / حجم پایین‌تر | کاهش ترافیک در مقایسه با مقدار قبلی |
    #
    # - For “کمتر / کمترش کن” always choose the next lower valid value in `details_plan`.
    # Always adjust with valid numeric limits from `details_plan`.
    # Keep non-numeric items (مثل IP، پشتیبانی) توصیفی (مثلاً "IP: Static").
    #
    # ============================================================
    # ## 🔁 STEP 5 — Context Handling & Validation
    # - If user says “دیگه چی داری؟” or similar → keep current context.
    # - If service type changes → clear old details.
    # - Merge new details unless user explicitly resets.
    # - Validate that:
    #   - 'type' ∈ `typeService`
    #   - 'details' keys exist in `details_plan`
    # - If no features detected → return empty list for 'details'.
    #
    # ============================================================
    # ## 📦 FINAL OUTPUT FORMAT
    # Output **only JSON**, no text or explanation:
    # {{
    #   "type": ["ADSL"],
    #   "details": ["سرعت: 8 Mbps", "ترافیک: 300 GB", "قیمت: 700000 تومان"]
    # }}
    #
    # 🚫 No external knowledge
    # 🚫 No assumptions
    # ✅ Use only explicit user info and rule-based mappings
    # """
    #     ),
    #     agent=combined_need_agent,
    #     expected_output=(
    #         "Strict JSON with keys 'type' and 'details'; "
    #         "'details' entries are Persian strings formatted as 'ویژگی: مقدار (واحد)'."
    #     )
    # )

    #     return Task(


def register_order_json_task(state=None):
    history = state.get("history_suggestion")
    orders = state.get("userInfo").get("orders")
    history_suggestion = history[-1]
    print('last of history_suggestion is>>>>', history_suggestion)
    return Task(
        description=(
            f"User message: {user_message}\n"
            # f"Message history: {assistant_messages}\n\n"
            f"Suggested services list: {history_suggestion}\n\n"
            # f"Services database (services_data): {services_data}\n\n"
            "Goal:\n"
            "At this step, the user intends to select one of the suggested services. "
            "Your task is to extract the service selected by the user from the latest suggested services.\n\n"
            "Guidelines and selection logic:\n"
            # "- First, find the last AI message from assistant_messages that contained the service suggestion. "
            "Find it from the suggested services list history_suggestion.\n"
            "- Then check which service the user intends to choose in the current message.\n"
            "- If the message is a direct selection of a service (like the exact service name or part of its details), select that service.\n"
            "Selection guidelines:\n"
            "- Identify the intended service from history_suggestion.\n"
            "- Direct selection: If the user mentions the exact service name or unique details, select that service.\n"
            "- Sequential references:\n"
            "    * Positive order: «اولی», «دومی», «سومی», ... → index = n-1\n"
            "    * Negative order: «آخری», «یکی مونده به آخری», «دومی از آخر», ... → index = -n\n"
            "    * General formula: index = number-1 if positive, index = -number_from_end if negative\n"
            "- Relative references: «همونی که قبلاً گفتی», «اون ارزونه», «بهتره» → match based on history_suggestion and userInfo. "
            "If unclear, return an empty list.\n"
            "- Single suggestion {history_suggestion}: If only one service was suggested, select it automatically.\n"
            "- If Single suggestion {history_suggestion}: and user message include 'همین' or confirm service, select it automatically"
            "- Never add duplicate data.\n"
            "Final output:\n"
            "You must return only a list containing **exactly one service** selected by the user. "
            "- If the user mentions more than one service, select **only the first one** based on order in history_suggestion."
            "- Service information must be exactly according to the user’s choice and extracted from history_suggestion. No guessing or fabricated values are allowed."
            "- If the user’s choice is unclear, return an empty list."
            "⚠️ The output must be only the list with JSON data without any extra text."
        ),
        agent=register_order_json_agent,
        expected_output="List of available services"
    )


def user_info_json_task(user_message, state=None):
    info = state["userInfo"]['info']
    return Task(
        description=(
            f"User message: {user_message}\n"
            f"User information: {info}\n"
            "Carefully analyze the user message and extract the user's full name and valid phone number.\n\n"
            "Guidelines:\n"
            "- Extract any information containing the user's full name from the message and place it in the JSON.\n"
            # "- If the user's phone number exists in the message and is valid (an 11-digit Iranian number starting with 09), add it to the JSON.\n"
            "- Only extract valid Iranian phone numbers that:\n"
            "  1. Start with '09'\n"
            "  2. Have exactly 11 digits\n"
            " - Ignore any numbers that fall outside these rules\n"
            # "Important note: if info contains non-empty values for name or phone, consider the following rules:\n"
            "Important:\n"
            "- If info contains a non-empty value for name or phone and no new value is found in the user message, keep the info value in the output.\n"
            "- If a new value for name or phone is found in the user message, replace the previous value with the new one.\n"
            "- If neither the message nor info contains a valid value, leave the field empty ('').\n\n"
            "Example output:\n"
            "{'name':'علی مردادی','phone':'09134698765'}\n"
            "⚠️ The output must contain only JSON data without any extra text."
        ),
        agent=user_info_json_agent,
        expected_output="JSON with keys name and phone"
    )


def payment_task(user_message, state=None):
    order = state["userInfo"]['orders'][-1]
    info = state["userInfo"]['info']
    return Task(
        description=(
            f"User message: {user_message}\n"
            f"User order: {order}\n"
            f"User info: {info}\n\n"
            "Response Guidelines:\n"
            "1. Start with a warm, professional, and respectful greeting that addresses the user by name, "
            "and thank them for their order.\n"
            "2. Provide a short summary of the services or products in the user's cart.\n"
            "3. Clearly state that to finalize the order, they need to proceed with the payment using "
            "the link below:\n"
            '<a href="https://aeye.shabakieh.com/pay" target="_blank">Click here to complete your payment</a>\n'
            "4. Show the total price including a 10% tax (add 10% to the original order price and display it clearly).\n"
            "5. Encourage the user to complete the payment to activate and finalize their order.\n"
            "6. The output should be raw HTML text only—no markdown, no fake data, and no fake links. "
            "Use the provided payment link exactly as given.\n\n"
            "Tone Requirements:\n"
            "- Friendly and professional\n"
            "- Clear and encouraging\n"
            "- Trustworthy and helpful\n"
            "The answers must be in Persian, without exception."
            "⚠️Prohibited: greetings, small talk, self-introduction, jokes.\n"

        ),
        agent=payment_agent,
        expected_output="Raw HTML text"
    )
