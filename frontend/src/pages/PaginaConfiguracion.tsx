import { NavLink, Outlet } from "react-router";

import estilos from "./PaginaConfiguracion.module.css";

const SECCIONES = [
  ["profesionales", "Profesionales"],
  ["sillones", "Sillones"],
  ["prestaciones", "Prestaciones"],
  ["horarios", "Horarios"],
] as const;

/** Contenedor de la configuración: título, navegación interna y la sección elegida (D2). */
export default function PaginaConfiguracion() {
  return (
    <main>
      <h1>Configuración</h1>
      <nav
        aria-label="Secciones de la configuración"
        className={estilos.navegacion}
      >
        {SECCIONES.map(([ruta, texto]) => (
          <NavLink key={ruta} to={`/configuracion/${ruta}`}>
            {texto}
          </NavLink>
        ))}
      </nav>
      <Outlet />
    </main>
  );
}
