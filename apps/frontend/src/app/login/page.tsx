'use client';

import React, { useState, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Lock, AlertCircle, Globe } from 'lucide-react';

type Language = 'es' | 'en';

const translations = {
  es: {
    mvp_badge: 'ENTORNO MVP — VERSIÓN DE DEMOSTRACIÓN',
    title: 'Panel Administrativo',
    subtitle: 'Gestión de Citas Legales en Tiempo Real',
    warning_notice: 'Aviso:',
    warning_p1: 'Este sistema es un',
    warning_p2: 'de validación funcional. Toda la información, sedes y citas registradas corresponden a datos de prueba.',
    password_label: 'Contraseña de Acceso',
    btn_submitting: 'Validando sesión...',
    btn_submit: 'Ingresar al Dashboard',
    footer: 'Sistema Protegido • La Victoria Foundation',
    error_invalid: 'Clave de acceso incorrecta',
    error_generic: 'Error al intentar iniciar sesión',
    lang_toggle_title: 'Switch to English',
    loading: 'Cargando...',
  },
  en: {
    mvp_badge: 'MVP ENVIRONMENT — DEMO VERSION',
    title: 'Admin Portal',
    subtitle: 'Real-Time Legal Appointment Management',
    warning_notice: 'Notice:',
    warning_p1: 'This system is a functional validation',
    warning_p2: 'All registered information, branches, and appointments correspond to test data.',
    password_label: 'Access Password',
    btn_submitting: 'Validating session...',
    btn_submit: 'Sign in to Dashboard',
    footer: 'Protected System • La Victoria Foundation',
    error_invalid: 'Incorrect access password',
    error_generic: 'Error attempting to sign in',
    lang_toggle_title: 'Cambiar a Español',
    loading: 'Loading...',
  },
};

function LoginForm() {
  const [lang, setLang] = useState<Language>('es');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirect = searchParams.get('redirect') || '/dashboard';

  useEffect(() => {
    const saved = localStorage.getItem('lv_lang') as Language;
    if (saved === 'es' || saved === 'en') {
      setLang(saved);
    }
  }, []);

  const toggleLanguage = () => {
    const next = lang === 'es' ? 'en' : 'es';
    setLang(next);
    localStorage.setItem('lv_lang', next);
  };

  const t = translations[lang];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password }),
      });

      if (res.ok) {
        window.location.href = redirect;
      } else {
        setError(t.error_invalid);
      }
    } catch (err) {
      setError(t.error_generic);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative z-10 max-w-md w-full bg-white/95 backdrop-blur-md rounded-3xl shadow-xl shadow-sky-950/5 p-8 border border-white/80">
      {/* Botón sutil de cambio de idioma */}
      <div className="absolute top-5 right-5">
        <button
          type="button"
          onClick={toggleLanguage}
          className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl border border-slate-200 bg-white hover:border-[#075985] text-slate-600 hover:text-[#075985] transition-all text-xs font-bold shadow-2xs hover:shadow-xs cursor-pointer"
          title={t.lang_toggle_title}
        >
          <Globe className="w-3.5 h-3.5 text-[#075985]" />
          <span className="uppercase text-[11px] font-bold tracking-wider">{lang === 'es' ? 'EN' : 'ES'}</span>
        </button>
      </div>

      <div className="text-center mb-8">
        <div className="flex items-center justify-center mb-5">
          <img 
            src="/logo.png" 
            alt="La Victoria Foundation" 
            className="h-20 w-auto object-contain drop-shadow-xs"
          />
        </div>
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-700 text-[11px] font-bold tracking-wide mb-3">
          <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse"></span>
          {t.mvp_badge}
        </div>
        <h1 className="text-xl font-bold text-[#075985] tracking-tight">{t.title}</h1>
        <p className="text-xs text-slate-500 mt-1">{t.subtitle}</p>
        <p className="text-[11px] text-amber-800/80 bg-amber-50 border border-amber-200/60 rounded-xl px-3 py-1.5 mt-3 leading-relaxed text-left">
          ⚠️ <strong>{t.warning_notice}</strong> {t.warning_p1} <strong>MVP</strong> {t.warning_p2}
        </p>
      </div>

      {error && (
        <div className="mb-6 p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-center gap-3 text-rose-600 text-sm font-medium">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
            {t.password_label}
          </label>
          <div className="relative">
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              placeholder="••••••••••••"
              className="w-full px-4 py-3 bg-slate-50/90 border border-slate-200 rounded-xl text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[#075985] focus:bg-white transition-all text-sm"
            />
            <Lock className="w-4 h-4 text-slate-400 absolute right-3.5 top-3.5" />
          </div>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full py-3 px-4 bg-gradient-to-r from-[#075985] to-[#0284c7] hover:from-[#0369a1] hover:to-[#0284c7] text-white font-bold rounded-xl shadow-md shadow-sky-600/20 transition-all flex items-center justify-center disabled:opacity-50 text-sm cursor-pointer"
        >
          {loading ? t.btn_submitting : t.btn_submit}
        </button>
      </form>

      <div className="mt-6 text-center text-xs text-slate-400">
        {t.footer}
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <main className="min-h-screen flex items-center justify-center bg-[#eef4f9] px-4 relative overflow-hidden">
      {/* Círculos animados flotantes en tonos azules y blancos */}
      <div 
        className="absolute -top-20 -left-20 w-80 sm:w-96 h-80 sm:h-96 rounded-full bg-gradient-to-br from-sky-400/35 to-blue-500/25 blur-2xl animate-blob-1 pointer-events-none"
      />
      <div 
        className="absolute top-1/4 -right-24 w-88 sm:w-[420px] h-88 sm:h-[420px] rounded-full bg-gradient-to-tr from-cyan-300/30 via-sky-400/25 to-white/60 blur-2xl animate-blob-2 pointer-events-none"
      />
      <div 
        className="absolute -bottom-24 left-1/3 w-96 sm:w-[460px] h-96 sm:h-[460px] rounded-full bg-gradient-to-tr from-blue-400/30 via-sky-300/20 to-white blur-2xl animate-blob-3 pointer-events-none"
      />

      <Suspense fallback={<div className="text-slate-600 text-sm">Cargando...</div>}>
        <LoginForm />
      </Suspense>
    </main>
  );
}
