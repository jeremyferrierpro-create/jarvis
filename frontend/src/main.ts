/**
 * J.A.R.V.I.S — Interface Web avec Orbe Three.js
 *
 * Se connecte au backend Python via WebSocket (ws://localhost:8765),
 * recoit les changements d'etat et pilote l'orbe en consequence.
 *
 * Etats: "idle" | "listening" | "thinking" | "speaking"
 */

import { createOrb, type OrbState } from "./orb";
import { injectVisionButton, captureFrame } from "./screen_capture";
import { initJarvisGlobe } from "./globe";
import { activerHolo, desactiverHolo } from "./hologramme";
import "./style.css";

// ── Config ────────────────────────────────────────────────────────────────────
const WS_URL = `ws://${window.location.hostname}:8765`;
const RECONNECT_INTERVAL_MS = 2_000;

// ── Boot sequence state ───────────────────────────────────────────────────────
let bootConnectedCallback: (() => void) | null = null;
let wsConnectedBeforeBoot = false;

// ── DOM refs ──────────────────────────────────────────────────────────────────
const canvas = document.getElementById("orb-canvas") as HTMLCanvasElement;
const statusEl = document.getElementById("status-text") as HTMLDivElement;
const errorEl = document.getElementById("error-text") as HTMLDivElement;
const badgeEl = document.getElementById("connection-badge") as HTMLDivElement;
const badgeLabelEl = document.getElementById(
  "connection-label"
) as HTMLSpanElement;
const muteButtonEl = document.getElementById("mute-button") as HTMLButtonElement;
const gpuButtonEl = document.getElementById("gpu-button") as HTMLButtonElement;
const helpOverlayEl = document.getElementById("help-overlay") as HTMLDivElement;
const timerHudEl = document.getElementById("timer-hud") as HTMLDivElement;
const timerDisplayEl = document.getElementById("timer-display") as HTMLDivElement;
const timerProgressEl = document.getElementById("timer-progress") as HTMLDivElement;
const subtitleToggleButtonEl = document.getElementById("subtitle-toggle") as HTMLButtonElement;
const keyboardToggleButtonEl = document.getElementById("keyboard-toggle") as HTMLButtonElement;
const keyboardHudEl = document.getElementById("keyboard-hud") as HTMLDivElement;
const keyboardInputEl = document.getElementById("keyboard-input") as HTMLInputElement;
const docUploadBtnEl = document.getElementById("doc-upload-btn") as HTMLButtonElement;
const docFileInputEl = document.getElementById("doc-file-input") as HTMLInputElement;
const docUploadPanelEl = document.getElementById("doc-upload-panel") as HTMLDivElement;
const docDropZoneEl = document.getElementById("doc-drop-zone") as HTMLDivElement;
const docUploadListEl = document.getElementById("doc-upload-list") as HTMLUListElement;
const docUploadStatusEl = document.getElementById("doc-upload-status") as HTMLDivElement;
const docContextSelectEl = document.getElementById("doc-context-select") as HTMLSelectElement;
const docPanelCloseEl = document.getElementById("doc-panel-close") as HTMLButtonElement;
const docScanBtnEl = document.getElementById("doc-scan-btn") as HTMLButtonElement;

const MAX_DOC_BYTES = 12 * 1024 * 1024;

const settingsButtonEl = document.getElementById("settings-button") as HTMLButtonElement;
const holoButtonEl = document.getElementById("holo-button") as HTMLButtonElement;
const micBtnEl = document.getElementById("mic-btn") as HTMLButtonElement;
const settingsModalEl = document.getElementById("settings-modal") as HTMLDivElement;
const settingsCloseBtn = document.getElementById("settings-close-btn") as HTMLSpanElement;
const settingsNameEl = document.getElementById("settings-name") as HTMLInputElement;
const settingsAgeEl = document.getElementById("settings-age") as HTMLInputElement;
const settingsAppsListEl = document.getElementById("settings-apps-list") as HTMLDivElement;
const appAddNameEl = document.getElementById("app-add-name") as HTMLInputElement;
const appAddPathEl = document.getElementById("app-add-path") as HTMLInputElement;
const appAddBtn = document.getElementById("app-add-btn") as HTMLButtonElement;
const settingsSaveBtn = document.getElementById("settings-save-btn") as HTMLButtonElement;
const settingsMicEl = document.getElementById("settings-mic") as HTMLSelectElement;
const settingsMusiqueLienEl = document.getElementById("settings-musique-lien") as HTMLInputElement;
const haEntitiesListEl = document.getElementById("ha-entities-list") as HTMLDivElement;
const haAddNomEl = document.getElementById("ha-add-nom") as HTMLInputElement;
const haAddEntityEl = document.getElementById("ha-add-entity") as HTMLInputElement;
const haAddBtn = document.getElementById("ha-add-btn") as HTMLButtonElement;

let currentCustomApps: { id: string, label: string, exe_path: string }[] = [];

type HaEntry = { nom: string; entity_id: string };
type HaTab = "lumieres" | "prises" | "capteurs";
let currentHaEntities: Record<HaTab, HaEntry[]> = { lumieres: [], prises: [], capteurs: [] };
let currentHaTab: HaTab = "lumieres";

let subtitlesEnabled = true;
let keyboardEnabled = false;

let timerInterval: number | null = null;
let timerSeconds = 0;
let timerTotalSeconds = 0;

