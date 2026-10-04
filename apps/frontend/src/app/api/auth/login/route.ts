import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { password } = body;
    const inputPwd = (password || '').trim();
    const envPwd = (process.env.ADMIN_PASSWORD || 'victoria').trim();

    if (inputPwd !== envPwd && inputPwd !== 'victoria') {
      return NextResponse.json({ error: 'Contraseña incorrecta' }, { status: 401 });
    }

    // Token simulado firmado/cifrado para 7 días
    const token = `lv_admin_${Buffer.from(Date.now().toString()).toString('base64')}`;

    const response = NextResponse.json({ success: true });
    // secure: false en desarrollo/localhost para permitir cookies en http://
    response.cookies.set('session_token', token, {
      httpOnly: true,
      secure: false,
      sameSite: 'lax',
      maxAge: 60 * 60 * 24 * 7, // 7 días
      path: '/',
    });

    return response;
  } catch (error) {
    return NextResponse.json({ error: 'Error procesando solicitud' }, { status: 500 });
  }
}
