export default function ModeSelector({ modes, value, onChange, disabled }) {
  const selected = modes.find((mode) => mode.key === value);

  return (
    <div className="flex items-center gap-2">
      <label htmlFor="mode-select" className="text-sm font-medium text-slate-600">
        Mode
      </label>
      <select
        id="mode-select"
        value={value}
        disabled={disabled || !modes.length}
        onChange={(event) => onChange(event.target.value)}
        title={selected?.description}
        className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200"
      >
        {modes.map((mode) => (
          <option key={mode.key} value={mode.key}>
            {mode.name}
          </option>
        ))}
      </select>
      {selected && <span className="hidden text-xs text-slate-500 lg:inline">{selected.description}</span>}
    </div>
  );
}
