const sections = ["checking", "pairing", "status"].map(id => document.querySelector(`#${id}`));
const [checking, pairing, statusPanel] = sections;
const pairForm = document.querySelector("#pair-form");
const pairError = document.querySelector("#pair-error");
const restartButton = document.querySelector("#restart");
const statusMessage = document.querySelector("#status-message");
const openAiConnect = document.querySelector("#openai-connect");
const openAiModels = document.querySelector("#openai-models");
const openAiMessage = document.querySelector("#openai-message");
const openAiDisconnect = document.querySelector("#openai-disconnect");
const openAiAccess = document.querySelector("#openai-access");
const subscriptionConnect = document.querySelector("#subscription-connect");
const subscriptionDisconnect = document.querySelector("#subscription-disconnect");
const subscriptionAuth = document.querySelector("#subscription-auth");
const subscriptionMessage = document.querySelector("#subscription-message");
const textAgent = document.querySelector("#text-agent");
const textResult = document.querySelector("#text-result");
const profileForm = document.querySelector("#profile");
const profileMessage = document.querySelector("#profile-message");
let csrfToken = "";
let subscriptionPolling = false;
let statusRetryTimer = 0;

function show(section) { for (const item of sections) item.hidden = item !== section; }

async function request(path, options = {}) {
  const response = await fetch(path, { credentials: "same-origin", ...options, headers: { Accept: "application/json", ...(options.headers || {}) } });
  const payload = await response.json().catch(() => ({}));
  return { response, payload };
}

function renderStatus(payload) {
  show(statusPanel);
  csrfToken = payload.csrfToken || csrfToken;
  const ready = payload.status === "ready";
  const state = document.querySelector("#runtime-state");
  state.className = `state ${ready ? "ready" : "error"}`;
  state.querySelector("span").textContent = ready ? "Ready" : "Needs attention";
  document.querySelector("#service").textContent = payload.service || "Unavailable";
  document.querySelector("#contract").textContent = payload.contractVersion ?? "—";
  document.querySelector("#migration").textContent = payload.database?.migrationVersion ?? "—";
  loadOpenAI();
  loadSubscription();
  loadProfile();
}

function fillSelect(select, values, selected, emptyLabel) {
  select.replaceChildren();
  if (!values.length) {
    const option = new Option(emptyLabel, ""); option.disabled = true; option.selected = true;
    select.add(option); return;
  }
  const labels = {
    "gpt-5.6-sol": "GPT-5.6 Sol",
    "gpt-5.6-terra": "GPT-5.6 Terra",
    "gpt-5.6-luna": "GPT-5.6 Luna",
    "gpt-live-1": "Live",
    "gpt-realtime-2.1": "Realtime 2.1",
    "gpt-realtime-2.1-mini": "Realtime 2.1 Mini",
  };
  for (const value of values) select.add(new Option(labels[value] || value, value, false, value === selected));
}

function renderOpenAI(payload) {
  const platformConnected = payload.connections?.platform ?? payload.connected;
  const subscriptionConnected = payload.connections?.subscription ?? false;
  const state = document.querySelector("#openai-state");
  state.className = `state ${payload.connected ? "ready" : ""}`;
  state.querySelector("span").textContent = payload.connected ? `Using ${payload.accessPath}` : "Not selected";
  openAiConnect.hidden = platformConnected;
  openAiDisconnect.hidden = !platformConnected;
  openAiAccess.hidden = !platformConnected && !subscriptionConnected;
  openAiModels.hidden = !payload.connected;
  textAgent.hidden = !payload.connected || !payload.selection?.text;
  const access = document.querySelector("#access-path");
  access.replaceChildren();
  if (platformConnected) access.add(new Option("OpenAI Platform API", "platform", false, payload.accessPath === "platform"));
  if (subscriptionConnected) access.add(new Option("ChatGPT / Codex subscription", "subscription", false, payload.accessPath === "subscription"));
  if (!payload.connected) return;
  fillSelect(document.querySelector("#realtime-model"), payload.models?.realtime || [], payload.selection?.realtime, "No Realtime model available");
  fillSelect(document.querySelector("#text-model"), payload.models?.text || [], payload.selection?.text, "Text unavailable in this build");
  document.querySelector("#reasoning-effort").value = payload.selection?.reasoning || "none";
}

async function loadProfile() {
  try {
    const { response, payload } = await request("/v1/management/profile");
    if (!response.ok) throw new Error(payload.error?.message || "Profile unavailable.");
    document.querySelector("#display-name").value = payload.displayName || "";
  } catch (error) { profileMessage.textContent = error.message; }
}

