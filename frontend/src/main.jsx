import React from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router';
import { ProveedorSesion } from './contexto/Sesion';
import { Aplicacion } from './Aplicacion';
import 'leaflet/dist/leaflet.css';
import './styles.css';

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <ProveedorSesion><Aplicacion /></ProveedorSesion>
    </BrowserRouter>
  </React.StrictMode>,
);
