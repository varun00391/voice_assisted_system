import { useCallback, useEffect, useState } from "react";

import { api } from "../../services/api.js";
import { preferences } from "../../services/preferences.js";

const STATE_STYLES = {
  healthy: "bg-emerald-100 text-emerald-800",
  degraded: "bg-amber-100 text-amber-800",
  unavailable: "bg-red-100 text-red-800",
};

export default function SettingsPage() {
  const [instructions, setInstructions] = useState(preferences.getCustomInstructions);
  const [saved, setSaved] = useState(false);
  const [providers, setProviders] = useState(null);
  const [healthError, setHealthError] = useState(null);

  const loadHealth = useCallback(async () => {
    setHealthError(null);
    try {
      setProviders((await api.getProviderHealth()).providers);
    } catch (error) {
      setHealthError(error.message);
    }
  }, []);

  useEffect(() => {
    loadHealth();
  }, [loadHealth]);

  function saveInstructions(event) {
    event.preventDefault();
    preferences.setCustomInstructions(instructions.trim());
    setSaved(true);
  }

  return (
    <div className="h-full overflow-y-auto px-4 py-8">
      <div className="mx-auto max-w-3xl space-y-6">
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold">Custom mode instructions</h2>
          <p className="mt-1 text-sm text-slate-600">Used when the answer mode is set to “Custom”.</p>
          <form onSubmit={saveInstructions} className="mt-4 space-y-3">
            <textarea
              rows={5}
              maxLength={2000}
              value={instructions}
              onChange={(event) => {
                setInstructions(event.target.value);
                setSaved(false);
              }}
              placeholder={"Explain everything like a senior AI architect.\nUse Python examples.\nKeep answers below 500 words."}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200"
            />
            <div className="flex items-center gap-3">
              <button
                type="submit"
                className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
              >
                Save
              </button>
              {saved && <span className="text-sm text-emerald-700">Saved</span>}
            </div>
          </form>
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">AI providers</h2>
            <button type="button" onClick={loadHealth} className="text-sm text-indigo-600 hover:underline">
              Refresh
            </button>
          </div>
          {healthError && <p className="mt-3 text-sm text-red-600">{healthError}</p>}
          {providers && !providers.length && (
            <p className="mt-3 text-sm text-slate-600">No providers configured. Add API keys to the .env file.</p>
          )}
          <ul className="mt-3 divide-y divide-slate-100">
            {providers?.map((provider, index) => (
              <li key={provider.provider} className="flex items-center justify-between py-2 text-sm">
                <span>
                  <span className="font-medium capitalize">{provider.provider}</span>
                  <span className="ml-2 text-slate-500">{provider.model}</span>
                  {index === 0 && <span className="ml-2 text-xs text-slate-400">primary</span>}
                </span>
                <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATE_STYLES[provider.state] || ""}`}>
                  {provider.state}
                </span>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  );
}
