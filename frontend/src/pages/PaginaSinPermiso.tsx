import { Link } from "react-router";

import { useSesion } from "../features/sesion/ProveedorSesion";
import { RUTA_INICIAL_POR_ROL } from "../features/sesion/rutas";

export default function PaginaSinPermiso() {
  const { sesion } = useSesion();
  const inicio =
    sesion === null ? "/" : RUTA_INICIAL_POR_ROL[sesion.claims.rol];
  return (
    <main>
      <h1>Sin permiso</h1>
      <p>No tenés permiso para ver esta pantalla.</p>
      <Link to={inicio}>Volver al inicio</Link>
    </main>
  );
}
