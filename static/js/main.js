const chatWindow = document.getElementById("chatWindow");
document.getElementById("askBtn").addEventListener("click", askAI);
document.getElementById("uploadBtn").addEventListener("click", uploadPDF);

function appendMessage(sender, text) {
    const div = document.createElement("div");
    div.classList.add("message");
    div.classList.add(sender === "user" ? "user-message" : "ai-message");
    div.innerText = text;
    chatWindow.appendChild(div);
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

async function uploadPDF() {
    const file = document.getElementById("pdfFile").files[0];
    if (!file) { alert("파일을 선택해주세요."); return; }

    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch("/upload", { method: "POST", body: formData });
    const data = await response.json();
    alert(data.message || data.error);
}

async function askAI() {
    const question = document.getElementById("question").value;
    if (!question) { alert("질문을 입력해주세요."); return; }

    appendMessage("user", question);

    // 답변 전 표시
    const loadingMsg = document.createElement("div");
    loadingMsg.className = "system-message";
    loadingMsg.innerText = "답변 중...";
    chatWindow.appendChild(loadingMsg);
    chatWindow.scrollTop = chatWindow.scrollHeight;

    const response = await fetch("/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ subject: "컴퓨터프로그래밍", question })
    });

    const data = await response.json();
    const answer = data.answer || data.error;

    // "답변 중..." 제거 후 AI 메시지 표시
    chatWindow.removeChild(loadingMsg);
    appendMessage("ai", answer);

    document.getElementById("question").value = "";
}

const sidebar = document.querySelector(".sidebar");
const chatArea = document.querySelector(".chat-area"); // 메인 영역
const hamburger = document.getElementById("hamburger");


document.getElementById("hamburger").addEventListener("click", () => {
    sidebar.classList.toggle("collapsed");

    if (sidebar.classList.contains("collapsed")) {
        chatArea.style.width = "100%";
    } else {
        chatArea.style.width = "calc(100% - 250px)"; // 사이드바 원래 너비
    }
});

document.getElementById("paperSearchToggle").addEventListener("change", (e) => {
    if (e.target.checked) {
        console.log("논문 기반 검색: ON");
    } else {
        console.log("논문 기반 검색: OFF");
    }
});

