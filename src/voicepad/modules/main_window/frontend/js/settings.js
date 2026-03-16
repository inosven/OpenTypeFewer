let app_config = {};
let mic_test_active = false;
let mic_poll_timer = null;
let hotkey_capturing = null;
let captured_keys = new Set();

// ── Theme ────────────────────────────────────────────────────────────────────

function apply_theme(theme_value) {
  if (theme_value === "system") {
    const prefers_dark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    document.documentElement.setAttribute("data-theme", prefers_dark ? "dark" : "light");
  } else {
    document.documentElement.setAttribute("data-theme", theme_value);
  }
}

// ── Navigation ───────────────────────────────────────────────────────────────

document.querySelectorAll(".nav-item").forEach(nav_item => {
  nav_item.addEventListener("click", () => {
    document.querySelectorAll(".nav-item").forEach(n => n.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));
    nav_item.classList.add("active");
    const tab_id = "tab-" + nav_item.dataset.tab;
    document.getElementById(tab_id).classList.add("active");

    if (nav_item.dataset.tab === "model") {
      load_ollama_models();
    }
  });
});

// ── Provider sub-tabs ────────────────────────────────────────────────────────

document.querySelectorAll(".sub-tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".sub-tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".sub-tab-panel").forEach(p => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById("provider-" + btn.dataset.provider).classList.add("active");
  });
});

// ── Config load / populate ───────────────────────────────────────────────────

async function load_config() {
  try {
    app_config = await window.pywebview.api.get_config();
    populate_form(app_config);
  } catch (load_error) {
    console.error("Failed to load config:", load_error);
  }
}

function populate_form(config_data) {
  const ui_theme = (config_data.ui || {}).theme || "system";
  apply_theme(ui_theme);

  const theme_select = document.getElementById("setting-theme");
  if (theme_select) theme_select.value = ui_theme;

  const ui_lang = document.getElementById("setting-ui-language");
  if (ui_lang) ui_lang.value = config_data.language || "en";

  const trigger_mode = document.getElementById("setting-trigger-mode");
  if (trigger_mode) trigger_mode.value = config_data.trigger_mode || "hold";

  const auto_stop = document.getElementById("setting-auto-stop");
  if (auto_stop) auto_stop.checked = config_data.auto_stop_on_focus_loss !== false;

  const sound_enabled = document.getElementById("setting-sound-enabled");
  if (sound_enabled) sound_enabled.checked = (config_data.notification || {}).sound_enabled !== false;

  const llm = config_data.llm || {};
  const thinking_enabled = llm.thinking_enabled || false;

  const ollama_cfg = llm.ollama || {};
  set_input("ollama-base-url", ollama_cfg.base_url || "http://localhost:11434");
  set_input("ollama-temperature", ollama_cfg.temperature || 0.3);
  set_checkbox("ollama-thinking", thinking_enabled);

  const remote_cfg = llm.remote || {};
  set_input("anthropic-api-key", remote_cfg.provider === "anthropic" ? (remote_cfg.api_key || "") : "");
  set_input("anthropic-model", remote_cfg.provider === "anthropic" ? (remote_cfg.model || "") : "claude-sonnet-4-20250514");
  set_input("anthropic-base-url", remote_cfg.provider === "anthropic" ? (remote_cfg.base_url || "") : "");
  set_checkbox("anthropic-thinking", thinking_enabled);

  set_input("openai-api-key", remote_cfg.provider === "openai" ? (remote_cfg.api_key || "") : "");
  set_input("openai-model", remote_cfg.provider === "openai" ? (remote_cfg.model || "") : "gpt-4o");
  set_input("openai-base-url", remote_cfg.provider === "openai" ? (remote_cfg.base_url || "") : "");
  set_checkbox("openai-thinking", thinking_enabled);

  const compatible_cfg = llm.compatible || {};
  set_input("compatible-base-url", compatible_cfg.base_url || "http://localhost:1234/v1");
  set_input("compatible-model", compatible_cfg.model || "");
  set_input("compatible-api-key", compatible_cfg.api_key || "");
  set_input("compatible-temperature", compatible_cfg.temperature || 0.3);
  set_checkbox("compatible-thinking", thinking_enabled);

  const hotkey_record = document.getElementById("hotkey-record");
  if (hotkey_record) hotkey_record.textContent = format_hotkey_display(config_data.hotkey || "ctrl+shift+space");

  const hotkey_mode = document.getElementById("hotkey-mode-switch");
  if (hotkey_mode) hotkey_mode.textContent = format_hotkey_display(config_data.mode_switch_hotkey || "ctrl+shift+m");

  render_preset_list(config_data.presets || []);
}

