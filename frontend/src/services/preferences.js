const MODE_KEY = "voice-assistant.mode";
const PROVIDER_KEY = "voice-assistant.provider";
const CUSTOM_INSTRUCTIONS_KEY = "voice-assistant.custom-instructions";

function read(key, fallback) {
  try {
    return localStorage.getItem(key) ?? fallback;
  } catch {
    return fallback;
  }
}

function write(key, value) {
  try {
    localStorage.setItem(key, value);
  } catch {
    // Storage can be unavailable (private mode); preferences then last for the session only.
  }
}

export const preferences = {
  getMode: () => read(MODE_KEY, null),
  setMode: (mode) => write(MODE_KEY, mode),
  getProvider: () => read(PROVIDER_KEY, "auto"),
  setProvider: (provider) => write(PROVIDER_KEY, provider),
  getCustomInstructions: () => read(CUSTOM_INSTRUCTIONS_KEY, ""),
  setCustomInstructions: (text) => write(CUSTOM_INSTRUCTIONS_KEY, text),
};
