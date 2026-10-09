import { beforeEach, expect, it, vi } from 'vitest';
import { servicioHttp } from '../servicios/servicioHttp';

beforeEach(() => {
  servicioHttp.limpiarCsrf();
  vi.restoreAllMocks();
});

it('renueva la sesión en cookies y reintenta la solicitud original', async () => {
  const respuestas = [
    { status: 401, ok: false, json: async () => ({ mensaje: 'Sesión vencida' }) },
    { status: 200, ok: true, json: async () => ({ token: 'csrf-prueba' }) },
    { status: 200, ok: true, json: async () => ({ mensaje: 'Renovada' }) },
    { status: 200, ok: true, json: async () => ({ usuario: { rol: 'Ciudadano' } }) },
  ];
  const solicitud = vi.spyOn(globalThis, 'fetch').mockImplementation(async () => respuestas.shift());
  const datos = await servicioHttp.obtener('/dashboard');

  expect(datos.usuario.rol).toBe('Ciudadano');
  expect(solicitud.mock.calls.map(([ruta]) => ruta)).toEqual([
    '/api/dashboard', '/api/sesion/csrf', '/api/auth/refresh', '/api/dashboard',
  ]);
  expect(solicitud.mock.calls[2][1]).toMatchObject({
    method: 'POST', credentials: 'include', headers: { 'X-CSRF-TOKEN': 'csrf-prueba' },
  });
});
