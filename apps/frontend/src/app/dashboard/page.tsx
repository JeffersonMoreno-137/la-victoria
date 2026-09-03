'use client';

import React, { useEffect, useState } from 'react';
import { Calendar, Users, MapPin, CheckCircle, Clock, FileText, ChevronRight } from 'lucide-react';

interface MetricData {
  total_appointments: number;
  scheduled_appointments: number;
  cancelled_appointments: number;
  rescheduled_appointments: number;
  queens_appointments: number;
  dallas_appointments: number;
}

interface AppointmentItem {
  id: string;
  branch_code: string;
  branch_name: string;
  lawyer_name: string;
  client_name: string;
  service_type: string;
  start_time: string;
  status: string;
}

export default function DashboardPage() {
  const [metrics, setMetrics] = useState<MetricData | null>(null);
  const [appointments, setAppointments] = useState<AppointmentItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const [resMetrics, resAppts] = await Promise.all([
          fetch(`${apiUrl}/api/metrics`),
          fetch(`${apiUrl}/api/appointments?limit=10`)
        ]);

        if (resMetrics.ok && resAppts.ok) {
          const mData = await resMetrics.json();
          const aData = await resAppts.json();
          setMetrics(mData);
          setAppointments(aData);
        } else {
          // Datos demostrativos iniciales si backend local aún no tiene base levantada
          setMetrics({
            total_appointments: 12,
            scheduled_appointments: 9,
            cancelled_appointments: 2,
            rescheduled_appointments: 1,
            queens_appointments: 7,
            dallas_appointments: 5
          });
          setAppointments([
            {
              id: '1',
              branch_code: 'NY_QUEENS',
              branch_name: 'Sede Queens, NY',
              lawyer_name: 'Abg. Carlos Mendoza (L1)',
              client_name: 'Juan Perez',
              service_type: 'ITIN',
              start_time: new Date(Date.now() + 86400000 * 2).toISOString(),
              status: 'SCHEDULED'
            },
            {
              id: '2',
              branch_code: 'TX_DALLAS',
              branch_name: 'Sede Dallas, TX',
              lawyer_name: 'Abg. Elena Morales (L1)',
              client_name: 'Maria Gomez',
              service_type: 'IMMIGRATION',
              start_time: new Date(Date.now() + 86400000 * 3).toISOString(),
              status: 'SCHEDULED'
            }
          ]);
        }
      } catch (err) {
        console.error('Error fetching dashboard data:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* Top Navbar */}
      <header className="h-16 border-b border-slate-800 bg-slate-900/50 backdrop-blur px-8 flex items-center justify-between sticky top-0 z-10">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-sky-500 flex items-center justify-center font-bold text-white shadow-lg shadow-sky-500/20">
            LV
          </div>
          <div>
            <h1 className="font-semibold text-sm">La Victoria Foundation</h1>
            <p className="text-xs text-slate-400">Legal AI & Appointment Management</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
            Asistente Luna Activo
          </span>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 p-8 max-w-7xl w-full mx-auto space-y-8">
        {/* Welcome Section */}
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Panel de Control General</h2>
          <p className="text-sm text-slate-400 mt-1">Supervisión en tiempo real de citas, sedes y abogados asignados.</p>
        </div>

        {/* Metrics Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow-sm">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-xs font-medium">Total de Citas</span>
              <Calendar className="w-4 h-4 text-sky-400" />
            </div>
            <div className="mt-3 text-3xl font-bold text-white">
              {metrics ? metrics.total_appointments : '...'}
            </div>
            <p className="text-xs text-slate-500 mt-1">Histórico general registrado</p>
          </div>

          <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow-sm">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-xs font-medium">Citas Confirmadas</span>
              <CheckCircle className="w-4 h-4 text-emerald-400" />
            </div>
            <div className="mt-3 text-3xl font-bold text-emerald-400">
              {metrics ? metrics.scheduled_appointments : '...'}
            </div>
            <p className="text-xs text-slate-500 mt-1">Slots activos próximos (+24h)</p>
          </div>

          <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow-sm">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-xs font-medium">Sede Queens, NY</span>
              <MapPin className="w-4 h-4 text-amber-400" />
            </div>
            <div className="mt-3 text-3xl font-bold text-amber-400">
              {metrics ? metrics.queens_appointments : '...'}
            </div>
            <p className="text-xs text-slate-500 mt-1">3 Abogados activos (L1, L2, L3)</p>
          </div>

          <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow-sm">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-xs font-medium">Sede Dallas, TX</span>
              <MapPin className="w-4 h-4 text-indigo-400" />
            </div>
            <div className="mt-3 text-3xl font-bold text-indigo-400">
              {metrics ? metrics.dallas_appointments : '...'}
            </div>
            <p className="text-xs text-slate-500 mt-1">3 Abogados activos (L1, L2, L3)</p>
          </div>
        </div>

        {/* Appointments Table */}
        <div className="rounded-2xl bg-slate-900 border border-slate-800 overflow-hidden shadow-sm">
          <div className="p-6 border-b border-slate-800 flex items-center justify-between">
            <div>
              <h3 className="text-base font-semibold text-white">Últimas Citas Agendadas</h3>
              <p className="text-xs text-slate-400 mt-0.5">Asignadas por el algoritmo First Available</p>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-900/60 text-xs uppercase font-semibold text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="px-6 py-4">Cliente</th>
                  <th className="px-6 py-4">Servicio</th>
                  <th className="px-6 py-4">Sede</th>
                  <th className="px-6 py-4">Abogado Asignado</th>
                  <th className="px-6 py-4">Fecha y Hora</th>
                  <th className="px-6 py-4">Estado</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {appointments.map((appt) => (
                  <tr key={appt.id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="px-6 py-4 font-medium text-white">{appt.client_name}</td>
                    <td className="px-6 py-4 text-slate-300">
                      <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium bg-slate-800 border border-slate-700 text-sky-400">
                        {appt.service_type}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-slate-400">{appt.branch_name}</td>
                    <td className="px-6 py-4 text-slate-300">{appt.lawyer_name}</td>
                    <td className="px-6 py-4 text-slate-400 font-mono text-xs">
                      {new Date(appt.start_time).toLocaleString('es-ES', { timeZone: 'America/New_York' })} EST
                    </td>
                    <td className="px-6 py-4">
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        {appt.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </main>
    </div>
  );
}
