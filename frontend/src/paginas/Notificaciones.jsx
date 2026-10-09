import { useState } from 'react';
import { Check, CheckCheck } from 'lucide-react';
import { Encabezado, Estado, Aviso } from '../componentes/Estado';
import { Paginacion } from '../componentes/Paginacion';
import { usarDatos } from '../hooks/usarDatos';
import { servicioDatos } from '../servicios/servicioDatos';
import { fecha } from '../utilidades/formato';

export function PaginaNotificaciones() {
  const [pagina, establecerPagina] = useState(1);
  const { datos, cargando, error, recargar } = usarDatos(() => servicioDatos.notificaciones(pagina), [pagina]);
  const [mensaje, establecerMensaje] = useState('');
  async function leerTodas() {
    try { await servicioDatos.leerTodas(); establecerMensaje('Notificaciones marcadas como leídas.'); recargar();
      window.dispatchEvent(new Event('notificaciones-actualizadas')); }
    catch (fallo) { establecerMensaje(fallo.message); }
  }
  async function leer(id) {
    try { await servicioDatos.leer(id); recargar(); window.dispatchEvent(new Event('notificaciones-actualizadas')); }
    catch (fallo) { establecerMensaje(fallo.message); }
  }
  return <><Encabezado seccion="ACTIVIDAD" titulo="Notificaciones"
    accion={<button className="btn btn-secondary" onClick={leerTodas} disabled={!datos?.no_leidas}>
      <CheckCheck size={17} aria-hidden="true" />Marcar todas como leídas</button>} />
    <Aviso mensaje={mensaje} /><Estado cargando={cargando} error={error} alReintentar={recargar}>
      {datos?.notificaciones?.data?.length ? <div className="tarjeta lista-notificaciones">
        {datos.notificaciones.data.map((notificacion) => <article className={notificacion.leida_en ? 'leida' : ''} key={notificacion.id}>
          <div><strong>{notificacion.titulo}</strong><p>{notificacion.mensaje}</p>
            <small>{fecha(notificacion.created_at)}</small></div>
          {!notificacion.leida_en && <button className="enlace-tabla" onClick={() => leer(notificacion.id)}>
            <Check size={15} aria-hidden="true" />Marcar leída</button>}
        </article>)}</div> : <div className="estado-panel">No tienes notificaciones.</div>}
      <Paginacion datos={datos?.notificaciones} alCambiar={establecerPagina} />
    </Estado></>;
}
