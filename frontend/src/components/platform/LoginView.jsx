import { useState } from "react";
import { Loader2, LogIn, UserPlus, KeyRound, ArrowLeft } from "lucide-react";
import { useAuth } from "../../auth";
import * as API from "../../api";

export default function LoginView() {
  const { login, register } = useAuth();
  const [mode, setMode] = useState("login"); // login | register | forgot | reset
  const [form, setForm] = useState({ name: "", email: "", password: "", phone: "" });
  const [resetForm, setResetForm] = useState({ token: "", new_password: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [info, setInfo] = useState(null);

  const upd = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true); setError(null); setInfo(null);
    try {
      if (mode === "login") await login(form.email, form.password);
      else if (mode === "register")
        await register({ name: form.name, email: form.email, password: form.password, phone: form.phone });
      else if (mode === "forgot") {
        await API.forgotPassword({ email: form.email });
        setInfo("If the email exists, a reset token was sent. Offline demo: check the admin outbox / server log, then use 'Have a token?'.");
      } else if (mode === "reset") {
        await API.resetPassword(resetForm);
        setInfo("Password reset. You can now sign in.");
        setMode("login");
      }
    } catch (err) {
      setError(err?.response?.data?.detail || "Something went wrong.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="mb-6 flex flex-col items-center text-center">
          <img src="/logo.jpeg" alt="Ahmedabad City Police" className="h-20 w-20 rounded-xl object-contain bg-white/5 p-1 ring-1 ring-ink-600" />
          <h1 className="mt-3 text-2xl font-bold text-white">City<span className="text-accent">Shield</span></h1>
          <p className="text-[11px] uppercase tracking-wider text-slate-500">
            Unified AI Policing · Cyber Crime Branch, Ahmedabad City Police
          </p>
        </div>

        <div className="rounded-2xl border border-ink-600 bg-ink-800/70 p-6 shadow-2xl">
          <h2 className="mb-4 text-lg font-semibold text-slate-100">
            {mode === "login" && "Sign in"}
            {mode === "register" && "Create citizen account"}
            {mode === "forgot" && "Forgot password"}
            {mode === "reset" && "Reset password"}
          </h2>

          {error && <div className="mb-3 rounded-lg bg-signal-red/10 p-2.5 text-xs text-signal-red">{error}</div>}
          {info && <div className="mb-3 rounded-lg bg-signal-green/10 p-2.5 text-xs text-signal-green">{info}</div>}

          <form onSubmit={submit} className="space-y-3">
            {mode === "register" && (
              <input required placeholder="Full name" value={form.name} onChange={upd("name")} className={inp} />
            )}
            {mode !== "reset" && (
              <input required type="email" placeholder="Email" value={form.email} onChange={upd("email")} className={inp} />
            )}
            {(mode === "login" || mode === "register") && (
              <input required type="password" placeholder="Password" value={form.password} onChange={upd("password")} className={inp} />
            )}
            {mode === "register" && (
              <input placeholder="Phone (optional)" value={form.phone} onChange={upd("phone")} className={inp} />
            )}
            {mode === "reset" && (
              <>
                <input required placeholder="Reset token" value={resetForm.token}
                  onChange={(e) => setResetForm({ ...resetForm, token: e.target.value })} className={inp} />
                <input required type="password" placeholder="New password" value={resetForm.new_password}
                  onChange={(e) => setResetForm({ ...resetForm, new_password: e.target.value })} className={inp} />
              </>
            )}

            <button type="submit" disabled={busy}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-accent-600 py-2.5 text-sm font-semibold text-white transition hover:bg-accent-700 disabled:opacity-50">
              {busy ? <Loader2 size={16} className="animate-spin" /> :
                mode === "login" ? <LogIn size={16} /> : mode === "register" ? <UserPlus size={16} /> : <KeyRound size={16} />}
              {mode === "login" ? "Sign in" : mode === "register" ? "Create account" : mode === "forgot" ? "Send reset link" : "Reset password"}
            </button>
          </form>

          <div className="mt-4 space-y-1 text-center text-xs text-slate-400">
            {mode === "login" && (
              <>
                <div>New citizen? <button onClick={() => setMode("register")} className="text-accent hover:underline">Register</button></div>
                <div><button onClick={() => setMode("forgot")} className="hover:underline">Forgot password?</button>
                  {" · "}<button onClick={() => setMode("reset")} className="hover:underline">Have a token?</button></div>
              </>
            )}
            {mode !== "login" && (
              <button onClick={() => setMode("login")} className="inline-flex items-center gap-1 hover:underline">
                <ArrowLeft size={12} /> Back to sign in
              </button>
            )}
          </div>
        </div>

        {/* demo credentials hint */}
        <div className="mt-4 rounded-lg border border-ink-700 bg-ink-800/40 p-3 text-[11px] text-slate-500">
          <div className="mb-1 font-semibold text-slate-400">Demo logins</div>
          <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 font-mono">
            <span>admin@city.gov</span><span>admin123</span>
            <span>lead@city.gov</span><span>lead123</span>
            <span>officer@city.gov</span><span>officer123</span>
            <span>citizen@example.com</span><span>citizen123</span>
          </div>
        </div>
      </div>
    </div>
  );
}

const inp = "w-full rounded-lg bg-ink-900/60 px-3 py-2.5 text-sm text-slate-100 outline-none ring-1 ring-ink-600 focus:ring-2 focus:ring-accent";
