import { useCallback, useEffect, useState } from "react";

import ChatPage from "./pages/Chat/ChatPage.jsx";
import ProfilePage from "./pages/Profile/ProfilePage.jsx";
import SettingsPage from "./pages/Settings/SettingsPage.jsx";
import { api } from "./services/api.js";
import { preferences } from "./services/preferences.js";

const PAGES = [
  { key: "chat", label: "Chat" },
  { key: "profile", label: "Profile" },
  { key: "settings", label: "Settings" },
];

export default function App() {
  const [page, setPage] = useState("chat");
  const [modes, setModes] = useState([]);
  const [mode, setMode] = useState(() => preferences.getMode() || "learning");
  const [providers, setProviders] = useState([]);
  const [provider, setProvider] = useState(() => preferences.getProvider());
  const [maxRecordingSeconds, setMaxRecordingSeconds] = useState(60);
  const [loadError, setLoadError] = useState(null);

  const refreshProviders = useCallback(async () => {
    try {
      const { providers: configured } = await api.getProviderHealth();
      setProviders(configured);
      setProvider((current) => (configured.some((p) => p.provider === current) ? current : "auto"));
    } catch {
      // Chat requests report their own errors; the selector simply stays on "Auto".
    }
  }, []);

  const loadAppData = useCallback(() => {
    setLoadError(null);
    refreshProviders();
    api
      .getModes()
      .then(({ default: defaultMode, modes: available }) => {
        setModes(available);
        setMode((current) => (available.some((m) => m.key === current) ? current : defaultMode));
      })
      .catch((error) => setLoadError(error.message));
    api
      .getConfig()
      .then((config) => setMaxRecordingSeconds(Math.floor(config.max_audio_duration_seconds)))
      .catch(() => {});
  }, [refreshProviders]);

  useEffect(() => {
    loadAppData();
  }, [loadAppData]);

  function changeMode(nextMode) {
    setMode(nextMode);
    preferences.setMode(nextMode);
  }

  function changeProvider(nextProvider) {
    setProvider(nextProvider);
    preferences.setProvider(nextProvider);
  }

  return (
    <div className="flex h-full flex-col">
      <header className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3">
        <h1 className="text-lg font-semibold">AI Voice Assistant</h1>
        <nav className="flex gap-1" aria-label="Main">
          {PAGES.map(({ key, label }) => (
            <button
              key={key}
              type="button"
              onClick={() => setPage(key)}
              aria-current={page === key ? "page" : undefined}
              className={`rounded-lg px-3 py-1.5 text-sm font-medium ${
                page === key ? "bg-indigo-50 text-indigo-700" : "text-slate-600 hover:bg-slate-100"
              }`}
            >
              {label}
            </button>
          ))}
        </nav>
      </header>

      {loadError && (
        <div role="alert" className="bg-red-50 px-4 py-2 text-center text-sm text-red-700">
          {loadError}
        </div>
      )}

      <main className="min-h-0 flex-1">
        <div className={page === "chat" ? "h-full" : "hidden"}>
          <ChatPage
            modes={modes}
            mode={mode}
            onModeChange={changeMode}
            providers={providers}
            provider={provider}
            onProviderChange={changeProvider}
            onAnswered={refreshProviders}
            maxRecordingSeconds={maxRecordingSeconds}
          />
        </div>
        {page === "profile" && <ProfilePage />}
        {page === "settings" && <SettingsPage onAccessKeyChange={loadAppData} />}
      </main>
    </div>
  );
}