const HELP_COMMANDS = [
  "Affiche la terre",
  "Où se trouve Tokyo ?",
  "Trace l'itinéraire Paris à Lyon",
  "Quelle heure est-il ?",
  "Ouvre Spotify",
  "Mets de la musique",
  "Prends une capture d'écran",
  "Mets en pause la lecture",
  "Augmente le volume",
  "Ferme le globe",
  "Lance une recherche sur YouTube",
  "Quelle est la météo ?",
  "Rappelle-moi de faire les courses",
  "Vérifie mes e-mails",
  "Raconte-moi une blague",
  "Lance le mode protocole",
  "Vérifie l'état du système",
  "Analyse les fichiers récents",
  "Active la vision",
  "Ouvre mon dossier Bureau",
  "Quel temps fait-il à New York ?",
  "Cherche sur Wikipédia l'intelligence artificielle",
  "Mets le volume à 50%",
  "Quelles sont les dernières news ?",
  "Lance le téléchargement",
  "Convertis ce fichier en PDF",
  "Ouvre mon TikTok",
  "Montre-moi les photos de vacances"
];

// ── Orb ───────────────────────────────────────────────────────────────────────
const orb = createOrb(canvas);

// ── State labels (French) ────────────────────────────────────────────────────
const STATE_LABELS: Record<OrbState, string> = {
  idle: "",
  listening: "ecoute...",
  thinking: "reflexion...",
  speaking: "",
};

function applyState(state: OrbState): void {
  orb.setState(state);
  statusEl.textContent = STATE_LABELS[state];
  if (state === "listening" || (state as string) === "active") {
    micBtnEl.classList.add("mic-active");
  } else {
    micBtnEl.classList.remove("mic-active");
  }
}

function setMuted(muted: boolean): void {
  muteButtonEl.classList.toggle("is-muted", muted);
  muteButtonEl.setAttribute("aria-pressed", String(muted));
}

// ── Error toast ───────────────────────────────────────────────────────────────
let errorTimer: ReturnType<typeof setTimeout> | null = null;

function showError(msg: string): void {
  errorEl.textContent = msg;
  errorEl.style.opacity = "1";
  if (errorTimer) clearTimeout(errorTimer);
  errorTimer = setTimeout(() => {
    errorEl.style.opacity = "0";
  }, 4_000);
}

// ── Connection badge ──────────────────────────────────────────────────────────
function setConnected(ok: boolean): void {
  badgeEl.classList.toggle("connected", ok);
  badgeEl.classList.toggle("disconnected", !ok);
  badgeLabelEl.textContent = ok ? "connecte" : "reconnexion";
  muteButtonEl.disabled = !ok;
}

// ── WebSocket with auto-reconnect ─────────────────────────────────────────────
let ws: WebSocket | null = null;
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

