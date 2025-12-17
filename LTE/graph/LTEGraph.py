from general.state_manager import save_state
import re
from LTE.task.LTETask import create_problem_list_task, get_assistant_account_user, create_json_account_task, \
    get_assistant_ask_witch_account, extract_select_account_task, get_assistant_ask_problem, LTE_detect_task, \
    update_json_support_task
import asyncio
from socket_instance import sio
from general.State import ChatState
from general.tools import run_task_as_crew, create_message, parse_json5, add_item_to_support_json, add_item_to_json,get_last_intent
from apis.apis import customer_search, customer_info
from apis.apis import execute_stored_procedure_support

import json


async def handle_ask_problem(state: ChatState) -> ChatState:
    print("handle problem ask")
    response = get_assistant_ask_problem(state)
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


async def handle_problem_list(state: ChatState) -> ChatState:
    print("handle problem list")
    user_input = state["input"]
    task = create_problem_list_task(user_input)
    result = run_task_as_crew(task)
    response = result.raw.strip()
    problems = parse_json5(response)
    state["userInfo"]['problems'].extend(problems)
    save_state(state)

    # response = re.sub(r"^```html\s*|\s*```$", "", response).strip()
    # message = create_message('assistant', response)
    # state["messages"].append(message)
    # asyncio.create_task(sio.emit("room_mehdi", message, room="mehdi"))
    if (state['intents'] != []):
        state['intents'].pop()
    lastIntent=get_last_intent(state)
    print("get_last_intent in problems>>",get_last_intent)
    if (lastIntent == ""):
        if (state['userInfo']["service_support"] == ""):
            state['next_node'] = "question_service_support"
        else:
            if (state['userInfo']['accountInfo'] == {}):
                state['next_node'] = 'get_info_account'

            elif (state['userInfo']['selectAccount'] == []):
                state['next_node'] = 'ask_witch_account'

            elif (state['userInfo']['problems'] == []):
                state['next_node'] = "ask_problem"
            else:
                state['next_node'] = "update_json_support"
    else:
        state['next_node']  = get_last_intent(state)
    save_state(state)
    return state


async def handle_get_account_user(state: ChatState) -> ChatState:
    print("handle get_account_user")
    response =  get_assistant_account_user(state)
    response = re.sub(r"^```html\s*|\s*```$", "", response).strip()
    message = create_message('assistant', response)
    state["messages"].append(message)
    # room = state["token"]
    # asyncio.create_task(sio.emit(f"room_{room}", message, room=room))
    if (state['intents'] != []):
        state['intents'].pop()

    state['next_node'] = "extract_json_account"
    save_state(state)
    return state


async def handle_json_account(state: ChatState) -> ChatState:
    print("handle json_account")
    task = create_json_account_task(state)
    result = run_task_as_crew(task)
    response = result.raw.strip()
    info = parse_json5(response)
    print("user info  is>>", info)
    # --- منطق ادغام (merge) ---
    # old_info = state["userInfo"].get("accountInfo", {})
    # merged_info = {}
    #
    # for key in ["lastname", "username", "mobile", "melicode"]:
    #     new_value = info.get(key)
    #     old_value = old_info.get(key, "")
    #
    #     # اگر مقدار جدید معتبر نیست (خالی یا None)، مقدار قبلی حفظ شود
    #     if new_value is None or str(new_value).strip() == "":
    #         merged_info[key] = old_value
    #     else:
    #         merged_info[key] = new_value

    # مقدار نهایی را در state ذخیره می‌کنیم
    state["userInfo"]["accountInfo"] = info
    print("user info json is>>", state["userInfo"]['accountInfo'])
    if (state['intents'] != []):
        state['intents'].pop()

    state['next_node'] = "ask_witch_account"
    save_state(state)
    return state


async def handle_ask_witch_account(state: ChatState) -> ChatState:
    print("handle ask_witch_account")
    service=state.get("userInfo")["service_support"]
    # if(service.lower() == "adsl"):
    #     username = state.get("userInfo", {}).get("accountInfo", {}).get("username", "")
    #     username = username.lstrip("0")
    #     print('username is>>', username)
    #     result = execute_stored_procedure_support('Robo_User', [username])
    # else:
    result = await customer_search(state['userInfo']['accountInfo'], )
    # print("state['userInfo']['accountInfo']", state['userInfo']['accountInfo'])
    # print("result ['accountInfo']",result)
    print("result ['accountInfo']", result)
    accounts = []
    if (result['result'] == True):
        accounts.append(result['list'])
    state["userInfo"]['accounts'] = accounts
    print('accounts is>>', accounts)
    save_state(state)
    btns = None
    if (len(accounts) > 0):
        btns = [f"شماره حساب {i}" for i in range(1, len(accounts[0]) + 1)]
    response =  get_assistant_ask_witch_account(state,btns)
    response = re.sub(r"^```html\s*|\s*```$", "", response).strip()


    message = create_message('assistant', response, btns)
    state["messages"].append(message)
    save_state(state)
    # room = state["token"]
    # asyncio.create_task(sio.emit(f"room_{room}", message, room=room))
    if (state['intents'] != []):
        state['intents'].pop()

    state['next_node'] = "extract_select_account"
    save_state(state)
    return state


