import { useEffect, useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router';
import { Aviso, Encabezado, Estado, TarjetasResumen } from '../componentes/Estado';
import { DatosIncidencia, HistorialIncidencia, TablaIncidencias } from '../componentes/Incidencias';
import { Evidencias } from '../componentes/Evidencias';
import { Mapa } from '../componentes/Mapa';
import { Paginacion } from '../componentes/Paginacion';
import { usarDatos } from '../hooks/usarDatos';
import { servicioDatos } from '../servicios/servicioDatos';

export function PanelTecnico({ historial = false }) {
  const ubicacion = useLocation();
  const [pagina, establecerPagina] = useState(1);
  const { datos, cargando, error, recargar } = usarDatos(() => historial
    ? servicioDatos.historialTecnico(pagina) : servicioDatos.tareas(pagina), [historial, pagina]);
  const { datos: resumen } = usarDatos(servicioDatos.resumen, []);
  return <><Encabezado seccion="PERSONAL TÉCNICO" titulo={historial ? 'Historial de tareas' : 'Mis tareas'}
    descripcion={historial ? 'Intervenciones anteriores.' : 'Casos asignados para atención.'} />
    <Aviso mensaje={ubicacion.state?.aviso} tipo="exito" />
    {!historial && <TarjetasResumen elementos={[
      ['Activas', resumen?.activas, 'Tareas asignadas'], ['Anteriores', resumen?.anteriores, 'Intervenciones pasadas'],
      ['Impedidas', resumen?.impedidas, 'Con impedimento'], ['Avisos', resumen?.no_leidas, 'Sin leer'],
    ]} />}
    <Estado cargando={cargando} error={error} alReintentar={recargar}>
      <TablaIncidencias incidencias={datos?.data || []} prefijo="/tecnico/tareas" sinEnlace={historial} />
      <Paginacion datos={datos} alCambiar={establecerPagina} />
    </Estado></>;
}

export function DetalleTecnico() {
  const { id } = useParams();
  const navegar = useNavigate();
  const { datos, cargando, error, recargar } = usarDatos(() => servicioDatos.detalleTecnico(id), [id]);
  const [accion, establecerAccion] = useState('en_camino');
  const [comentario, establecerComentario] = useState('');
  const [foto, establecerFoto] = useState(null);
  const [tipo, establecerTipo] = useState('ATENCION');
  const [mensaje, establecerMensaje] = useState('');
  const [enviando, establecerEnviando] = useState(false);

  async function registrar(evento) {
    evento.preventDefault(); establecerEnviando(true); establecerMensaje('');
    const datosEnvio = new FormData();
    datosEnvio.append('accion', accion);
    datosEnvio.append('comentario', comentario);
    if (foto) { datosEnvio.append('fotografia', foto); datosEnvio.append('tipo_evidencia', accion === 'atendido' ? 'CIERRE' : tipo); }
    try {
      const resultado = await servicioDatos.actualizarTarea(id, datosEnvio);
      if (resultado.estado === 'Impedido') {
        navegar('/tecnico/historial', { replace: true,
          state: { aviso: 'Impedimento registrado correctamente. La tarea pasó al historial.' } });
        return;
      }
      establecerMensaje('Avance registrado correctamente.'); establecerComentario(''); establecerFoto(null);
      recargar();
    } catch (fallo) { establecerMensaje(fallo.message); }
    finally { establecerEnviando(false); }
  }

  const opciones = datos?.estado === 'Asignado'
    ? [['en_camino', 'En camino'], ['iniciar', 'Iniciar atención'], ['impedido', 'Impedido']]
    : datos?.estado === 'En atención'
      ? [['atendido', 'Atendido'], ['impedido', 'Impedido']] : [];

  useEffect(() => {
    if (datos?.estado === 'En atención') establecerAccion('atendido');
  }, [datos?.estado]);

  return <><Encabezado seccion="PERSONAL TÉCNICO" titulo="Detalle de tarea"
    accion={<button className="btn btn-secondary" onClick={() => navegar(-1)}>Volver</button>} />
    <Aviso mensaje={mensaje} tipo={mensaje.includes('correctamente') ? 'exito' : 'error'} />
    <Estado cargando={cargando} error={error} alReintentar={recargar}>
      <div className="distribucion"><div className="columna-lateral"><DatosIncidencia incidencia={datos} />
        {datos?.latitud && datos.longitud && <section className="tarjeta padding"><h2>Ubicación</h2>
          <Mapa latitud={datos.latitud} longitud={datos.longitud} /></section>}
        <Evidencias evidencias={datos?.evidencias} /></div>
        <div className="columna-lateral">{opciones.length > 0 && <section className="tarjeta padding"><h2>Registrar avance</h2>
          {datos?.estado === 'Asignado' && <p className="descripcion">Para marcar este reporte como Atendido, selecciona primero «Iniciar atención» y registra el avance. Después aparecerá la opción «Atendido».</p>}
          <form className="formulario" onSubmit={registrar}>
            <label className="campo"><span>Acción</span><select value={opciones.some(([clave]) => clave === accion) ? accion : opciones[0][0]}
              onChange={(evento) => establecerAccion(evento.target.value)}>{opciones.map(([clave, etiqueta]) =>
                <option key={clave} value={clave}>{etiqueta}</option>)}</select></label>
            <label className="campo"><span>Comentario *</span><textarea required minLength={10} value={comentario}
              onChange={(evento) => establecerComentario(evento.target.value)} /></label>
            <label className="campo"><span>Fotografía de evidencia</span><input type="file" accept="image/jpeg,image/png,image/webp"
              onChange={(evento) => establecerFoto(evento.target.files?.[0] || null)} />
              <small>Opcional, recomendado para marcar Atendido.</small></label>
            {foto && accion !== 'atendido' && <label className="campo"><span>Tipo de evidencia</span><select value={tipo}
              onChange={(evento) => establecerTipo(evento.target.value)}><option>ATENCION</option><option>OTRA</option></select></label>}
            <button className="btn btn-primary" disabled={enviando}>{enviando ? 'Guardando…' : 'Registrar avance'}</button>
          </form></section>}
          <HistorialIncidencia historial={datos?.historial} actualizaciones={datos?.actualizaciones} /></div></div>
    </Estado></>;
}
