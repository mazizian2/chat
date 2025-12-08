from crewai import Task
import json
from LTE.agent.LTEAgent import ask_problem_agent, set_problem_agent, get_info_account_user_agent, \
    extract_info_accounts_agent, \
    ask_witch_account_agent, extract_select_account_agent, LTE_support_Analyst, update_json_support_agent
from general.tools import OUTPUT_HTML, chat_create, thread_message,chat_stream
from dotenv import load_dotenv
import jdatetime
import os
from openai import OpenAI

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)
INTENTS = [
    "support",
    "buy_service",
    "unknown",
    "greeting",
]
SUBINTENTS = [
    "help_internet",
    "detect_user_info",
    "request_collect_user_info",
    "collect_user_info",
    "ask_which_account",
    "detect_select_account",
    "check_modem",
    "turn_on_modem",
    "setting_modem",
    "edit_setting_modem",
    "return_operator",
]

ask_problem_assistant = f"""
Ask the user,  to describe their internet problem 
"You are a friendly support assistant at 'shabakieh' ISP. You speak in a warm, "
                 "approachable tone and you sometimes use emojis to make users feel comfortable.\n "
                 "If the user greets you, greet them back. But if they do NOT greet, do not start "
                 "with a greeting—go straight to asking about their issue. Always stay focused "
                 "only on internet-related problems and shabakieh services. Respond in the same "
                 "language as the user.\n"
                 "Ask the user, in a friendly and informal tone, to describe their internet problem.\n"
                 "If the user's name is available, use it naturally for personalization.\n\n"
                 "### Response Style Rules:\n"
                 "- Use casual, friendly language.\n"
                 "- Use emojis or stickers where appropriate.\n"
                 "- If the user greeted you, greet them back politely.\n"
                 "- If the user did NOT greet, do NOT greet. Go straight to asking about the problem.\n"
                 "- Keep the message short and natural.\n"
                 "- Always respond in the SAME language as the user.\n"
                 "- Focus ONLY on internet and Shabakieh-related issues.\n\n"
                 "⚠️ Prohibited: Greeting, small talk, or self-introduction.\n"
                 f"{OUTPUT_HTML}"
                 "expected_output:Raw HTML text"
                 """

get_account_user_assistant = f"""

Collect user account information for shabakieh support
"You are a professional technical support agent.\n "
                 "Your task is to obtain the user's account details accurately.\n "
                 "Tone must be polite, professional,friendly, and trustworthy. \n"
                 " Always respond in the user's language (Persian or English).\n"
                 " Tone: polite, friendly, and instructive.\n"
                 "⚠️ Forbidden: greetings, chit-chat, self-introduction, jokes.\n"
                 "According to service_support, you must do the following differently for LTE and ADSL:\n"
                 "if service_support is lte:\n"
                 "Fields to request: 
                 username (starts with 989559, 12 digits), \n"
                 "mobile (starts with 09, 11 digits)\n, 
                 name and last name\n, 
                 national ID (10 digits). \n"
                 "Notify user about missing or incorrect information with guidance.\n\n"
                 "### Instructions for LLM:\n"
                 "1. If all fields are empty: list username, mobile,name and last name, national ID with format rules "
                 "and ask the user to provide at least one.\n"
                 "2. If some fields are filled: no need to ask again.\n"
                 "3. If any field is invalid: identify the field, show correct format, request correct data.\n\n"
                 "if service_support is adsl:\n"
                 "You are an Internet support person. "
                 "The response should be just a polite sentence explaining that we need the 11-digit code (phone number) to investigate and resolve the user's issue. "
                 "The response should be short, direct, and relevant to the user's message. "
                 "Just ask the user for the 10-digit code.\n"


                 f"{OUTPUT_HTML}"
                 "expected_output:Raw HTML text"
                 """

ask_witch_account_assistant = f"""
Account Selector Assistant\n
Assist the user in selecting one of their available accounts \n
    "Your task is to display all of the user's accounts in a way that allows easy selection and guide the user to choose one of their accounts.\n "
"Your tone should be polite, friendly, and helpful.\n"

"Display accounts as a numbered list (1., 2., 3., ...) and help the user select one that needs support.\n"
"### Response Rules:\n"
"- Each item must include a row number."
"- Present the accounts in a selectable format.\n"
"- Ask the user to choose the account they need support with.\n"
"- The response language should match the user's message (Persian or English).\n"
"- Maintain a polite, friendly, and guiding tone.\n"
"- Using relevant emojis is allowed.\n"
"- Traffic unit is megabytes.\n"
" Important: Show only the Mask of the mobile number and username and melicode, not the entire number."
"⚠️ Prohibited: Greeting, small talk, or self-introduction.\n"
f"{OUTPUT_HTML}"
"expected_output:Raw HTML text"
"""


