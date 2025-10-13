// static/js/ai_description.js
(function () {
  function getCookie(name) {
    const matches = document.cookie.match(new RegExp(
      "(?:^|; )" + name.replace(/([$?*|{}\]\\\/\+\^])/g, '\\$1') + "=([^;]*)"
    ));
    return matches ? decodeURIComponent(matches[1]) : null;
  }

  function findField(selectors) {
    for (const s of selectors) {
      const el = document.querySelector(s);
      if (el) return el;
    }
    return null;
  }

  function pickText(el) {
    return (el && (el.options ? el.options[el.selectedIndex]?.text : el.value || el.textContent || "")).trim();
  }

  async function callAI(payload) {
    const csrftoken = getCookie('csrftoken');
    const resp = await fetch("/events/ai/generate-description/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrftoken || ""
      },
      body: JSON.stringify(payload),
    });
    return await resp.json();
  }

  function promptKeywords() {
    const kw = window.prompt("Уточните ключевые слова/идею (опционально):", "");
    return kw === null ? null : kw.trim();
  }

  function confirmInsertMode() {
    return window.confirm("Заменить текущее описание на сгенерированное?\nНажмите ОК — заменить, Отмена — добавить в конец.");
  }

  function showToast(msg, type) {
    // минималистичное уведомление
    const n = document.createElement("div");
    n.textContent = msg;
    n.style.cssText = "position:fixed;right:16px;top:16px;padding:10px 12px;border-radius:6px;color:#fff;z-index:9999;" +
      (type === "err" ? "background:#e74c3c" : "background:#2ecc71");
    document.body.appendChild(n);
    setTimeout(() => n.remove(), 2500);
  }

  async function onClick() {
    const btn = document.getElementById("ai-generate-btn");
    if (!btn) return;

    // Попытаемся собрать контекст из формы
    const titleEl = findField(["#id_title", "input[name='title']"]);
    const startsEl = findField(["#id_starts_at", "input[name='starts_at']", "#id_date", "input[name='date']"]);
    const locEl = findField(["#id_location", "input[name='location']"]);
    const catEl = findField(["#id_category", "select[name='category']", "#id_new_category", "select[name='new_category']"]);
    const descrEl = findField(["#id_description", "textarea[name='description']", "#id_new_description", "textarea[name='new_description']"]);

    if (!descrEl) {
      showToast("Не найдено поле описания на странице", "err");
      return;
    }

    const keywords = promptKeywords();
    if (keywords === null) return; // пользователь нажал Cancel

    btn.disabled = true;
    const prevText = btn.textContent;
    btn.textContent = "Генерация...";

    try {
      const payload = {
        title: titleEl ? titleEl.value : "",
        starts_at: startsEl ? startsEl.value : "",
        location: locEl ? locEl.value : "",
        category_name: pickText(catEl),
        keywords: keywords || ""
      };

      const data = await callAI(payload);
      if (data.error) {
        showToast("Ошибка ИИ: " + data.error, "err");
        return;
      }
      const text = (data.text || "").trim();
      if (!text) {
        showToast("Пустой ответ от ИИ", "err");
        return;
      }

      const replace = confirmInsertMode();
      if (replace) {
        descrEl.value = text;
      } else {
        const sep = descrEl.value ? "\n\n" : "";
        descrEl.value = descrEl.value + sep + text;
      }
      descrEl.dispatchEvent(new Event('input', { bubbles: true }));
      showToast("Описание вставлено", "ok");
    } catch (e) {
      showToast("Сбой генерации: " + e, "err");
    } finally {
      btn.disabled = false;
      btn.textContent = prevText;
    }
  }

  window.addEventListener("DOMContentLoaded", () => {
    const btn = document.getElementById("ai-generate-btn");
    if (btn) btn.addEventListener("click", onClick);
  });
})();
