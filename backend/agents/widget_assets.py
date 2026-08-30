"""Widget client assets served by Django at /widget.js and /widget."""

WIDGET_JS = r"""(function () {
  "use strict";

  var script = document.currentScript;
  if (!script || !script.dataset || !script.dataset.agent) return;

  var agentKey = script.dataset.agent;
  var base = new URL(script.src).origin;
  var title = script.dataset.title || "Chat with us";
  var storageKey = "ai-agent-visitor-" + agentKey;
  var PRIMARY = "#4f46e5";

  function visitorId() {
    try {
      var v = sessionStorage.getItem(storageKey);
      if (v) return v;
      v = (window.crypto && crypto.randomUUID)
        ? crypto.randomUUID()
        : "v-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2);
      sessionStorage.setItem(storageKey, v);
      return v;
    } catch (e) {
      return "v-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2);
    }
  }

  var css = [
    "#ai-agent-widget{position:fixed;bottom:18px;right:18px;z-index:999999;font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;font-size:14px;line-height:1.45;--ai-primary:" + PRIMARY + "}",
    "#ai-agent-widget .ai-btn{width:56px;height:56px;border:0;border-radius:50%;background:var(--ai-primary);color:#fff;font-size:24px;cursor:pointer;box-shadow:0 6px 20px rgba(0,0,0,.25)}",
    "#ai-agent-widget .ai-panel{display:none;position:absolute;bottom:70px;right:0;width:340px;max-width:calc(100vw - 36px);height:440px;background:#fff;border-radius:12px;box-shadow:0 12px 40px rgba(0,0,0,.3);flex-direction:column;overflow:hidden}",
    "#ai-agent-widget.open .ai-panel{display:flex}",
    "#ai-agent-widget .ai-head{background:var(--ai-primary);color:#fff;padding:12px 14px;font-weight:600;display:flex;justify-content:space-between;align-items:center}",
    "#ai-agent-widget .ai-close{background:none;border:0;color:#fff;font-size:20px;cursor:pointer}",
    "#ai-agent-widget .ai-messages{flex:1;overflow-y:auto;padding:12px;display:flex;flex-direction:column;gap:6px}",
    "#ai-agent-widget .ai-bubble{max-width:80%;padding:8px 11px;border-radius:12px;white-space:pre-wrap;word-wrap:break-word}",
    "#ai-agent-widget .ai-bubble.user{align-self:flex-end;background:var(--ai-primary);color:#fff}",
    "#ai-agent-widget .ai-bubble.assistant{align-self:flex-start;background:#f1f5f9;color:#111}",
    "#ai-agent-widget .ai-bubble.ai-typing{color:#94a3b8}",
    "#ai-agent-widget .ai-form{display:flex;border-top:1px solid #e2e8f0;padding:8px}",
    "#ai-agent-widget .ai-input{flex:1;border:1px solid #cbd5e1;border-radius:8px;padding:8px 10px;margin-right:6px;font-size:14px}",
    "#ai-agent-widget .ai-form button{border:0;background:var(--ai-primary);color:#fff;border-radius:8px;padding:0 14px;cursor:pointer}"
  ].join("");
  var style = document.createElement("style");
  style.textContent = css;
  document.head.appendChild(style);

  var root = document.createElement("div");
  root.id = "ai-agent-widget";
  root.innerHTML =
    '<button type="button" class="ai-btn" aria-label="Chat">&#128172;</button>' +
    '<div class="ai-panel">' +
    '<div class="ai-head"><span class="ai-title">' + title + '</span><button type="button" class="ai-close" aria-label="Close">&times;</button></div>' +
    '<div class="ai-messages"></div>' +
    '<form class="ai-form"><input type="text" class="ai-input" placeholder="Type a message..." autocomplete="off" /><button type="submit" aria-label="Send">Send</button></form>' +
    "</div>";
  document.body.appendChild(root);

  var btn = root.querySelector(".ai-btn");
  var titleEl = root.querySelector(".ai-title");
  var messages = root.querySelector(".ai-messages");
  var form = root.querySelector(".ai-form");
  var input = root.querySelector(".ai-input");
  var welcome = "";
  var opened = false;

  function bubble(role, text) {
    var el = document.createElement("div");
    el.className = "ai-bubble " + role;
    el.textContent = text;
    messages.appendChild(el);
    messages.scrollTop = messages.scrollHeight;
  }

  function setColor(hex) {
    if (/^#[0-9a-fA-F]{3}$|^#[0-9a-fA-F]{6}$/.test(hex || "")) {
      root.style.setProperty("--ai-primary", hex);
    }
  }

  function showOpen() {
    opened = true;
    if (welcome && !messages.querySelector(".ai-bubble")) bubble("assistant", welcome);
    input.focus();
  }

  function loadConfig() {
    fetch(base + "/public/config/" + encodeURIComponent(agentKey))
      .then(function (r) { return r.json(); })
      .then(function (cfg) {
        var name = (cfg && cfg.agent && cfg.agent.name) || "";
        title = (cfg && cfg.title) || title;
        titleEl.textContent = title;
        if (cfg) setColor(cfg.primary_color);
        if (cfg && cfg.welcome_message) welcome = cfg.welcome_message;
        if (opened) showOpen();
      })
      .catch(function () {});
  }

  function loadHistory() {
    fetch(base + "/public/chat/" + encodeURIComponent(agentKey), {
      headers: { "X-Visitor-ID": visitorId() }
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data || !data.messages) return;
        (data.messages || []).forEach(function (m) {
          if (m.role === "user" || m.role === "assistant") bubble(m.role, m.content);
        });
      })
      .catch(function () {});
  }

  function send(text) {
    bubble("user", text);
    var typing = document.createElement("div");
    typing.className = "ai-bubble ai-typing";
    typing.textContent = "\u2026";
    messages.appendChild(typing);
    messages.scrollTop = messages.scrollHeight;
    input.value = "";
    input.disabled = true;

    fetch(base + "/public/chat/" + encodeURIComponent(agentKey), {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Visitor-ID": visitorId() },
      body: JSON.stringify({ message: text })
    })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, data: d }; }); })
      .then(function (r) {
        typing.remove();
        if (r.ok && r.data.message) bubble("assistant", r.data.message);
        else bubble("assistant", r.data.detail || "Something went wrong. Please try again.");
      })
      .catch(function () { typing.remove(); bubble("assistant", "Could not reach the chat service. Please try again."); })
      .finally(function () { input.disabled = false; input.focus(); });
  }

  btn.addEventListener("click", function () {
    root.classList.toggle("open");
    if (root.classList.contains("open")) {
      showOpen();
      if (!messages.querySelector(".ai-bubble")) loadHistory();
    }
  });
  root.querySelector(".ai-close").addEventListener("click", function () {
    root.classList.remove("open");
  });
  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var text = input.value.trim();
    if (text) send(text);
  });

  loadConfig();
})();
"""

