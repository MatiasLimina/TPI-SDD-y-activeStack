import { Route, Routes } from "react-router";

import { ProveedorSesion } from "./features/sesion/ProveedorSesion";
import PaginaLogin from "./pages/PaginaLogin";

export default function App() {
  return (
    <ProveedorSesion>
      <Routes>
        <Route path="/login" element={<PaginaLogin />} />
      </Routes>
    </ProveedorSesion>
  );
}
