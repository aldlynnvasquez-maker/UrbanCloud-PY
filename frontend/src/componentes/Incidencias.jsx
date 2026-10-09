import { Link } from 'react-router';
import { SlidersHorizontal } from 'lucide-react';
import { fecha, filtrarIncidencias } from '../utilidades/formato';
import { Insignia } from './Estado';

export function TablaIncidencias({ incidencias = [], buscar = '', estado = 'Todos', prefijo, sinEnlace = false }) {
  const filas = filtrarIncidencias(incidencias, buscar, estado);
  if (!filas.length) return <div className="estado-panel">No hay incidencias que coincidan con los filtros.</div>;
  return <div className="tarjeta tabla-contenedor"><table>
    <thead><tr><th>Código / incidencia</th><th>Ubicación</th><th>Fecha</th><th>Prioridad</th><th>Estado</th><th></th></tr></thead>
    <tbody>{filas.map((incidencia) => <tr key={incidencia.id}>
      <td><strong>{incidencia.titulo}</strong><small>{incidencia.codigo}</small></td>
      <td>{incidencia.distrito}<small>{incidencia.direccion}</small></td>
      <td>{fecha(incidencia.fecha)}</td><td>{incidencia.prioridad || 'Pendiente'}</td>
      <td><Insignia estado={incidencia.estado} /></td>
      <td>{!sinEnlace && <Link className="enlace-tabla" to={`${prefijo}/${incidencia.id}`}>Ver detalle</Link>}</td>
    </tr>)}</tbody></table></div>;
}

export function FiltrosIncidencias({ buscar, alBuscar, estado, alEstado, estados = [], alFiltrar, extras }) {
  return <form className="filtros" onSubmit={(evento) => { evento.preventDefault(); alFiltrar?.(); }}><label className="campo"><span>Buscar</span>
    <input value={buscar} onChange={(evento) => alBuscar(evento.target.value)} placeholder="Código, título o dirección" /></label>
    <label className="campo"><span>Estado</span><select value={estado} onChange={(evento) => alEstado(evento.target.value)}>
      <option>Todos</option>{estados.map((valor) => <option key={valor}>{valor}</option>)}
    </select></label>{extras}{alFiltrar && <button className="btn btn-secondary">
      <SlidersHorizontal size={16} aria-hidden="true" />Filtrar</button>}</form>;
}

export function DatosIncidencia({ incidencia }) {
  return <section className="tarjeta padding"><div className="cabecera-tarjeta"><div>
    <small className="codigo">{incidencia.codigo}</small><h2>{incidencia.titulo}</h2></div>
    <Insignia estado={incidencia.estado} /></div>
    <p className="descripcion">{incidencia.descripcion}</p>
    <div className="datos-grid">
      {[['Categoría', incidencia.categoria], ['Prioridad', incidencia.prioridad],
        ['Área', incidencia.area], ['Distrito', incidencia.distrito], ['Dirección', incidencia.direccion],
        ['Plazo', fecha(incidencia.fecha_limite)]].map(([titulo, valor]) =>
        <div className="dato" key={titulo}><small>{titulo}</small><strong>{valor || 'Pendiente'}</strong></div>)}
    </div>
  </section>;
}

export function HistorialIncidencia({ historial = [], actualizaciones = [] }) {
  return <section className="tarjeta padding"><h2>Historial</h2>
    {historial.length ? <ol className="linea-tiempo">{historial.map((evento, indice) =>
      <li key={`${evento.fecha}-${indice}`}><strong>{evento.nuevo}</strong>
        <small>{fecha(evento.fecha)}</small>{evento.comentario && <p>{evento.comentario}</p>}</li>)}</ol>
      : <p className="vacio-breve">Sin movimientos registrados.</p>}
    {actualizaciones.length > 0 && <><h3>Avances</h3><ul className="avances">{actualizaciones.map((avance, indice) =>
      <li key={indice}><span>{avance.comentario}</span><small>{fecha(avance.fecha)}</small></li>)}</ul></>}
  </section>;
}
