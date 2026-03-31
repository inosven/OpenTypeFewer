let app_config = {};
let mic_test_active = false;
let mic_poll_timer = null;
let hotkey_capturing = null;
let captured_keys = new Set();
let editing_preset_index = -1;

const IS_MACOS = /Mac|iPhone|iPad|iPod/.test(navigator.platform);

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
    load_microphone_list();
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

  const asr_cfg = config_data.asr || {};
  set_select("asr-model-size", asr_cfg.model_size || "large-v3");
  set_select("asr-device", asr_cfg.device || "auto");
  set_select("asr-language", asr_cfg.language ?? "");

  const hotkey_record = document.getElementById("hotkey-record");
  if (hotkey_record) {
    const record_hk = config_data.hotkey || "ctrl+shift+space";
    hotkey_record.textContent = format_hotkey_display(record_hk);
    hotkey_record.dataset.storageValue = record_hk;
  }

  const hotkey_mode = document.getElementById("hotkey-mode-switch");
  if (hotkey_mode) {
    const mode_hk = config_data.mode_switch_hotkey || "";
    hotkey_mode.textContent = mode_hk ? format_hotkey_display(mode_hk) : "None";
    hotkey_mode.dataset.storageValue = mode_hk;
  }

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

function set_select(element_id, value) {
  const el = document.getElementById(element_id);
  if (el) el.value = value;
}