function connect(): void {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }

  ws = new WebSocket(WS_URL);

  ws.addEventListener("open", () => {
    setConnected(true);
    // Notifie la séquence de boot que le serveur est prêt
    if (bootConnectedCallback) {
      bootConnectedCallback();
      bootConnectedCallback = null;
    } else {
      wsConnectedBeforeBoot = true;
    }
  });

  ws.addEventListener("message", async (event: MessageEvent) => {
    try {
      const data = JSON.parse(event.data as string) as {
        state?: string;
        action?: string;
        muted?: boolean;
        volume?: number;
        id?: string;
        duration?: number;
        text?: string;
        type?: string;
        version?: string;
        url?: string;
        cpu?: number;
        ram?: number;
        data?: Record<string, unknown>;
      };

      if (data.action === "request_screen_capture") {
        const frame = await captureFrame();
        if (frame && ws && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({
            type: "screen_frame",
            id: data.id,
            data: frame,
          }));
        } else if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({
            type: "screen_frame",
            id: data.id,
            error: "no_stream",
          }));
        }
        return;
      }

      if (data.type === "document_scan_result") {
        const m = (data as { message?: string }).message || "Scan termine";
        setDocStatus(m.slice(0, 120), "ok");
        return;
      }

      if (data.type === "document_upload_result") {
        const ok = (data as { ok?: boolean }).ok;
        const fn = (data as { filename?: string }).filename || "fichier";
        const err = (data as { error?: string }).error;
        const resume = (data as { resume?: string }).resume;
        if (ok) {
          setDocStatus(`✔ ${fn} analysé`, "ok");
          if (resume) {
            const li = document.createElement("li");
            li.textContent = `${fn} — ${resume.slice(0, 80)}…`;
            docUploadListEl.prepend(li);
          }
        } else {
          setDocStatus(`✕ ${err || "Erreur"}`, "err");
        }
        return;
      }

      if (data.type === "documents_list") {
        const docs = (data as { documents?: { filename: string; chars: number; date: string }[] }).documents || [];
        docUploadListEl.innerHTML = "";
        docs.slice().reverse().forEach(d => {
          const li = document.createElement("li");
          li.textContent = `${d.filename} (${d.chars} car.) — ${d.date}`;
          docUploadListEl.appendChild(li);
        });
        return;
      }

      if (data.type === "mic_state") {
        if (data.muted) {
          micBtnEl.classList.add("mic-muted");
          micBtnEl.classList.remove("mic-active");
        } else {
          micBtnEl.classList.remove("mic-muted");
        }
        return;
      }

      if (data.type === "settings_data" && data.data) {
        const settings = data.data as any;
        if (settings.user_name) settingsNameEl.value = settings.user_name;
        if (settings.user_age) settingsAgeEl.value = settings.user_age;
        // Populate microphone list
        if (settings.mic_list && Array.isArray(settings.mic_list)) {
          settingsMicEl.innerHTML = '<option value="">-- Détection automatique --</option>';
          (settings.mic_list as {index: number, name: string}[]).forEach(m => {
            const opt = document.createElement("option");
            opt.value = String(m.index);
            opt.textContent = `[${m.index}] ${m.name}`;
            if (m.index === settings.mic_device_index) opt.selected = true;
            settingsMicEl.appendChild(opt);
          });
        }
        if (settings.custom_apps) {
          currentCustomApps = settings.custom_apps;
          renderCustomApps();
        }
        if (settings.ha_custom_entities) {
          currentHaEntities = {
            lumieres: settings.ha_custom_entities.lumieres || [],
            prises:   settings.ha_custom_entities.prises   || [],
            capteurs: settings.ha_custom_entities.capteurs || [],
          };
        } else {
          currentHaEntities = { lumieres: [], prises: [], capteurs: [] };
        }
        renderHaEntities();
        settingsMusiqueLienEl.value = settings.musique_lien || "";
        return;
      }

      if (data.action === "help") {
        showHelpHUD();
        return;
      }
      if (data.action === "timer_start") {
        startTimer(data.duration || 0);
        return;
      }
      if (data.action === "timer_stop") {
        stopTimer();
        return;
      }
      if (data.action === "timer_add") {
        addTimer(data.duration || 60);
        return;
      }
      if (data.action === "timer_remove") {
        removeTimer(data.duration || 60);
        return;
      }
      if (data.action === "demo") {
        orb.triggerDemo();
        return;
      }
      // ── Globe 3D Navigation ─────────────────────────────────────────
      if (data.action === "jarvis_globe") {
        if (typeof (window as any).jarvisGlobe === "function") {
          (window as any).jarvisGlobe(data);
        }
        return;
      }
      if (data.action === "set_volume" && typeof data.volume === "number") {
        orb.setVolume(data.volume);
        return;
      }
      if (data.action === "jarvis_text" && typeof data.text === "string") {
        showSubtitles(data.text);
        return;
      }
      if (data.type === "update_available") {
        const banner = document.getElementById("update-banner");
        if (banner) {
          banner.style.display = "block";
          banner.textContent = `SYSTEM_UPDATE_AVAILABLE_V${data.version}`;
          banner.onclick = () => {
            window.open(data.url, "_blank");
          };
        }
        return;
      }

      if (data.action === "system_stats") {
        const cpuVal = document.getElementById("cpu-value");
        const ramVal = document.getElementById("ram-value");
        const cpuHud = document.getElementById("cpu-hud");
        const ramHud = document.getElementById("ram-hud");

        if (cpuVal && typeof data.cpu === "number") {
          cpuVal.textContent = `${Math.round(data.cpu)}%`;
          cpuHud?.classList.toggle("stat-critical", data.cpu > 90);
        }
        if (ramVal && typeof data.ram === "number") {
          ramVal.textContent = `${Math.round(data.ram)}%`;
          ramHud?.classList.toggle("stat-critical", data.ram > 90);
        }
        return;
      }

      if (data.action === "temp_panel" && data.data) {
        showTempPanel(data.data as Parameters<typeof showTempPanel>[0]);
      }

      if (data.action === "weather_panel" && data.data) {
        showWeatherPanel(data.data as Parameters<typeof showWeatherPanel>[0]);
      }

      if (data.type === "show_recipe") {
        const modal = document.getElementById("recipe-modal");
        const titleEl = document.getElementById("recipe-title");
        const ingListEl = document.getElementById("recipe-ingredients-list");
        const instListEl = document.getElementById("recipe-instructions-list");

        if (modal && titleEl && ingListEl && instListEl) {
          titleEl.textContent = (data as any).titre || "RECETTE J.A.R.V.I.S";

          ingListEl.innerHTML = "";
          const ingredients = (data as any).ingredients || [];
          ingredients.forEach((ing: string) => {
            const li = document.createElement("li");
            li.textContent = ing;
            ingListEl.appendChild(li);
          });

          instListEl.innerHTML = "";
          const instructions = (data as any).instructions || [];
          instructions.forEach((inst: string) => {
            const li = document.createElement("li");
            li.textContent = inst;
            instListEl.appendChild(li);
          });

          modal.classList.remove("hidden");
        }
        return;
      }

      if (data.state) {
        applyState(data.state as OrbState);
      }
      if (typeof data.volume === "number") {
        orb.setVolume(data.volume);
      }
      if (typeof data.muted === "boolean") {
        setMuted(data.muted);
      }
    } catch {
      // ignore malformed messages
    }
  });

  ws.addEventListener("close", () => {
    setConnected(false);
    applyState("idle");
    scheduleReconnect();
  });

  ws.addEventListener("error", () => {
    setConnected(false);
  });
}

// ── Subtitles HUD Logic ──────────────────────────────────────────────────────
let subtitleTimer: number | null = null;
let subtitleTypeInterval: number | null = null;

