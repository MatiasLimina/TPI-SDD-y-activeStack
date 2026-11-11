import { Navigate, Route, Routes } from "react-router";

import {
  ConRol,
  ConSesion,
  RedireccionInicial,
  SoloSinSesion,
} from "./features/sesion/guardas";
import { ProveedorSesion } from "./features/sesion/ProveedorSesion";
import PantallaHorarios from "./features/horarios/PantallaHorarios";
import PantallaPrestaciones from "./features/recursos/PantallaPrestaciones";
import PantallaProfesionales from "./features/recursos/PantallaProfesionales";
import PantallaSillones from "./features/recursos/PantallaSillones";
import PaginaAgenda from "./pages/PaginaAgenda";
import PaginaBloqueos from "./pages/PaginaBloqueos";
import PaginaConfiguracion from "./pages/PaginaConfiguracion";
import PaginaLogin from "./pages/PaginaLogin";
import PaginaNoEncontrada from "./pages/PaginaNoEncontrada";
import PaginaPacientes from "./pages/PaginaPacientes";
import Layout from "./shared/layout/Layout";

/** Árbol de rutas: el único lugar donde se agregan pantallas (D14). */
export function RutasApp() {
  return (
    <Routes>
      <Route path="/" element={<RedireccionInicial />} />
      <Route element={<SoloSinSesion />}>
        <Route path="/login" element={<PaginaLogin />} />
      </Route>
      <Route element={<ConSesion />}>
        <Route element={<Layout />}>
          <Route path="/agenda" element={<PaginaAgenda />} />
          <Route path="/bloqueos" element={<PaginaBloqueos />} />
          <Route element={<ConRol roles={["recepcionista"]} />}>
            <Route path="/pacientes" element={<PaginaPacientes />} />
            <Route path="/configuracion" element={<PaginaConfiguracion />}>
              <Route index element={<Navigate to="profesionales" replace />} />
              <Route path="profesionales" element={<PantallaProfesionales />} />
              <Route path="sillones" element={<PantallaSillones />} />
              <Route path="prestaciones" element={<PantallaPrestaciones />} />
              <Route path="horarios" element={<PantallaHorarios />} />
            </Route>
          </Route>
        </Route>
      </Route>
      <Route path="*" element={<PaginaNoEncontrada />} />
    </Routes>
  );
}

export default function App() {
  return (
    <ProveedorSesion>
      <RutasApp />
    </ProveedorSesion>
  );
}