def get_assistant_ask_problem(state: dict) -> str:
    threadId = state.get("thread_id")
    user_info = state["userInfo"]['info']
    user_message = state["input"]
    context_message = (
        f"User info {user_info}"
        f"user message {user_message}"
    )
    messages = [
        {
            "role": "system",
            "content": f"""
        ### CONTEXT INFORMATION (JSON):
        {context_message}
        ### MAIN ASSISTANT INSTRUCTIONS:
        {ask_problem_assistant}



    (The model should use the information above. The answer should only be generated based on the assistant's rules.)
    """
        },
        {
            "role": "user",
            "content": user_message
        }
    ]

    response =chat_stream(messages, state)

    return response


def get_assistant_account_user(state: dict) -> str:
    threadId = state.get("thread_id")
    user_message = state["input"]
    service_support = state["userInfo"]["service_support"]

    info_accounts = state["userInfo"]["accountInfo"]

    # context_message = (
    #     f"User message: {user_message}\n"
    #     f"Service support: {user_message}\n"
    #     f"Current account info: {info_accounts}\n\n"
    # )
    context_message = json.dumps({
        "user_message": user_message,
        "info_accounts": info_accounts,
        "service_support": service_support,
    })
    messages = [
        {
            "role": "system",
            "content": f"""
        ### CONTEXT INFORMATION (JSON):
        {context_message}
        ### MAIN ASSISTANT INSTRUCTIONS:
        {get_account_user_assistant}



    (The model should use the information above. The answer should only be generated based on the assistant's rules.)
    """
        },
        {
            "role": "user",
            "content": user_message
        }
    ]

    response =chat_stream(messages, state)

    return response


def get_assistant_ask_witch_account(state: dict,btns=None) -> str:
    threadId = state.get("thread_id")
    user_message = state["input"]
    accounts = state["userInfo"]["accounts"]
    selected_account = state["userInfo"]["selectAccount"]
    context_message = (
        f"User message: {user_message}\n"
        f"User accounts: {accounts}\n"
        f"Selected account: {selected_account}\n"
    )
    messages = [
        {
            "role": "system",
            "content": f"""
        ### CONTEXT INFORMATION (JSON):
        {context_message}
        ### MAIN ASSISTANT INSTRUCTIONS:
        {ask_witch_account_assistant}



    (The model should use the information above. The answer should only be generated based on the assistant's rules.)
    """
        },
        {
            "role": "user",
            "content": user_message
        }
    ]

    response = chat_stream(messages, state,btns)

    return response


def create_problem_list_task(user_message):
    return Task(
        description=(
            f"User message: {user_message}\n"
            "### Response Instructions:\n"
            "- Output ONLY a clean bullet-point list using hyphens (,).\n"
            "- Each bullet must be concise, clear, and describe a single problem.\n"
            "- Do NOT provide solutions, explanations, or extra text.\n"
            "- ALWAYS respond in the exact same language as the user.\n"
            "- If the message is unrelated to internet or 'Shabakieh' services, return an empty list.\n\n"
            "- Accept the user's input even if the problem is expressed in a single word.\n"
            "\n"
            "⚠️ **EXTREMELY IMPORTANT RULE:**\n"
            "- Do NOT modify or remove existing problems in the list unless the user explicitly says their issue is resolved or something similar.\n"

            "### Strict Output Format:\n"
            "[\n"
            "  'problem1',\n"
            "  'problem2',\n"
            "  ...\n"
            "]\n\n"
        ),
        agent=set_problem_agent,
        expected_output="A list of string problems"
    )


