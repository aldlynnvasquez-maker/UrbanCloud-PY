export function fecha(valor) {
  if (!valor) return 'Sin fecha';
  return new Intl.DateTimeFormat('es-PE', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(valor));
}

export function filtrarIncidencias(incidencias, buscar = '', estado = 'Todos') {
  const texto = buscar.trim().toLocaleLowerCase('es');
  return incidencias.filter((incidencia) =>
    (estado === 'Todos' || incidencia.estado === estado)
    && (!texto || `${incidencia.codigo} ${incidencia.titulo} ${incidencia.direccion}`
      .toLocaleLowerCase('es').includes(texto)));
}
