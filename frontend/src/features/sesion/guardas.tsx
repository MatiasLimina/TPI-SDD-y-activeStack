import { Navigate, Outlet } from "react-router";

import PaginaSinPermiso from "../../pages/PaginaSinPermiso";
import type { Rol } from "./claims";
import { RUTA_INICIAL_POR_ROL } from "./rutas";
import { useSesion } from "./ProveedorSesion";

/** Rutas protegidas: sin sesión, a `/login` reemplazando la entrada del historial. */
export function ConSesion() {
  const { sesion } = useSesion();
  if (sesion === null) return <Navigate to="/login" replace />;
  return <Outlet />;
}

/** `/login`: con sesión activa lleva al inicio del rol (D6). */
export function SoloSinSesion() {
  const { sesion } = useSesion();
  if (sesion !== null)
    return <Navigate to={RUTA_INICIAL_POR_ROL[sesion.claims.rol]} replace />;
  return <Outlet />;
}

/** `/`: lleva a `/login` sin sesión y al inicio del rol con sesión. */
export function RedireccionInicial() {
  const { sesion } = useSesion();
  const destino =
    sesion === null ? "/login" : RUTA_INICIAL_POR_ROL[sesion.claims.rol];
  return <Navigate to={destino} replace />;
}

/** Ruta restringida: a otro rol autenticado le muestra la falta de permiso, sin cambiar la URL (D5). */
export function ConRol({ roles }: { roles: Rol[] }) {
  const { sesion } = useSesion();
  if (sesion === null || !roles.includes(sesion.claims.rol))
    return <PaginaSinPermiso />;
  return <Outlet />;
}
