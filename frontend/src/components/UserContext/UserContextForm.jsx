import { useEffect, useState } from "react";

import { api } from "../../services/api.js";

const TEXT_FIELDS = [
  { key: "name", label: "Name", multiline: false },
  { key: "professional_background", label: "Professional background", multiline: false, placeholder: "Data Scientist" },
  { key: "preferences", label: "Answer preferences", multiline: true, placeholder: "Use Python examples" },
  { key: "learning_goals", label: "Learning goals", multiline: true },
  { key: "interview_goals", label: "Interview goals", multiline: true, placeholder: "Prepare for Senior AI Architect interviews" },
  { key: "other_information", label: "Other information", multiline: true },
];

const EMPTY_FORM = {
  name: "",
  professional_background: "",
  experience_years: "",
  skills: "",
  preferences: "",
  learning_goals: "",
  interview_goals: "",
  other_information: "",
};

function toForm(context) {
  return {
    ...EMPTY_FORM,
    ...Object.fromEntries(TEXT_FIELDS.map(({ key }) => [key, context[key] ?? ""])),
    experience_years: context.experience_years ?? "",
    skills: (context.skills || []).join(", "),
  };
}

function toPayload(form) {
  const payload = Object.fromEntries(TEXT_FIELDS.map(({ key }) => [key, form[key].trim() || null]));
  payload.experience_years = form.experience_years === "" ? null : Number(form.experience_years);
  payload.skills = form.skills
    .split(",")
    .map((skill) => skill.trim())
    .filter(Boolean);
  return payload;
}

const inputClass =
  "mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200";

export default function UserContextForm() {
  const [form, setForm] = useState(EMPTY_FORM);
  const [state, setState] = useState({ loading: true, saving: false, error: null, notice: null });

  useEffect(() => {
    api
      .getUserContext()
      .then((context) => {
        setForm(toForm(context));
        setState((s) => ({ ...s, loading: false }));
      })
      .catch((error) => setState((s) => ({ ...s, loading: false, error: error.message })));
  }, []);

  const update = (key) => (event) => setForm((current) => ({ ...current, [key]: event.target.value }));

  async function handleSave(event) {
    event.preventDefault();
    setState((s) => ({ ...s, saving: true, error: null, notice: null }));
    try {
      const saved = await api.saveUserContext(toPayload(form));
      setForm(toForm(saved));
      setState((s) => ({ ...s, saving: false, notice: "Saved. Relevant details will be used in future answers." }));
    } catch (error) {
      setState((s) => ({ ...s, saving: false, error: error.message }));
    }
  }

  async function handleClear() {
    if (!window.confirm("Delete all of your saved context?")) return;
    setState((s) => ({ ...s, saving: true, error: null, notice: null }));
    try {
      await api.clearUserContext();
      setForm(EMPTY_FORM);
      setState((s) => ({ ...s, saving: false, notice: "Your saved context was deleted." }));
    } catch (error) {
      setState((s) => ({ ...s, saving: false, error: error.message }));
    }
  }

  if (state.loading) return <p className="text-sm text-slate-500">Loading…</p>;

  return (
    <form onSubmit={handleSave} className="space-y-4">
      <p className="text-sm text-slate-600">
        Only what you enter here is stored. The assistant uses the parts relevant to each question.
      </p>

      <div className="grid gap-4 md:grid-cols-2">
        {TEXT_FIELDS.slice(0, 2).map(({ key, label, placeholder }) => (
          <label key={key} className="block text-sm font-medium text-slate-700">
            {label}
            <input className={inputClass} value={form[key]} placeholder={placeholder} onChange={update(key)} />
          </label>
        ))}
        <label className="block text-sm font-medium text-slate-700">
          Years of experience
          <input
            type="number"
            min="0"
            max="80"
            className={inputClass}
            value={form.experience_years}
            onChange={update("experience_years")}
          />
        </label>
        <label className="block text-sm font-medium text-slate-700">
          Skills (comma separated)
          <input
            className={inputClass}
            value={form.skills}
            placeholder="Python, Machine Learning, RAG"
            onChange={update("skills")}
          />
        </label>
      </div>

      {TEXT_FIELDS.slice(2).map(({ key, label, placeholder }) => (
        <label key={key} className="block text-sm font-medium text-slate-700">
          {label}
          <textarea rows={2} className={inputClass} value={form[key]} placeholder={placeholder} onChange={update(key)} />
        </label>
      ))}

      {state.error && <p className="text-sm text-red-600">{state.error}</p>}
      {state.notice && <p className="text-sm text-emerald-700">{state.notice}</p>}

      <div className="flex gap-3">
        <button
          type="submit"
          disabled={state.saving}
          className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
        >
          Save
        </button>
        <button
          type="button"
          disabled={state.saving}
          onClick={handleClear}
          className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-60"
        >
          Delete all
        </button>
      </div>
    </form>
  );
}
