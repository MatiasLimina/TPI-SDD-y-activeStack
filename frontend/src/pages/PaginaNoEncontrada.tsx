import { Link } from "react-router";

export default function PaginaNoEncontrada() {
  return (
    <main>
      <h1>Página no encontrada</h1>
      <p>La dirección que pediste no existe.</p>
      <Link to="/">Ir al inicio</Link>
    </main>
  );
}