def create_json_account_task(state):
    user_message = state["input"]

    info_accounts = state["userInfo"]["accountInfo"]
    service_support = state["userInfo"]["service_support"]
    print('service_support', service_support)
    prompt = ""
    if (service_support.lower() == 'lte'):
        prompt = (
            f"User message: {user_message}\n"
            f"Current account info: {info_accounts}\n\n"
            "Analyze the user message and extract a valid JSON according to the following rules:\n"
            "- If the message contains a 12-digit code starting with 989559, treat it as 'username'.\n"
            "- If the message contains a 10-digit code, treat it as 'melicode'.\n"
            "- If the message contains an 11-digit code starting with 09, treat it as 'mobile'.\n"
            "- If the message contains the user's last name and name, treat it as 'lastname' and 'name'.\n\n"
            "⚙️ Output Rules:\n"
            "- The result must be a valid JSON object with the keys: ['lastname', 'username', 'mobile', 'melicode'].\n"
            # "- If the user message provides a new valid value for a field, update that field accordingly.\n"
            # "- ⚠️ If a field is **not mentioned** or **no new value is detected**, **retain its existing value from the given Current account info**.\n"
            # "-  replace previous values with empty strings or null values.\n"
            # "-If there are new values in the user's message, just replace the old values with the new values and replace the old values with empty strings.\n"

            "- Only include the fields detected in the current user message; set all others to empty strings ('').\n"
            "- That means: do not keep any old values — every field not mentioned in the new message must become an empty string.\n"
            # "- In other words, the final output JSON must represent the *merged* state of old and newly extracted information.\n"
            "- Always output only pure JSON, with no additional explanations or text.\n\n"
            "Be aware that Persian users may write or pronounce their last name and name in various informal forms.\n"
            "If a word matches or contains a known name and last name  from Current account info, extract it as 'name' and 'lastname'.\n\n"
            "Example:\n"
            "User message: فقط موبایلمو می‌گم 09123456789\n"
            "Current info: {'lastname': 'مرادی', 'username': '989559143561', 'mobile': '09120000000', 'melicode': '1234567890'}\n"
            "Output:\n"
            "{'name': '','lastname': '', 'username': '', 'mobile': '09123456789', 'melicode': ''}\n\n"
            "User message: من صادق میرحسینی ام\n"
            "Current info: {'name': '','lastname': '', 'username': '', 'mobile': '', 'melicode': ''}\n"
            "Output:\n"
            "Current info: {'name': 'صادق','lastname': 'میرحسینی', 'username': '', 'mobile': '', 'melicode': ''}\n"
            "⚠️ The output must contain only JSON data without any extra text."
        )
    else:
        prompt = (
            f"User message: {user_message}\n"
            f"Current account info: {info_accounts}\n\n"
            "Analyze the user message and extract a valid JSON according to the following rule:\n"
            "- If the message contains an 11-digit code starting with 09, treat it as 'username'.\n\n"
            "⚙️ Output Rules:\n"
            "- Output a JSON object containing only: ['username'].\n"
            "- Output only pure JSON with no extra text.\n\n"
            "Example:\n"
            "User message: 09123456789\n"
            "Output:\n"
            "{\"username\": \"09123456789\"}"
        )
    print("prompt>>>", prompt)
    return Task(
        description=prompt,
        agent=extract_info_accounts_agent,
        expected_output="pure JSON object with required fields, no extra text"
    )


def extract_select_account_task(state):
    user_message = state["input"]
    acc = state["userInfo"]["accounts"]
    fields = [
        "pppoe_username",
        "name",
        "lastname",
        "Traffic",
        "service_title",
        "date_service_start_fa",
        "date_service_expire_fa"
    ]

    accounts = []

    for account_list in acc:
        for acc in account_list:
            filtered = {key: acc[key] for key in fields if key in acc}
            accounts.append(filtered)
    select_account = state["userInfo"]["selectAccount"]
    return Task(
        description=(
            f"User message: {user_message}\n"
            f"User accounts: {accounts}\n"
            f"Previously selected account: {select_account}\n\n"
            "Guidelines for account selection:\n"
            "- Determine which account the user intends to choose in the current message.\n"
            "- Direct selection: If the user mentions an exact username, melicode, or any account detail, select that account.\n"
            "- Sequential references:\n"
            "    * Positive order: 'first', 'second', 'third', ... → index = n-1\n"
            "    * Negative order: 'last', 'second to last', 'third from the end', ... → index = -n\n"
            "    * General formula: index = number-1 if positive, index = -number_from_end if negative example: user say 'هفتمی' index select: 6, user say 'دومی از آخر' index select:-2\n"

            "- Relative references: 'the same as before' → match based on the previously selected account.\n"
            "- Single account: If there is only one account in the list, select it automatically.\n"
            "- Avoid duplicate selections.\n\n"
            "Output instructions:\n"
            "- Return only a list containing exactly **one account** selected by the user.\n"
            "- If multiple accounts are mentioned, select only the first one according to the accounts list.\n"
            "- Extract account information exactly as it appears in the accounts list; do not fabricate or guess values.\n"
            "- If the user's choice is unclear, return an empty list.\n\n"
            "Example of correct JSON output:\n"
            "Do not include any explanations, messages, or text outside the JSON."

        ),
        agent=extract_select_account_agent,
        expected_output="Only valid JSON"

    )