function showSubtitles(text: string) {
  const container = document.getElementById("subtitle-hud")!;
  const textEl = document.getElementById("subtitle-text")!;
  const metaEl = document.getElementById("subtitle-meta")!;

  // Clear any existing animation
  if (subtitleTimer) clearTimeout(subtitleTimer);
  if (subtitleTypeInterval) clearInterval(subtitleTypeInterval);

  if (!subtitlesEnabled) {
    container.style.display = "none";
    return;
  }

  container.style.display = "block";
  textEl.textContent = "";
  metaEl.textContent = "DECRYPTING_RESPONSE...";
  metaEl.style.color = "rgba(0, 229, 255, 0.4)";

  let i = 0;
  // Faster for long text (news), slower for short phrases
  const speed = text.length > 100 ? 15 : 25;

  subtitleTypeInterval = window.setInterval(() => {
    if (i < text.length) {
      // Add a bit of "glitch" feel by sometimes adding random chars before the real one
      textEl.textContent += text.charAt(i);
      i++;

      // Auto-scroll if it's long? (The box is fixed width/max-width)
    } else {
      if (subtitleTypeInterval) clearInterval(subtitleTypeInterval);
      metaEl.textContent = "DECRYPTION_COMPLETE [STABLE]";
      metaEl.style.color = "#22c55e";

      // Hide after a delay proportional to text length
      const delay = Math.max(3000, text.length * 50);
      subtitleTimer = window.setTimeout(() => {
        container.style.display = "none";
      }, delay);
    }
  }, speed);
}

function scheduleReconnect(): void {
  if (reconnectTimer) return;
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null;
    connect();
  }, RECONNECT_INTERVAL_MS);
}

// ── Events ──────────────────────────────────────────────────────────────────
muteButtonEl.addEventListener("click", () => {
  if (!ws || ws.readyState !== WebSocket.OPEN) return;

  // Envoi du signal stop au backend
  ws.send(JSON.stringify({ type: "stop_audio" }));

  // Feedback immédiat sur l'orbe
  applyState("idle");
});

gpuButtonEl.addEventListener("click", () => {
  const isPressed = gpuButtonEl.getAttribute("aria-pressed") === "true";
  const newState = !isPressed;
  gpuButtonEl.setAttribute("aria-pressed", newState.toString());

  if (newState) {
    orb.setQuality("high");
    // Feedback visuel / textuel
    console.log("GPU Acceleration Enabled");
  } else {
    orb.setQuality("low");
    console.log("GPU Acceleration Disabled");
  }
});

subtitleToggleButtonEl.addEventListener("click", () => {
  subtitlesEnabled = !subtitlesEnabled;
  subtitleToggleButtonEl.setAttribute("aria-pressed", subtitlesEnabled.toString());
  subtitleToggleButtonEl.textContent = subtitlesEnabled ? "HUD TEXT" : "TEXT OFF";

  if (!subtitlesEnabled) {
    document.getElementById("subtitle-hud")!.style.display = "none";
  }
});

keyboardToggleButtonEl.addEventListener("click", () => {
  keyboardEnabled = !keyboardEnabled;
  keyboardToggleButtonEl.setAttribute("aria-pressed", keyboardEnabled.toString());
  keyboardHudEl.style.display = keyboardEnabled ? "block" : "none";

  if (keyboardEnabled) {
    setTimeout(() => keyboardInputEl.focus(), 100);
  }
});

keyboardInputEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    const val = keyboardInputEl.value.trim();
    if (val && ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "user_input", text: val }));
      keyboardInputEl.value = "";
    }
  }
});

function setDocStatus(msg: string, kind: "ok" | "err" | "wait" = "wait") {
  docUploadStatusEl.textContent = msg;
  docUploadStatusEl.className = "doc-upload-status " + kind;
}

function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}

async function uploadDocumentFile(file: File) {
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    setDocStatus("WebSocket non connecté", "err");
    return;
  }
  if (file.size > MAX_DOC_BYTES) {
    setDocStatus(`Fichier trop gros (max 12 Mo) : ${file.name}`, "err");
    return;
  }
  setDocStatus(`Analyse de ${file.name}…`, "wait");
  try {
    const b64 = await fileToBase64(file);
    ws.send(JSON.stringify({
      type: "document_upload",
      filename: file.name,
      data: b64,
      context: docContextSelectEl.value || "general",
    }));
  } catch {
    setDocStatus("Erreur lecture fichier", "err");
  }
}

async function handleDocFiles(files: FileList | File[]) {
  for (const file of Array.from(files)) {
    await uploadDocumentFile(file);
  }
}

docUploadBtnEl?.addEventListener("click", () => {
  const open = docUploadPanelEl.classList.toggle("visible");
  docUploadBtnEl.setAttribute("aria-pressed", open ? "true" : "false");
  if (open && ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: "list_documents" }));
  }
});

docPanelCloseEl?.addEventListener("click", () => {
  docUploadPanelEl.classList.remove("visible");
  docUploadBtnEl.setAttribute("aria-pressed", "false");
});

docScanBtnEl?.addEventListener("click", () => {
  if (!ws || ws.readyState !== WebSocket.OPEN) return;
  setDocStatus("Analyse cognitive en cours…", "wait");
  ws.send(JSON.stringify({ type: "document_scan" }));
});

docDropZoneEl?.addEventListener("click", () => docFileInputEl?.click());

docFileInputEl?.addEventListener("change", () => {
  if (docFileInputEl.files?.length) {
    void handleDocFiles(docFileInputEl.files);
    docFileInputEl.value = "";
  }
});

docDropZoneEl?.addEventListener("dragover", (e) => {
  e.preventDefault();
  docDropZoneEl.classList.add("dragover");
});

docDropZoneEl?.addEventListener("dragleave", () => {
  docDropZoneEl.classList.remove("dragover");
});

docDropZoneEl?.addEventListener("drop", (e) => {
  e.preventDefault();
  docDropZoneEl.classList.remove("dragover");
  if (e.dataTransfer?.files?.length) {
    void handleDocFiles(e.dataTransfer.files);
  }
});

