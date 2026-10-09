import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import { Aviso, Encabezado, Estado, TarjetasResumen } from '../componentes/Estado';
import { DatosIncidencia, FiltrosIncidencias, HistorialIncidencia, TablaIncidencias } from '../componentes/Incidencias';
import { Evidencias } from '../componentes/Evidencias';
import { Mapa } from '../componentes/Mapa';
import { Paginacion } from '../componentes/Paginacion';
import { usarDatos } from '../hooks/usarDatos';
import { servicioDatos } from '../servicios/servicioDatos';

export function PanelOperador() {
  const { datos, cargando, error, recargar } = usarDatos(servicioDatos.resumen, []);
  return <><Encabezado seccion="OPERADOR" titulo="Resumen de incidencias"
    descripcion="Prioriza la revisión y confirma las sugerencias del análisis inicial."
    accion={<Link to="/operador/bandeja" className="btn btn-primary">Ir a la bandeja</Link>} />
    <Estado cargando={cargando} error={error} alReintentar={recargar}>
      <TarjetasResumen elementos={[
        ['Abiertas', datos?.abiertas, 'En curso'], ['Por revisar', datos?.pendientes, 'Incluye solicitudes de revisión'],
        ['Prioridad alta', datos?.prioridad_alta, 'Requieren atención'], ['Cerradas', datos?.cerradas, 'Finalizadas'],
      ]} />
      <div className="distribucion"><section className="tarjeta padding"><h2>Qué revisar primero</h2>
        <p className="descripcion">Hay {datos?.pendientes || 0} casos esperando una decisión del Operador.</p>
        <Link className="btn btn-primary" to="/operador/bandeja">Abrir bandeja</Link></section>
        <section className="tarjeta padding"><h2>Por categoría</h2>
          {datos?.por_categoria?.map((categoria) => <div className="fila-metrica" key={categoria.nombre}>
            <span>{categoria.nombre}</span><strong>{categoria.total}</strong></div>)}</section></div>
    </Estado></>;
}

export function ListaOperador({ tipo = 'bandeja' }) {
  const [pagina, establecerPagina] = useState(1);
  const [buscar, establecerBuscar] = useState('');
  const [estado, establecerEstado] = useState('Todos');
  const [area, establecerArea] = useState('');
  const [prioridad, establecerPrioridad] = useState('');
  const [aplicados, establecerAplicados] = useState({});
  const { datos, cargando, error, recargar } = usarDatos(() => tipo === 'todos'
    ? servicioDatos.todasOperador(aplicados, pagina) : servicioDatos.bandejaOperador(pagina),
  [tipo, pagina, JSON.stringify(aplicados)]);
  const { datos: catalogos } = usarDatos(servicioDatos.catalogos, []);
  const titulos = { bandeja: 'Bandeja de revisión', todos: 'Todos los incidentes', alertas: 'Alertas' };
  return <><Encabezado seccion="OPERADOR" titulo={titulos[tipo]} />
    {tipo === 'todos' && <FiltrosIncidencias buscar={buscar} alBuscar={establecerBuscar} estado={estado} alEstado={establecerEstado}
      estados={catalogos?.estados?.map((item) => item.nombre) || []}
      extras={<><label className="campo"><span>Área</span><select value={area} onChange={(evento) => establecerArea(evento.target.value)}>
        <option value="">Todas</option>{catalogos?.areas?.map((item) => <option key={item.id} value={item.id}>{item.nombre}</option>)}</select></label>
        <label className="campo"><span>Prioridad</span><select value={prioridad} onChange={(evento) => establecerPrioridad(evento.target.value)}>
          <option value="">Todas</option>{catalogos?.prioridades?.map((item) => <option key={item.id} value={item.id}>{item.nombre}</option>)}</select></label></>}
      alFiltrar={() => { establecerPagina(1); establecerAplicados({ ...(buscar.trim() && { buscar: buscar.trim() }),
        ...(estado !== 'Todos' && { estado }), ...(area && { area_id: area }), ...(prioridad && { prioridad_id: prioridad }) }); }} />}
    <Estado cargando={cargando} error={error} alReintentar={recargar}>
      <TablaIncidencias incidencias={datos?.data || []} prefijo="/operador/incidencias" />
      <Paginacion datos={datos} alCambiar={establecerPagina} />
    </Estado></>;
}

