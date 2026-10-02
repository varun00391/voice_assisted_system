import UserContextForm from "../../components/UserContext/UserContextForm.jsx";

export default function ProfilePage() {
  return (
    <div className="h-full overflow-y-auto px-4 py-8">
      <div className="mx-auto max-w-3xl rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="mb-4 text-lg font-semibold">Your context</h2>
        <UserContextForm />
      </div>
    </div>
  );
}