def LTE_detect_task(state: dict) -> Task:
    user_message = state["input"]
    last_ai_message = None
    for msg in reversed(state.get("messages", [])):
        if msg.get("role") == "assistant":
            last_ai_message = msg.get("content")
            break

    status_account = list(state["userInfo"]["selectAccount"].keys())[-1]
    traffic_account = state["userInfo"]["selectAccount"]["info"]["Traffic"]
    print("traffic_account issssssssss>>>", traffic_account)
    print("traffic_account issssssssss2>>>", traffic_account == "0")
    date_str = state["userInfo"]["selectAccount"]["info"]["date_service_expire_fa"]
    expire_account = jdatetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M")
    expire_str = expire_account.strftime("%Y-%m-%d %H:%M:%S")  # تبدیل به رشته‌ی خوانا

    problems = state["userInfo"]["problems"]
    now = jdatetime.datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")  # تبدیل به رشته‌ی خوانا
    # with open("assets/json/next_step_support.json", "r", encoding="utf-8") as f:
    #     support = json.load(f)
    support = state["userInfo"]["next_step_support"]
    print("next_step_support is", support)
    if (traffic_account == "0"):
        return Task(
            description=(
                f" If the user's remaining traffic ({traffic_account}) reaches zero,"
                " notify them that their internet quota has been exhausted and they need to purchase a new plan to continue using the service "
                "ask the user to let you know if they need to purchase a new plan so you can guide them accordingly.\n"
                f"{OUTPUT_HTML}"
            ),
            agent=LTE_support_Analyst,
            expected_output="Raw HTML text",

        )
    elif (expire_account < now):
        return Task(
            description=(
                " immediately respond that the user's service period has expired, "
                "explain this clearly, and guide them on how to renew their subscription. "
                f"{OUTPUT_HTML}"
            ),
            agent=LTE_support_Analyst,
            expected_output="Raw HTML text",

        )
    else:
        return Task(
            name="LTE_Detection_Task",
            description=(
                f"This task is responsible for analyzing the user input '{user_message}' "
                "to accurately identify LTE network issues. "
                f"Last AI message: {last_ai_message}. "
                f"User account status: {status_account}. "
                f"User problems: {', '.join(problems)}. "
                f"support text : {support}.\n"
                f"Account expiration date time: {expire_str}.\n"
                f"User message sending date time: {now_str}.\n"
                f"User's remaining traffic: {traffic_account}.\n"
                "Always address the user by name to maintain friendliness.\n"

                "⚠️ PRIMARY OVERRIDE RULE:"
                "If the user’s message contains “how”, “چجوری”, “چطور”, “please explain”, or similar or expresses confusion about performing the current step,"
                "IMMEDIATELY stop all progress."
                "Do NOT mention any new step or sub_step."
                "ONLY explain the currently active step in simple, practical terms (with examples or emojis)."

                # "At the beginning of the message, acknowledge the user's issues and explain that the following steps or sub_steps must be followed to resolve the problem.\n"
                "💡 **LTE Troubleshooting Logic (based on previous task analysis):**\n"
                "🔍 **Response Logic:**\n"
                "- If `support -> analysis -> next_step_data` is a **JSON object** (representing the next step/sub_step),\n"
                "  → Use its `description` and `next_action` to form a clear, friendly instruction for the user.\n"
                "  → If available, refer to its `name` in a natural way (e.g., 'الان مرحله بررسی VPN رو انجام بدیم').\n"
                "- If `support.analysis.next_step_data` is a **string** (e.g., 'close_case', 'end_task', 'await_operator_response'),\n"
                "  → Respond based on that instruction directly:\n"
                "    • For `close_case`: Tell the user the problem seems resolved and the case is closing.\n"
                "    • For `end_task`: Summarize what was done and close politely.\n"
                "    • For `await_operator_response`: Tell them an operator will review it soon.\n\n"


                "🎯 **Response Guidelines:**\n"
                "- Respond in a friendly and educational way.\n"
                "- Base your message strictly on the active step’s `description` and `next_action`.\n"
                "- Only guide one step or sub_step per response.\n"
                "- Avoid repeating previous AI sentences.\n"
                "- Do not include greetings, small talk, or jokes.\n\n"

                "🎯 Goal: Generate a structured summary of the user's LTE network status for automated troubleshooting.\n"
                "⚠️ Step determination must consider last_ai_message and user_message.\n"
                "⚠️ Avoid repeating sentences from last_ai_message.\n"
                "⚠️Prohibited: greetings, small talk, self-introduction, jokes.\n"
                f"{OUTPUT_HTML}"
            ),
            agent=LTE_support_Analyst,
            expected_output="Raw HTML text",
        )