async def handle_extract_select_account(state: ChatState) -> ChatState:
    print("handle extract_select_account")
    task = extract_select_account_task(state)
    result = run_task_as_crew(task)
    response = result.raw.strip()
    select = parse_json5(response)
    if (len(select) == 0):
        state['next_node'] = "ask_witch_account"
        save_state(state)
    else:
        select = select[-1]
        print('account selection is>>', select)
        print('account selection is pppoe_username>>', select['pppoe_username'])
        info = await customer_info(username=select['pppoe_username'])
        state["userInfo"]['selectAccount'] = info
        save_state(state)
        with open("assets/json/support_main.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        # with open("assets/json/support.json", "w", encoding="utf-8") as f:
        #     json.dump(data, f, ensure_ascii=False, indent=2)

        state["userInfo"]["support"] = data
        state["userInfo"]["next_step_support"] = {}
        save_state(state)
        if (state['intents'] != []):
            state['intents'].pop()
        if (state['userInfo']['problems'] == []):
            state['next_node'] = "ask_problem"
        else:
            state['next_node'] = "update_json_support"
    save_state(state)
    return state


def check_step_by_name(steps, target_name):
    for step in steps:
        if step.get("name") == target_name:
            step["checked"] = True
        # بررسی sub_steps به صورت بازگشتی
        sub_steps = step.get("sub_steps", [])
        if sub_steps:
            check_step_by_name(sub_steps, target_name)
    return steps


async def handle_update_json_support_task(state: ChatState) -> ChatState:
    print("handle update_json_support_task")
    task = update_json_support_task(state)
    result = run_task_as_crew(task)
    d = result.raw.strip()

    print('update_json_support is>>', d)
    # data = json.loads(d)
    data = parse_json5(d)

    # with open("assets/json/support.json", "r", encoding="utf-8") as f:
    #     s = json.load(f)
    s = state["userInfo"]["support"]
    print("data issssssssss >>", data)
    if (len(state["userInfo"]["selectAccount"]) < 1):
        if (len(state["userInfo"]["accountInfo"]) < 1):
            state['next_node'] = "get_info_account"
            save_state(state)
        else:
            state['next_node'] = "ask_witch_account"
            save_state(state)
    else:
        status_account = list(state["userInfo"]["selectAccount"].keys())[-1]
        if isinstance(s, list):
            s = next((s for s in s if s["status"] == status_account), None)
        s["steps"] = check_step_by_name(s["steps"], data['updated_step'])

        print('analysis is>>', data['next_step_data'])

        # with open("assets/json/support.json", "w") as file:
        #     json.dump(s, file, indent=4)

        state["userInfo"]["support"] = s,
        state["userInfo"]["next_step_support"] = data['next_step_data'],

        save_state(state)
        next_step_data = data.get('next_step_data')

        if (isinstance(next_step_data, dict) and next_step_data.get("step") == 5) \
                or isinstance(next_step_data, str):
            item = {
                "token": state.get("token", ""),
                "selectAccount": state.get("userInfo", {}).get("selectAccount", {}),
                "problems": state.get("userInfo", {}).get("problems", []),
                "user_message": state.get("input", "")
            }
            add_item_to_support_json('output/supports.json', item)
        # with open("assets/json/next_step_support.json", "w") as file:
        #     json.dump(data['next_step_data'], file, indent=4)

        state['next_node'] = "LTE_detect"
    save_state(state)
    return state


async def handle_LTE_detect(state: ChatState) -> ChatState:
    print("handle LTE_detect")
    task = LTE_detect_task(state)
    result = run_task_as_crew(task)
    response = result.raw.strip()
    response = re.sub(r"^```html\s*|\s*```$", "", response).strip()
    message = create_message('assistant', response)
    state["messages"].append(message)
    room = state["token"]
    asyncio.create_task(sio.emit(f"room_{room}", message, room=room))
    asyncio.create_task(sio.emit("room_e3740a54-9912-4e70-8b73-8cb23fc3c6e4", message, room=room))

    if (state['intents'] != []):
        state['intents'].pop()

    state['next_node'] = ""
    save_state(state)
    return state
