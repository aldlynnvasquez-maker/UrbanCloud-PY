import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import { Aviso, Encabezado, Estado, TarjetasResumen } from '../componentes/Estado';
import { DatosIncidencia, HistorialIncidencia, TablaIncidencias } from '../componentes/Incidencias';
import { Evidencias } from '../componentes/Evidencias';
import { Mapa } from '../componentes/Mapa';
import { Paginacion } from '../componentes/Paginacion';
import { usarDatos } from '../hooks/usarDatos';
import { servicioDatos } from '../servicios/servicioDatos';

export function PanelSupervisor() {
  const { datos, cargando, error, recargar } = usarDatos(servicioDatos.resumen, []);
  return <><Encabezado seccion="SUPERVISOR" titulo="Resumen operativo"
    accion={<><Link className="btn btn-primary" to="/supervisor/derivados">Ver casos derivados</Link>
      <Link className="btn btn-secondary" to="/supervisor/atendidos">Ver cierres pendientes</Link></>} />
    <Estado cargando={cargando} error={error} alReintentar={recargar}>
      <TarjetasResumen elementos={[
        ['Abiertas', datos?.abiertas, 'Casos activos'], ['Próximas a vencer', datos?.proximas_vencer, 'Dentro de 48 horas'],
        ['Sin responsable', datos?.sin_responsable, 'Asignación pendiente'], ['Cierres validados', datos?.cerradas, 'Finalizados'],
      ]} />
      <div className="distribucion"><section className="tarjeta padding"><h2>Atención prioritaria</h2>
        <p className="descripcion">Consulta las incidencias impedidas, sin responsable y los vencimientos próximos.</p>
        <Link className="btn btn-secondary" to="/supervisor/riesgos">Ver riesgos</Link></section>
        <section className="tarjeta padding"><h2>Capacidad por área</h2>
          {datos?.carga_por_area?.map((area) => <div className="fila-metrica" key={area.id}>
            <span>{area.nombre}</span><strong>{area.tecnicos_activos} técnicos</strong></div>)}</section></div>
    </Estado></>;
}

export function ListaSupervisor({ tipo = 'derivados' }) {
  const [pagina, establecerPagina] = useState(1);
  const { datos, cargando, error, recargar } = usarDatos(() => servicioDatos.casosSupervisor(
    tipo === 'derivados' ? { estado: 'Derivado' }
      : tipo === 'atendidos' ? { estado: 'Atendido' } : { riesgos: 1 }, pagina), [tipo, pagina]);
  const titulo = tipo === 'derivados' ? 'Casos derivados'
    : tipo === 'atendidos' ? 'Pendientes de cierre' : 'Riesgos y SLA';
  return <><Encabezado seccion="SUPERVISOR" titulo={titulo} />
    <Estado cargando={cargando} error={error} alReintentar={recargar}>
      <TablaIncidencias incidencias={datos?.data || []} prefijo="/supervisor/incidencias" />
      <Paginacion datos={datos} alCambiar={establecerPagina} />
    </Estado></>;
}

export function EquipoSupervisor() {
  const { datos, cargando, error, recargar } = usarDatos(servicioDatos.equipo, []);
  return <><Encabezado seccion="SUPERVISOR" titulo="Carga del equipo" />
    <Estado cargando={cargando} error={error} alReintentar={recargar}>
      <div className="tarjeta tabla-contenedor"><table><thead><tr><th>Técnico</th><th>Área</th><th>Tareas activas</th><th>Disponibilidad</th></tr></thead>
        <tbody>{datos?.map((tecnico) => <tr key={tecnico.id}><td><strong>{tecnico.nombre}</strong></td>
          <td>{tecnico.area}</td><td>{tecnico.tareas_activas}</td>
          <td>{tecnico.tareas_activas === 0 ? 'Disponible' : 'En servicio'}</td></tr>)}</tbody></table></div>
    </Estado></>;
}

