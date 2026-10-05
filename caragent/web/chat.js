"use strict";
const $ = id => document.getElementById(id);
const STORAGE_KEY = "caragent-chat-v1";
let vehicles = [], messages = [], busy = false;

async function api(path, options) {
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok) throw Error(typeof data.detail === "string" ? data.detail : "İstek tamamlanamadı. Mesajınızı kontrol edin.");
  return data;
}

function safeLink(value) {
  try { const url = new URL(value); return ["https:", "http:"].includes(url.protocol) ? url.href : null; }
  catch { return null; }
}

function save() {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify({ vehicle: $("vehicle").value, messages: messages.slice(-60) })); }
  catch { $("status").textContent = "Sohbet bu tarayıcıda kaydedilemedi."; }
}

function renderSources(sources) {
  const details = document.createElement("details"); details.className = "sources";
  const summary = document.createElement("summary"); summary.textContent = `Kaynakları incele (${sources.length})`; details.append(summary);
  for (const source of sources) {
    const item = document.createElement("div"); item.className = "source-item";
    const title = document.createElement("a"); title.textContent = `[${source.citation}] ${source.title}`;
    const url = safeLink(source.url);
    if (url) { title.href = url; title.target = "_blank"; title.rel = "noopener noreferrer"; }
    item.append(title);
    const meta = document.createElement("p"); meta.className = "source-meta";
    meta.textContent = `${source.model} ${source.year} · Sayfa ${source.page} · ${source.reason === "graph_neighbor" ? "Graph bağlantısı" : "Metin eşleşmesi"}`;
    item.append(meta);
    const excerpt = document.createElement("details"), label = document.createElement("summary"); label.textContent = "Kayıtlı metni göster";
    const text = document.createElement("div"); text.className = "source-text"; text.textContent = source.text;
    excerpt.append(label, text); item.append(excerpt); details.append(item);
  }
  return details;
}

function messageElement(message) {
  const element = document.createElement("article"); element.className = `message ${message.role}`;
  const label = document.createElement("div"); label.className = "message-label"; label.textContent = message.role === "user" ? "SEN" : "CARAGENT";
  const text = document.createElement("div"); text.className = "message-text"; text.textContent = message.content;
  element.append(label, text);
  if (message.warning) { const notice = document.createElement("p"); notice.className = "notice"; notice.textContent = message.warning; element.append(notice); }
  if (message.sources?.length) element.append(renderSources(message.sources));
  return element;
}

function render() {
  const box = $("messages"); box.replaceChildren();
  if (!messages.length) {
    const empty = document.createElement("div"); empty.className = "empty";
    const symbol = document.createElement("span"); symbol.className = "symbol"; symbol.textContent = "✳";
    const heading = document.createElement("h3"); heading.textContent = "Bir soruyla başlayalım.";
    const note = document.createElement("p"); note.textContent = "Toyota kılavuzlarını birlikte inceleyelim. Bir konu sorabilir, ardından cevabın üzerinden konuşmaya devam edebilirsin.";
    empty.append(symbol, heading, note); box.append(empty);
  }
  for (const message of messages) box.append(messageElement(message));
  if (busy) {
    const pending = messageElement({ role: "assistant", content: "Kılavuzlara bakıp yanıtını hazırlıyorum…" });
    pending.classList.add("pending"); pending.id = "pending"; box.append(pending);
  }
  $("suggestions").hidden = messages.length > 0;
  box.scrollTop = box.scrollHeight;
}

function controls() {
  const unavailable = busy || !$("vehicle").value;
  $("submit").disabled = unavailable; $("question").disabled = unavailable;
  $("vehicle").disabled = busy || !vehicles.length;
  $("new-chat").disabled = busy || !vehicles.length;
}

function updateVehicle() {
  const selected = vehicles.find(vehicle => vehicle.id === $("vehicle").value);
  $("market").textContent = selected ? `Kaynak pazarı: ${selected.market}` : "";
  $("chat-vehicle").textContent = selected ? `Toyota ${selected.model} · ${selected.year}` : "Önce Toyota kılavuzlarını içe aktarın.";
}

async function init() {
  try {
    const [vehicleData, stats] = await Promise.all([api("/api/vehicles"), api("/api/stats")]);
    vehicles = vehicleData.vehicles; $("vehicle").replaceChildren();
    for (const vehicle of vehicles) {
      const option = document.createElement("option"); option.value = vehicle.id; option.textContent = `Toyota ${vehicle.model} · ${vehicle.year}`; $("vehicle").append(option);
    }
    if (!vehicles.length) { const option = document.createElement("option"); option.value = ""; option.textContent = "Kılavuz bulunamadı"; $("vehicle").append(option); }
    const names = { CaragentVehicle: "Araç", CaragentManual: "Kılavuz bölümü", CaragentChunk: "Metin parçası" };
    for (const row of stats.counts) {
      if (!names[row.label]) continue;
      const card = document.createElement("div"), value = document.createElement("b"); value.textContent = row.count; card.append(value, document.createTextNode(names[row.label])); $("counts").append(card);
    }
    $("model-status").textContent = stats.answer_mode === "ollama" ? "Yerel model · Sohbet" : "Kaynak gösterme modu";
    if (stats.answer_mode !== "ollama") $("status").textContent = "Sohbet için yerel modeli etkinleştirip uygulamayı yeniden başlatın.";
    try {
      const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
      if (saved && vehicles.some(vehicle => vehicle.id === saved.vehicle) && Array.isArray(saved.messages)) {
        $("vehicle").value = saved.vehicle;
        const entries = saved.messages.filter(message => ["user", "assistant"].includes(message.role) && typeof message.content === "string");
        for (let index = 0; index + 1 < entries.length; index += 2) {
          if (entries[index].role === "user" && entries[index + 1].role === "assistant") messages.push(entries[index], entries[index + 1]);
        }
      }
    } catch { /* Invalid local data starts a new conversation. */ }
    updateVehicle(); controls(); render();
  } catch (error) { $("status").textContent = error.message; $("model-status").textContent = "Bağlantı kurulamadı"; }
}

$("form").addEventListener("submit", async event => {
  event.preventDefault();
  const question = $("question").value.trim();
  if (busy || question.length < 2 || !$("vehicle").value) return;
  const history = messages.slice(-12).map(message => ({ role: message.role, content: message.content.slice(0, 6000) }));
  messages.push({ role: "user", content: question });
  $("question").value = ""; busy = true; $("status").textContent = "Yanıt hazırlanıyor…"; controls(); render();
  try {
    const data = await api("/api/ask", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, vehicle_id: $("vehicle").value, limit: 4, history }) });
    messages.push({ role: "assistant", content: data.answer, sources: data.sources, warning: data.warning, mode: data.mode });
    $("status").textContent = data.mode === "sources" ? "Yerel model yanıtı alınamadı; kaynak metinleri gösterildi." : "";
    save();
  } catch (error) {
    messages.pop(); $("question").value = question; $("status").textContent = error.message + " Yeniden gönderebilirsin.";
  } finally { busy = false; controls(); render(); $("question").focus(); }
});

$("question").addEventListener("keydown", event => {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) { event.preventDefault(); $("form").requestSubmit(); }
});
$("new-chat").addEventListener("click", () => { messages = []; $("status").textContent = ""; save(); render(); $("question").focus(); });
$("vehicle").addEventListener("change", () => { messages = []; $("status").textContent = ""; updateVehicle(); save(); render(); controls(); });
document.querySelectorAll("[data-question]").forEach(button => button.addEventListener("click", () => {
  $("question").value = button.dataset.question; $("question").focus();
}));
init();
