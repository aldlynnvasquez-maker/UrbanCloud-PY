import { MapPin } from 'lucide-react';

export function IconoMarca({ compacto = false }) {
  return (
    <span className={`marca-icono${compacto ? ' marca-icono-compacto' : ''}`} aria-hidden="true">
      <MapPin size={compacto ? 16 : 23} strokeWidth={2.2} />
    </span>
  );
}

export function Marca() {
  return (
    <>
      <IconoMarca />
      <span className="marca-texto">
        <strong>UrbanCloud <b>AI</b></strong>
        <small>Ciudad mejor conectada</small>
      </span>
    </>
  );
}