function show_save_status(status_id, success) {
  const status_el = document.getElementById(status_id);
  if (!status_el) return;
  status_el.textContent = success ? "Saved!" : "Save failed";
  status_el.classList.remove("error");
  if (!success) status_el.classList.add("error");
  status_el.classList.add("visible");
  setTimeout(() => status_el.classList.remove("visible"), 2000);
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

// ── Microphone device list ───────────────────────────────────────────────────

async function load_microphone_list() {
  const mic_select = document.getElementById("setting-mic-device");
  if (!mic_select) return;

  try {
    const device_list = await window.pywebview.api.list_microphones();
    const current_device = (app_config.audio || {}).input_device || "";

    mic_select.innerHTML = '<option value="">System Default</option>';
    device_list.forEach(device_entry => {
      const option_el = document.createElement("option");
      option_el.value = String(device_entry.index);
      option_el.textContent = device_entry.name;
      if (String(device_entry.index) === String(current_device)) option_el.selected = true;
      mic_select.appendChild(option_el);
    });
  } catch (list_error) {
    console.warn("Failed to list microphones:", list_error);
  }
}

document.getElementById("setting-mic-device")?.addEventListener("change", async (event) => {
  const updated_config = JSON.parse(JSON.stringify(app_config));
  if (!updated_config.audio) updated_config.audio = {};
  const device_val = event.target.value;
  updated_config.audio.input_device = device_val ? parseInt(device_val) : null;
  await save_config(updated_config);
});

// ── Microphone test ──────────────────────────────────────────────────────────

document.getElementById("mic-test-btn")?.addEventListener("click", async () => {
  const volume_container = document.getElementById("mic-volume-container");
  const btn = document.getElementById("mic-test-btn");

  if (mic_test_active) {
    mic_test_active = false;
    clearInterval(mic_poll_timer);
    await window.pywebview.api.stop_mic_test();
    volume_container.style.display = "none";
    btn.textContent = "Test Mic";
    return;
  }

  const mic_device = document.getElementById("setting-mic-device")?.value || "";
  const device_index = mic_device ? parseInt(mic_device) : null;
  const started = await window.pywebview.api.start_mic_test(device_index);
  if (!started) return;

  mic_test_active = true;
  volume_container.style.display = "block";
  btn.textContent = "Stop Test";

  mic_poll_timer = setInterval(async () => {
    if (!mic_test_active) return;
    try {
      const volume_level = await window.pywebview.api.get_mic_test_level();
      const fill_el = document.getElementById("mic-volume-fill");
      if (fill_el) fill_el.style.width = (volume_level * 100) + "%";
    } catch {
      // ignore errors during test
    }
  }, 80);
});

// ── Hotkey display helpers ───────────────────────────────────────────────────

const MODIFIER_KEYS = new Set(["Control", "Shift", "Alt", "Meta", "Fn"]);

const KEY_STORAGE_MAP = {
  " ": "space", "Tab": "tab", "Enter": "enter",
  "Escape": "esc", "Backspace": "backspace", "Delete": "delete",
  "ArrowUp": "up", "ArrowDown": "down",
  "ArrowLeft": "left", "ArrowRight": "right",
};

function format_hotkey_display(hotkey_str) {
  if (!hotkey_str) return "None";
  const parts = hotkey_str.split("+").map(p => p.trim());

  if (IS_MACOS) {
    const mac_map = {
      "ctrl": "⌃", "shift": "⇧", "alt": "⌥", "cmd": "⌘",
      "space": "Space", "tab": "Tab", "enter": "Enter",
    };
    return parts.map(p => mac_map[p.toLowerCase()] || p.toUpperCase()).join("");
  }

  const win_map = {
    "ctrl": "Ctrl", "shift": "Shift", "alt": "Alt",
    "cmd": "Win", "win": "Win", "windows": "Win",
    "space": "Space", "tab": "Tab", "enter": "Enter",
  };
  return parts.map(p => win_map[p.toLowerCase()] || p.charAt(0).toUpperCase() + p.slice(1)).join("+");
}

function hotkey_to_storage_string(key_set) {
  const parts = [];
  if (key_set.has("Control")) parts.push("ctrl");
  if (key_set.has("Shift")) parts.push("shift");
  if (key_set.has("Alt")) parts.push("alt");
  if (key_set.has("Meta")) parts.push("cmd");
  for (const key_name of key_set) {
    if (!MODIFIER_KEYS.has(key_name)) {
      const storage_name = KEY_STORAGE_MAP[key_name] || key_name.toLowerCase();
      parts.push(storage_name);
    }
  }
  return parts.join("+");
}

// ── Hotkey capture (Python-side for Windows, JS-side for macOS) ──────────────

async function start_hotkey_capture(capture_el) {
  document.querySelectorAll(".hotkey-capture, .preset-hotkey-btn").forEach(el => el.classList.remove("capturing"));
  capture_el.classList.add("capturing");
  capture_el.textContent = "Press keys...";

  if (!IS_MACOS && window.pywebview && window.pywebview.api) {
    try {
      const captured_str = await window.pywebview.api.capture_hotkey();
      if (captured_str) {
        capture_el.textContent = format_hotkey_display(captured_str);
        capture_el.classList.remove("capturing");
        capture_el.dataset.storageValue = captured_str;
        on_hotkey_captured(capture_el, captured_str);
        return;
      }
    } catch (capture_error) {
      console.warn("Python capture failed, falling back to JS:", capture_error);
    }
  }

  hotkey_capturing = capture_el.id;
  captured_keys = new Set();
  capture_el.focus();
}

function on_hotkey_captured(capture_el, storage_str) {
  if (capture_el.id.startsWith("preset-hotkey-")) {
    const preset_index = parseInt(capture_el.id.replace("preset-hotkey-", ""));
    const updated_config = JSON.parse(JSON.stringify(app_config));
    if (updated_config.presets && updated_config.presets[preset_index]) {
      updated_config.presets[preset_index].hotkey = storage_str;
      save_config(updated_config);
    }
  }
}

document.querySelectorAll(".hotkey-capture").forEach(capture_el => {
  capture_el.addEventListener("click", () => start_hotkey_capture(capture_el));
});

document.addEventListener("keydown", (key_event) => {
  if (!hotkey_capturing) return;
  key_event.preventDefault();
  key_event.stopPropagation();
  captured_keys.add(key_event.key);
});

document.addEventListener("keyup", (key_event) => {
  if (!hotkey_capturing) return;
  key_event.preventDefault();
  key_event.stopPropagation();

  const non_modifiers = [...captured_keys].filter(k => !MODIFIER_KEYS.has(k));

  if (!MODIFIER_KEYS.has(key_event.key) || non_modifiers.length > 0) {
    const storage_str = hotkey_to_storage_string(captured_keys);
    const display_str = format_hotkey_display(storage_str);
    const capture_el = document.getElementById(hotkey_capturing);

    if (capture_el) {
      capture_el.textContent = display_str || "None";
      capture_el.classList.remove("capturing");
      capture_el.dataset.storageValue = storage_str;
      on_hotkey_captured(capture_el, storage_str);
    }
    hotkey_capturing = null;
    captured_keys = new Set();
  }
});

document.addEventListener("click", (click_event) => {
  if (!hotkey_capturing) return;
  const capture_el = document.getElementById(hotkey_capturing);
  if (capture_el && !capture_el.contains(click_event.target)) {
    capture_el.classList.remove("capturing");
    const existing_val = capture_el.dataset.storageValue;
    capture_el.textContent = existing_val ? format_hotkey_display(existing_val) : "None";
    hotkey_capturing = null;
    captured_keys = new Set();
  }
});

// ── Save ASR settings ────────────────────────────────────────────────────────

document.getElementById("save-asr-btn")?.addEventListener("click", async () => {
  const updated_config = JSON.parse(JSON.stringify(app_config));
  if (!updated_config.asr) updated_config.asr = {};
  updated_config.asr.model_size = document.getElementById("asr-model-size").value;
  updated_config.asr.device = document.getElementById("asr-device").value;
  const asr_lang = document.getElementById("asr-language").value;
  updated_config.asr.language = asr_lang || null;

  const success = await save_config(updated_config);
  show_save_status("save-asr-status", success);
});

// ── Hotkey conflict detection ────────────────────────────────────────────────

function collect_all_hotkeys(config_data, exclude_field) {
  const hotkey_map = {};
  if (exclude_field !== "hotkey" && config_data.hotkey) {
    hotkey_map["Record"] = config_data.hotkey;
  }
  if (exclude_field !== "mode_switch_hotkey" && config_data.mode_switch_hotkey) {
    hotkey_map["Mode Switch"] = config_data.mode_switch_hotkey;
  }
  const preset_list = config_data.presets || [];
  preset_list.forEach((preset_entry, preset_index) => {
    if (preset_entry.hotkey) {
      const preset_key = `preset_${preset_index}`;
      if (exclude_field !== preset_key) {
        hotkey_map[preset_entry.name || `Preset ${preset_index + 1}`] = preset_entry.hotkey;
      }
    }
  });
  return hotkey_map;
}

function find_hotkey_conflict(new_hotkey, config_data, exclude_field) {
  if (!new_hotkey) return null;
  const existing_map = collect_all_hotkeys(config_data, exclude_field);
  for (const [label, existing_hotkey] of Object.entries(existing_map)) {
    if (existing_hotkey === new_hotkey) return label;
  }
  return null;
}

// ── Save hotkeys ─────────────────────────────────────────────────────────────

document.getElementById("save-hotkeys-btn")?.addEventListener("click", async () => {
  const hotkey_record_el = document.getElementById("hotkey-record");
  const hotkey_mode_el = document.getElementById("hotkey-mode-switch");
  const updated_config = JSON.parse(JSON.stringify(app_config));

  const new_record = hotkey_record_el?.dataset.storageValue;
  const new_mode = hotkey_mode_el?.dataset.storageValue || "";

  if (new_record) {
    const conflict = find_hotkey_conflict(new_record, updated_config, "hotkey");
    if (conflict) {
      show_toast(`Record hotkey conflicts with "${conflict}"`);
      return;
    }
    updated_config.hotkey = new_record;
  }

  if (new_mode) {
    const conflict = find_hotkey_conflict(new_mode, updated_config, "mode_switch_hotkey");
    if (conflict) {
      show_toast(`Mode Switch hotkey conflicts with "${conflict}"`);
      return;
    }
  }
  updated_config.mode_switch_hotkey = new_mode;

  if (new_record && new_mode && new_record === new_mode) {
    show_toast("Record and Mode Switch hotkeys cannot be the same");
    return;
  }

  const success = await save_config(updated_config);
  show_save_status("save-hotkeys-status", success);
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

  const success = await save_config(updated_config);
  show_save_status("save-model-status", success);
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
    const hotkey_display = preset_entry.hotkey
      ? format_hotkey_display(preset_entry.hotkey)
      : "None";

    const preset_wrapper = document.createElement("div");

    const preset_item = document.createElement("div");
    preset_item.className = "preset-item";
    preset_item.innerHTML = `
      <div style="flex:1">
        <div class="preset-item-name">${preset_entry.name || "Unnamed"}</div>
        <div class="preset-item-meta">${preset_entry.processing || "direct"} · ${preset_entry.language || "source"}</div>
      </div>
      <div class="preset-hotkey-btn" id="preset-hotkey-${preset_index}" tabindex="0"
           data-storage-value="${preset_entry.hotkey || ""}" title="Click to change hotkey">${hotkey_display}</div>
      <button class="preset-item-edit" data-index="${preset_index}" title="Edit">✎</button>
      <button class="preset-item-delete" data-index="${preset_index}" title="Delete">✕</button>
    `;
    preset_wrapper.appendChild(preset_item);

    if (editing_preset_index === preset_index) {
      const edit_form = build_preset_edit_form(preset_entry, preset_index);
      preset_wrapper.appendChild(edit_form);
    }

    preset_list_el.appendChild(preset_wrapper);
  });

  preset_list_el.querySelectorAll(".preset-hotkey-btn").forEach(capture_el => {
    capture_el.addEventListener("click", (click_event) => {
      click_event.stopPropagation();
      start_hotkey_capture(capture_el);
    });
  });

  preset_list_el.querySelectorAll(".preset-item-edit").forEach(edit_btn => {
    edit_btn.addEventListener("click", () => {
      const preset_index = parseInt(edit_btn.dataset.index);
      if (editing_preset_index === preset_index) {
        editing_preset_index = -1;
      } else {
        editing_preset_index = preset_index;
      }
      render_preset_list(app_config.presets || []);
    });
  });

  preset_list_el.querySelectorAll(".preset-item-delete").forEach(delete_btn => {
    delete_btn.addEventListener("click", async () => {
      const preset_index = parseInt(delete_btn.dataset.index);
      const updated_config = JSON.parse(JSON.stringify(app_config));
      updated_config.presets.splice(preset_index, 1);
      editing_preset_index = -1;
      await save_config(updated_config);
    });
  });
}

