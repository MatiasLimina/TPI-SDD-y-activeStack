import estilos from "../gestion/Gestion.module.css";
import { useState } from "react";

import { Campo } from "../../shared/ui/Campo";
import type { Prestacion } from "../agenda/tipos";
import { ConfirmarAccion } from "../gestion/ConfirmarAccion";
import { DialogoFormulario } from "../gestion/DialogoFormulario";
import { EstadoListado } from "../gestion/EstadoListado";
import { calcularCambios, camposVacios } from "../gestion/formulario";
import { useDialogo } from "../gestion/useDialogo";
import { useEnvioGestion } from "../gestion/useEnvioGestion";
import { useListado } from "../gestion/useListado";
import { useClienteApi } from "../sesion/ProveedorSesion";

const TEXTO_DURACION_ENTERA = "Ingresá minutos enteros.";
const FORMATO_ENTERO = /^-?\d+$/;
const CONFIG_ERRORES = {
  campos: { nombre: "nombre", duracion_min: "duracion" },
  duplicado: { nombre: "Ya existe una prestación con ese nombre." },
  codigos: {
    duracion_invalida: {
      campo: "duracion",
      texto: "La duración debe ser múltiplo de 5, de 5 a 480 minutos.",
    },
  },
} as const;
const CONSECUENCIA =
  "No va a admitir turnos nuevos. Los turnos ya agendados no cambian y se pueden cancelar. No se puede reactivar.";

type Destino = Prestacion | "nuevo";

interface PropsFormulario {
  destino: Destino | null;
  alGuardado: () => void;
  alCerrar: () => void;
  alRegistroInexistente: () => void;
}

function FormularioPrestacion({
  destino,
  alGuardado,
  alCerrar,
  alRegistroInexistente,
}: PropsFormulario) {
  const cliente = useClienteApi();
  const envio = useEnvioGestion(CONFIG_ERRORES, alRegistroInexistente);
  const edicion = destino !== null && destino !== "nuevo" ? destino : null;
  const [nombre, setNombre] = useState(edicion?.nombre ?? "");
  const [duracion, setDuracion] = useState(
    edicion === null ? "" : String(edicion.duracion_min),
  );
  // Una prestación nueva requiere sillón por defecto (DD-09)
  const [requiereSillon, setRequiereSillon] = useState(
    edicion?.requiere_sillon ?? true,
  );

  async function enviar() {
    const vacios = camposVacios({ nombre, duracion }, ["nombre", "duracion"]);
    // La duración es la única regla de formato del cliente: el valor no se redondea (D15)
    const noEntera =
      !vacios.includes("duracion") && !FORMATO_ENTERO.test(duracion.trim());
    if (
      !envio.validarObligatorios(
        vacios,
        noEntera ? { duracion: TEXTO_DURACION_ENTERA } : {},
      )
    )
      return;
    const minutos = Number(duracion.trim());
    if (edicion === null) {
      const exito = await envio.enviar(() =>
        cliente.pedir("POST", "/prestaciones", {
          nombre: nombre.trim(),
          duracion_min: minutos,
          requiere_sillon: requiereSillon,
        }),
      );
      if (exito) alGuardado();
      return;
    }
    const cambios = calcularCambios(
      {
        nombre: edicion.nombre,
        duracion_min: edicion.duracion_min,
        requiere_sillon: edicion.requiere_sillon,
      },
      { nombre, duracion_min: minutos, requiere_sillon: requiereSillon },
      [],
    );
    if (Object.keys(cambios).length === 0) {
      envio.avisarSinCambios();
      return;
    }
    const exito = await envio.enviar(() =>
      cliente.pedir("PATCH", `/prestaciones/${edicion.id}`, cambios),
    );
    if (exito) alGuardado();
  }

  return (
    <DialogoFormulario
      titulo={edicion === null ? "Nueva prestación" : "Editar prestación"}
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
      <Campo etiqueta="Duración (minutos)" error={envio.errores.duracion}>
        {(atributos) => (
          <input
            {...atributos}
            type="text"
            inputMode="numeric"
            value={duracion}
            onChange={(e) => setDuracion(e.target.value)}
          />
        )}
      </Campo>
      <label>
        <input
          type="checkbox"
          checked={requiereSillon}
          onChange={(e) => setRequiereSillon(e.target.checked)}
        />
        Requiere sillón
      </label>
    </DialogoFormulario>
  );
}

/** Sección de prestaciones de la configuración (RN-AU-03, DD-26). */
export default function PantallaPrestaciones() {
  const listado = useListado<Prestacion[]>("/prestaciones");
  const formulario = useDialogo<Destino>();
  const desactivar = useDialogo<Prestacion>();
  const [aviso, setAviso] = useState<string | null>(null);

  return (
    <section>
      <h2>Prestaciones</h2>
      <button
        type="button"
        onClick={() => {
          setAviso(null);
          formulario.abrir("nuevo");
        }}
      >
        Nueva prestación
      </button>
      {aviso !== null && <p role="status">{aviso}</p>}
      <EstadoListado
        listado={listado}
        textoVacio="Todavía no hay prestaciones cargadas."
      >
        {(prestaciones) => (
          <table className={estilos.tabla}>
            <thead>
              <tr>
                <th>Nombre</th>
                <th>Duración</th>
                <th>Requiere sillón</th>
                <th>Estado</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {prestaciones.map((p) => (
                <tr
                  key={p.id}
                  className={p.activa ? undefined : estilos.inactivo}
                >
                  <td>{p.nombre}</td>
                  <td>{p.duracion_min} min</td>
                  <td>{p.requiere_sillon ? "Sí" : "No"}</td>
                  <td>{p.activa ? "Activo" : "Inactivo"}</td>
                  <td className={estilos.acciones}>
                    <button
                      type="button"
                      onClick={() => {
                        setAviso(null);
                        formulario.abrir(p);
                      }}
                    >
                      Editar {p.nombre}
                    </button>
                    {p.activa && (
                      <button
                        type="button"
                        onClick={() => {
                          setAviso(null);
                          desactivar.abrir(p);
                        }}
                      >
                        Desactivar {p.nombre}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </EstadoListado>
      <FormularioPrestacion
        key={`formulario-${formulario.clave}`}
        destino={formulario.valor}
        alGuardado={() => {
          formulario.cerrar();
          setAviso("Prestación guardada.");
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
                titulo: "Desactivar prestación",
                textoConfirmar: "Confirmar desactivación",
                metodo: "POST",
                ruta: `/prestaciones/${desactivar.valor.id}/desactivar`,
                aviso: "Prestación desactivada.",
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
