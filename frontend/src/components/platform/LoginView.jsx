import { useState } from "react";
import { Loader2, LogIn, UserPlus, KeyRound, ArrowLeft } from "lucide-react";
import { useAuth } from "../../auth";
import * as API from "../../api";
import Footer from "./Footer";
import { useT } from "../../i18n";

export default function LoginView() {
  const t = useT();
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
        setInfo(t("login.resetSent"));
      } else if (mode === "reset") {
        await API.resetPassword(resetForm);
        setInfo(t("login.resetDone"));
        setMode("login");
      }
    } catch (err) {
      setError(err?.response?.data?.detail || t("common.error"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col">
      <div className="tricolor-bar" />
      <div className="flex flex-1 items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="mb-6 flex flex-col items-center text-center">
          <img src="/logo.png" alt={t("common.logoAlt")} className="h-24 w-24 object-contain" />
          <h1 className="mt-3 font-serif text-3xl font-bold text-white">City<span className="text-accent">Shield</span></h1>
          <p className="text-[11px] uppercase tracking-wider text-slate-500">
            {t("login.brandSub")}
          </p>
        </div>

        <div className="rounded-2xl border border-ink-600 bg-ink-800/70 p-6 shadow-2xl">
          <h2 className="mb-4 text-lg font-semibold text-slate-100">
            {mode === "login" && t("login.title")}
            {mode === "register" && t("login.registerTitle")}
            {mode === "forgot" && t("login.forgotTitle")}
            {mode === "reset" && t("login.resetTitle")}
          </h2>

          {error && <div className="mb-3 rounded-lg bg-signal-red/10 p-2.5 text-xs text-signal-red">{error}</div>}
          {info && <div className="mb-3 rounded-lg bg-signal-green/10 p-2.5 text-xs text-signal-green">{info}</div>}

          <form onSubmit={submit} className="space-y-3">
            {mode === "register" && (
              <input required placeholder={t("login.fullName")} value={form.name} onChange={upd("name")} className={inp} />
            )}
            {mode !== "reset" && (
              <input required type="email" placeholder={t("login.email")} value={form.email} onChange={upd("email")} className={inp} />
            )}
            {(mode === "login" || mode === "register") && (
              <input required type="password" placeholder={t("login.password")} value={form.password} onChange={upd("password")} className={inp} />
            )}
            {mode === "register" && (
              <input placeholder={t("login.phoneOptional")} value={form.phone} onChange={upd("phone")} className={inp} />
            )}
            {mode === "reset" && (
              <>
                <input required placeholder={t("login.resetToken")} value={resetForm.token}
                  onChange={(e) => setResetForm({ ...resetForm, token: e.target.value })} className={inp} />
                <input required type="password" placeholder={t("login.newPassword")} value={resetForm.new_password}
                  onChange={(e) => setResetForm({ ...resetForm, new_password: e.target.value })} className={inp} />
              </>
            )}

            <button type="submit" disabled={busy}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-accent-600 py-2.5 text-sm font-semibold text-white transition hover:bg-accent-700 disabled:opacity-50">
              {busy ? <Loader2 size={16} className="animate-spin" /> :
                mode === "login" ? <LogIn size={16} /> : mode === "register" ? <UserPlus size={16} /> : <KeyRound size={16} />}
              {mode === "login" ? t("login.signIn") : mode === "register" ? t("login.createAccount") : mode === "forgot" ? t("login.sendResetLink") : t("login.resetTitle")}
            </button>
          </form>

          <div className="mt-4 space-y-1 text-center text-xs text-slate-400">
            {mode === "login" && (
              <>
                <div>{t("login.newCitizen")} <button onClick={() => setMode("register")} className="text-accent hover:underline">{t("login.registerLink")}</button></div>
                <div><button onClick={() => setMode("forgot")} className="hover:underline">{t("login.forgot")}</button>
                  {" · "}<button onClick={() => setMode("reset")} className="hover:underline">{t("login.haveToken")}</button></div>
              </>
            )}
            {mode !== "login" && (
              <button onClick={() => setMode("login")} className="inline-flex items-center gap-1 hover:underline">
                <ArrowLeft size={12} /> {t("login.backToSignIn")}
              </button>
            )}
          </div>
        </div>

        {/* demo credentials hint */}
        <div className="mt-4 rounded-lg border border-ink-700 bg-ink-800/40 p-3 text-[11px] text-slate-500">
          <div className="mb-1 font-semibold text-slate-400">{t("login.demoAccounts")}</div>
          <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 font-mono">
            <span>admin@city.gov</span><span>admin123</span>
            <span>lead@city.gov</span><span>lead123</span>
            <span>officer@city.gov</span><span>officer123</span>
            <span>citizen@example.com</span><span>citizen123</span>
          </div>
        </div>
      </div>
      </div>
      <Footer />
    </div>
  );
}

const inp = "w-full rounded-lg bg-ink-900/60 px-3 py-2.5 text-sm text-slate-100 outline-none ring-1 ring-ink-600 focus:ring-2 focus:ring-accent";
