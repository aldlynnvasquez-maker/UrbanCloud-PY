import { beforeEach, expect, it, vi } from 'vitest';
import { render } from '@testing-library/react';
import { Mapa } from '../componentes/Mapa';

const leaflet = vi.hoisted(() => ({ map: vi.fn(), tileLayer: vi.fn(), circleMarker: vi.fn() }));

vi.mock('leaflet', () => ({ default: leaflet }));

beforeEach(() => {
  const instancia = { on: vi.fn(), remove: vi.fn() };
  instancia.setView = vi.fn().mockReturnValue(instancia);
  leaflet.map.mockReset().mockReturnValue(instancia);
  leaflet.tileLayer.mockReset().mockReturnValue({ addTo: vi.fn() });
  leaflet.circleMarker.mockReset().mockReturnValue({ addTo: vi.fn().mockReturnThis(), setLatLng: vi.fn() });
});

it('centra el mapa y coloca el pin cuando llega la ubicación del dispositivo', () => {
  const { rerender } = render(<Mapa latitud={null} longitud={null} />);
  const mapa = leaflet.map.mock.results[0].value;

  rerender(<Mapa latitud={null} longitud={null} posicionSolicitada={[-9.08, -78.57]} />);

  expect(mapa.setView).toHaveBeenLastCalledWith([-9.08, -78.57], 16);
  expect(leaflet.circleMarker).toHaveBeenCalledWith([-9.08, -78.57], expect.objectContaining({ radius: 10 }));
});

it('envía el origen al proveedor de mapas y muestra la atribución enlazada', () => {
  render(<Mapa latitud={null} longitud={null} />);
  expect(leaflet.tileLayer).toHaveBeenCalledWith(
    'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
    expect.objectContaining({
      referrerPolicy: 'strict-origin-when-cross-origin',
      attribution: expect.stringContaining('https://www.openstreetmap.org/copyright'),
    }),
  );
});
