/* ===== jQuery Version ===== */
$(document).on("click", "#de_18c9a260-01d0-948c-b5e6-0c71ac4197ee", function () {
    $("#de_6960c6c2-00f9-5f01-8979-e343ed720b2a").toggleClass("hide_element");
});

$(document).on("click", "#de_4f31eeb1-ad1d-7e82-f7bb-802a08b02b14", function () {
    // $("#de_f39355d2-98f9-a165-8a62-ddc2cca51973").removeClass("hide_element");
});

$(document).on("click", "#de_c41a807a-7839-9017-ce80-ed220a1af4a6", function () {
    $("#de_f39355d2-98f9-a165-8a62-ddc2cca51973").addClass("hide_element");
});


$(document).on("click", "#de_1c3750c5-b482-0080-d645-38019119bd99", function () {
    const $body = $("body");
    if ($body.hasClass("light")) {
        $body.removeClass("light").addClass("dark");
    } else if ($body.hasClass("dark")) {
        $body.removeClass("dark").addClass("light");
    }
});

$(document).on("click", "#de_9211e9a9-f9b9-6eba-ff98-242a79cec4be", function () {
    $("#de_5dd24054-4f1c-53c3-e607-be38dddad2ff").removeClass("hide_element_mobile_device");
});

$(document).on("click", "#de_0ab70a99-8ba8-0a70-64ad-77a9b963af51", function () {
    $("#de_5dd24054-4f1c-53c3-e607-be38dddad2ff").addClass("hide_element_mobile_device");
});

$(document).on("click", "#de_d2afc18e-5641-c738-57ad-6b49cbac85c7", function () {
    $("#de_533f55e7-c509-aae4-c8f9-bbb95ba80c2b").removeClass("hide_element");
    $("#de_f2ba296d-cbcb-437e-b90e-6f400842e018").addClass("hide_element");
    $("#de_b4f3b2f3-fa7d-444f-04f5-ff0b2d0dc658").addClass("hide_element");
    $("#de_5dd24054-4f1c-53c3-e607-be38dddad2ff").addClass("hide_element_mobile_device");
});

$(document).on("click", ".suggestions", function () {
    $("#de_b4f3b2f3-fa7d-444f-04f5-ff0b2d0dc658").removeClass("hide_element");
    $("#de_f2ba296d-cbcb-437e-b90e-6f400842e018").addClass("hide_element");
    $("#de_533f55e7-c509-aae4-c8f9-bbb95ba80c2b").addClass("hide_element");
});

$(document).on("click", "#de_de30249a-0bdc-732a-6b19-b3a7a086577d", function () {
    $("#de_b4f3b2f3-fa7d-444f-04f5-ff0b2d0dc658").addClass("hide_element");
    $("#de_f2ba296d-cbcb-437e-b90e-6f400842e018").removeClass("hide_element");
    $("#de_533f55e7-c509-aae4-c8f9-bbb95ba80c2b").addClass("hide_element");
    $("#de_5dd24054-4f1c-53c3-e607-be38dddad2ff").addClass("hide_element_mobile_device");
});

function addUserMessage(messageText) {
    // آی‌دی المنت مقصد
    const targetId = "de_b4f3b2f3-fa7d-444f-04f5-ff0b2d0dc658";

    // ساخت ساختار HTML با jQuery
    const messageElement = $(`
    <div class="de_element user_message_box">
      <div class="de_element paddingChat user_message">
        <div class="de_element paddingChat user_message_text">
          <span>${messageText}</span>
        </div>
      </div>
    </div>
  `);

    // اضافه کردن به المنت مقصد
    $("#" + targetId).append(messageElement);
    addAILoading();
}
const typingQueues = {};
const isTyping = {};
let activeSendMessage = false; // وضعیت ارسال پیام

// ------------------------------------------------------
// 🔥 تابع اصلی تایپ HTML (کاراکتر به کاراکتر)
// ------------------------------------------------------
function typeHTML(uuid, span, speed = 30, instant = false) {
    if (isTyping[uuid]) return;
    isTyping[uuid] = true;

    const queue = typingQueues[uuid] || [];
    let currentChunkIndex = 0;

    function nextChunk() {
        if (currentChunkIndex >= queue.length) {
            isTyping[uuid] = false;
            activeSendMessage = true; // بعد از نمایش پیام
            return;
        }

        const htmlString = queue[currentChunkIndex];
        currentChunkIndex++;

        const wrapper = document.createElement("div");
        wrapper.innerHTML = htmlString;
        const nodes = Array.from(wrapper.childNodes);
        let nodeIndex = 0;

        function nextNode() {
            if (nodeIndex >= nodes.length) {
                nextChunk();
                return;
            }

            processNode(nodes[nodeIndex], span, () => {
                nodeIndex++;
                nextNode();
            }, instant); // ارسال حالت فوری
        }

        nextNode();
    }

    if (instant) {
        // نمایش فوری کل محتوا
        span.innerHTML = queue.join("");
        isTyping[uuid] = false;
        activeSendMessage = true;
    } else {
        nextChunk();
    }
}