function renderSubscription(payload) {
  const state = document.querySelector("#subscription-state");
  state.className = `state ${payload.connected ? "ready" : ""}`;
  state.querySelector("span").textContent = payload.connected ? "Connected" : "Not connected";
  subscriptionConnect.hidden = payload.connected;
  subscriptionDisconnect.hidden = !payload.connected;
  if (payload.connected) {
    subscriptionPolling = false;
    subscriptionConnect.disabled = false;
    subscriptionAuth.hidden = true;
  }
}

async function loadSubscription() {
  try {
    const { response, payload } = await request("/v1/management/openai/subscription");
    if (!response.ok) throw new Error(payload.error?.message || "ChatGPT status unavailable.");
    renderSubscription(payload);
  } catch (error) { subscriptionMessage.textContent = error.message; }
}

async function loadOpenAI() {
  try {
    const { response, payload } = await request("/v1/management/openai");
    if (!response.ok) throw new Error(payload.error?.message || "OpenAI status unavailable.");
    renderOpenAI(payload);
  } catch (error) { openAiMessage.textContent = error.message; }
}

function retryStatus(attempt) {
  show(checking);
  checking.querySelector("h2").textContent = "Starting this R1…";
  checking.querySelector(".support").textContent = "Device management is available. The on-device runtime is starting.";
  window.clearTimeout(statusRetryTimer);
  statusRetryTimer = window.setTimeout(() => loadStatus(attempt + 1), 1000);
}

async function loadStatus(attempt = 0) {
  try {
    const { response, payload } = await request("/v1/management/status");
    if (response.status === 403) return show(pairing);
    if (response.status === 503 && attempt < 30) return retryStatus(attempt);
    if (!response.ok) throw new Error("Runtime status is unavailable.");
    window.clearTimeout(statusRetryTimer);
    renderStatus(payload);
  } catch (error) {
    if (attempt < 30) return retryStatus(attempt);
    show(checking);
    checking.querySelector("h2").textContent = "This R1 is unavailable";
    checking.querySelector(".support").textContent = error.message;
  }
}

pairForm.addEventListener("submit", async event => {
  event.preventDefault(); pairError.hidden = true;
  const button = pairForm.querySelector("button"); button.disabled = true;
  try {
    const code = new FormData(pairForm).get("code");
    const { response, payload } = await request("/v1/management/pair", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ code }) });
    if (!response.ok) throw new Error(payload.error?.message || "Pairing failed.");
    csrfToken = payload.csrfToken; await loadStatus();
  } catch (error) { pairError.textContent = error.message; pairError.hidden = false; }
  finally { button.disabled = false; }
});

restartButton.addEventListener("click", async () => {
  restartButton.disabled = true; statusMessage.textContent = "Restarting the on-device runtime…";
  try {
    const { response, payload } = await request("/v1/management/restart", { method: "POST", headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken }, body: "{}" });
    if (!response.ok) throw new Error(payload.error?.message || "Restart failed.");
    window.setTimeout(loadStatus, 1500);
  } catch (error) { statusMessage.textContent = error.message; }
  finally { restartButton.disabled = false; }
});

openAiConnect.addEventListener("submit", async event => {
  event.preventDefault(); openAiMessage.textContent = "Checking this credential…";
  const button = openAiConnect.querySelector("button"); button.disabled = true;
  try {
    const apiKey = new FormData(openAiConnect).get("apiKey");
    const { response, payload } = await request("/v1/management/openai/connect", {
      method: "POST", headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken }, body: JSON.stringify({ apiKey })
    });
    if (!response.ok) throw new Error(payload.error?.message || "OpenAI connection failed.");
    openAiConnect.reset(); renderOpenAI(payload); openAiMessage.textContent = "OpenAI is ready for Voice.";
  } catch (error) { openAiMessage.textContent = error.message; }
  finally { button.disabled = false; }
});

openAiModels.addEventListener("submit", async event => {
  event.preventDefault(); openAiMessage.textContent = "Saving models…";
  const data = new FormData(openAiModels);
  try {
    const { response, payload } = await request("/v1/management/openai/models", {
      method: "POST", headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
      body: JSON.stringify({
        textModel: data.get("textModel") || null,
        realtimeModel: data.get("realtimeModel") || null,
        reasoningEffort: data.get("reasoningEffort") || "none"
      })
    });
    if (!response.ok) throw new Error(payload.error?.message || "Model selection failed.");
    renderOpenAI(payload); openAiMessage.textContent = "Model selection saved.";
  } catch (error) { openAiMessage.textContent = error.message; }
});

