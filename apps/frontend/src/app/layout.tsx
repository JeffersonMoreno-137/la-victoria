import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'La Victoria Foundation - Dashboard Administrativo',
  description: 'Sistema de gestión de citas legales y orientación comunitaria',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