function set_input(element_id, value) {
  const el = document.getElementById(element_id);
  if (el) el.value = value;
}

function set_checkbox(element_id, checked) {
  const el = document.getElementById(element_id);
  if (el) el.checked = checked;
}

// ── Ollama model list ────────────────────────────────────────────────────────

async function load_ollama_models() {
  const model_select = document.getElementById("ollama-model-select");
  if (!model_select) return;

  model_select.innerHTML = '<option value="">Loading...</option>';

  try {
    const model_list = await window.pywebview.api.list_ollama_models();
    const current_model = (app_config.llm || {}).ollama?.model || "";

    model_select.innerHTML = "";
    if (model_list.length === 0) {
      model_select.innerHTML = '<option value="">No models found</option>';
      return;
    }

    model_list.forEach(model_name => {
      const option_el = document.createElement("option");
      option_el.value = model_name;
      option_el.textContent = model_name;
      if (model_name === current_model) option_el.selected = true;
      model_select.appendChild(option_el);
    });
  } catch (model_error) {
    model_select.innerHTML = '<option value="">Ollama not running</option>';
  }
}

// ── Theme change ─────────────────────────────────────────────────────────────

document.getElementById("setting-theme")?.addEventListener("change", (event) => {
  apply_theme(event.target.value);
});

// ── Microphone test ──────────────────────────────────────────────────────────

document.getElementById("mic-test-btn")?.addEventListener("click", async () => {
  const bars_container = document.getElementById("mic-volume-bars");
  const btn = document.getElementById("mic-test-btn");

  if (mic_test_active) {
    mic_test_active = false;
    clearInterval(mic_poll_timer);
    bars_container.style.display = "none";
    btn.textContent = "Test Mic";
    return;
  }

  mic_test_active = true;
  bars_container.style.display = "flex";
  btn.textContent = "Stop Test";

  mic_poll_timer = setInterval(async () => {
    if (!mic_test_active) return;
    try {
      const volume_level = await window.pywebview.api.test_microphone();
      update_mic_bars(volume_level);
    } catch {
      // ignore errors during test
    }
  }, 100);
});

function update_mic_bars(volume_level) {
  for (let bar_index = 0; bar_index < 8; bar_index++) {
    const bar_el = document.getElementById("mbar" + bar_index);
    if (!bar_el) continue;
    const base_height = 4 + bar_index * 3;
    const random_factor = 0.5 + Math.random() * 1.0;
    const computed_height = base_height + volume_level * 24 * random_factor;
    bar_el.style.height = Math.min(computed_height, 32) + "px";
  }
}

// ── Hotkey capture ───────────────────────────────────────────────────────────

const MODIFIER_KEYS = new Set(["Control", "Shift", "Alt", "Meta", "Fn"]);

const KEY_DISPLAY_MAP = {
  "Control": "⌃", "Shift": "⇧", "Alt": "⌥", "Meta": "⌘",
  " ": "Space", "ArrowUp": "↑", "ArrowDown": "↓",
  "ArrowLeft": "←", "ArrowRight": "→",
};

function format_hotkey_display(hotkey_str) {
  if (!hotkey_str) return "";
  return hotkey_str.split("+").map(key_part => {
    const trimmed = key_part.trim();
    const key_map = {
      "ctrl": "⌃", "shift": "⇧", "alt": "⌥", "cmd": "⌘",
      "space": "Space", "tab": "Tab", "enter": "Enter",
    };
    return key_map[trimmed.toLowerCase()] || trimmed.toUpperCase();
  }).join("");
}

function hotkey_to_storage_string(key_set) {
  const parts = [];
  if (key_set.has("Control")) parts.push("ctrl");
  if (key_set.has("Shift")) parts.push("shift");
  if (key_set.has("Alt")) parts.push("alt");
  if (key_set.has("Meta")) parts.push("cmd");
  for (const key_name of key_set) {
    if (!MODIFIER_KEYS.has(key_name)) {
      parts.push(key_name.toLowerCase());
    }
  }
  return parts.join("+");
}

document.querySelectorAll(".hotkey-capture").forEach(capture_el => {
  capture_el.addEventListener("click", () => {
    document.querySelectorAll(".hotkey-capture").forEach(el => el.classList.remove("capturing"));
    capture_el.classList.add("capturing");
    capture_el.textContent = "Press keys...";
    hotkey_capturing = capture_el.id;
    captured_keys = new Set();
  });
});

document.addEventListener("keydown", (key_event) => {
  if (!hotkey_capturing) return;
  key_event.preventDefault();
  captured_keys.add(key_event.key);
});

