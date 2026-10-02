const DISPLAY_NAMES = { groq: "Groq", euron: "Euron" };

export function providerLabel(name) {
  if (!name) return "";
  return DISPLAY_NAMES[name] || name.charAt(0).toUpperCase() + name.slice(1);
}
