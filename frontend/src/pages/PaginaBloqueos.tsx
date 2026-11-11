import estilos from "../features/gestion/Gestion.module.css";
import { useState } from "react";
import { useSearchParams } from "react-router";

import type { Bloqueo } from "../features/agenda/tipos";
import {
  nombreProfesional,
  PROFESIONAL_NO_DISPONIBLE,
} from "../features/agenda/grilla";
import { terminado } from "../features/bloqueos/bloqueos";
import { FormularioBloqueo } from "../features/bloqueos/FormularioBloqueo";
import { ConfirmarAccion } from "../features/gestion/ConfirmarAccion";
import { TEXTO_SIN_PERMISO_LEER } from "../features/gestion/erroresGestion";
import { EstadoListado } from "../features/gestion/EstadoListado";
import { useDialogo } from "../features/gestion/useDialogo";
import { useListado } from "../features/gestion/useListado";
import type { ProfesionalFicha } from "../features/recursos/tipos";
import { useSesion } from "../features/sesion/ProveedorSesion";
import { esUuid } from "../shared/api/esUuid";
import { fechaHoraCompleta } from "../shared/tiempo/zonaConsultorio";
import { Campo } from "../shared/ui/Campo";

function nombreDe(profesionales: ProfesionalFicha[], id: string): string {
  const p = profesionales.find((c) => c.id === id);
  return p === undefined ? PROFESIONAL_NO_DISPONIBLE : nombreProfesional(p);
}

/** Nombre accesible de Borrar: profesional, Desde y Hasta distinguen bloqueos del mismo inicio (D16). */
function nombreDeBorrado(
  b: Bloqueo,
  profesionales: ProfesionalFicha[],
): string {
  return `${nombreDe(profesionales, b.profesional_id)} del ${fechaHoraCompleta(b.inicio)} al ${fechaHoraCompleta(b.fin)}`;
}

/** Bloqueos de agenda para ambos roles: listado, alta y borrado (RN-HB-02, RN-AU-02). */
export default function PaginaBloqueos() {
  const { sesion } = useSesion();
  const esRecepcionista = sesion?.claims.rol === "recepcionista";
  const [parametros, setParametros] = useSearchParams();
  // El odontólogo nunca manda profesional_id: la API devuelve los de su profesional (DD-30 k)
  const solicitado = parametros.get("profesional");
  const filtro = esRecepcionista && esUuid(solicitado) ? solicitado : null;
  const profesionales = useListado<ProfesionalFicha[]>("/profesionales");
  const catalogo = profesionales.datos ?? [];
  const bloqueos = useListado<Bloqueo[]>(
    filtro === null
      ? "/bloqueos"
      : `/bloqueos?${new URLSearchParams({ profesional_id: filtro }).toString()}`,
  );
  const formulario = useDialogo<"nuevo">();
  const borrar = useDialogo<Bloqueo>();
  const [aviso, setAviso] = useState<string | null>(null);
  const [mostrarTerminados, setMostrarTerminados] = useState(false);
  const ahora = new Date();

  function creado(bloqueo: Bloqueo) {
    formulario.cerrar();
    setAviso(
      terminado(bloqueo.fin, new Date()) && !mostrarTerminados
        ? "Bloqueo creado. Está oculto porque ya terminó."
        : "Bloqueo creado.",
    );
    bloqueos.recargar();
  }

  return (
    <main>
      <h1>{esRecepcionista ? "Bloqueos" : "Mis bloqueos"}</h1>
      {profesionales.error !== null && (
        <div role="alert">
          <p>
            {profesionales.error.status === 403
              ? TEXTO_SIN_PERMISO_LEER
              : profesionales.error.mensaje}
          </p>
          <button type="button" onClick={profesionales.reintentar}>
            Reintentar
          </button>
        </div>
      )}
      {esRecepcionista && (
        <Campo etiqueta="Profesional">
          {(atributos) => (
            <select
              {...atributos}
              value={filtro ?? ""}
              onChange={(e) => {
                setAviso(null);
                setParametros(
                  e.target.value === "" ? {} : { profesional: e.target.value },
                );
              }}
            >
              <option value="">Todos</option>
              {catalogo.map((p) => (
                <option key={p.id} value={p.id}>
                  {nombreProfesional(p)}
                  {p.activo ? "" : " (inactivo)"}
                </option>
              ))}
              {filtro !== null && !catalogo.some((p) => p.id === filtro) && (
                <option value={filtro}>{PROFESIONAL_NO_DISPONIBLE}</option>
              )}
            </select>
          )}
        </Campo>
      )}
      <label>
        <input
          type="checkbox"
          checked={mostrarTerminados}
          onChange={(e) => setMostrarTerminados(e.target.checked)}
        />
        Mostrar bloqueos terminados
      </label>
      <button
        type="button"
        onClick={() => {
          setAviso(null);
          formulario.abrir("nuevo");
        }}
      >
        Nuevo bloqueo
      </button>
      {aviso !== null && <p role="status">{aviso}</p>}
      <EstadoListado listado={bloqueos} textoVacio="No hay bloqueos cargados.">
        {(lista) => {
          const visibles = mostrarTerminados
            ? lista
            : lista.filter((b) => !terminado(b.fin, ahora));
          if (visibles.length === 0)
            return <p>No hay bloqueos vigentes ni próximos.</p>;
          return (
            <table className={estilos.tabla}>
              <thead>
                <tr>
                  <th>Profesional</th>
                  <th>Desde</th>
                  <th>Hasta</th>
                  <th>Motivo</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {visibles.map((b) => (
                  <tr key={b.id}>
                    <td>{nombreDe(catalogo, b.profesional_id)}</td>
                    <td>{fechaHoraCompleta(b.inicio)}</td>
                    <td>{fechaHoraCompleta(b.fin)}</td>
                    <td>{b.motivo ?? "Sin motivo"}</td>
                    <td className={estilos.acciones}>
                      <button
                        type="button"
                        onClick={() => {
                          setAviso(null);
                          borrar.abrir(b);
                        }}
                      >
                        Borrar bloqueo de {nombreDeBorrado(b, catalogo)}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          );
        }}
      </EstadoListado>
      <FormularioBloqueo
        key={`formulario-${formulario.clave}`}
        abierto={formulario.valor !== null}
        esRecepcionista={esRecepcionista}
        profesionales={catalogo}
        alGuardado={creado}
        alCerrar={formulario.cerrar}
        alReleerProfesionales={profesionales.recargar}
      />
      <ConfirmarAccion
        key={`borrar-${borrar.clave}`}
        accion={
          borrar.valor === null
            ? null
            : {
                titulo: "Borrar bloqueo",
                textoConfirmar: "Confirmar borrado",
                metodo: "DELETE",
                ruta: `/bloqueos/${borrar.valor.id}`,
                aviso: "Bloqueo borrado.",
                contenido: (
                  <>
                    <p>
                      ¿Borrar el bloqueo de{" "}
                      <strong>{nombreDeBorrado(borrar.valor, catalogo)}</strong>
                      ?
                    </p>
                    <p>El horario vuelve a admitir turnos.</p>
                  </>
                ),
              }
        }
        alHecho={(texto) => {
          borrar.cerrar();
          setAviso(texto);
          bloqueos.recargar();
        }}
        alCerrar={borrar.cerrar}
        alFallar={(error) => {
          if (
            error.codigo === "recurso_inexistente" ||
            error.codigo === "profesional_ajeno"
          )
            bloqueos.recargar();
        }}
      />
    </main>
  );
}
