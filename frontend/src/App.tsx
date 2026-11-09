import { Route, Routes } from "react-router";

import {
  ConRol,
  ConSesion,
  RedireccionInicial,
  SoloSinSesion,
} from "./features/sesion/guardas";
import { ProveedorSesion } from "./features/sesion/ProveedorSesion";
import PaginaAgenda from "./pages/PaginaAgenda";
import PaginaConfiguracion from "./pages/PaginaConfiguracion";
import PaginaLogin from "./pages/PaginaLogin";
import PaginaNoEncontrada from "./pages/PaginaNoEncontrada";
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
          <Route element={<ConRol roles={["recepcionista"]} />}>
            <Route path="/configuracion" element={<PaginaConfiguracion />} />
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
