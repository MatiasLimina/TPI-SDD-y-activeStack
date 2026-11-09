import { Link, Outlet } from "react-router";

import { useSesion } from "../../features/sesion/ProveedorSesion";
import { ETIQUETA_POR_ROL } from "../../features/sesion/rutas";

export default function Layout() {
  const { sesion } = useSesion();
  if (sesion === null) return null;
  const { rol } = sesion.claims;
  return (
    <>
      <header>
        <p>
          Rol: <strong>{ETIQUETA_POR_ROL[rol]}</strong>
        </p>
        <nav>
          <Link to="/agenda">Agenda</Link>
          {rol === "recepcionista" && (
            <Link to="/configuracion">Configuración</Link>
          )}
        </nav>
      </header>
      <Outlet />
    </>
  );
}