// ── Mic button (toggle mute) ──────────────────────────────────────────────────
micBtnEl.addEventListener("click", () => {
  if (!ws || ws.readyState !== WebSocket.OPEN) return;
  ws.send(JSON.stringify({ type: "toggle_mic" }));
});

// ── Fullscreen (pywebview) ───────────────────────────────────────────────────
const fullscreenBtn = document.getElementById("fullscreen-btn") as HTMLButtonElement;
let _isFullscreen = false;

function updateFsIcon() {
  if (!fullscreenBtn) return;
  fullscreenBtn.innerHTML = _isFullscreen ? "&#x2715;" : "&#x26F6;";
  fullscreenBtn.title     = _isFullscreen ? "Quitter le plein écran" : "Plein écran";
}

fullscreenBtn?.addEventListener("click", () => {
  if (!ws || ws.readyState !== WebSocket.OPEN) return;
  ws.send(JSON.stringify({ type: "toggle_fullscreen" }));
  _isFullscreen = !_isFullscreen;
  updateFsIcon();
});

// ── Settings UI Logic ────────────────────────────────────────────────────────
settingsButtonEl.addEventListener("click", () => {
  settingsModalEl.classList.add("visible");
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: "get_settings" }));
  }
});

settingsCloseBtn.addEventListener("click", () => {
  settingsModalEl.classList.remove("visible");
});

// ── Hologramme mode toggle ────────────────────────────────────────────────────
let _holoActive = false;
const _holoOverlay = document.getElementById("holo-overlay") as HTMLDivElement;

function _openHolo() {
  _holoActive = true;
  _holoOverlay.style.display = "block";
  holoButtonEl.setAttribute("aria-pressed", "true");
  activerHolo();
}

function _closeHolo() {
  _holoActive = false;
  desactiverHolo();
  _holoOverlay.style.display = "none";
  holoButtonEl.setAttribute("aria-pressed", "false");
}

holoButtonEl?.addEventListener("click", () => {
  if (_holoActive) _closeHolo(); else _openHolo();
});

document.getElementById("holo-close-btn")?.addEventListener("click", _closeHolo);

// Record hologramme — persisté en localStorage, affiché visuellement dans le jeu

function renderCustomApps() {
  settingsAppsListEl.innerHTML = "";
  currentCustomApps.forEach((app, index) => {
    const div = document.createElement("div");
    div.className = "settings-app-item";
    div.innerHTML = `
      <div><strong>${app.label}</strong> <br> <span style="font-size:10px;color:rgba(0,229,255,0.5)">${app.exe_path.replace(/\\/g, '\\\\')}</span></div>
      <div class="settings-app-remove" data-index="${index}">[ X ]</div>
    `;
    settingsAppsListEl.appendChild(div);
  });

  document.querySelectorAll(".settings-app-remove").forEach(btn => {
    btn.addEventListener("click", (e) => {
      const idx = parseInt((e.target as HTMLElement).getAttribute("data-index") || "0", 10);
      currentCustomApps.splice(idx, 1);
      renderCustomApps();
    });
  });
}

appAddBtn.addEventListener("click", () => {
  const name = appAddNameEl.value.trim();
  const path = appAddPathEl.value.trim();
  if (name && path) {
    const id = name.toLowerCase().replace(/[^a-z0-9]/g, "_");
    currentCustomApps.push({ id, label: name, exe_path: path });
    appAddNameEl.value = "";
    appAddPathEl.value = "";
    renderCustomApps();
  }
});

settingsSaveBtn.addEventListener("click", () => {
  const micVal = settingsMicEl.value;
  const settings = {
    user_name: settingsNameEl.value.trim(),
    user_age: settingsAgeEl.value.trim(),
    mic_device_index: micVal !== "" ? parseInt(micVal, 10) : null,
    custom_apps: currentCustomApps,
    ha_custom_entities: currentHaEntities,
    musique_lien: settingsMusiqueLienEl.value.trim(),
  };

  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: "update_settings", settings }));
  }

  settingsModalEl.classList.remove("visible");
});

// ── HA Entities UI ────────────────────────────────────────────────────────────
function renderHaEntities() {
  haEntitiesListEl.innerHTML = "";
  const entries = currentHaEntities[currentHaTab];
  if (entries.length === 0) {
    const empty = document.createElement("div");
    empty.style.cssText = "padding:10px;font-size:11px;color:rgba(0,229,255,0.3);text-align:center;";
    empty.textContent = "Aucun appareil — ajoutez-en un ci-dessous";
    haEntitiesListEl.appendChild(empty);
    return;
  }
  entries.forEach((entry, index) => {
    const div = document.createElement("div");
    div.className = "settings-app-item";
    div.innerHTML = `
      <div>
        <strong style="text-transform:capitalize">${entry.nom}</strong>
        <br><span style="font-size:10px;color:rgba(0,229,255,0.45)">${entry.entity_id}</span>
      </div>
      <div class="settings-app-remove ha-remove" data-index="${index}">[ X ]</div>
    `;
    haEntitiesListEl.appendChild(div);
  });
  document.querySelectorAll(".ha-remove").forEach(btn => {
    btn.addEventListener("click", (e) => {
      const idx = parseInt((e.target as HTMLElement).getAttribute("data-index") || "0", 10);
      currentHaEntities[currentHaTab].splice(idx, 1);
      renderHaEntities();
    });
  });
}

document.querySelectorAll(".ha-tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".ha-tab-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    currentHaTab = (btn as HTMLElement).dataset.tab as HaTab;
    renderHaEntities();
  });
});

