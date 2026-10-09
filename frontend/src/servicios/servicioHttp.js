const origen = (import.meta.env.VITE_API_URL || '/api').replace(/\/$/, '');
let tokenCsrf = null;
let renovacionPendiente = null;

export class ErrorSolicitud extends Error {
  constructor(mensaje, estado, errores = {}) {
    super(mensaje);
    this.name = 'ErrorSolicitud';
    this.estado = estado;
    this.errores = errores;
  }
}

function mensajeError(estado, datos) {
  if (estado === 503 && datos?.mensaje) return datos.mensaje;
  if (estado >= 500) return 'El servidor no pudo completar la solicitud. Inténtalo de nuevo.';
  if (estado === 401 || estado === 419) return 'Tu sesión terminó. Inicia sesión nuevamente.';
  if (estado === 403) return 'No tienes permiso para realizar esta acción.';
  if (estado === 404) return 'No encontramos lo que buscas.';
  const primero = Object.values(datos?.errors || {})[0];
  const mensaje = primero?.[0] || datos?.mensaje || datos?.message;
  if (typeof mensaje === 'string' && mensaje.startsWith('validation.')) {
    return 'Revisa los datos ingresados e inténtalo nuevamente.';
  }
  return mensaje || 'No se pudo completar la solicitud.';
}

async function asegurarCsrf() {
  if (!tokenCsrf) {
    const respuesta = await fetch(`${origen}/sesion/csrf`, { credentials: 'include' });
    if (!respuesta.ok) throw new ErrorSolicitud('No se pudo iniciar una solicitud segura.', respuesta.status);
    tokenCsrf = (await respuesta.json()).token;
  }
  return tokenCsrf;
}

async function renovarSesion() {
  if (!renovacionPendiente) {
    renovacionPendiente = (async () => {
      const token = await asegurarCsrf();
      const respuesta = await fetch(`${origen}/auth/refresh`, {
        method: 'POST', credentials: 'include',
        headers: { Accept: 'application/json', 'X-CSRF-TOKEN': token },
      });
      return respuesta.ok;
    })().finally(() => { renovacionPendiente = null; });
  }
  return renovacionPendiente;
}

async function enviar(ruta, { metodo = 'GET', datos, archivo = false } = {}) {
  const cabeceras = { Accept: 'application/json' };
  if (metodo !== 'GET' && metodo !== 'HEAD') {
    cabeceras['X-CSRF-TOKEN'] = await asegurarCsrf();
  }
  if (datos && !(datos instanceof FormData)) cabeceras['Content-Type'] = 'application/json';

  let respuesta;
  try {
    respuesta = await fetch(`${origen}${ruta}`, {
      method: metodo,
      credentials: 'include',
      headers: cabeceras,
      body: datos ? (datos instanceof FormData ? datos : JSON.stringify(datos)) : undefined,
    });
  } catch {
    throw new ErrorSolicitud('No hay conexión con UrbanCloud AI. Revisa tu red.', 0);
  }

  if (respuesta.status === 401 && !['/login', '/registro', '/auth/refresh'].includes(ruta)) {
    try {
      if (await renovarSesion()) {
        respuesta = await fetch(`${origen}${ruta}`, {
          method: metodo, credentials: 'include', headers: cabeceras,
          body: datos ? (datos instanceof FormData ? datos : JSON.stringify(datos)) : undefined,
        });
      }
    } catch { /* Se informa la sesión vencida usando el error original. */ }
  }

  if (respuesta.status === 419) tokenCsrf = null;
  if (!respuesta.ok) {
    if (respuesta.status === 401 || respuesta.status === 419) {
      window.dispatchEvent(new Event('sesion-caducada'));
    }
    const contenido = await respuesta.json().catch(() => ({}));
    throw new ErrorSolicitud(mensajeError(respuesta.status, contenido), respuesta.status, contenido.errors || {});
  }
  if (archivo) return respuesta.blob();
  return respuesta.status === 204 ? null : respuesta.json();
}

export const servicioHttp = {
  obtener: (ruta) => enviar(ruta),
  publicar: (ruta, datos) => enviar(ruta, { metodo: 'POST', datos }),
  cambiar: (ruta, datos) => enviar(ruta, { metodo: 'PATCH', datos }),
  archivo: (ruta) => enviar(new URL(ruta).pathname, { archivo: true }),
  limpiarCsrf: () => { tokenCsrf = null; },
};
