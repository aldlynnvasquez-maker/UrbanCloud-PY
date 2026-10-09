export function Paginacion({ datos, alCambiar }) {
  if (!datos || datos.last_page <= 1) return null;
  return <div className="paginacion">
    <button className="btn btn-secondary" disabled={datos.current_page <= 1}
      onClick={() => alCambiar(datos.current_page - 1)}>Anterior</button>
    <span>Página {datos.current_page} de {datos.last_page}</span>
    <button className="btn btn-secondary" disabled={datos.current_page >= datos.last_page}
      onClick={() => alCambiar(datos.current_page + 1)}>Siguiente</button>
  </div>;
}