haAddBtn.addEventListener("click", () => {
  const nom = haAddNomEl.value.trim();
  const entity_id = haAddEntityEl.value.trim();
  if (nom && entity_id) {
    currentHaEntities[currentHaTab].push({ nom, entity_id });
    haAddNomEl.value = "";
    haAddEntityEl.value = "";
    renderHaEntities();
  }
});

// ── Boot Sequence ─────────────────────────────────────────────────────────────
function runBootSequence(): void {
  const overlay    = document.getElementById("boot-overlay") as HTMLDivElement;
  const modulesEl  = document.getElementById("boot-modules") as HTMLDivElement;
  const progressBar = document.getElementById("boot-progress-bar") as HTMLDivElement;
  const progressLbl = document.getElementById("boot-progress-label") as HTMLDivElement;
  const statusText  = document.getElementById("boot-status-text") as HTMLDivElement;
  const finalText   = document.getElementById("boot-final-text") as HTMLDivElement;
  const buildYear   = document.getElementById("boot-build-year") as HTMLSpanElement;

  if (!overlay) return;
  if (buildYear) buildYear.textContent = new Date().getFullYear().toString();

  const MODULES = [
    "NEURAL_NETWORK_CORE",
    "SPEECH_RECOGNITION",
    "KNOWLEDGE_DATABASE",
    "VISION_SYSTEM",
    "AUDIO_SYNTHESIS_TTS",
    "HOME_AUTOMATION_LINK",
    "COMM_PROTOCOLS",
  ];

  const TOTAL = MODULES.length + 1; // +1 pour la connexion serveur
  let done = 0;

  function setProgress(n: number) {
    const pct = Math.round((n / TOTAL) * 100);
    progressBar.style.width = `${pct}%`;
    progressLbl.textContent = `CHARGEMENT... ${pct}%`;
  }

  function addLine(name: string): HTMLDivElement {
    const div = document.createElement("div");
    div.className = "boot-module-line";
    div.innerHTML = `
      <span class="boot-module-name">${name}</span>
      <span class="boot-module-dots"></span>
      <span class="boot-module-status pending">INITIALISATION</span>
    `;
    modulesEl.appendChild(div);
    return div;
  }

  function setLineOnline(line: HTMLDivElement, mode: "ok" | "wait" = "ok") {
    const s = line.querySelector(".boot-module-status") as HTMLSpanElement;
    s.classList.remove("pending");
    if (mode === "ok") {
      s.textContent = "[ ONLINE ]";
      s.classList.add("online");
      done++;
      setProgress(done);
    } else {
      s.textContent = "[ EN ATTENTE ]";
      s.classList.add("waiting");
    }
  }

  function finishBoot() {
    setProgress(TOTAL);
    progressLbl.textContent = "CHARGEMENT... 100%";
    statusText.textContent = "SYSTÈMES OPÉRATIONNELS — BONNE JOURNÉE";
    finalText.style.opacity = "1";
    finalText.style.transform = "scale(1)";

    setTimeout(() => {
      overlay.style.opacity = "0";
      setTimeout(() => { overlay.style.display = "none"; }, 900);
    }, 1600);
  }

  // Défilement des modules locaux (~280 ms entre chaque)
  MODULES.forEach((name, i) => {
    const delay = 250 + i * 280;
    setTimeout(() => {
      const line = addLine(name);
      setTimeout(() => setLineOnline(line, "ok"), 200);
    }, delay);
  });

  // Module serveur — attend la connexion WebSocket
  const serverDelay = 250 + MODULES.length * 280;
  setTimeout(() => {
    const line = addLine("SERVER_CONNECTION");
    statusText.textContent = "CONNEXION AU SERVEUR EN COURS...";

    if (wsConnectedBeforeBoot) {
      // WS déjà connecté avant cette étape
      setTimeout(() => { setLineOnline(line, "ok"); setTimeout(finishBoot, 350); }, 250);
    } else {
      setLineOnline(line, "wait");
      bootConnectedCallback = () => {
        const s = line.querySelector(".boot-module-status") as HTMLSpanElement;
        s.classList.remove("waiting");
        s.textContent = "[ ONLINE ]";
        s.classList.add("online");
        done++;
        setTimeout(finishBoot, 350);
      };
      // Sécurité : ferme le boot après 25 s si le serveur ne répond pas
      setTimeout(() => {
        if (bootConnectedCallback) {
          bootConnectedCallback = null;
          overlay.style.opacity = "0";
          setTimeout(() => { overlay.style.display = "none"; }, 900);
        }
      }, 25_000);
    }
  }, serverDelay);
}

// ── Boot ──────────────────────────────────────────────────────────────────────
setConnected(false);
applyState("idle");
setMuted(false);
injectVisionButton();
initJarvisGlobe();
runBootSequence();

