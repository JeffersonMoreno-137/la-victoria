'use client';

import React, { useState, useRef, useEffect } from 'react';
import { 
  ChevronLeft, 
  ChevronRight, 
  Calendar as CalendarIcon, 
  CheckCircle2, 
  Plus, 
  LogOut, 
  ShieldCheck, 
  Coffee, 
  Clock, 
  UserCheck, 
  X, 
  FileText, 
  Menu, 
  Globe 
} from 'lucide-react';
import { useRouter } from 'next/navigation';

interface AppointmentSlot {
  id: string;
  clientName: string;
  serviceType: string;
  hour: number;
  lawyerId: string;
  dateStr: string;
  status: 'SCHEDULED' | 'RESCHEDULED' | 'CANCELLED' | 'COMPLETED';
}

type Language = 'es' | 'en';

const translations = {
  es: {
    panel_title: 'Panel de Agendamiento',
    panel_subtitle: 'Sincronización en Tiempo Real',
    tabs: {
      CALENDARIO: 'CALENDARIO',
      ABOGADOS: 'ABOGADOS',
      SEDES: 'SEDES',
      CITAS: 'CITAS',
      REPORTES: 'REPORTES',
    },
    branches: {
      NY_QUEENS: '📍 Queens, NY',
      TX_DALLAS: '📍 Dallas, TX',
    },
    logout: 'SALIR',
    prev_day: 'Día anterior',
    next_day: 'Día siguiente',
    total_branch_appointments: 'Total Citas Sede',
    available_slots: 'Slots Libres',
    hour_est: 'Hora (EST)',
    priority: 'Prioridad',
    appointments_today: 'citas hoy',
    lunch_break: 'Pausa de Almuerzo Institucional / Lunch Break (Inhabilitado)',
    book_slot: 'Agendar Cita',
    modal_title: 'Agendar Cita en el Calendario',
    client_name: 'Nombre Completo del Cliente',
    client_placeholder: 'Ej: Laura Sanchez',
    service_type: 'Tipo de Trámite / Servicio',
    date: 'Fecha',
    time: 'Horario',
    cancel: 'Cancelar',
    confirm_appointment: 'Confirmar Cita',
    mvp_badge: 'ENTORNO MVP',
    mvp_notice: 'Modo Demostración: Toda la información, abogados y citas registradas corresponden a datos de prueba simulados.',
    services: {
      itin: 'Trámite de ITIN Number (W-7)',
      i130: 'Petición Familiar (I-130)',
      asilo: 'Asesoría de Asilo',
      i485: 'Ajuste de Estatus (I-485)',
      notaria: 'Notaría y Traducciones',
    }
  },
  en: {
    panel_title: 'Booking Dashboard',
    panel_subtitle: 'Real-Time Synchronization',
    tabs: {
      CALENDARIO: 'CALENDAR',
      ABOGADOS: 'ATTORNEYS',
      SEDES: 'BRANCHES',
      CITAS: 'APPOINTMENTS',
      REPORTES: 'REPORTS',
    },
    branches: {
      NY_QUEENS: '📍 Queens, NY',
      TX_DALLAS: '📍 Dallas, TX',
    },
    logout: 'LOGOUT',
    prev_day: 'Previous day',
    next_day: 'Next day',
    total_branch_appointments: 'Branch Total Bookings',
    available_slots: 'Available Slots',
    hour_est: 'Time (EST)',
    priority: 'Priority',
    appointments_today: 'appointments today',
    lunch_break: 'Institutional Lunch Break (Unavailable)',
    book_slot: 'Book Appointment',
    modal_title: 'Schedule Appointment on Calendar',
    client_name: 'Client Full Name',
    client_placeholder: 'Ex: Laura Sanchez',
    service_type: 'Service / Legal Procedure',
    date: 'Date',
    time: 'Schedule',
    cancel: 'Cancel',
    confirm_appointment: 'Confirm Appointment',
    mvp_badge: 'MVP ENVIRONMENT',
    mvp_notice: 'Demonstration Mode: All information, attorneys, and scheduled bookings are simulated test data.',
    services: {
      itin: 'ITIN Number Application (W-7)',
      i130: 'Family Petition (I-130)',
      asilo: 'Asylum Consultation',
      i485: 'Adjustment of Status (I-485)',
      notaria: 'Notary & Translations',
    }
  }
};

