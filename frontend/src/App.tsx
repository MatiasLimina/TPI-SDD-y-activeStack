import { Route, Routes } from "react-router";

import { ConSesion, SoloSinSesion } from "./features/sesion/guardas";
import { ProveedorSesion } from "./features/sesion/ProveedorSesion";
import PaginaAgenda from "./pages/PaginaAgenda";
import PaginaLogin from "./pages/PaginaLogin";
import Layout from "./shared/layout/Layout";

/** Árbol de rutas: el único lugar donde se agregan pantallas (D14). */
export function RutasApp() {
  return (
    <Routes>
      <Route element={<SoloSinSesion />}>
        <Route path="/login" element={<PaginaLogin />} />
      </Route>
      <Route element={<ConSesion />}>
        <Route element={<Layout />}>
          <Route path="/agenda" element={<PaginaAgenda />} />
        </Route>
      </Route>
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