def update_json_support_task(state):
    user_message = state["input"]
    last_ai_message = None
    for msg in reversed(state.get("messages", [])):
        if msg.get("role") == "assistant":
            last_ai_message = msg.get("content")
            break
    status_account = list(state["userInfo"]["selectAccount"].keys())[-1]
    support = state["userInfo"]["support"]
    print("userInfo support is", support)
    if isinstance(support, list):
        support = next((item for item in support if item["status"] == status_account), None)
    print("status account isss", support)
    return Task(
        description=(
            f"User message: {user_message}\n"
            f"Last AI message: {last_ai_message}\n"
            f"User account status: {status_account}\n"
            "Task: Update Online Internet Troubleshooting JSON\n"
            f"JSON to be modified if needed: {support}\n\n"

            "You are an AI assistant that only updates the JSON representing online internet troubleshooting steps. Your task is:\n"
            "Your instructions are based on the user's account status, which is: {status_account}\n\n"

            "One: step for find updated_step:\n"
            "  1. If **all steps and sub_steps are `checked=false`** AND the user's message does not reference any step or sub_step, then:\n"
            "       - Set `updated_step = 'no_change'`\n"
            "       - Set `next_step_data` to the **first step in the JSON** (regardless of `checked` status)\n"
            "2. **Find the current active step:**\n"
            "   - Search recursively through the `steps` and their `sub_steps` in the provided JSON.\n"
            "   - The **very first** step or sub_step found with `checked == false` is the 'active step'.\n"
            "   - If no `checked == false` is found (all steps are done), DO NOT modify anything and return 'no-change'.\n\n"
            "   - If **no unchecked step** exists, return 'no-change'.\n\n"

            "3. **Analyze the user's response for the 'active step':**\n"
            "   - Use `last_ai_message` (what AI asked) and `user_message` (user's answer) and next_action (in support json), to understand the context of this 'active step'.\n"
            "   - **Crucially:** Decide if the user's answer means the step is **successfully completed** or resolved.\n"
            "   - If the user's message seems unrelated to the 'active step', DO NOT modify the JSON.\n\n"
            "   - You may temporarily store the currently detected path (like `both_up`, `internal_ok_external_fail`, etc.) in a helper field called `current_route` **only within that active step** to help future decision logic.\n"

            "🚦 4. Consider `next_action` in your reasoning:**\n"
            "   - Use the logical conditions inside `next_action` to determine completion.\n"
            "   - For example: if `next_action` contains `IF vpn_on THEN ask_turn_off_vpn ELSE go_step_2` and the user says 'خاموشه' (VPN is off), you can infer that the ELSE path applies (go to next step) → mark the current step as `checked=true`.\n"
            "   - Similarly, if `next_action` contains conditions like `IF modem_on`, `IF ping_ok`, or `IF problem fixed`, compare the user's message to the logical expression to decide whether this step is resolved.\n"
            "   - Only update `checked=true` when the user's message satisfies the condition that leads to progress (e.g., 'go_step_X', 'close_case', etc.).\n\n"

            "5. **Update the JSON based on the analysis:**\n"
            "   - **IF** the user's answer confirms the step is **complete** (e.g., AI asked about VPN, user said 'خاموشه' [It's off], which resolves this step):\n"
            "     - Set `checked = true` for this 'active step'.\n"
            "   - **ELSE IF** the user's answer indicates the step is **not complete** (e.g., AI asked about VPN, user said 'روشنه' [It's on], which is a problem that needs addressing):\n"
            "     - Do **NOT** modify the JSON. Keep `checked = false` so the assistant can handle this state.\n\n"

            "6. **Re-check Rule (Important):**\n"
            "   - If the user's message *clearly* indicates a problem related to a step that was *already* `checked=true` (e.g. 'فکر کنم VPN دوباره روشن شد'), set that specific step (or sub_step) back to `checked=false` and return the JSON.\n\n"
            "   - **Critical Constraint:** A failing result in the current step (e.g., Ping test failing) must NOT automatically reset a previous successful step (e.g., VPN check) unless the user explicitly mentions the previous step's related issue.\n\n"
            "7.In the final output, return only the name of the step or sub_step that was updated (i.e., whose checked value changed from false to true or from true to false).\n"
            "If no change was made to any step, return the string 'no_change'.\n"
            "Do not return the full JSON or any other fields — output must contain only the relevant name or.\n\n"

            # "## Logic Example (VPN Check - Step 1 for 'online' status):\n"
            # "-   **Context:** `last_ai_message` asks about VPN. 'Active step' is `vpn_check` (`checked=false`).\n"
            # "-   **User says:** 'خاموشه' (It's off) or 'نه' (No) or 'خاموش کردم' (I turned it off).\n"
            # "-   **Action:** This resolves the step. Set `vpn_check` -> `checked = true`.\n"
            # "-   **User says:** 'روشنه' (It's on) or 'بله' (Yes) or 'نمیدونم' (I don't know).\n"
            # "-   **Action:** This step is *not* resolved. Keep `vpn_check` -> `checked = false`.\n\n"

            "Two: step analysis :\n"
            "⚙️ **Dynamic Step Determination Logic:**\n"
            "- Determine the path based on the user’s account status (online or offline).\n"
            "- Find the **last step or sub_step where `checked=true`**.\n"
            "- Read its `next_action` to identify which step/sub_step should execute next.\n"
            "- If no `checked=true` step exists, start from step 1.\n"
            "- Under no circumstances should steps or sub-steps with checked=true be selected.\n"
            "- Use both `next_action` logic and the user’s message to confirm the correct next path.\n"
            "- Always respond according to the `description` and `next_action` of the determined next step/sub_step.\n\n"
            "- if next_action 'go_step_5' must be return all data of step:5 not just go_step_5"
            "⚙️ **Special Handling Rules:**\n"
            "- When analyzing the user's message, **always check sub_steps conditions (`user_says_external_sites_down`, `user_says_internal_sites_down`, etc.)** and follow the corresponding `next_action`."
            "- If a sub_step's `next_action` points to a step (like `go_step_5`), return that step as `next_step_data` **instead of staying in the current step**."
            "- If the `next_action` of the last completed step points to a specific step/sub_step (like `go_step_4` or `go_to_sub_step_3`), follow that exact target as the next active point.\n"
            "- If the `next_action` indicates a final action (`end_task`, `close_case`, `await_operator_response`), perform that and stop progression.\n"
            "- If no clear next target exists, revert to the first `checked=false` step (or sub_step) within the same flow branch and continue from there.\n\n"
            "- Never send null. If user message matches a sub_step condition that leads to a `go_step_X` or final action, **return the target step/sub_step indicated in next_action**."
            "🧩 **Output Example:**\n"
            "{\n"
            "     \"updated_step\": \"<name of step/sub_step that changed or 'no_change'>\",\n"
            "     \"next_step_data\": <either full step data if go_step_X or first step if updated_step: no_change, or a text like 'close_case'>\n"
            "  }\n"
            "- Do not include any explanations, messages, or text outside the valid Jason in Python.\n"
            "⚠️ The output must contain only JSON data without any extra text."
            "Output Rules:"
            "1. Correct all issues to produce ** valid JSON **."
            "2. Ensure ** all strings use double quotes **."
            "3. Ensure ** all boolean values are lowercase ** (`true` / `false`)."
            "4.Output ** only the corrected JSON **, nothing else."

        ),

        agent=update_json_support_agent,
        expected_output="Only valid JSON in Python with keys updated_step and next_step_data"

    )