// Masquer le message d'aide après 10 secondes
setTimeout(() => {
  const tip = document.getElementById("user-tip");
  if (tip) {
    tip.style.opacity = "0";
    setTimeout(() => { tip.style.display = "none"; }, 1000);
  }
}, 10000);
// ── Help HUD Logic ───────────────────────────────────────────────────────────
function showHelpHUD() {
  helpOverlayEl.style.display = "block";
  helpOverlayEl.innerHTML = "";

  // Select 16 random commands
  const shuffled = [...HELP_COMMANDS].sort(() => 0.5 - Math.random());
  const selected = shuffled.slice(0, 16);

  selected.forEach((cmd, i) => {
    const isRight = i % 2 === 1;
    const widget = document.createElement("div");
    widget.className = `help-widget ${isRight ? 'right' : ''}`;

    // Grid-like positioning with random offsets (starting lower to avoid the tip)
    const row = Math.floor(i / 2);
    const top = 160 + (row * 95) + (Math.random() * 15);
    widget.style.top = `${top}px`;

    // Position them more towards the center to "fill around"
    const sideOffset = 30 + (Math.random() * 40);
    if (isRight) widget.style.right = `${sideOffset}px`;
    else widget.style.left = `${sideOffset}px`;

    // Faster reveal and varied animations
    widget.style.animation = `float ${2 + Math.random() * 2}s ease-in-out infinite`;
    widget.style.animationDelay = `${Math.random() * 1}s`;

    widget.innerHTML = `
      <div class="help-widget-title" style="display:flex; justify-content: space-between;">
        <span>CAPACITÉ ${Math.floor(Math.random() * 999)}</span>
        <span style="opacity:0.3">[SYNC]</span>
      </div>
      <div class="help-widget-cmd">"${cmd}"</div>
    `;

    helpOverlayEl.appendChild(widget);

    // Cinematic reveal synchronized with speech (one widget every 800ms)
    setTimeout(() => widget.classList.add("visible"), i * 800);
  });

  // Auto-hide after 20 seconds
  setTimeout(() => {
    const widgets = document.querySelectorAll(".help-widget");
    widgets.forEach((w, i) => {
      setTimeout(() => w.classList.remove("visible"), i * 100);
    });
    setTimeout(() => helpOverlayEl.style.display = "none", 2000);
  }, 20000);
}

// ── Timer Logic ─────────────────────────────────────────────────────────────
function startTimer(duration: number) {
  stopTimer();
  timerSeconds = duration;
  timerTotalSeconds = duration;
  timerHudEl.style.display = "block";
  updateTimerDisplay();

  timerInterval = window.setInterval(() => {
    timerSeconds--;
    updateTimerDisplay();
    if (timerSeconds <= 0) {
      timerDisplayEl.textContent = "FINISH";
      timerDisplayEl.style.color = "#ff3d00";
      setTimeout(() => stopTimer(), 3000);
    }
  }, 1000);
}

function stopTimer() {
  if (timerInterval) {
    clearInterval(timerInterval);
    timerInterval = null;
  }
  timerHudEl.style.display = "none";
}

function addTimer(extraSeconds: number) {
  timerSeconds += extraSeconds;
  timerTotalSeconds += extraSeconds;
  updateTimerDisplay();
}

function removeTimer(lessSeconds: number) {
  timerSeconds = Math.max(0, timerSeconds - lessSeconds);
  updateTimerDisplay();
}