WIDGET_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>AI Agent Widget Demo</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 640px; margin: 40px auto; padding: 0 16px; color: #111; }
    input { width: 100%; padding: 10px; font-size: 14px; margin: 8px 0; box-sizing: border-box; }
    button { padding: 10px 16px; cursor: pointer; }
    .hint { color: #666; font-size: 13px; }
    code { background: #f1f5f9; padding: 1px 5px; border-radius: 4px; }
  </style>
</head>
<body>
  <h1>AI Agent Widget Demo</h1>
  <p>Create a <b>website</b> deployment for one of your agents, then paste its
     <code>public_identifier</code> below. The chat button appears bottom-right.
     Open DevTools &rarr; Network to watch the <code>POST /public/chat/&#123;key&#125;</code> request.</p>
  <input id="key" placeholder="pub_xxxxxxxxxxxxxxxxxxxxx" autocomplete="off">
  <button id="launch" type="button">Open chat</button>
  <script>
    function boot(key) {
      var s = document.createElement("script");
      s.src = location.origin + "/widget.js";
      s.setAttribute("data-agent", key);
      s.setAttribute("data-title", "Receptionist");
      document.head.appendChild(s);
    }
    document.getElementById("launch").addEventListener("click", function () {
      var key = document.getElementById("key").value.trim();
      if (key) boot(key);
    });
  </script>
</body>
</html>
"""