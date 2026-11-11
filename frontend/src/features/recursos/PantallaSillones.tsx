import estilos from "../gestion/Gestion.module.css";
import { useState, type ChangeEvent } from "react";

import { Campo } from "../../shared/ui/Campo";
import type { Sillon } from "../agenda/tipos";
import { ConfirmarAccion } from "../gestion/ConfirmarAccion";
import { DialogoFormulario } from "../gestion/DialogoFormulario";
import { EstadoListado } from "../gestion/EstadoListado";
import { calcularCambios, camposVacios } from "../gestion/formulario";
import { useClienteApi } from "../sesion/ProveedorSesion";
import { useDialogo } from "../gestion/useDialogo";
import { useEnvioGestion } from "../gestion/useEnvioGestion";
import { useListado } from "../gestion/useListado";

const MAXIMO_NOMBRE = 50;
const CONFIG_ERRORES = {
  campos: { nombre: "nombre" },
  duplicado: { nombre: "Ya existe un sillón con ese nombre." },
} as const;
const CONSECUENCIA =
  "No va a admitir turnos nuevos. Los turnos ya agendados no cambian y se pueden cancelar. No se puede reactivar.";

type Destino = Sillon | "nuevo";

interface PropsFormulario {
  destino: Destino | null;
  alGuardado: () => void;
  alCerrar: () => void;
  alRegistroInexistente: () => void;
}

function FormularioSillon({
  destino,
  alGuardado,
  alCerrar,
  alRegistroInexistente,
}: PropsFormulario) {
  const cliente = useClienteApi();
  const envio = useEnvioGestion(CONFIG_ERRORES, alRegistroInexistente);
  const edicion = destino !== null && destino !== "nuevo" ? destino : null;
  const [nombre, setNombre] = useState(edicion?.nombre ?? "");

  async function enviar() {
    if (!envio.validarObligatorios(camposVacios({ nombre }, ["nombre"])))
      return;
    if (edicion === null) {
      const exito = await envio.enviar(() =>
        cliente.pedir("POST", "/sillones", { nombre: nombre.trim() }),
      );
      if (exito) alGuardado();
      return;
    }
    const cambios = calcularCambios({ nombre: edicion.nombre }, { nombre }, []);
    if (Object.keys(cambios).length === 0) {
      envio.avisarSinCambios();
      return;
    }
    const exito = await envio.enviar(() =>
      cliente.pedir("PATCH", `/sillones/${edicion.id}`, cambios),
    );
    if (exito) alGuardado();
  }

  return (
    <DialogoFormulario
      titulo={edicion === null ? "Nuevo sillón" : "Editar sillón"}
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
            maxLength={MAXIMO_NOMBRE}
            value={nombre}
            onChange={(e: ChangeEvent<HTMLInputElement>) =>
              setNombre(e.target.value)
            }
          />
        )}
      </Campo>
    </DialogoFormulario>
  );
}

/** Sección de sillones de la configuración (RN-AU-03, DD-26). */
export default function PantallaSillones() {
  const listado = useListado<Sillon[]>("/sillones");
  const formulario = useDialogo<Destino>();
  const desactivar = useDialogo<Sillon>();
  const [aviso, setAviso] = useState<string | null>(null);

  function guardado() {
    formulario.cerrar();
    setAviso("Sillón guardado.");
    listado.recargar();
  }

  return (
    <section>
      <h2>Sillones</h2>
      <button
        type="button"
        onClick={() => {
          setAviso(null);
          formulario.abrir("nuevo");
        }}
      >
        Nuevo sillón
      </button>
      {aviso !== null && <p role="status">{aviso}</p>}
      <EstadoListado
        listado={listado}
        textoVacio="Todavía no hay sillones cargados."
      >
        {(sillones) => (
          <table className={estilos.tabla}>
            <thead>
              <tr>
                <th>Nombre</th>
                <th>Estado</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {sillones.map((s) => (
                <tr
                  key={s.id}
                  className={s.activo ? undefined : estilos.inactivo}
                >
                  <td>{s.nombre}</td>
                  <td>{s.activo ? "Activo" : "Inactivo"}</td>
                  <td className={estilos.acciones}>
                    <button
                      type="button"
                      onClick={() => {
                        setAviso(null);
                        formulario.abrir(s);
                      }}
                    >
                      Editar {s.nombre}
                    </button>
                    {s.activo && (
                      <button
                        type="button"
                        onClick={() => {
                          setAviso(null);
                          desactivar.abrir(s);
                        }}
                      >
                        Desactivar {s.nombre}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </EstadoListado>
      <FormularioSillon
        key={`formulario-${formulario.clave}`}
        destino={formulario.valor}
        alGuardado={guardado}
        alCerrar={formulario.cerrar}
        alRegistroInexistente={listado.recargar}
      />
      <ConfirmarAccion
        key={`desactivar-${desactivar.clave}`}
        accion={
          desactivar.valor === null
            ? null
            : {
                titulo: "Desactivar sillón",
                textoConfirmar: "Confirmar desactivación",
                metodo: "POST",
                ruta: `/sillones/${desactivar.valor.id}/desactivar`,
                aviso: "Sillón desactivado.",
                contenido: (
                  <>
                    <p>
                      ¿Desactivar <strong>{desactivar.valor.nombre}</strong>?
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