function updateTimerDisplay() {
  const mins = Math.floor(timerSeconds / 60);
  const secs = timerSeconds % 60;
  timerDisplayEl.textContent = `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;

  const progress = ((timerTotalSeconds - timerSeconds) / timerTotalSeconds) * 100;
  timerProgressEl.style.width = `${progress}%`;

  // Flash effect if near end
  if (timerSeconds <= 10) {
    timerDisplayEl.style.color = (timerSeconds % 2 === 0) ? "#ff3d00" : "#00e5ff";
  } else {
    timerDisplayEl.style.color = "#00e5ff";
  }
}

connect();

// ── Clock Logic ─────────────────────────────────────────────────────────────
function updateClock() {
  const now = new Date();
  const timeStr = now.toLocaleTimeString('fr-FR', { hour12: false });

  // Globe overlay clock (existing)
  const clockEl = document.getElementById("globe-clock");
  if (clockEl) clockEl.textContent = timeStr;

  // Orb HUD clock (top of screen, always visible)
  const orbTime = document.getElementById("orb-time-display");
  if (orbTime) orbTime.textContent = timeStr;

  const orbDate = document.getElementById("orb-date-display");
  if (orbDate) {
    orbDate.textContent = now.toLocaleDateString('fr-FR', {
      day: '2-digit', month: '2-digit', year: 'numeric'
    });
  }
}
setInterval(updateClock, 1000);
updateClock();

// Silence unused-import warning for showError
void showError;

// ── Temp Panel (left side — Home Assistant interior) ────────────────────────

// Comfort scale: 10°C → 30°C maps to 0% → 100%
function tempToPercent(t: number): number {
  return Math.min(100, Math.max(0, ((t - 10) / 20) * 100));
}

function showTempPanel(d: {
  piece: string; temperature: string; humidite?: string | null;
}) {
  const panel = document.getElementById("temp-panel");
  if (!panel) return;

  const temp = parseFloat(d.temperature) || 0;
  (document.getElementById("tp-piece") as HTMLElement).textContent = d.piece.toUpperCase();
  (document.getElementById("tp-temp") as HTMLElement).textContent = String(Math.round(temp));

  const humRow = document.getElementById("tp-hum-row") as HTMLElement;
  if (d.humidite) {
    (document.getElementById("tp-hum") as HTMLElement).textContent = d.humidite;
    humRow.style.display = "flex";
  } else {
    humRow.style.display = "none";
  }

  const pct = tempToPercent(temp);
  (document.getElementById("tp-marker") as HTMLElement).style.left = `${pct}%`;

  panel.classList.add("tp-visible");
}

function hideTempPanel() {
  const panel = document.getElementById("temp-panel");
  if (!panel) return;
  panel.classList.remove("tp-visible");
  panel.style.left = "";
  panel.style.top = "";
  panel.style.transform = "";
}

document.getElementById("tp-close-btn")?.addEventListener("click", hideTempPanel);

// ── Weather Panel ────────────────────────────────────────────────────────────

const WEATHER_ICONS: Record<number, string> = {
  0: "☀️", 1: "🌤", 2: "⛅", 3: "☁️",
  45: "🌫", 48: "🌫",
  51: "🌦", 53: "🌦", 55: "🌧",
  61: "🌧", 63: "🌧", 65: "🌧",
  71: "🌨", 73: "🌨", 75: "❄️", 77: "🌨",
  80: "🌦", 81: "🌦", 82: "⛈",
  85: "🌨", 86: "❄️",
  95: "⛈", 96: "⛈", 99: "⛈",
};

function showWeatherPanel(d: {
  ville: string; temperature: number; ressenti: number;
  humidite: number; vent: number; code: number; description: string;
}) {
  const panel = document.getElementById("weather-panel");
  if (!panel) return;

  (document.getElementById("wp-city") as HTMLElement).textContent = d.ville.toUpperCase();
  (document.getElementById("wp-temp") as HTMLElement).textContent = String(d.temperature);
  (document.getElementById("wp-desc") as HTMLElement).textContent = d.description.toUpperCase();
  (document.getElementById("wp-feels") as HTMLElement).textContent = String(d.ressenti);
  (document.getElementById("wp-humidity") as HTMLElement).textContent = String(d.humidite);
  (document.getElementById("wp-wind") as HTMLElement).textContent = String(d.vent);
  (document.getElementById("wp-icon") as HTMLElement).textContent = WEATHER_ICONS[d.code] ?? "🌡";

  panel.classList.add("wp-visible");
}

function hideWeatherPanel() {
  const panel = document.getElementById("weather-panel");
  if (!panel) return;
  panel.classList.remove("wp-visible");
  panel.style.left = "";
  panel.style.right = "";
  panel.style.top = "";
  panel.style.transform = "";
}

document.getElementById("wp-close-btn")?.addEventListener("click", hideWeatherPanel);

// ── Drag & Drop — Temp Panel & Weather Panel ─────────────────────────────────
function makePanelDraggable(panel: HTMLElement, header: HTMLElement) {
  let isDragging = false;
  let offsetX = 0;
  let offsetY = 0;

  header.style.cursor = "grab";

  header.addEventListener("mousedown", (e) => {
    isDragging = true;
    const rect = panel.getBoundingClientRect();
    panel.style.left      = `${rect.left}px`;
    panel.style.top       = `${rect.top}px`;
    panel.style.right     = "auto";
    panel.style.bottom    = "auto";
    panel.style.transform = "none";
    offsetX = e.clientX - rect.left;
    offsetY = e.clientY - rect.top;
    header.style.cursor = "grabbing";
    e.preventDefault();
  });

  document.addEventListener("mousemove", (e) => {
    if (!isDragging) return;
    const newX = Math.max(0, Math.min(e.clientX - offsetX, window.innerWidth  - panel.offsetWidth));
    const newY = Math.max(0, Math.min(e.clientY - offsetY, window.innerHeight - panel.offsetHeight));
    panel.style.left = `${newX}px`;
    panel.style.top  = `${newY}px`;
  });

  document.addEventListener("mouseup", () => {
    if (isDragging) { isDragging = false; header.style.cursor = "grab"; }
  });
}

const _tpPanel  = document.getElementById("temp-panel");
const _tpHeader = _tpPanel?.querySelector(".tp-header") as HTMLElement | null;
if (_tpPanel && _tpHeader) makePanelDraggable(_tpPanel, _tpHeader);

const _wpPanel  = document.getElementById("weather-panel");
const _wpHeader = _wpPanel?.querySelector(".wp-header") as HTMLElement | null;
if (_wpPanel && _wpHeader) makePanelDraggable(_wpPanel, _wpHeader);

// ── Recipe Modal Logic ───────────────────────────────────────────────────────

const recipeModal = document.getElementById("recipe-modal");
const closeRecipeBtn = document.getElementById("close-recipe");
const recipeHeader = document.getElementById("recipe-header");

if (closeRecipeBtn && recipeModal) {
  closeRecipeBtn.addEventListener("click", () => {
    recipeModal.classList.add("hidden");
  });
}

// Drag & Drop for Recipe Modal
if (recipeModal && recipeHeader) {
  let isDragging = false;
  let offsetX = 0;
  let offsetY = 0;

  recipeHeader.addEventListener("mousedown", (e) => {
    isDragging = true;
    const rect = recipeModal.getBoundingClientRect();
    offsetX = e.clientX - rect.left;
    offsetY = e.clientY - rect.top;
    recipeModal.style.cursor = "grabbing";
  });

  document.addEventListener("mousemove", (e) => {
    if (!isDragging) return;
    
    // Prevent dragging outside the window
    let newX = e.clientX - offsetX;
    let newY = e.clientY - offsetY;
    
    // Boundaries
    const maxX = window.innerWidth - recipeModal.offsetWidth;
    const maxY = window.innerHeight - recipeModal.offsetHeight;
    
    newX = Math.max(0, Math.min(newX, maxX));
    newY = Math.max(0, Math.min(newY, maxY));

    recipeModal.style.left = `${newX}px`;
    recipeModal.style.top = `${newY}px`;
    recipeModal.style.transform = "none"; // disable original translation for dragging
  });

  document.addEventListener("mouseup", () => {
    if (isDragging) {
      isDragging = false;
      recipeModal.style.cursor = "default";
    }
  });
}
