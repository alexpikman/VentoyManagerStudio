const $ = (selector) => document.querySelector(selector);

function formatBytes(value) {
  const bytes = Number(value);
  if (!Number.isFinite(bytes) || bytes <= 0) return "Размер не определён";
  const units = ["Б", "КБ", "МБ", "ГБ", "ТБ"];
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / (1024 ** index)).toFixed(index > 1 ? 1 : 0)} ${units[index]}`;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[char]);
}

async function fetchJson(url) {
  const response = await fetch(url, { headers: { Accept: "application/json" }, cache: "no-store" });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || payload.message || `HTTP ${response.status}`);
  return payload;
}

async function loadSystem() {
  try {
    const [health, system] = await Promise.all([fetchJson("/api/health"), fetchJson("/api/system")]);
    $("#api-dot").classList.add("online");
    $("#api-status").textContent = "Backend подключён";
    $("#api-metric").textContent = "ONLINE";
    $("#system-label").textContent = system.platform;
    document.title = `${health.application} · ${health.version}`;
  } catch (error) {
    $("#api-dot").classList.remove("online");
    $("#api-status").textContent = "Backend недоступен";
    $("#api-metric").textContent = "OFFLINE";
    $("#system-label").textContent = "Нет соединения";
  }
}

function renderDisks(payload) {
  const disks = payload.disks || [];
  $("#disk-count").textContent = String(disks.length);
  $("#ventoy-count").textContent = "—";
  $("#disk-counter").textContent = payload.supported ? `${disks.length} ДИСК(ОВ)` : "НЕДОСТУПНО";

  if (!payload.supported) {
    $("#disk-list").innerHTML = `<div class="empty-state"><strong>Платформа не поддерживается</strong><p>${escapeHtml(payload.message)}</p></div>`;
    return;
  }
  if (!disks.length) {
    $("#disk-list").innerHTML = `<div class="empty-state"><strong>Накопители не обнаружены</strong><p>Подключите USB-накопитель и обновите данные.</p></div>`;
    return;
  }

  $("#disk-list").innerHTML = disks.map((disk) => {
    const partitions = Array.isArray(disk.Partitions) ? disk.Partitions : [];
    const isProtected = disk.IsBoot || disk.IsSystem;
    const title = disk.FriendlyName || `Физический диск ${disk.Number}`;
    const partitionMarkup = partitions.length
      ? `<div class="partition-list">${partitions.map((part) => {
          const drive = part.DriveLetter ? `${escapeHtml(part.DriveLetter)}:` : "Без буквы";
          const label = part.Label ? escapeHtml(part.Label) : "Без метки";
          return `<div class="partition-item"><strong>${drive}</strong><span>${label}</span><span>${escapeHtml(part.FileSystem || "ФС не определена")}</span><span>${formatBytes(part.Size)}</span>${part.IsSystem ? '<span class="disk-tag system">SYSTEM</span>' : ""}</div>`;
        }).join("")}</div>`
      : "";
    return `<article class="disk-row">
      <div><div class="disk-name">${escapeHtml(title)}</div><div class="disk-sub">DISK ${escapeHtml(disk.Number)} · ${escapeHtml(disk.BusType || "BUS UNKNOWN")}</div></div>
      <div class="disk-detail"><span>ЁМКОСТЬ</span>${formatBytes(disk.Size)}</div>
      <div class="disk-detail"><span>РАЗМЕТКА</span>${escapeHtml(disk.PartitionStyle || "—")}</div>
      <div><span class="disk-tag ${isProtected ? "system" : ""}">${isProtected ? "SYSTEM DISK" : escapeHtml(disk.HealthStatus || "DETECTED")}</span></div>
      ${partitionMarkup}
    </article>`;
  }).join("");
}

async function loadDisks() {
  const button = $("#refresh-button");
  button.disabled = true;
  button.innerHTML = '<span class="button-symbol">↻</span> Сканирование…';
  $("#disk-list").innerHTML = '<div class="empty-state"><span class="loader"></span><strong>Получаем сведения о дисках</strong><p>Только чтение. Изменения накопителей не выполняются.</p></div>';
  try {
    renderDisks(await fetchJson("/api/disks"));
  } catch (error) {
    $("#disk-count").textContent = "!";
    $("#disk-counter").textContent = "ОШИБКА СКАНИРОВАНИЯ";
    $("#disk-list").innerHTML = `<div class="error-state">Не удалось получить сведения о накопителях.<br>${escapeHtml(error.message)}</div>`;
  } finally {
    button.disabled = false;
    button.innerHTML = '<span class="button-symbol">↻</span> Обновить данные';
  }
}

const sectionNames = {
  overview: "ОБЗОР", usb: "USB-НАКОПИТЕЛИ", releases: "VENTOY RELEASES",
  images: "ISO MANAGER", menu: "MENU EDITOR", themes: "GRUB THEME STUDIO",
  backup: "BACKUP & RECOVERY", diagnostics: "ДИАГНОСТИКА", settings: "НАСТРОЙКИ"
};

document.querySelectorAll(".nav-item").forEach((item) => {
  item.addEventListener("click", () => {
    document.querySelectorAll(".nav-item").forEach((button) => button.classList.remove("active"));
    item.classList.add("active");
    const section = item.dataset.view;
    $("#current-section").textContent = sectionNames[section] || "ОБЗОР";
    if (section !== "overview") {
      // Navigation placeholders are intentionally explicit until each module is implemented.
      const title = item.textContent.trim();
      $("#page-content").innerHTML = `
        <div class="page-heading"><div><div class="eyebrow">MODULE WORKSPACE</div><h1>${escapeHtml(title)}</h1><p class="page-description">Модуль предусмотрен архитектурой и будет подключён на соответствующем этапе разработки.</p></div></div>
        <div class="notice notice-info"><span class="notice-icon">i</span><div><strong>Модуль ещё не реализован</strong><p>Сейчас доступна базовая системная панель и безопасное обнаружение дисков. Эта страница не имитирует работу отсутствующих функций.</p></div></div>
        <section class="panel"><div class="panel-header"><div><div class="eyebrow">DEVELOPMENT STATUS</div><h2>Ожидает реализации</h2></div><span class="panel-counter">PLANNED</span></div><div class="disk-list"><div class="empty-state"><strong>${escapeHtml(title)}</strong><p>Функциональность будет добавлена отдельным проверяемым этапом.</p></div></div></section>`;
    } else {
      window.location.reload();
    }
  });
});

$("#refresh-button").addEventListener("click", async () => {
  await Promise.all([loadSystem(), loadDisks()]);
});

loadSystem();
loadDisks();
