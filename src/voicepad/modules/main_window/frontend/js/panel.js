const POLL_INTERVAL_MS = 100;
const BAR_COUNT = 5;

let current_state = "ready";

function apply_theme(theme_value) {
  if (theme_value === "system") {
    const prefers_dark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    document.documentElement.setAttribute("data-theme", prefers_dark ? "dark" : "light");
  } else {
    document.documentElement.setAttribute("data-theme", theme_value);
  }
}

function update_panel_state(status_data) {
  const new_state = status_data.state || "ready";
  const body_el = document.body;

  if (new_state !== current_state) {
    body_el.classList.remove("state-recording", "state-processing");
    if (new_state === "recording") {
      body_el.classList.add("state-recording");
    } else if (new_state === "processing") {
      body_el.classList.add("state-processing");
    }

    const status_label = document.getElementById("status-label");
    const mic_icon = document.querySelector(".icon-mic");
    const spin_icon = document.querySelector(".icon-spin");

    if (new_state === "recording") {
      status_label.textContent = "Recording";
      mic_icon.style.display = "";
      spin_icon.style.display = "none";
    } else if (new_state === "processing") {
      status_label.textContent = "Processing";
      mic_icon.style.display = "none";
      spin_icon.style.display = "";
    } else {
      status_label.textContent = "Ready";
      mic_icon.style.display = "";
      spin_icon.style.display = "none";
    }

    current_state = new_state;
  }

  const preset_name_el = document.getElementById("preset-name");
  if (status_data.preset_name) {
    preset_name_el.textContent = status_data.preset_name;
  }

  const mode_language_el = document.getElementById("mode-language");
  if (status_data.mode_label) {
    mode_language_el.textContent = status_data.mode_label;
  }

  const hotkey_hint_el = document.getElementById("hotkey-hint");
  if (status_data.hotkey_display) {
    hotkey_hint_el.textContent = status_data.hotkey_display;
  }

  update_volume_bars(status_data.volume_level || 0);
}

function update_volume_bars(volume_level) {
  for (let bar_index = 0; bar_index < BAR_COUNT; bar_index++) {
    const bar_el = document.getElementById("bar" + bar_index);
    if (!bar_el) continue;

    const base_height = 4 + bar_index * 3;
    const random_factor = 0.6 + Math.random() * 0.8;
    const computed_height = base_height + volume_level * 16 * random_factor;
    bar_el.style.height = Math.min(computed_height, 24) + "px";
  }
}

async function poll_status() {
  try {
    if (window.pywebview && window.pywebview.api) {
      const status_data = await window.pywebview.api.get_status();
      if (status_data) {
        update_panel_state(status_data);
        if (status_data.theme) {
          apply_theme(status_data.theme);
        }
      }
    }
  } catch (poll_error) {
    // silently ignore poll failures
  }
  setTimeout(poll_status, POLL_INTERVAL_MS);
}

document.getElementById("settings-btn").addEventListener("click", () => {
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.open_settings();
  }
});

window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
  const root_el = document.documentElement;
  if (root_el.getAttribute("data-theme") === "dark" || root_el.getAttribute("data-theme") === "light") {
    return;
  }
  apply_theme("system");
});

window.addEventListener("pywebviewready", () => {
  poll_status();
});

// Fallback in case pywebviewready already fired or fires late
setTimeout(() => {
  if (window.pywebview) {
    poll_status();
  }
}, 200);