function FormularioRevision({ incidencia, catalogos, alCompletar }) {
  const [valores, establecerValores] = useState({
    categoria_id: String(catalogos.categorias.find((item) => item.nombre === incidencia.categoria)?.id || ''),
    prioridad_id: String(catalogos.prioridades.find((item) => item.nombre === incidencia.prioridad)?.id || ''),
    area_id: String(catalogos.areas.find((item) => item.nombre === incidencia.area)?.id || ''),
    motivo: '',
  });
  const [error, establecerError] = useState('');
  const [enviando, establecerEnviando] = useState(false);

  async function enviar(evento) {
    evento.preventDefault(); establecerError(''); establecerEnviando(true);
    try { await servicioDatos.revisar(incidencia.id, valores); alCompletar(); }
    catch (fallo) { establecerError(fallo.message); }
    finally { establecerEnviando(false); }
  }

  return <section className="tarjeta padding"><h2>Confirmar o corregir clasificación</h2>
    <Aviso mensaje={error} tipo="error" /><form className="formulario" onSubmit={enviar}>
      {[['categoria_id', 'Categoría', catalogos.categorias], ['prioridad_id', 'Prioridad', catalogos.prioridades],
        ['area_id', 'Área responsable', catalogos.areas]].map(([clave, titulo, opciones]) =>
        <label className="campo" key={clave}><span>{titulo}</span><select required value={valores[clave]}
          onChange={(evento) => establecerValores({ ...valores, [clave]: evento.target.value })}>
          <option value="">Selecciona</option>{opciones.map((opcion) =>
            <option value={opcion.id} key={opcion.id}>{opcion.nombre}</option>)}</select></label>)}
      <label className="campo"><span>Motivo de corrección</span><textarea value={valores.motivo}
        onChange={(evento) => establecerValores({ ...valores, motivo: evento.target.value })}
        placeholder="Obligatorio si cambias una sugerencia" /></label>
      <button className="btn btn-primary" disabled={enviando}>Confirmar y derivar</button>
    </form></section>;
}

function ResolverRevision({ incidencia, alCompletar }) {
  const [decision, establecerDecision] = useState('reabrir');
  const [motivo, establecerMotivo] = useState('');
  const [error, establecerError] = useState('');
  const [enviando, establecerEnviando] = useState(false);
  async function enviar(evento) {
    evento.preventDefault(); establecerError(''); establecerEnviando(true);
    try { await servicioDatos.resolverRevision(incidencia.id, { decision, motivo }); alCompletar(); }
    catch (fallo) { establecerError(fallo.message); }
    finally { establecerEnviando(false); }
  }
  return <section className="tarjeta padding"><h2>Resolver solicitud de revisión</h2>
    <Aviso mensaje={error} tipo="error" /><form className="formulario" onSubmit={enviar}>
      <label className="campo"><span>Decisión</span><select value={decision} onChange={(evento) => establecerDecision(evento.target.value)}>
        <option value="reabrir">Reabrir caso</option><option value="mantener_cierre">Mantener cierre</option></select></label>
      <label className="campo"><span>Respuesta y motivo</span><textarea required minLength={10} value={motivo}
        onChange={(evento) => establecerMotivo(evento.target.value)} /></label>
      <button className="btn btn-primary" disabled={enviando}>Registrar decisión</button></form></section>;
}

export function DetalleOperador() {
  const { id } = useParams();
  const navegar = useNavigate();
  const { datos, cargando, error, recargar } = usarDatos(() => servicioDatos.detalleOperador(id), [id]);
  const { datos: catalogos, cargando: cargandoCatalogos } = usarDatos(servicioDatos.catalogos, []);
  const [mensaje, establecerMensaje] = useState('');
  useEffect(() => { establecerMensaje(''); }, [id]);
  function completar() { establecerMensaje('Decisión registrada.'); recargar(); }
  return <><Encabezado seccion="OPERADOR" titulo="Detalle de incidencia"
    accion={<button className="btn btn-secondary" onClick={() => navegar(-1)}>Volver</button>} />
    <Aviso mensaje={mensaje} tipo="exito" />
    <Estado cargando={cargando || cargandoCatalogos} error={error} alReintentar={recargar}>
      <div className="distribucion"><div className="columna-lateral"><DatosIncidencia incidencia={datos} />
        {datos?.latitud && datos?.longitud && <section className="tarjeta padding"><h2>Ubicación</h2><Mapa latitud={datos.latitud} longitud={datos.longitud} /></section>}
        <Evidencias evidencias={datos?.evidencias} /><HistorialIncidencia historial={datos?.historial} actualizaciones={datos?.actualizaciones} /></div>
        <div className="columna-lateral"><section className="tarjeta padding"><h2>Sugerencia de IA</h2>
          {datos?.analisis_ia?.map((analisis, indice) => <div key={indice} className="datos-grid">
            {[['Categoría', analisis.categoria_sugerida], ['Prioridad', analisis.prioridad_sugerida],
              ['Área', analisis.area_sugerida], ['Confianza', `${Math.round(Number(analisis.confianza) * 100)}%`]]
              .map(([titulo, valor]) => <div className="dato" key={titulo}><small>{titulo}</small><strong>{valor}</strong></div>)}
          </div>)}</section>
          {datos?.estado === 'En revisión' && catalogos && <FormularioRevision incidencia={datos} catalogos={catalogos} alCompletar={completar} />}
          {datos?.estado === 'Revisión solicitada' && <ResolverRevision incidencia={datos} alCompletar={completar} />}
        </div></div>
    </Estado></>;
}