function build_preset_edit_form(preset_entry, preset_index) {
  const form_el = document.createElement("div");
  form_el.className = "preset-edit-form";

  const processing_options = ["direct", "polish", "custom"].map(val =>
    `<option value="${val}" ${preset_entry.processing === val ? "selected" : ""}>${val.charAt(0).toUpperCase() + val.slice(1)}</option>`
  ).join("");

  const language_options = [
    { val: "source", label: "Original" },
    { val: "en", label: "English" },
    { val: "zh", label: "Chinese" },
  ].map(opt =>
    `<option value="${opt.val}" ${preset_entry.language === opt.val ? "selected" : ""}>${opt.label}</option>`
  ).join("");

  form_el.innerHTML = `
    <div class="form-row">
      <div class="form-label">Name</div>
      <input type="text" id="edit-preset-name-${preset_index}" value="${preset_entry.name || ""}">
    </div>
    <div class="form-row">
      <div class="form-label">Processing</div>
      <select id="edit-preset-processing-${preset_index}">${processing_options}</select>
    </div>
    <div class="form-row">
      <div class="form-label">Language</div>
      <select id="edit-preset-language-${preset_index}">${language_options}</select>
    </div>
    <div class="form-group">
      <div class="form-label" style="margin-bottom:4px">Custom Prompt</div>
      <textarea id="edit-preset-prompt-${preset_index}">${preset_entry.custom_prompt || ""}</textarea>
    </div>
    <div style="display:flex;gap:8px;">
      <button class="btn btn-primary" id="edit-preset-save-${preset_index}">Save</button>
      <button class="btn btn-secondary" id="edit-preset-cancel-${preset_index}">Cancel</button>
    </div>
  `;

  setTimeout(() => {
    document.getElementById(`edit-preset-save-${preset_index}`)?.addEventListener("click", async () => {
      const updated_config = JSON.parse(JSON.stringify(app_config));
      const preset = updated_config.presets[preset_index];
      preset.name = document.getElementById(`edit-preset-name-${preset_index}`).value.trim() || preset.name;
      preset.processing = document.getElementById(`edit-preset-processing-${preset_index}`).value;
      preset.language = document.getElementById(`edit-preset-language-${preset_index}`).value;
      preset.custom_prompt = document.getElementById(`edit-preset-prompt-${preset_index}`).value.trim();
      editing_preset_index = -1;
      await save_config(updated_config);
    });

    document.getElementById(`edit-preset-cancel-${preset_index}`)?.addEventListener("click", () => {
      editing_preset_index = -1;
      render_preset_list(app_config.presets || []);
    });
  }, 0);

  return form_el;
}

document.getElementById("add-preset-btn")?.addEventListener("click", async () => {
  const preset_name = document.getElementById("new-preset-name").value.trim();
  if (!preset_name) return;

  const hotkey_el = document.getElementById("new-preset-hotkey");
  const new_preset = {
    name: preset_name,
    hotkey: hotkey_el?.dataset.storageValue || "",
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
  if (hotkey_el) {
    hotkey_el.textContent = "Click to set";
    hotkey_el.dataset.storageValue = "";
  }
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
    const result = await window.pywebview.api.save_config(config_data);
    app_config = config_data;

    const current_theme = (config_data.ui || {}).theme || "system";
    apply_theme(current_theme);

    const current_presets = config_data.presets || [];
    render_preset_list(current_presets);
    return result !== false;
  } catch (save_error) {
    console.error("Failed to save config:", save_error);
    return false;
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