document.addEventListener("keyup", (key_event) => {
  if (!hotkey_capturing) return;
  key_event.preventDefault();

  const released_key = key_event.key;
  const non_modifiers = [...captured_keys].filter(k => !MODIFIER_KEYS.has(k));

  if (!MODIFIER_KEYS.has(released_key) || non_modifiers.length > 0) {
    const storage_str = hotkey_to_storage_string(captured_keys);
    const display_str = format_hotkey_display(storage_str);
    const capture_el = document.getElementById(hotkey_capturing);

    if (capture_el) {
      capture_el.textContent = display_str || "None";
      capture_el.classList.remove("capturing");
      capture_el.dataset.storageValue = storage_str;
    }
    hotkey_capturing = null;
    captured_keys = new Set();
  }
});

// ── Save hotkeys ─────────────────────────────────────────────────────────────

document.getElementById("save-hotkeys-btn")?.addEventListener("click", async () => {
  const hotkey_record_el = document.getElementById("hotkey-record");
  const hotkey_mode_el = document.getElementById("hotkey-mode-switch");

  const updated_config = JSON.parse(JSON.stringify(app_config));

  if (hotkey_record_el?.dataset.storageValue) {
    updated_config.hotkey = hotkey_record_el.dataset.storageValue;
  }
  if (hotkey_mode_el?.dataset.storageValue) {
    updated_config.mode_switch_hotkey = hotkey_mode_el.dataset.storageValue;
  }

  await save_config(updated_config);
});

// ── Save model settings ──────────────────────────────────────────────────────

document.getElementById("save-model-btn")?.addEventListener("click", async () => {
  const active_provider_btn = document.querySelector(".sub-tab-btn.active");
  const active_provider = active_provider_btn?.dataset.provider || "ollama";
  const updated_config = JSON.parse(JSON.stringify(app_config));

  if (!updated_config.llm) updated_config.llm = {};

  if (active_provider === "ollama") {
    updated_config.llm.backend = "ollama";
    if (!updated_config.llm.ollama) updated_config.llm.ollama = {};
    updated_config.llm.ollama.base_url = document.getElementById("ollama-base-url").value;
    const selected_model = document.getElementById("ollama-model-select").value;
    if (selected_model) updated_config.llm.ollama.model = selected_model;
    updated_config.llm.ollama.temperature = parseFloat(document.getElementById("ollama-temperature").value) || 0.3;
    updated_config.llm.thinking_enabled = document.getElementById("ollama-thinking").checked;
  } else if (active_provider === "anthropic") {
    updated_config.llm.backend = "remote";
    if (!updated_config.llm.remote) updated_config.llm.remote = {};
    updated_config.llm.remote.provider = "anthropic";
    updated_config.llm.remote.api_key = document.getElementById("anthropic-api-key").value;
    updated_config.llm.remote.model = document.getElementById("anthropic-model").value;
    updated_config.llm.remote.base_url = document.getElementById("anthropic-base-url").value;
    updated_config.llm.thinking_enabled = document.getElementById("anthropic-thinking").checked;
  } else if (active_provider === "openai") {
    updated_config.llm.backend = "remote";
    if (!updated_config.llm.remote) updated_config.llm.remote = {};
    updated_config.llm.remote.provider = "openai";
    updated_config.llm.remote.api_key = document.getElementById("openai-api-key").value;
    updated_config.llm.remote.model = document.getElementById("openai-model").value;
    updated_config.llm.remote.base_url = document.getElementById("openai-base-url").value;
    updated_config.llm.thinking_enabled = document.getElementById("openai-thinking").checked;
  } else if (active_provider === "compatible") {
    updated_config.llm.backend = "remote";
    if (!updated_config.llm.remote) updated_config.llm.remote = {};
    updated_config.llm.remote.provider = "compatible";
    if (!updated_config.llm.compatible) updated_config.llm.compatible = {};
    updated_config.llm.compatible.base_url = document.getElementById("compatible-base-url").value;
    updated_config.llm.compatible.model = document.getElementById("compatible-model").value;
    updated_config.llm.compatible.api_key = document.getElementById("compatible-api-key").value;
    updated_config.llm.compatible.temperature = parseFloat(document.getElementById("compatible-temperature").value) || 0.3;
    updated_config.llm.thinking_enabled = document.getElementById("compatible-thinking").checked;
  }

  await save_config(updated_config);
});

// ── General settings auto-save ───────────────────────────────────────────────

document.getElementById("setting-theme")?.addEventListener("change", async (event) => {
  const updated_config = JSON.parse(JSON.stringify(app_config));
  if (!updated_config.ui) updated_config.ui = {};
  updated_config.ui.theme = event.target.value;
  await save_config(updated_config);
});

