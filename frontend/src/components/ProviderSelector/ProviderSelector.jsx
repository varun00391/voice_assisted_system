import { providerLabel } from "../../services/providers.js";

export default function ProviderSelector({ providers, value, onChange, disabled }) {
  const autoLabel = providers.length
    ? `Auto (${providers.map((p) => providerLabel(p.provider)).join(" → ")})`
    : "Auto";

  return (
    <div className="flex items-center gap-2">
      <label htmlFor="provider-select" className="text-sm font-medium text-slate-600">
        LLM
      </label>
      <select
        id="provider-select"
        value={value}
        disabled={disabled || !providers.length}
        onChange={(event) => onChange(event.target.value)}
        title="Preferred provider. If it is rate limited or temporarily unavailable, another provider answers."
        className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200"
      >
        <option value="auto">{autoLabel}</option>
        {providers.map((provider) => (
          <option key={provider.provider} value={provider.provider}>
            {providerLabel(provider.provider)}
            {provider.state === "unavailable" ? " (temporarily unavailable)" : ""}
          </option>
        ))}
      </select>
    </div>
  );
}
