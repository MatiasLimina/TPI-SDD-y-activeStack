import estilos from "../features/gestion/Gestion.module.css";
import { useEffect, useRef, useState } from "react";

import { ConfirmarAccion } from "../features/gestion/ConfirmarAccion";
import { EstadoListado } from "../features/gestion/EstadoListado";
import { useDialogo } from "../features/gestion/useDialogo";
import { useListado } from "../features/gestion/useListado";
import {
  FormularioPaciente,
  type DestinoPaciente,
} from "../features/pacientes/FormularioPaciente";
import type { PacienteFicha } from "../features/pacientes/tipos";

const ESPERA_MS = 300;
const POR_PAGINA = 20;
const MAXIMO_BUSQUEDA = 100;

function nombrePaciente(p: PacienteFicha): string {
  return `${p.apellido}, ${p.nombre}`;
}

/** Nombre accesible de las acciones: el documento distingue a los homónimos (D16). */
function referencia(p: PacienteFicha): string {
  return `${nombrePaciente(p)} (${p.documento})`;
}

function rutaDePagina(busqueda: string, pagina: number): string {
  const parametros = new URLSearchParams();
  if (busqueda !== "") parametros.set("q", busqueda);
  // Se pide uno de más: si llega, hay página siguiente (D7)
  parametros.set("limite", String(POR_PAGINA + 1));
  parametros.set("desplazamiento", String((pagina - 1) * POR_PAGINA));
  return `/pacientes?${parametros.toString()}`;
}

/** Pantalla de pacientes de la recepcionista: búsqueda paginada, alta, edición y baja (DD-31). */
export default function PaginaPacientes() {
  const [texto, setTexto] = useState("");
  // Texto y página viven en el estado, no en la URL: nombres y documentos no quedan en el historial (D7)
  const [busqueda, setBusqueda] = useState("");
  const [pagina, setPagina] = useState(1);
  const busquedaActual = useRef(busqueda);
  const listado = useListado<PacienteFicha[]>(rutaDePagina(busqueda, pagina));
  const formulario = useDialogo<DestinoPaciente>();
  const desactivar = useDialogo<PacienteFicha>();
  const [aviso, setAviso] = useState<string | null>(null);

  useEffect(() => {
    const temporizador = setTimeout(() => {
      const nueva = texto.trim();
      if (nueva === busquedaActual.current) return;
      busquedaActual.current = nueva;
      setBusqueda(nueva);
      setPagina(1);
    }, ESPERA_MS);
    return () => clearTimeout(temporizador);
  }, [texto]);

  return (
    <main>
      <h1>Pacientes</h1>
      <label htmlFor="buscar-pacientes">Buscar</label>
      <input
        id="buscar-pacientes"
        type="search"
        maxLength={MAXIMO_BUSQUEDA}
        value={texto}
        onChange={(e) => setTexto(e.target.value)}
      />
      <button
        type="button"
        onClick={() => {
          setAviso(null);
          formulario.abrir("nuevo");
        }}
      >
        Nuevo paciente
      </button>
      {aviso !== null && <p role="status">{aviso}</p>}
      <EstadoListado
        listado={listado}
        textoVacio={
          busqueda === ""
            ? "Todavía no hay pacientes registrados."
            : "No se encontraron pacientes."
        }
      >
        {(pacientes) => (
          <>
            <table className={estilos.tabla}>
              <thead>
                <tr>
                  <th>Nombre</th>
                  <th>Documento</th>
                  <th>Teléfono</th>
                  <th>Email</th>
                  <th>Estado</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {pacientes.slice(0, POR_PAGINA).map((p) => (
                  <tr
                    key={p.id}
                    className={p.activo ? undefined : estilos.inactivo}
                  >
                    <td>{nombrePaciente(p)}</td>
                    <td>{p.documento}</td>
                    <td>{p.telefono}</td>
                    <td>{p.email ?? "Sin email"}</td>
                    <td>{p.activo ? "Activo" : "Inactivo"}</td>
                    <td className={estilos.acciones}>
                      <button
                        type="button"
                        onClick={() => {
                          setAviso(null);
                          formulario.abrir(p);
                        }}
                      >
                        Editar {referencia(p)}
                      </button>
                      {p.activo && (
                        <button
                          type="button"
                          onClick={() => {
                            setAviso(null);
                            desactivar.abrir(p);
                          }}
                        >
                          Desactivar {referencia(p)}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <nav
              aria-label="Paginación de pacientes"
              className={estilos.paginacion}
            >
              <button
                type="button"
                disabled={pagina === 1}
                onClick={() => setPagina(pagina - 1)}
              >
                Anterior
              </button>
              <span>Página {pagina}</span>
              <button
                type="button"
                disabled={pacientes.length <= POR_PAGINA}
                onClick={() => setPagina(pagina + 1)}
              >
                Siguiente
              </button>
            </nav>
          </>
        )}
      </EstadoListado>
      <FormularioPaciente
        key={`formulario-${formulario.clave}`}
        destino={formulario.valor}
        alGuardado={() => {
          formulario.cerrar();
          setAviso("Paciente guardado.");
          listado.recargar();
        }}
        alCerrar={formulario.cerrar}
        alRegistroInexistente={listado.recargar}
      />
      <ConfirmarAccion
        key={`desactivar-${desactivar.clave}`}
        accion={
          desactivar.valor === null
            ? null
            : {
                titulo: "Desactivar paciente",
                textoConfirmar: "Confirmar desactivación",
                metodo: "POST",
                ruta: `/pacientes/${desactivar.valor.id}/desactivar`,
                aviso: "Paciente desactivado.",
                contenido: (
                  <>
                    <p>
                      ¿Desactivar{" "}
                      <strong>{referencia(desactivar.valor)}</strong>?
                    </p>
                    <p>
                      No va a poder recibir turnos nuevos. Sus turnos ya
                      agendados no cambian y se pueden cancelar. No se puede
                      reactivar.
                    </p>
                  </>
                ),
              }
        }
        alHecho={(texto) => {
          desactivar.cerrar();
          setAviso(texto);
          listado.recargar();
        }}
        alCerrar={desactivar.cerrar}
        alFallar={(error) => {
          if (error.codigo === "recurso_inexistente") listado.recargar();
        }}
      />
    </main>
  );
}
