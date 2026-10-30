document.addEventListener("DOMContentLoaded", function () {
  const bubble = document.createElement("div");
  bubble.id = "llm-chat-bubble";
  bubble.innerHTML = "💬";
  document.body.appendChild(bubble);

  const panel = document.createElement("div");
  panel.id = "llm-chat-panel";
  panel.style.display = "none";
  panel.innerHTML = `
    <div id="llm-chat-header">
      <span>Ask us anything</span>
      <span id="llm-chat-close">&times;</span>
    </div>
    <div id="llm-chat-messages"></div>
    <div id="llm-chat-input-row">
      <input type="text" id="llm-chat-input" placeholder="Type a question..." />
      <button id="llm-chat-send">Send</button>
    </div>
  `;
  document.body.appendChild(panel);

  const messagesEl = panel.querySelector("#llm-chat-messages");
  const inputEl = panel.querySelector("#llm-chat-input");
  const sendBtn = panel.querySelector("#llm-chat-send");
  const closeBtn = panel.querySelector("#llm-chat-close");

  function addMessage(text, who) {
    const msg = document.createElement("div");
    msg.className = "llm-chat-msg llm-chat-msg-" + who;
    msg.textContent = text;
    messagesEl.appendChild(msg);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function toggle() {
    const open = panel.style.display !== "none";
    panel.style.display = open ? "none" : "flex";
    if (!open && !messagesEl.hasChildNodes()) {
      addMessage("Hi! Ask me about our products.", "bot");
    }
  }

  bubble.addEventListener("click", toggle);
  closeBtn.addEventListener("click", toggle);

  async function send() {
    const question = inputEl.value.trim();
    if (!question) return;
    addMessage(question, "user");
    inputEl.value = "";
    sendBtn.disabled = true;
    addMessage("...", "bot-typing");

    try {
      const res = await fetch("/llm_chat/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ jsonrpc: "2.0", method: "call", params: { question: question } }),
      });
      const data = await res.json();
      const typing = messagesEl.querySelector(".llm-chat-msg-bot-typing");
      if (typing) typing.remove();
      addMessage((data.result && data.result.answer) || "Sorry, I couldn't get an answer.", "bot");
    } catch (e) {
      const typing = messagesEl.querySelector(".llm-chat-msg-bot-typing");
      if (typing) typing.remove();
      addMessage("Sorry, something went wrong.", "bot");
    } finally {
      sendBtn.disabled = false;
    }
  }

  sendBtn.addEventListener("click", send);
  inputEl.addEventListener("keydown", function (e) {
    if (e.key === "Enter") send();
  });
});