profileForm.addEventListener("submit", async event => {
  event.preventDefault(); profileMessage.textContent = "Saving…";
  const displayName = new FormData(profileForm).get("displayName");
  try {
    const { response, payload } = await request("/v1/management/profile", {
      method: "POST", headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
      body: JSON.stringify({ displayName })
    });
    if (!response.ok) throw new Error(payload.error?.message || "Name could not be saved.");
    document.querySelector("#display-name").value = payload.displayName || "";
    profileMessage.textContent = payload.displayName ? "Voice greeting saved." : "Voice greeting cleared.";
  } catch (error) { profileMessage.textContent = error.message; }
});

openAiAccess.addEventListener("submit", async event => {
  event.preventDefault();
  const accessPath = new FormData(openAiAccess).get("accessPath");
  try {
    const { response, payload } = await request("/v1/management/openai/access", {
      method: "POST", headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
      body: JSON.stringify({ accessPath })
    });
    if (!response.ok) throw new Error(payload.error?.message || "Connection selection failed.");
    renderOpenAI(payload); openAiMessage.textContent = "Text and Voice connection selected.";
  } catch (error) { openAiMessage.textContent = error.message; }
});

subscriptionConnect.addEventListener("click", async () => {
  if (subscriptionPolling) return;
  subscriptionPolling = true;
  subscriptionConnect.disabled = true; subscriptionMessage.textContent = "Starting ChatGPT login…";
  try {
    const { response, payload } = await request("/v1/management/openai/subscription/start", {
      method: "POST", headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken }, body: "{}"
    });
    if (!response.ok) throw new Error(payload.error?.message || "ChatGPT login could not start.");
    document.querySelector("#subscription-code").textContent = payload.userCode;
    document.querySelector("#subscription-link").href = payload.verificationUrl;
    subscriptionAuth.hidden = false;
    subscriptionMessage.textContent = "";
    pollSubscription(payload.authSessionId, Math.max(1, payload.pollIntervalSeconds || 5));
  } catch (error) {
    subscriptionPolling = false;
    subscriptionConnect.disabled = false;
    subscriptionMessage.textContent = error.message;
  }
});

async function pollSubscription(authSessionId, interval) {
  try {
    const { response, payload } = await request("/v1/management/openai/subscription/poll", {
      method: "POST", headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
      body: JSON.stringify({ authSessionId })
    });
    if (!response.ok) throw new Error(payload.error?.message || "ChatGPT login failed.");
    if (payload.status === "completed") {
      subscriptionPolling = false;
      renderSubscription(payload.runtime || { connected: true });
      subscriptionMessage.textContent = "ChatGPT is ready for text and Voice.";
      await loadOpenAI();
      return;
    }
    window.setTimeout(() => pollSubscription(authSessionId, interval), interval * 1000);
  } catch (error) {
    subscriptionPolling = false;
    subscriptionConnect.disabled = false;
    subscriptionMessage.textContent = error.message;
  }
}

subscriptionDisconnect.addEventListener("click", async () => {
  try {
    const { response, payload } = await request("/v1/management/openai/subscription/disconnect", {
      method: "POST", headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken }, body: "{}"
    });
    if (!response.ok) throw new Error(payload.error?.message || "ChatGPT disconnect failed.");
    subscriptionPolling = false;
    subscriptionAuth.hidden = true;
    renderSubscription(payload); subscriptionMessage.textContent = "ChatGPT disconnected from this R1.";
    await loadOpenAI();
  } catch (error) { subscriptionMessage.textContent = error.message; }
});

openAiDisconnect.addEventListener("click", async () => {
  openAiMessage.textContent = "Disconnecting…";
  try {
    const { response, payload } = await request("/v1/management/openai/disconnect", {
      method: "POST", headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken }, body: "{}"
    });
    if (!response.ok) throw new Error(payload.error?.message || "Disconnect failed.");
    renderOpenAI(payload); openAiMessage.textContent = "OpenAI disconnected from this R1.";
  } catch (error) { openAiMessage.textContent = error.message; }
});

textAgent.addEventListener("submit", async event => {
  event.preventDefault();
  const button = textAgent.querySelector("button");
  const input = new FormData(textAgent).get("input");
  button.disabled = true;
  textResult.hidden = false;
  textResult.textContent = "Thinking…";
  try {
    const { response, payload } = await request("/v1/management/text/turns", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
      body: JSON.stringify({ input })
    });
    if (!response.ok) throw new Error(payload.error?.message || "The text agent could not complete this turn.");
    textResult.textContent = payload.text;
  } catch (error) { textResult.textContent = error.message; }
  finally { button.disabled = false; }
});

loadStatus();