document.getElementById("setting-ui-language")?.addEventListener("change", async (event) => {
  const updated_config = JSON.parse(JSON.stringify(app_config));
  updated_config.language = event.target.value;
  await save_config(updated_config);
});

document.getElementById("setting-trigger-mode")?.addEventListener("change", async (event) => {
  const updated_config = JSON.parse(JSON.stringify(app_config));
  updated_config.trigger_mode = event.target.value;
  await save_config(updated_config);
});

document.getElementById("setting-auto-stop")?.addEventListener("change", async (event) => {
  const updated_config = JSON.parse(JSON.stringify(app_config));
  updated_config.auto_stop_on_focus_loss = event.target.checked;
  await save_config(updated_config);
});

document.getElementById("setting-sound-enabled")?.addEventListener("change", async (event) => {
  const updated_config = JSON.parse(JSON.stringify(app_config));
  if (!updated_config.notification) updated_config.notification = {};
  updated_config.notification.sound_enabled = event.target.checked;
  await save_config(updated_config);
});

// ── Presets ──────────────────────────────────────────────────────────────────

function render_preset_list(preset_entries) {
  const preset_list_el = document.getElementById("preset-list");
  if (!preset_list_el) return;

  preset_list_el.innerHTML = "";

  if (preset_entries.length === 0) {
    preset_list_el.innerHTML = '<div style="color:var(--text-secondary);font-size:12px;padding:8px 0;">No presets yet. Add one below.</div>';
    return;
  }

  preset_entries.forEach((preset_entry, preset_index) => {
    const preset_item = document.createElement("div");
    preset_item.className = "preset-item";
    preset_item.innerHTML = `
      <div style="flex:1">
        <div class="preset-item-name">${preset_entry.name || "Unnamed"}</div>
        <div class="preset-item-meta">${preset_entry.processing || "direct"} · ${preset_entry.language || "source"}</div>
      </div>
      <button class="preset-item-delete" data-index="${preset_index}" title="Delete">✕</button>
    `;
    preset_list_el.appendChild(preset_item);
  });

  preset_list_el.querySelectorAll(".preset-item-delete").forEach(delete_btn => {
    delete_btn.addEventListener("click", async () => {
      const preset_index = parseInt(delete_btn.dataset.index);
      const updated_config = JSON.parse(JSON.stringify(app_config));
      updated_config.presets.splice(preset_index, 1);
      await save_config(updated_config);
    });
  });
}

document.getElementById("add-preset-btn")?.addEventListener("click", async () => {
  const preset_name = document.getElementById("new-preset-name").value.trim();
  if (!preset_name) return;

  const new_preset = {
    name: preset_name,
    processing: document.getElementById("new-preset-processing").value,
    language: document.getElementById("new-preset-language").value,
    custom_prompt: document.getElementById("new-preset-prompt").value.trim(),
  };

  const updated_config = JSON.parse(JSON.stringify(app_config));
  if (!updated_config.presets) updated_config.presets = [];
  updated_config.presets.push(new_preset);

  await save_config(updated_config);

  document.getElementById("new-preset-name").value = "";
  document.getElementById("new-preset-prompt").value = "";
});

// ── About ────────────────────────────────────────────────────────────────────

document.getElementById("github-btn")?.addEventListener("click", () => {
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.open_github();
  }
});

document.getElementById("check-updates-btn")?.addEventListener("click", async () => {
  const status_el = document.getElementById("update-status");
  status_el.textContent = "Checking...";
  try {
    const update_info = await window.pywebview.api.check_for_updates();
    if (update_info.has_update) {
      status_el.textContent = `Update available: ${update_info.latest_version}`;
      status_el.style.color = "var(--accent)";
    } else {
      status_el.textContent = "You are on the latest version.";
    }
  } catch {
    status_el.textContent = "Could not check for updates.";
  }
});

// ── Save config ──────────────────────────────────────────────────────────────

async function save_config(config_data) {
  try {
    await window.pywebview.api.save_config(config_data);
    app_config = config_data;

    const current_theme = (config_data.ui || {}).theme || "system";
    apply_theme(current_theme);

    const current_presets = config_data.presets || [];
    render_preset_list(current_presets);
  } catch (save_error) {
    console.error("Failed to save config:", save_error);
  }
}

// ── Init ─────────────────────────────────────────────────────────────────────

window.addEventListener("pywebviewready", () => {
  load_config();
});

setTimeout(() => {
  if (window.pywebview) {
    load_config();
  }
}, 200);

window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
  const current_theme = (app_config.ui || {}).theme || "system";
  if (current_theme === "system") {
    apply_theme("system");
  }
});