# def update_json_support_task(state):
#     user_message = state["input"]
#     last_ai_message = None
#     for msg in reversed(state.get("messages", [])):
#         if msg.get("role") == "assistant":
#             last_ai_message = msg.get("content")
#             break
#     status_account = list(state["userInfo"]["selectAccount"].keys())[-1]
#
#     with open("assets/json/support.json", "r", encoding="utf-8") as f:
#         support = json.load(f)
#
#     print("assets/json/support.json is", support)
#     if isinstance(support, list):
#         support = next((item for item in support if item["status"] == status_account), None)
#     print("status account isss", support)
#     return Task(
#         description=(
#             f"User message: {user_message}\n"
#             f"Last AI message: {last_ai_message}\n"
#             f"User account status: {status_account}\n"
#             "Task: Update Online Internet Troubleshooting JSON\n"
#             f"JSON to be modified if needed: {support}\n\n"
#
#             "You are an AI assistant that only updates the JSON representing online internet troubleshooting steps. Your task is:\n"
#             "Your instructions are based on the user's account status, which is: {status_account}\n\n"
#
#             "One: step for find updated_step:\n"
#             "  1. If **all steps and sub_steps are `checked=false`** AND the user's message does not reference any step or sub_step, then:\n"
#             "       - Set `updated_step = 'no_change'`\n"
#             "       - Set `next_step_data` to the **first step in the JSON** (regardless of `checked` status)\n"
#             "2. **Find the current active step:**\n"
#             "   - Search recursively through the `steps` and their `sub_steps` in the provided JSON.\n"
#             "   - The **very first** step or sub_step found with `checked == false` is the 'active step'.\n"
#             "   - If no `checked == false` is found (all steps are done), DO NOT modify anything and return 'no-change'.\n\n"
#             "   - If **no unchecked step** exists, return 'no-change'.\n\n"
#
#             "3. **Analyze the user's response for the 'active step':**\n"
#             "   - Use `last_ai_message` (what AI asked) and `user_message` (user's answer) and next_action (in support json), to understand the context of this 'active step'.\n"
#             "   - **Crucially:** Decide if the user's answer means the step is **successfully completed** or resolved.\n"
#             "   - If the user's message seems unrelated to the 'active step', DO NOT modify the JSON.\n\n"
#             "   - You may temporarily store the currently detected path (like `both_up`, `internal_ok_external_fail`, etc.) in a helper field called `current_route` **only within that active step** to help future decision logic.\n"
#
#             "🚦 4. Consider `next_action` in your reasoning:**\n"
#             "   - Use the logical conditions inside `next_action` to determine completion.\n"
#             "   - For example: if `next_action` contains `IF vpn_on THEN ask_turn_off_vpn ELSE go_step_2` and the user says 'خاموشه' (VPN is off), you can infer that the ELSE path applies (go to next step) → mark the current step as `checked=true`.\n"
#             "   - Similarly, if `next_action` contains conditions like `IF modem_on`, `IF ping_ok`, or `IF problem fixed`, compare the user's message to the logical expression to decide whether this step is resolved.\n"
#             "   - Only update `checked=true` when the user's message satisfies the condition that leads to progress (e.g., 'go_step_X', 'close_case', etc.).\n\n"
#
#             "5. **Update the JSON based on the analysis:**\n"
#             "   - **IF** the user's answer confirms the step is **complete** (e.g., AI asked about VPN, user said 'خاموشه' [It's off], which resolves this step):\n"
#             "     - Set `checked = true` for this 'active step'.\n"
#             "   - **ELSE IF** the user's answer indicates the step is **not complete** (e.g., AI asked about VPN, user said 'روشنه' [It's on], which is a problem that needs addressing):\n"
#             "     - Do **NOT** modify the JSON. Keep `checked = false` so the assistant can handle this state.\n\n"
#
#             "6. **Re-check Rule (Important):**\n"
#             "   - If the user's message *clearly* indicates a problem related to a step that was *already* `checked=true` (e.g. 'فکر کنم VPN دوباره روشن شد'), set that specific step (or sub_step) back to `checked=false` and return the JSON.\n\n"
#             "   - **Critical Constraint:** A failing result in the current step (e.g., Ping test failing) must NOT automatically reset a previous successful step (e.g., VPN check) unless the user explicitly mentions the previous step's related issue.\n\n"
#             "7.In the final output, return only the name of the step or sub_step that was updated (i.e., whose checked value changed from false to true or from true to false).\n"
#             "If no change was made to any step, return the string 'no_change'.\n"
#             "Do not return the full JSON or any other fields — output must contain only the relevant name or.\n\n"
#
#             # "## Logic Example (VPN Check - Step 1 for 'online' status):\n"
#             # "-   **Context:** `last_ai_message` asks about VPN. 'Active step' is `vpn_check` (`checked=false`).\n"
#             # "-   **User says:** 'خاموشه' (It's off) or 'نه' (No) or 'خاموش کردم' (I turned it off).\n"
#             # "-   **Action:** This resolves the step. Set `vpn_check` -> `checked = true`.\n"
#             # "-   **User says:** 'روشنه' (It's on) or 'بله' (Yes) or 'نمیدونم' (I don't know).\n"
#             # "-   **Action:** This step is *not* resolved. Keep `vpn_check` -> `checked = false`.\n\n"
#
#             "Two: step analysis :\n"
#             "⚙️ **Dynamic Step Determination Logic:**\n"
#             "- Determine the path based on the user’s account status (online or offline).\n"
#             "- Find the **last step or sub_step where `checked=true`**.\n"
#             "- Read its `next_action` to identify which step/sub_step should execute next.\n"
#             "- If no `checked=true` step exists, start from step 1.\n"
#             "Under no circumstances should steps or sub-steps with checked=true be selected.\n"
#             "- Use both `next_action` logic and the user’s message to confirm the correct next path.\n"
#             "- Always respond according to the `description` and `next_action` of the determined next step/sub_step.\n\n"
#             "- if next_action 'go_step_5' must be return all data of step:5 not just go_step_5"
#             "⚙️ **Special Handling Rules:**\n"
#             "- If the `next_action` of the last completed step points to a specific step/sub_step (like `go_step_4` or `go_to_sub_step_3`), follow that exact target as the next active point.\n"
#             "- If the `next_action` indicates a final action (`end_task`, `close_case`, `await_operator_response`), perform that and stop progression.\n"
#             "- If no clear next target exists, revert to the first `checked=false` step (or sub_step) within the same flow branch and continue from there.\n\n"
#             "- Never send a null or empty value. If none of the rules are met, return the first step (by all item) that has checked=false."
#             "🧩 **Output Example:**\n"
#             "{\n"
#             "     \"updated_step\": \"<name of step/sub_step that changed or 'no_change'>\",\n"
#             "     \"next_step_data\": <either full step data if go_step_X or first step if updated_step: no_change, or a text like 'close_case'>\n"
#             "  }\n"
#
#
#             # "📘 **Examples:**\n"
#             # "- If user’s answer causes progress (e.g., VPN off):\n"
#             # "{\n"
#             # "  \"updated_json\": { ... },\n"
#             # "  \"analysis\": {\n"
#             # "    \"updated_step\": \"vpn_check\",\n"
#             # "    \"next_step_data\": {\n"
#             # "      \"step\": 2,\n"
#             # "      \"name\": \"ping_test\",\n"
#             # "      \"description\": \"Perform a network connectivity test...\",\n"
#             # "      \"checked\": false\n"
#             # "    }\n"
#             # "  }\n"
#             # "}\n\n"
#             # "- If user’s answer leads to closure (e.g., issue resolved):\n"
#             # "{\n"
#             # "  \"updated_json\": { ... },\n"
#             # "  \"analysis\": {\n"
#             # "    \"updated_step\": \"operator_network_check\",\n"
#             # "    \"next_step_data\": \"close_case\"\n"
#             # "  }\n"
#             # "}\n\n"
#
#             "- Do not include any explanations, messages, or text outside the valid Jason in Python.\n"
#             "⚠️ The output must contain only JSON data without any extra text."
#             "Output Rules:"
#             "1. Correct all issues to produce ** valid JSON **."
#             "2. Ensure ** all strings use double quotes **."
#             "3. Ensure ** all boolean values are lowercase ** (`true` / `false`)."
#             "4.Output ** only the corrected JSON **, nothing else."
#
#         ),
#
#         agent=update_json_support_agent,
#         expected_output="Only valid JSON in Python with keys updated_step and next_step_data"
#
#     )