// ------------------------------------------------------
// تابع کمکی: پردازش هر نود (متن یا عنصر)
// ------------------------------------------------------
function processNode(node, parent, callback, instant = false) {
    if (node.nodeType === Node.TEXT_NODE) {
        const text = node.textContent;
        if (instant) {
            parent.append(text);
            callback();
            return;
        }

        let i = 0;
        function typeChar() {
            if (i < text.length) {
                parent.append(text[i]);
                i++;
                scrollToBottom();
                setTimeout(typeChar, 30);
            } else {
                callback();
            }
        }
        typeChar();

    } else if (node.nodeType === Node.ELEMENT_NODE) {
        const el = document.createElement(node.tagName);

        // کپی اتربیوت‌ها
        for (let attr of node.attributes) {
            el.setAttribute(attr.name, attr.value);
        }

        parent.appendChild(el);

        const children = Array.from(node.childNodes);
        let childIndex = 0;

        function nextChild() {
            if (childIndex >= children.length) {
                callback();
                return;
            }
            processNode(children[childIndex], el, () => {
                childIndex++;
                nextChild();
            }, instant);
        }

        nextChild();
    } else {
        callback();
    }
}

// ------------------------------------------------------
// تابع اضافه کردن پیام AI
// ------------------------------------------------------
function addAIMessage(data, instant = false) {

    $(".ai_loading_box").remove();
    if (typeof data === "string") {
        data = { content: data };
    }

    data.content = data.content || "";
    data.buttons = data.buttons || [];
    data.plans   = data.plans || null;
    data.counter = data.counter || 0;
    data.uuid    = data.uuid || ("msg_" + crypto.randomUUID());

    const targetId = "de_b4f3b2f3-fa7d-444f-04f5-ff0b2d0dc658";

    const existingMsg = $("#" + data.uuid);
    if (existingMsg.length) {
        const span = existingMsg.find(".stream_text")[0];
        typingQueues[data.uuid] = typingQueues[data.uuid] || [];

        if (data.content.trim() !== "") {
            typingQueues[data.uuid].push(data.content);
            typeHTML(data.uuid, span, 0, instant);
        }
        return;
    }

    const aiMessage = $(`
        <div class="de_element ai_message_box" id="${data.uuid}">
            <div class="de_element ai_message">
                <div class="de_element paddingChat ai_message_text">
                    <span class="stream_text" data-counter="${data.counter}"></span>
                </div>
            </div>
        </div>
    `);

    const hasButtons = data.buttons.length > 0;
    const hasPlans = !!data.plans;

    if (hasButtons || hasPlans) {
        const buttonBox = $('<div class="de_element paddingChat ai_inline_button_box"></div>');

        if (hasPlans) {
            const moreButton = $(`
                <div class="de_element chat_suggest ai_inline_button ask_ai"
                     data-plans="true"
                     data-target="${data.uuid}">
                    <span class="de_element ai_inline_button_text"><span>بیشتر</span></span>
                </div>
            `);
            moreButton.data("plansData", data.plans);
            buttonBox.append(moreButton);
        }

        data.buttons.forEach(btnText => {
            const button = $(`
                <div class="de_element chat_suggest ai_inline_button ask_ai" data-ask="${btnText}">
                    <span class="de_element ai_inline_button_text"><span>${btnText}</span></span>
                </div>
            `);
            buttonBox.append(button);
        });

        aiMessage.find(".ai_message").append(buttonBox);
    }

    $("#" + targetId).append(aiMessage);

    typingQueues[data.uuid] = typingQueues[data.uuid] || [];
    if (data.content.trim() !== "") {
        typingQueues[data.uuid].push(data.content);
        const span = aiMessage.find(".stream_text")[0];
        typeHTML(data.uuid, span, 30, instant); // instant = true → نمایش فوری
    }

    scrollToBottom();
}

function scrollToBottom() {
    const chatBox = $("#de_b4f3b2f3-fa7d-444f-04f5-ff0b2d0dc658");
    chatBox.scrollTop(chatBox[0].scrollHeight);
}

function addAILoading() {
    const targetId = "de_b4f3b2f3-fa7d-444f-04f5-ff0b2d0dc658";

    const loadingElement = $(`
    <div class="de_element ai_loading_box">
      <div class="de_element ai_loading">
        <p class="de_element paddingChat ai_loading_text">
          <span class="dot"></span>
          <span class="dot"></span>
          <span class="dot"></span>
        </p>
      </div>
    </div>
  `);

    $("#" + targetId).append(loadingElement);
    scrollToBottom();
}

function sendMessage(text = "") {
    if (text == "") {
        text = $("#message_input").val().trim();
    }
    if (activeSendMessage && text !== '') {
        activeSendMessage = false;
        $('#myButton').prop('disabled', true);
        socket.emit("message", {room: roomId, msg: text});
        $("#message_input").val("");
    }

}

// addAILoading();
activeSendMessage = true;
$(document).on('click', "#de_017c70ba-73ed-331e-46ab-c2170bea3093", function () {
    showChatBox();
    sendMessage();
})

