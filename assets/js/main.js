const socket = io("/", {transports: ["websocket"]});

// function sendMessage(textMessage) {
//     socket.emit("message", {room: roomId, msg: textMessage});
// }
$(document).ready(function () {

    socket.on("connect", () => {
        console.log("✅ Connected:", socket.id);
        // پیوستن به Room
        socket.emit("join", {room: roomId});
    });

    socket.on(`room_${roomId}`, (data) => {
        console.log("data>>>:", data)
        if (data.role == 'assistant') {
            // if(data.buttons){
            addAIMessage(data);
            // }else{
            // addAIMessage(data.content);
            // }
        } else {
            addUserMessage(data.content);
        }
    });

})