export default function DashboardCalendarPage() {
  const router = useRouter();
  const dateInputRef = useRef<HTMLInputElement>(null);
  const calendarPopupRef = useRef<HTMLDivElement>(null);
  const [mounted, setMounted] = useState(false);
  const [lang, setLang] = useState<Language>('es');
  const [selectedBranch, setSelectedBranch] = useState<'NY_QUEENS' | 'TX_DALLAS'>('NY_QUEENS');
  const [selectedDate, setSelectedDate] = useState<string>('2026-09-03');
  const [isCalendarOpen, setIsCalendarOpen] = useState<boolean>(false);
  const [pickerMonth, setPickerMonth] = useState<number>(8); // 8 = Septiembre (0-indexed)
  const [pickerYear, setPickerYear] = useState<number>(2026);
  const [activeTab, setActiveTab] = useState('CALENDARIO');
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newSlotData, setNewSlotData] = useState({ lawyerId: 'l1', hour: 9, clientName: '', serviceType: 'Trámite de ITIN Number' });

  const t = translations[lang];

  // Cerrar el popup al hacer clic fuera
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (calendarPopupRef.current && !calendarPopupRef.current.contains(e.target as Node)) {
        setIsCalendarOpen(false);
      }
    };
    if (isCalendarOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isCalendarOpen]);

  // Marcar como montado en el cliente para evitar mismatch de SSR y sincronizar idioma
  useEffect(() => {
    setMounted(true);
    const saved = localStorage.getItem('lv_lang') as Language;
    if (saved === 'es' || saved === 'en') {
      setLang(saved);
    }
  }, []);

  // Lista de citas reactiva en memoria
  const [appointments, setAppointments] = useState<AppointmentSlot[]>([
    { id: '1', clientName: 'Carlos Mendoza', serviceType: 'Trámite ITIN (Form W-7)', hour: 9, lawyerId: 'l1', dateStr: '2026-09-03', status: 'SCHEDULED' },
    { id: '2', clientName: 'Maria Gomez', serviceType: 'Asesoría de Asilo', hour: 10, lawyerId: 'l2', dateStr: '2026-09-03', status: 'SCHEDULED' },
    { id: '3', clientName: 'Juan Diaz', serviceType: 'Petición Familiar (I-130)', hour: 11, lawyerId: 'l3', dateStr: '2026-09-03', status: 'SCHEDULED' },
    { id: '4', clientName: 'Elena Perez', serviceType: 'Notaría y Traducción', hour: 14, lawyerId: 'l1', dateStr: '2026-09-03', status: 'SCHEDULED' },
    { id: '5', clientName: 'Roberto Soto', serviceType: 'Ajuste de Estatus (I-485)', hour: 15, lawyerId: 'l2', dateStr: '2026-09-03', status: 'SCHEDULED' },
  ]);

  // Abogados de cada sede (Regla de negocio: 3 por sede)
  const lawyersQueens = [
    { id: 'l1', name: 'Abg. Carlos Mendoza', role: lang === 'es' ? 'Inmigración & ITIN' : 'Immigration & ITIN', priority: 'L1', verified: true },
    { id: 'l2', name: 'Abg. Sofia Ramirez', role: lang === 'es' ? 'Defensa & Peticiones' : 'Defense & Petitions', priority: 'L2', verified: true },
    { id: 'l3', name: 'Abg. Michael Chen', role: lang === 'es' ? 'Notaría & Trámites' : 'Notary & Procedures', priority: 'L3', verified: false },
  ];

  const lawyersDallas = [
    { id: 'l4', name: 'Abg. Elena Morales', role: lang === 'es' ? 'Directora Legal' : 'Legal Director', priority: 'L1', verified: true },
    { id: 'l5', name: 'Abg. David Hernandez', role: lang === 'es' ? 'Asilo & Ajuste' : 'Asylum & Adjustment', priority: 'L2', verified: true },
    { id: 'l6', name: 'Abg. Laura Vasquez', role: lang === 'es' ? 'Orientación General' : 'General Guidance', priority: 'L3', verified: false },
  ];

  const currentLawyers = selectedBranch === 'NY_QUEENS' ? lawyersQueens : lawyersDallas;

  // Franjas horarias de lunes a viernes (09:00 a 16:00 EST, 12:00 almuerzo)
  const timeSlots = [
    { hour: 9, label: '09:00 AM' },
    { hour: 10, label: '10:00 AM' },
    { hour: 11, label: '11:00 AM' },
    { hour: 12, label: '12:00 PM', isLunch: true },
    { hour: 13, label: '01:00 PM' },
    { hour: 14, label: '02:00 PM' },
    { hour: 15, label: '03:00 PM' },
    { hour: 16, label: '04:00 PM' },
  ];

  // Cargar citas reales de la Base de Datos PostgreSQL al inicio y al cambiar sede/fecha
  useEffect(() => {
    const fetchAppointmentsFromDB = async () => {
      try {
        const res = await fetch('http://localhost:8000/api/appointments');
        if (!res.ok) return;
        const data = await res.json();
        if (Array.isArray(data) && data.length > 0) {
          const dbSlots: AppointmentSlot[] = data.map((item: any) => {
            const startDate = new Date(item.start_time);
            const hour = startDate.getHours();
            const year = startDate.getFullYear();
            const month = String(startDate.getMonth() + 1).padStart(2, '0');
            const day = String(startDate.getDate()).padStart(2, '0');
            const dateStr = `${year}-${month}-${day}`;

            // Asociar con el identificador del abogado visual (l1..l6)
            let matchedLawyerId = item.lawyer_id;
            if (item.lawyer_name?.includes('Mendoza')) matchedLawyerId = 'l1';
            else if (item.lawyer_name?.includes('Ramirez')) matchedLawyerId = 'l2';
            else if (item.lawyer_name?.includes('Chen')) matchedLawyerId = 'l3';
            else if (item.lawyer_name?.includes('Morales')) matchedLawyerId = 'l4';
            else if (item.lawyer_name?.includes('Hernandez')) matchedLawyerId = 'l5';
            else if (item.lawyer_name?.includes('Vasquez')) matchedLawyerId = 'l6';

            return {
              id: item.id,
              clientName: item.client_name,
              serviceType: item.service_type === 'ITIN' ? 'Trámite ITIN (Form W-7)' 
                         : item.service_type === 'NOTARY' ? 'Notaría y Traducción'
                         : 'Asesoría Inmigración',
              hour: hour,
              lawyerId: matchedLawyerId,
              dateStr: dateStr,
              status: item.status || 'SCHEDULED'
            };
          });

          setAppointments(dbSlots);
        }
      } catch (err) {
        console.warn('Usando citas precargadas locales:', err);
      }
    };

    fetchAppointmentsFromDB();
  }, [selectedBranch]);

  // Conexión WebSockets en background sin banner visual
  useEffect(() => {
    if (typeof window === 'undefined') return;

    let ws: WebSocket | null = null;
    let reconnectTimeout: any = null;
    let isCleanedUp = false;

    const connectWebSocket = () => {
      if (isCleanedUp) return;
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.hostname}:8000/ws/appointments`;

      try {
        ws = new WebSocket(wsUrl);

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.event === 'APPOINTMENT_CREATED' && data.appointment) {
              let matchedLawyerId = data.appointment.lawyer_id;
              if (data.appointment.lawyer_name?.includes('Mendoza')) matchedLawyerId = 'l1';
              else if (data.appointment.lawyer_name?.includes('Ramirez')) matchedLawyerId = 'l2';
              else if (data.appointment.lawyer_name?.includes('Chen')) matchedLawyerId = 'l3';
              else if (data.appointment.lawyer_name?.includes('Morales')) matchedLawyerId = 'l4';
              else if (data.appointment.lawyer_name?.includes('Hernandez')) matchedLawyerId = 'l5';
              else if (data.appointment.lawyer_name?.includes('Vasquez')) matchedLawyerId = 'l6';

              const newAppt: AppointmentSlot = {
                id: data.appointment.id || Date.now().toString(),
                clientName: data.appointment.client_name,
                serviceType: data.appointment.service_type,
                hour: data.appointment.hour,
                lawyerId: matchedLawyerId,
                dateStr: data.appointment.date,
                status: data.appointment.status || 'SCHEDULED'
              };

              setAppointments((prev) => {
                const filtered = prev.filter((a) => a.id !== newAppt.id);
                return [...filtered, newAppt];
              });
            } else if (data.event === 'APPOINTMENT_CANCELLED' && data.appointment) {
              const cancelledId = data.appointment.id;
              setAppointments((prev) =>
                prev.map((a) => (a.id === cancelledId ? { ...a, status: 'CANCELLED' } : a))
              );
            }
          } catch (err) {
            console.error('Error parseando evento websocket:', err);
          }
        };

        ws.onclose = () => {
          if (!isCleanedUp) {
            reconnectTimeout = setTimeout(connectWebSocket, 4000);
          }
        };

        ws.onerror = () => {
          ws?.close();
        };
      } catch (err) {
        if (!isCleanedUp) {
          reconnectTimeout = setTimeout(connectWebSocket, 4000);
        }
      }
    };

    connectWebSocket();

    return () => {
      isCleanedUp = true;
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      if (ws) ws.close();
    };
  }, []);

  const triggerDatePicker = () => {
    if (dateInputRef.current) {
      if (typeof (dateInputRef.current as any).showPicker === 'function') {
        (dateInputRef.current as any).showPicker();
      } else {
        dateInputRef.current.focus();
      }
    }
  };

  const handleDateChange = (daysDelta: number) => {
    const parts = selectedDate.split('-').map(Number);
    const dateObj = new Date(parts[0], parts[1] - 1, parts[2]);
    dateObj.setDate(dateObj.getDate() + daysDelta);
    
    const year = dateObj.getFullYear();
    const month = String(dateObj.getMonth() + 1).padStart(2, '0');
    const day = String(dateObj.getDate()).padStart(2, '0');
    setSelectedDate(`${year}-${month}-${day}`);
  };

  const handleLogout = async () => {
    try {
      await fetch('/api/auth/logout', { method: 'POST' });
    } catch (err) {
      console.error('Error al cerrar sesión:', err);
    }
    document.cookie = 'session_token=; path=/; expires=Thu, 01 Jan 1970 00:00:01 GMT;';
    window.location.href = '/login';
  };

  const openNewSlotModal = (lawyerId: string, hour: number) => {
    setNewSlotData({
      lawyerId,
      hour,
      clientName: '',
      serviceType: t.services.itin
    });
    setIsModalOpen(true);
  };

  const handleCreateAppointment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newSlotData.clientName.trim()) return;

    const newAppt: AppointmentSlot = {
      id: Date.now().toString(),
      clientName: newSlotData.clientName,
      serviceType: newSlotData.serviceType,
      hour: newSlotData.hour,
      lawyerId: newSlotData.lawyerId,
      dateStr: selectedDate,
      status: 'SCHEDULED'
    };

    setAppointments((prev) => [...prev, newAppt]);
    setIsModalOpen(false);

    try {
      await fetch('http://localhost:8000/api/appointments', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          branch_code: selectedBranch,
          lawyer_id: newSlotData.lawyerId,
          client_name: newSlotData.clientName,
          service_type: newSlotData.serviceType,
          date: selectedDate,
          hour: newSlotData.hour
        })
      });
    } catch (err) {
      console.warn('Backend API no disponible para persistencia remota, mantenido localmente');
    }
  };

  const parts = selectedDate.split('-').map(Number);
  const displayDateObj = new Date(parts[0], parts[1] - 1, parts[2]);
  
  const dayNum = displayDateObj.getDate();
  const rawMonthName = displayDateObj.toLocaleDateString(lang === 'es' ? 'es-ES' : 'en-US', { month: 'long' });
  const capitalizedMonth = rawMonthName.charAt(0).toUpperCase() + rawMonthName.slice(1);
  const yearNum = displayDateObj.getFullYear();
  const formattedDate = `${dayNum} ${capitalizedMonth} ${yearNum}`;

  const rawDayName = displayDateObj.toLocaleDateString(lang === 'es' ? 'es-ES' : 'en-US', { weekday: 'long' });
  const dayName = rawDayName.charAt(0).toUpperCase() + rawDayName.slice(1);

  const dayAppointments = appointments.filter((a) => a.dateStr === selectedDate && a.status !== 'CANCELLED');
  const totalCitasHoy = dayAppointments.filter((a) => currentLawyers.some((l) => l.id === a.lawyerId)).length;

  return (
    <div className="min-h-screen flex flex-col font-sans bg-[#f8fafc] text-slate-800 antialiased">
      
      {/* 1. Header Top Bar (Responsive con Selector de Idioma) */}
      <header className="sticky top-0 z-40 bg-white border-b border-slate-200 shadow-xs">
        <div className="max-w-[1440px] mx-auto px-4 sm:px-8 h-20 flex items-center justify-between">
          
          {/* Logo Oficial & Marca */}
          <div className="flex items-center space-x-3.5">
            <img 
              src="/logo.png" 
              alt="La Victoria Foundation" 
              className="h-12 w-auto object-contain flex-shrink-0"
            />
            <div className="border-l border-slate-200 pl-3.5 hidden sm:block">
              <span className="font-extrabold text-sm tracking-tight text-[#075985] block leading-tight">
                {t.panel_title}
              </span>
              <p className="text-[11px] text-slate-500 font-medium">
                {t.panel_subtitle}
              </p>
            </div>
          </div>

          {/* Navegación Desktop */}
          <nav className="hidden xl:flex items-center gap-1.5 p-1 rounded-xl bg-slate-100/90 border border-slate-200">
            {(['CALENDARIO', 'ABOGADOS', 'SEDES', 'CITAS', 'REPORTES'] as const).map((tabKey) => {
              const isActive = activeTab === tabKey;
              return (
                <button
                  key={tabKey}
                  onClick={() => setActiveTab(tabKey)}
                  className={`px-5 py-2 rounded-lg text-xs font-bold tracking-wider transition-all ${
                    isActive 
                      ? 'bg-[#075985] text-white shadow-xs' 
                      : 'text-slate-600 hover:text-[#075985] hover:bg-white/60'
                  }`}
                >
                  {t.tabs[tabKey]}
                </button>
              );
            })}
          </nav>

          {/* Selector de Idioma, Selector de Sede y Botón Salir */}
          <div className="flex items-center space-x-2 sm:space-x-3">
            
            {/* Selector de Idioma (ES / EN) a la izquierda de la sede */}
            <button
              onClick={() => {
                const next = lang === 'es' ? 'en' : 'es';
                setLang(next);
                localStorage.setItem('lv_lang', next);
              }}
              className="flex items-center gap-1.5 px-3 py-2 sm:py-2.5 rounded-xl border border-slate-200 bg-white hover:border-[#075985] text-slate-700 hover:text-[#075985] transition-all shadow-xs text-xs font-bold cursor-pointer"
              title={lang === 'es' ? 'Switch to English' : 'Cambiar a Español'}
            >
              <Globe className="w-4 h-4 text-[#075985]" />
              <span className="uppercase">{lang}</span>
            </button>

            {/* Selector de Sede */}
            <div className="relative">
              <select
                value={selectedBranch}
                onChange={(e) => setSelectedBranch(e.target.value as any)}
                className="text-xs font-bold py-2 sm:py-2.5 pl-2.5 sm:pl-3.5 pr-7 sm:pr-8 rounded-xl border border-slate-200 bg-white text-slate-700 cursor-pointer focus:outline-none focus:ring-2 focus:ring-[#075985] shadow-xs max-w-[150px] sm:max-w-none truncate"
              >
                <option value="NY_QUEENS">{t.branches.NY_QUEENS}</option>
                <option value="TX_DALLAS">{t.branches.TX_DALLAS}</option>
              </select>
            </div>

            {/* Botón Salir */}
            <button
              onClick={handleLogout}
              className="px-3 sm:px-4 py-2 sm:py-2.5 rounded-xl bg-[#075985] hover:bg-[#0369a1] text-white text-xs font-bold transition-all shadow-xs flex items-center gap-1.5"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">{t.logout}</span>
            </button>

            {/* Botón Menú Móvil */}
            <button
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="xl:hidden p-2 rounded-xl border border-slate-200 text-slate-600 hover:bg-slate-100"
              title="Menú"
            >
              <Menu className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Menú Desplegable en Móvil */}
        {isMobileMenuOpen && (
          <div className="xl:hidden border-t border-slate-200 bg-white px-4 py-3 space-y-1">
            {(['CALENDARIO', 'ABOGADOS', 'SEDES', 'CITAS', 'REPORTES'] as const).map((tabKey) => (
              <button
                key={tabKey}
                onClick={() => {
                  setActiveTab(tabKey);
                  setIsMobileMenuOpen(false);
                }}
                className={`w-full text-left px-4 py-2.5 rounded-lg text-xs font-bold ${
                  activeTab === tabKey ? 'bg-[#075985] text-white' : 'text-slate-600 hover:bg-slate-50'
                }`}
              >
                {t.tabs[tabKey]}
              </button>
            ))}
          </div>
        )}
      </header>

      {/* Banner de Aviso MVP / Información de Prueba */}
      <div className="bg-gradient-to-r from-amber-50 via-sky-50 to-amber-50 border-b border-amber-200/50 py-2 px-4 sm:px-8">
        <div className="max-w-[1440px] mx-auto flex flex-wrap items-center justify-between gap-2 text-xs">
          <div className="flex items-center gap-2 text-amber-900 font-medium">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-amber-500 text-white font-extrabold text-[10px] tracking-wider shadow-xs">
              <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse"></span>
              {t.mvp_badge}
            </span>
            <span>{t.mvp_notice}</span>
          </div>
          <span className="text-[11px] font-semibold text-sky-800 hidden md:inline">
            La Victoria Foundation © 2026
          </span>
        </div>
      </div>

      {/* 2. Sub-Header: Controles de Fecha & Métricas (Escala Estilizada y Equilibrada) */}
      <div className="max-w-[1440px] w-full mx-auto px-4 sm:px-8 pt-4 pb-3 flex flex-wrap items-center justify-between gap-3">
        
        {/* Controles de Fecha con Selector Moderno Flotante */}
        <div className="flex flex-wrap items-center gap-2 relative">
          <div className="flex items-center p-0.5 rounded-lg bg-white border border-slate-200 shadow-xs">
            <button
              onClick={() => handleDateChange(-1)}
              className="p-1.5 rounded-md text-slate-600 hover:bg-slate-100 transition-colors"
              title={t.prev_day}
            >
              <ChevronLeft className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => handleDateChange(1)}
              className="p-1.5 rounded-md text-slate-600 hover:bg-slate-100 transition-colors"
              title={t.next_day}
            >
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Botón Píldora de Fecha con Apertura de Calendario Estilizado */}
          <div className="relative" ref={calendarPopupRef}>
            <button
              onClick={() => setIsCalendarOpen(!isCalendarOpen)}
              className="flex items-center gap-2 px-3.5 py-1.5 rounded-xl bg-white border border-slate-200 hover:border-[#075985] shadow-xs cursor-pointer group transition-all text-left"
              title="Abrir calendario"
            >
              <CalendarIcon className="w-3.5 h-3.5 text-[#075985] group-hover:scale-110 transition-transform" />
              <span className="text-xs font-bold text-slate-800 select-none">
                {formattedDate}
              </span>
            </button>

            {/* POPUP DE CALENDARIO MODERNO Y ELEGANTE */}
            {isCalendarOpen && (
              <div className="absolute left-0 top-full mt-2 z-50 w-72 bg-white rounded-2xl shadow-xl border border-slate-200/90 p-4 animate-in fade-in zoom-in-95 duration-150">
                {/* Header del Calendario: Mes y Año + Flechas */}
                <div className="flex items-center justify-between pb-3 mb-2 border-b border-slate-100">
                  <span className="font-extrabold text-sm text-slate-900 capitalize">
                    {new Date(pickerYear, pickerMonth).toLocaleDateString(lang === 'es' ? 'es-ES' : 'en-US', { month: 'long', year: 'numeric' })}
                  </span>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => {
                        if (pickerMonth === 0) {
                          setPickerMonth(11);
                          setPickerYear(pickerYear - 1);
                        } else {
                          setPickerMonth(pickerMonth - 1);
                        }
                      }}
                      className="p-1 rounded-lg hover:bg-slate-100 text-slate-500"
                    >
                      <ChevronLeft className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => {
                        if (pickerMonth === 11) {
                          setPickerMonth(0);
                          setPickerYear(pickerYear + 1);
                        } else {
                          setPickerMonth(pickerMonth + 1);
                        }
                      }}
                      className="p-1 rounded-lg hover:bg-slate-100 text-slate-500"
                    >
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {/* Días de la semana */}
                <div className="grid grid-cols-7 gap-1 text-center mb-1 text-[11px] font-bold text-slate-400">
                  {lang === 'es' 
                    ? ['Do', 'Lu', 'Ma', 'Mi', 'Ju', 'Vi', 'Sá'].map((d) => <span key={d}>{d}</span>)
                    : ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'].map((d) => <span key={d}>{d}</span>)
                  }
                </div>

                {/* Días del Mes */}
                <div className="grid grid-cols-7 gap-1 text-center text-xs">
                  {(() => {
                    const firstDayIndex = new Date(pickerYear, pickerMonth, 1).getDay();
                    const daysInMonth = new Date(pickerYear, pickerMonth + 1, 0).getDate();
                    const blanks = Array.from({ length: firstDayIndex });
                    const days = Array.from({ length: daysInMonth }, (_, i) => i + 1);

                    const selectedParts = selectedDate.split('-').map(Number);
                    const isSameMonthYear = selectedParts[0] === pickerYear && (selectedParts[1] - 1) === pickerMonth;

                    return (
                      <>
                        {blanks.map((_, idx) => (
                          <div key={`blank-${idx}`} className="h-8" />
                        ))}
                        {days.map((day) => {
                          const isSelected = isSameMonthYear && selectedParts[2] === day;
                          const monthStr = String(pickerMonth + 1).padStart(2, '0');
                          const dayStr = String(day).padStart(2, '0');
                          const fullDateStr = `${pickerYear}-${monthStr}-${dayStr}`;

                          return (
                            <button
                              key={day}
                              onClick={() => {
                                setSelectedDate(fullDateStr);
                                setIsCalendarOpen(false);
                              }}
                              className={`h-8 w-8 mx-auto rounded-xl flex items-center justify-center font-bold transition-all ${
                                isSelected
                                  ? 'bg-[#075985] text-white shadow-xs scale-105'
                                  : 'text-slate-700 hover:bg-sky-50 hover:text-[#075985]'
                              }`}
                            >
                              {day}
                            </button>
                          );
                        })}
                      </>
                    );
                  })()}
                </div>

                {/* Pie con botón de fecha de hoy */}
                <div className="pt-3 mt-2 border-t border-slate-100 flex items-center justify-between text-xs">
                  <button
                    onClick={() => {
                      setSelectedDate('2026-09-03');
                      setPickerMonth(8);
                      setPickerYear(2026);
                      setIsCalendarOpen(false);
                    }}
                    className="text-[#075985] font-bold hover:underline"
                  >
                    {lang === 'es' ? 'Ir a Hoy (3 Sept)' : 'Go to Today (Sept 3)'}
                  </button>
                  <button
                    onClick={() => setIsCalendarOpen(false)}
                    className="text-slate-400 hover:text-slate-600 font-medium"
                  >
                    {lang === 'es' ? 'Cerrar' : 'Close'}
                  </button>
                </div>
              </div>
            )}
          </div>

          <span className="font-serif italic text-lg sm:text-xl text-[#075985] font-semibold tracking-wide ml-1">
            {dayName}
          </span>
        </div>

        {/* Tarjetas de Métricas Elegantes y Compactas */}
        <div className="flex items-center gap-2 sm:gap-2.5 w-full sm:w-auto justify-between sm:justify-start">
          <div className="flex-1 sm:flex-initial px-3.5 py-1.5 rounded-xl bg-white border border-slate-200 flex items-center gap-2.5 shadow-xs">
            <div className="w-8 h-8 rounded-lg bg-sky-50 text-[#075985] flex items-center justify-center flex-shrink-0">
              <UserCheck className="w-4 h-4" />
            </div>
            <div>
              <div className="text-[9px] font-bold uppercase tracking-wider text-slate-400 leading-none mb-0.5">{t.total_branch_appointments}</div>
              <div className="text-base font-black text-slate-900 leading-tight">
                {totalCitasHoy}
              </div>
            </div>
          </div>

          <div className="flex-1 sm:flex-initial px-3.5 py-1.5 rounded-xl bg-white border border-slate-200 flex items-center gap-2.5 shadow-xs">
            <div className="w-8 h-8 rounded-lg bg-sky-50 text-[#075985] flex items-center justify-center flex-shrink-0">
              <Clock className="w-4 h-4" />
            </div>
            <div>
              <div className="text-[9px] font-bold uppercase tracking-wider text-slate-400 leading-none mb-0.5">{t.available_slots}</div>
              <div className="text-base font-black text-[#075985] leading-tight">
                {currentLawyers.length * 7 - totalCitasHoy}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 3. Multi-Resource Grid: Calendario Moderno, Suave y Estético */}
      <div className="max-w-[1440px] w-full mx-auto px-4 sm:px-8 pb-12 flex-1 flex flex-col">
        <div className="rounded-3xl border border-slate-200/80 bg-white shadow-sm overflow-hidden flex flex-col flex-1">
          
          <div className="overflow-x-auto flex-1 flex flex-col">
            <div className="min-w-[760px] w-full flex flex-col flex-1">
              
              {/* Header de la Grilla: Columnas por Abogado con Acabado Moderno */}
              <div className="grid grid-cols-[100px_repeat(3,1fr)] border-b border-slate-200/90 bg-slate-50/60 sticky top-0 z-10 backdrop-blur-xs">
                <div className="p-3 text-[11px] font-extrabold uppercase tracking-wider text-slate-400 flex items-center justify-center border-r border-slate-100">
                  {t.hour_est}
                </div>

                {currentLawyers.map((lawyer) => {
                  const citasAbogado = dayAppointments.filter((a) => a.lawyerId === lawyer.id).length;
                  return (
                    <div
                      key={lawyer.id}
                      className="py-3 px-4 text-center border-r last:border-r-0 border-slate-100 flex flex-col items-center justify-center transition-colors hover:bg-slate-50/90"
                    >
                      <div className="flex items-center gap-1.5 mb-0.5">
                        <span className="font-extrabold text-sm text-slate-800 tracking-tight">
                          {lawyer.name}
                        </span>
                        {lawyer.verified && (
                          <ShieldCheck className="w-3.5 h-3.5 text-[#075985]" />
                        )}
                      </div>
                      <div className="text-[11px] font-medium text-slate-500 mb-1.5">
                        {lawyer.role}
                      </div>
                      <div className="flex items-center gap-1.5">
                        <span className="text-[9px] uppercase font-bold tracking-wider px-2.5 py-0.5 rounded-full bg-[#075985]/10 text-[#075985] border border-[#075985]/20">
                          {t.priority} {lawyer.priority}
                        </span>
                        <span className="text-[11px] font-semibold text-slate-500">
                          {citasAbogado} {t.appointments_today}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Filas del Calendario (Bordes Suaves, Espaciado Cómodo y Aspecto Pulido) */}
              <div className="divide-y divide-slate-100 bg-white flex-1">
                {timeSlots.map((slot) => {
                  // Fila de Almuerzo institucional: Suave y perfectamente integrada
                  if (slot.isLunch) {
                    return (
                      <div
                        key={slot.hour}
                        className="grid grid-cols-[100px_repeat(3,1fr)] min-h-[52px] bg-slate-50/50"
                      >
                        <div className="p-2.5 text-xs font-bold text-slate-400 flex items-center justify-center border-r border-slate-100">
                          {slot.label}
                        </div>
                        <div className="col-span-3 flex items-center justify-center gap-2 text-slate-500 text-xs font-semibold tracking-wide bg-sky-50/30">
                          <Coffee className="w-4 h-4 text-[#075985]" />
                          <span>{t.lunch_break}</span>
                        </div>
                      </div>
                    );
                  }

                  // Filas regulares con slots para cada abogado
                  return (
                    <div
                      key={slot.hour}
                      className="grid grid-cols-[100px_repeat(3,1fr)] min-h-[78px] group hover:bg-slate-50/30 transition-colors"
                    >
                      {/* Etiqueta de Hora */}
                      <div className="p-3 text-xs font-semibold text-slate-400 flex items-start justify-center pt-3 border-r border-slate-100 select-none">
                        {slot.label}
                      </div>

                      {/* Celdas por Abogado */}
                      {currentLawyers.map((lawyer) => {
                        const appointment = dayAppointments.find(
                          (a) => a.hour === slot.hour && a.lawyerId === lawyer.id
                        );

                        return (
                          <div
                            key={lawyer.id}
                            className="p-2 border-r last:border-r-0 border-slate-100 relative group/cell"
                          >
                            {appointment ? (
                              // Tarjeta de Cita Agendada Moderna con Bordes Suaves
                              <div className="h-full w-full rounded-2xl bg-gradient-to-r from-sky-50/90 to-blue-50/60 border border-sky-200/80 p-2.5 flex flex-col justify-between shadow-xs hover:shadow-sm hover:border-[#075985]/40 transition-all">
                                <div className="flex items-start justify-between gap-1.5">
                                  <div className="min-w-0 flex-1">
                                    <span className="font-bold text-xs text-[#075985] block truncate leading-tight">
                                      {appointment.serviceType}
                                    </span>
                                    <p className="text-xs font-medium text-slate-700 mt-0.5 truncate">
                                      👤 {appointment.clientName}
                                    </p>
                                  </div>
                                  <CheckCircle2 className="w-3.5 h-3.5 text-[#075985] flex-shrink-0 mt-0.5" />
                                </div>
                                <div className="flex items-center justify-end text-[10px] font-semibold mt-1">
                                  <span className="inline-flex items-center px-1.5 py-0.5 rounded-md bg-[#075985]/10 text-[#075985] font-bold">Confirmado</span>
                                </div>
                              </div>
                            ) : (
                              // Slot Disponible con Borde Suave e Interacción Sutil
                              <div 
                                onClick={() => openNewSlotModal(lawyer.id, slot.hour)}
                                className="h-full w-full rounded-2xl border border-dashed border-slate-200 flex items-center justify-center opacity-60 sm:opacity-0 group-hover/cell:opacity-100 transition-all hover:border-[#075985] hover:bg-sky-50/50 hover:shadow-xs cursor-pointer py-2"
                              >
                                <span className="text-xs font-bold text-[#075985] flex items-center gap-1.5">
                                  <Plus className="w-3.5 h-3.5" />
                                  {t.book_slot}
                                </span>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Modal para Agendar Nueva Cita (Bilingüe) */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4">
          <div className="bg-white rounded-2xl shadow-xl max-w-md w-full p-6 border border-slate-200 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100">
              <div className="flex items-center gap-2 text-[#075985]">
                <FileText className="w-5 h-5" />
                <h3 className="font-bold text-base text-slate-900">{t.modal_title}</h3>
              </div>
              <button 
                onClick={() => setIsModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateAppointment} className="mt-5 space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                  {t.client_name}
                </label>
                <input
                  type="text"
                  required
                  placeholder={t.client_placeholder}
                  value={newSlotData.clientName}
                  onChange={(e) => setNewSlotData({ ...newSlotData, clientName: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-[#075985]"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                  {t.service_type}
                </label>
                <select
                  value={newSlotData.serviceType}
                  onChange={(e) => setNewSlotData({ ...newSlotData, serviceType: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-[#075985]"
                >
                  <option value={t.services.itin}>{t.services.itin}</option>
                  <option value={t.services.i130}>{t.services.i130}</option>
                  <option value={t.services.asilo}>{t.services.asilo}</option>
                  <option value={t.services.i485}>{t.services.i485}</option>
                  <option value={t.services.notaria}>{t.services.notaria}</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3 pt-1">
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-100 text-xs">
                  <span className="text-slate-400 block font-medium">{t.date}:</span>
                  <span className="font-bold text-slate-800">{selectedDate}</span>
                </div>
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-100 text-xs">
                  <span className="text-slate-400 block font-medium">{t.time}:</span>
                  <span className="font-bold text-slate-800">{newSlotData.hour}:00 EST</span>
                </div>
              </div>

              <div className="flex gap-3 pt-3">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="flex-1 py-2.5 rounded-xl border border-slate-200 text-slate-600 font-semibold text-xs hover:bg-slate-50"
                >
                  {t.cancel}
                </button>
                <button
                  type="submit"
                  className="flex-1 py-2.5 rounded-xl bg-[#075985] text-white font-bold text-xs hover:bg-[#0369a1] shadow-xs"
                >
                  {t.confirm_appointment}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}