function showChatBox() {

    $("#de_b4f3b2f3-fa7d-444f-04f5-ff0b2d0dc658").removeClass("hide_element");
    $("#de_f2ba296d-cbcb-437e-b90e-6f400842e018").addClass("hide_element");
    $("#de_533f55e7-c509-aae4-c8f9-bbb95ba80c2b").addClass("hide_element");
}

async function testDownloadSpeed(url, callback) {
    try {
        const startTime = performance.now();

        // جلوگیری از کش
        const cacheBuster = url.includes("?") ? "&t=" + Date.now() : "?t=" + Date.now();
        const response = await fetch(url + cacheBuster);

        if (!response.ok) throw new Error("خطا در دانلود فایل");

        const reader = response.body.getReader();
        let bytesReceived = 0;
        let done = false;

        while (!done) {
            const {value, done: streamDone} = await reader.read();
            if (value) bytesReceived += value.length;
            done = streamDone;
        }

        const endTime = performance.now();
        const duration = (endTime - startTime) / 1000; // ثانیه

        const sizeMb = (bytesReceived * 8) / (1024 * 1024); // مگابیت
        const speedMbps = (sizeMb / duration).toFixed(2);

        callback({
            success: true,
            speedMbps: speedMbps,
            duration: duration.toFixed(2),
            sizeMb: sizeMb.toFixed(2)
        });

    } catch (err) {
        callback({
            success: false,
            error: "❌ خطا در تست سرعت: " + err.message
        });
    }
}


$(document).on('keydown', '#message_input', function (e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
        showChatBox();
    }
});
$(document).on("click", ".ask_ai", function () {
    const isPlansButton = $(this).data("plans");
    const targetId = $(this).data("target");
    const askText = $(this).data("ask");
    const planType = $(this).data("planType"); // اضافه برای تشخیص طرح‌ها

    // ۱️⃣ دکمه بیشتر (نمایش طرح‌ها)
    if (isPlansButton) {
        const plansData = $(this).data("plansData");
        showPlans(plansData, targetId);
        return;
    }

    // ۲️⃣ اگر مربوط به یک plan بود → ارسال به API ثبت‌نام
    if (planType === "register") {

        addUserMessage(askText);
        // const uuid = window.userUUID || "test-uuid"; // فرض کن uuid رو از جایی داری
        const apiUrl = `https://aeye.shabakieh.com/register_plan/?need=${encodeURIComponent(askText)}&token=${roomId}`;

        // نمایش لودینگ یا پیام موقت
        console.log("در حال ارسال به:", apiUrl);

        fetch(apiUrl)
            .then(res => res.json())
            .then(data => {
                console.log("✅ نتیجه:", data);
                // addAIMessage(`✅ طرح "${askText}" با موفقیت ثبت شد.`);
            })
            .catch(err => {
                console.error("❌ خطا:", err);
                // addAIMessage(`❌ خطا در ثبت طرح "${askText}"`);
            });
        return;
    }

    // ۳️⃣ حالت پیش‌فرض: ارسال پیام عادی
    if (askText) {
        console.log(askText);
        sendMessage(askText);
    }
});
$(document).on('click', '.internet_test', function () {
    showChatBox();
    addUserMessage("تست سرعت");
    testDownloadSpeed("https://aeye.shabakieh.com/assets/download/20MB.file",
        function (result) {
            if (result.success) {
                addAIMessage(`✅ تست سرعت با موفقیت انجام شد.`);
                addAIMessage(`📶 سرعت اینترنت شما: ${result.speedMbps} Mbps`);
                addAIMessage(`⏱️ مدت زمان دانلود فایل: ${result.duration} ثانیه`);
                addAIMessage(`📦 حجم فایل تست: ${result.sizeMb} مگابیت`);
            } else {
                addAIMessage("❌ خطا در تست سرعت اینترنت. لطفاً دوباره تلاش کنید.");
                if (result.error) console.error("جزئیات خطا:", result.error);
            }
        }
    );
});

function showPlans(plans, targetId) {
    const plansBox = $('<div class="de_element plans_box"></div>');

    plans.forEach(planText => {
        const lines = planText.split('\n').filter(l => l.trim() !== '');
        let category = "", title = "", price = "";

        lines.forEach(line => {
            if (line.includes("دسته‌بندی")) category = line.substring(line.indexOf(":") + 1).trim();
            if (line.includes("عنوان")) title = line.substring(line.indexOf(":") + 1).trim();
            if (line.includes("قیمت")) price = line.substring(line.indexOf(":") + 1).trim();
        });

        if (title != '') {
            const card = $(`
            <div class="plan_card ask_ai" data-ask="${title}" data-plan-type="register">
                <div class="plan_line"><strong>دسته‌بندی:</strong> ${category}</div>
                <div class="plan_line title"><strong>عنوان:</strong> ${title}</div>
                <div class="plan_line"><strong>قیمت:</strong> ${price}</div>
            </div>
        `);
            plansBox.append(card);
        }


    });

    $("#" + targetId).find(".ai_message").append(plansBox);
    scrollToBottom();
}