function AccionesSupervisor({ incidencia, tecnicos, alCompletar }) {
  const [tecnicoId, establecerTecnicoId] = useState('');
  const [comentario, establecerComentario] = useState('');
  const [error, establecerError] = useState('');
  const [enviando, establecerEnviando] = useState(false);
  async function ejecutar(accion, datos) {
    establecerError(''); establecerEnviando(true);
    try {
      if (accion === 'asignar') await servicioDatos.asignar(incidencia.id, datos);
      if (accion === 'cerrar') await servicioDatos.cerrar(incidencia.id, datos);
      if (accion === 'devolver') await servicioDatos.devolver(incidencia.id, datos);
      alCompletar();
    } catch (fallo) { establecerError(fallo.message); }
    finally { establecerEnviando(false); }
  }
  return <div className="columna-lateral"><Aviso mensaje={error} tipo="error" />
    {['Derivado', 'Asignado', 'En atención', 'Impedido'].includes(incidencia.estado) &&
      <section className="tarjeta padding"><h2>{incidencia.estado === 'Derivado' ? 'Asignar técnico' : 'Reasignar técnico'}</h2>
        <form className="formulario" onSubmit={(evento) => { evento.preventDefault(); ejecutar('asignar', { tecnico_id: Number(tecnicoId), comentario }); }}>
          <label className="campo"><span>Técnico compatible</span><select required value={tecnicoId}
            onChange={(evento) => establecerTecnicoId(evento.target.value)}><option value="">Selecciona</option>
            {tecnicos?.map((tecnico) => <option key={tecnico.id} value={tecnico.id}>
              {tecnico.nombre} · {tecnico.asignaciones_activas} tareas</option>)}</select></label>
          <label className="campo"><span>Comentario</span><textarea value={comentario}
            onChange={(evento) => establecerComentario(evento.target.value)} /></label>
          <button className="btn btn-primary" disabled={enviando || !tecnicos?.length}>Confirmar asignación</button>
        </form></section>}
    {incidencia.estado === 'Impedido' && <section className="tarjeta padding"><h2>Devolver al Operador</h2>
      <p className="descripcion">Úsalo cuando el caso requiera nueva clasificación.</p>
      <form className="formulario" onSubmit={(evento) => { evento.preventDefault(); ejecutar('devolver', { motivo: comentario }); }}>
        <label className="campo"><span>Motivo</span><textarea required minLength={10} value={comentario}
          onChange={(evento) => establecerComentario(evento.target.value)} /></label>
        <button className="btn btn-secondary" disabled={enviando}>Devolver</button></form></section>}
    {incidencia.estado === 'Atendido' && <section className="tarjeta padding"><h2>Validar cierre</h2>
      <p className="descripcion">Revisa las notas y evidencias antes de aprobar.</p>
      <form className="formulario" onSubmit={(evento) => { evento.preventDefault(); ejecutar('cerrar', { comentario }); }}>
        <label className="campo"><span>Comentario</span><textarea value={comentario}
          onChange={(evento) => establecerComentario(evento.target.value)} /></label>
        <button className="btn btn-primary" disabled={enviando}>Aprobar cierre</button></form></section>}
  </div>;
}

export function DetalleSupervisor() {
  const { id } = useParams();
  const navegar = useNavigate();
  const { datos, cargando, error, recargar } = usarDatos(() => servicioDatos.detalleSupervisor(id), [id]);
  const [mensaje, establecerMensaje] = useState('');
  return <><Encabezado seccion="SUPERVISOR" titulo="Detalle de incidencia"
    accion={<button className="btn btn-secondary" onClick={() => navegar(-1)}>Volver</button>} />
    <Aviso mensaje={mensaje} tipo="exito" />
    <Estado cargando={cargando} error={error} alReintentar={recargar}>
      <div className="distribucion"><div className="columna-lateral"><DatosIncidencia incidencia={datos?.incidencia} />
        {datos?.incidencia?.latitud && datos.incidencia.longitud && <section className="tarjeta padding"><h2>Ubicación</h2>
          <Mapa latitud={datos.incidencia.latitud} longitud={datos.incidencia.longitud} /></section>}
        <Evidencias evidencias={datos?.incidencia?.evidencias} />
        <HistorialIncidencia historial={datos?.incidencia?.historial} actualizaciones={datos?.incidencia?.actualizaciones} /></div>
        <AccionesSupervisor incidencia={datos?.incidencia} tecnicos={datos?.tecnicos_compatibles}
          alCompletar={() => { establecerMensaje('Decisión registrada.'); recargar(); }} /></div>
    </Estado></>;
}
