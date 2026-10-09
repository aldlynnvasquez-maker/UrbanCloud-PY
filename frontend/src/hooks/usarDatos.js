import { useCallback, useEffect, useState } from 'react';

export function usarDatos(cargar, dependencias = []) {
  const [datos, establecerDatos] = useState(null);
  const [cargando, establecerCargando] = useState(true);
  const [error, establecerError] = useState('');

  const recargar = useCallback(async () => {
    establecerCargando(true);
    establecerError('');
    try {
      establecerDatos(await cargar());
    } catch (fallo) {
      establecerError(fallo.message);
    } finally {
      establecerCargando(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, dependencias);

  useEffect(() => { recargar(); }, [recargar]);
  return { datos, cargando, error, recargar };
}
