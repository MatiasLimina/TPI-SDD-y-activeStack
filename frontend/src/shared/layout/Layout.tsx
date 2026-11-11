import { NavLink, Outlet } from "react-router";

import { useSesion } from "../../features/sesion/ProveedorSesion";
import { ETIQUETA_POR_ROL } from "../../features/sesion/rutas";
import estilos from "./Layout.module.css";

export default function Layout() {
  const { sesion, cerrarSesion } = useSesion();
  if (sesion === null) return null;
  const { rol } = sesion.claims;
  return (
    <>
      <header>
        <p>
          Rol: <strong>{ETIQUETA_POR_ROL[rol]}</strong>
        </p>
        <nav className={estilos.nav}>
          <NavLink to="/agenda">Agenda</NavLink>
          {rol === "recepcionista" && (
            <>
              <NavLink to="/configuracion">Configuración</NavLink>
              <NavLink to="/pacientes">Pacientes</NavLink>
            </>
          )}
          <NavLink to="/bloqueos">Bloqueos</NavLink>
        </nav>
        <button type="button" onClick={cerrarSesion}>
          Cerrar sesión
        </button>
      </header>
      <Outlet />
    </>
  );
}
