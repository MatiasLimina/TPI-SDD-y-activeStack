import estilos from "../gestion/Gestion.module.css";
import { useState } from "react";

import { Campo } from "../../shared/ui/Campo";
import { nombreProfesional } from "../agenda/grilla";
import { ConfirmarAccion } from "../gestion/ConfirmarAccion";
import { DialogoFormulario } from "../gestion/DialogoFormulario";
import { EstadoListado } from "../gestion/EstadoListado";
import { calcularCambios, camposVacios } from "../gestion/formulario";
import { useDialogo } from "../gestion/useDialogo";
import { useEnvioGestion } from "../gestion/useEnvioGestion";
import { useListado } from "../gestion/useListado";
import { useClienteApi } from "../sesion/ProveedorSesion";
import type { ProfesionalFicha } from "./tipos";

const CONFIG_ERRORES = {
  campos: { nombre: "nombre", apellido: "apellido", matricula: "matricula" },
  duplicado: { matricula: "Ya existe un profesional con esa matrícula." },
} as const;
const CONSECUENCIA =
  "No va a admitir turnos nuevos. Los turnos ya agendados no cambian y se pueden cancelar. No se puede reactivar.";

type Destino = ProfesionalFicha | "nuevo";

interface PropsFormulario {
  destino: Destino | null;
  alGuardado: () => void;
  alCerrar: () => void;
  alRegistroInexistente: () => void;
}

function FormularioProfesional({
  destino,
  alGuardado,
  alCerrar,
  alRegistroInexistente,
}: PropsFormulario) {
  const cliente = useClienteApi();
  const envio = useEnvioGestion(CONFIG_ERRORES, alRegistroInexistente);
  const edicion = destino !== null && destino !== "nuevo" ? destino : null;
  const [nombre, setNombre] = useState(edicion?.nombre ?? "");
  const [apellido, setApellido] = useState(edicion?.apellido ?? "");
  const [matricula, setMatricula] = useState(edicion?.matricula ?? "");

  async function enviar() {
    const vacios = camposVacios({ nombre, apellido }, ["nombre", "apellido"]);
    if (!envio.validarObligatorios(vacios)) return;
    if (edicion === null) {
      const cuerpo: Record<string, string> = {
        nombre: nombre.trim(),
        apellido: apellido.trim(),
      };
      if (matricula.trim() !== "") cuerpo.matricula = matricula.trim();
      const exito = await envio.enviar(() =>
        cliente.pedir("POST", "/profesionales", cuerpo),
      );
      if (exito) alGuardado();
      return;
    }
    const cambios = calcularCambios(
      {
        nombre: edicion.nombre,
        apellido: edicion.apellido,
        matricula: edicion.matricula,
      },
      { nombre, apellido, matricula },
      ["matricula"],
    );
    if (Object.keys(cambios).length === 0) {
      envio.avisarSinCambios();
      return;
    }
    const exito = await envio.enviar(() =>
      cliente.pedir("PATCH", `/profesionales/${edicion.id}`, cambios),
    );
    if (exito) alGuardado();
  }

  return (
    <DialogoFormulario
      titulo={edicion === null ? "Nuevo profesional" : "Editar profesional"}
      abierto={destino !== null}
      alCerrar={alCerrar}
      alEnviar={() => void enviar()}
      enviando={envio.enviando}
      deshabilitarEnvio={envio.obsoleto}
      errorGeneral={envio.general === null ? null : <p>{envio.general}</p>}
      sinCambios={envio.sinCambios}
    >
      <Campo etiqueta="Nombre" error={envio.errores.nombre}>
        {(atributos) => (
          <input
            {...atributos}
            type="text"
            maxLength={100}
            value={nombre}
            onChange={(e) => setNombre(e.target.value)}
          />
        )}
      </Campo>
      <Campo etiqueta="Apellido" error={envio.errores.apellido}>
        {(atributos) => (
          <input
            {...atributos}
            type="text"
            maxLength={100}
            value={apellido}
            onChange={(e) => setApellido(e.target.value)}
          />
        )}
      </Campo>
      <Campo etiqueta="Matrícula" error={envio.errores.matricula}>
        {(atributos) => (
          <input
            {...atributos}
            type="text"
            maxLength={30}
            value={matricula}
            onChange={(e) => setMatricula(e.target.value)}
          />
        )}
      </Campo>
    </DialogoFormulario>
  );
}

/** Sección de profesionales de la configuración (RN-AU-03, DD-26). */
export default function PantallaProfesionales() {
  const listado = useListado<ProfesionalFicha[]>("/profesionales");
  const formulario = useDialogo<Destino>();
  const desactivar = useDialogo<ProfesionalFicha>();
  const [aviso, setAviso] = useState<string | null>(null);

  return (
    <section>
      <h2>Profesionales</h2>
      <button
        type="button"
        onClick={() => {
          setAviso(null);
          formulario.abrir("nuevo");
        }}
      >
        Nuevo profesional
      </button>
      {aviso !== null && <p role="status">{aviso}</p>}
      <EstadoListado
        listado={listado}
        textoVacio="Todavía no hay profesionales cargados."
      >
        {(profesionales) => (
          <table className={estilos.tabla}>
            <thead>
              <tr>
                <th>Nombre</th>
                <th>Matrícula</th>
                <th>Estado</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {profesionales.map((p) => (
                <tr
                  key={p.id}
                  className={p.activo ? undefined : estilos.inactivo}
                >
                  <td>{nombreProfesional(p)}</td>
                  <td>{p.matricula ?? "Sin matrícula"}</td>
                  <td>{p.activo ? "Activo" : "Inactivo"}</td>
                  <td className={estilos.acciones}>
                    <button
                      type="button"
                      onClick={() => {
                        setAviso(null);
                        formulario.abrir(p);
                      }}
                    >
                      Editar {nombreProfesional(p)}
                    </button>
                    {p.activo && (
                      <button
                        type="button"
                        onClick={() => {
                          setAviso(null);
                          desactivar.abrir(p);
                        }}
                      >
                        Desactivar {nombreProfesional(p)}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </EstadoListado>
      <FormularioProfesional
        key={`formulario-${formulario.clave}`}
        destino={formulario.valor}
        alGuardado={() => {
          formulario.cerrar();
          setAviso("Profesional guardado.");
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
                titulo: "Desactivar profesional",
                textoConfirmar: "Confirmar desactivación",
                metodo: "POST",
                ruta: `/profesionales/${desactivar.valor.id}/desactivar`,
                aviso: "Profesional desactivado.",
                contenido: (
                  <>
                    <p>
                      ¿Desactivar{" "}
                      <strong>{nombreProfesional(desactivar.valor)}</strong>?
                    </p>
                    <p>{CONSECUENCIA}</p>
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
    </section>
  );
}
