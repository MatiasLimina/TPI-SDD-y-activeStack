import estilos from "../gestion/Gestion.module.css";
import { useId, useState } from "react";
import { useSearchParams } from "react-router";

import { esUuid } from "../../shared/api/esUuid";
import { Campo } from "../../shared/ui/Campo";
import { nombreProfesional } from "../agenda/grilla";
import { ConfirmarAccion } from "../gestion/ConfirmarAccion";
import { DialogoFormulario } from "../gestion/DialogoFormulario";
import { calcularCambios, camposVacios } from "../gestion/formulario";
import { useDialogo } from "../gestion/useDialogo";
import { useEnvioGestion } from "../gestion/useEnvioGestion";
import { useListado } from "../gestion/useListado";
import { TEXTO_SIN_PERMISO_LEER } from "../gestion/erroresGestion";
import type { ProfesionalFicha } from "../recursos/tipos";
import { useClienteApi } from "../sesion/ProveedorSesion";
import {
  agruparPorDia,
  horaCorta,
  NOMBRES_DIAS,
  textoFranja,
  type Franja,
} from "./franjas";

const TEXTO_SIN_PROFESIONAL =
  "Elegí un profesional para ver o cargar su horario.";
const AYUDA_FRANJA =
  "Un turno debe entrar completo en una franja: dos franjas contiguas no se suman.";
const CONFIG_ERRORES = {
  campos: {
    dia_semana: "dia",
    hora_inicio: "desde",
    hora_fin: "hasta",
  },
  codigos: {
    franja_invalida: {
      texto:
        "La franja debe terminar después de empezar, el mismo día, y en horas múltiplo de 5 minutos.",
    },
    franja_superpuesta: { texto: "Se superpone con otra franja de ese día." },
  },
} as const;

type Destino = Franja | "nueva";

interface PropsFormulario {
  profesionalId: string;
  destino: Destino | null;
  alGuardado: () => void;
  alCerrar: () => void;
  alRegistroInexistente: () => void;
}

function FormularioFranja({
  profesionalId,
  destino,
  alGuardado,
  alCerrar,
  alRegistroInexistente,
}: PropsFormulario) {
  const cliente = useClienteApi();
  const envio = useEnvioGestion(CONFIG_ERRORES, alRegistroInexistente);
  const edicion = destino !== null && destino !== "nueva" ? destino : null;
  const [dia, setDia] = useState(
    edicion === null ? "" : String(edicion.dia_semana),
  );
  const [desde, setDesde] = useState(
    edicion === null ? "" : horaCorta(edicion.hora_inicio),
  );
  const [hasta, setHasta] = useState(
    edicion === null ? "" : horaCorta(edicion.hora_fin),
  );

  async function enviar() {
    const vacios = camposVacios({ dia, desde, hasta }, [
      "dia",
      "desde",
      "hasta",
    ]);
    if (!envio.validarObligatorios(vacios)) return;
    const ruta = `/profesionales/${profesionalId}/horarios`;
    if (edicion === null) {
      const exito = await envio.enviar(() =>
        cliente.pedir("POST", ruta, {
          dia_semana: Number(dia),
          hora_inicio: desde,
          hora_fin: hasta,
        }),
      );
      if (exito) alGuardado();
      return;
    }
    const cambios = calcularCambios(
      {
        dia_semana: edicion.dia_semana,
        hora_inicio: edicion.hora_inicio,
        hora_fin: edicion.hora_fin,
      },
      { dia_semana: Number(dia), hora_inicio: desde, hora_fin: hasta },
      [],
    );
    if (Object.keys(cambios).length === 0) {
      envio.avisarSinCambios();
      return;
    }
    const exito = await envio.enviar(() =>
      cliente.pedir("PATCH", `${ruta}/${edicion.id}`, cambios),
    );
    if (exito) alGuardado();
  }

  return (
    <DialogoFormulario
      titulo={edicion === null ? "Nueva franja" : "Editar franja"}
      abierto={destino !== null}
      alCerrar={alCerrar}
      alEnviar={() => void enviar()}
      enviando={envio.enviando}
      deshabilitarEnvio={envio.obsoleto}
      errorGeneral={envio.general === null ? null : <p>{envio.general}</p>}
      sinCambios={envio.sinCambios}
    >
      <p>{AYUDA_FRANJA}</p>
      <Campo etiqueta="Día" error={envio.errores.dia}>
        {(atributos) => (
          <select
            {...atributos}
            value={dia}
            onChange={(e) => setDia(e.target.value)}
          >
            <option value="">Sin elegir</option>
            {NOMBRES_DIAS.map((nombre, valor) => (
              <option key={nombre} value={String(valor)}>
                {nombre}
              </option>
            ))}
          </select>
        )}
      </Campo>
      <Campo etiqueta="Desde" error={envio.errores.desde}>
        {(atributos) => (
          <input
            {...atributos}
            type="time"
            step={300}
            value={desde}
            onChange={(e) => setDesde(e.target.value)}
          />
        )}
      </Campo>
      <Campo etiqueta="Hasta" error={envio.errores.hasta}>
        {(atributos) => (
          <input
            {...atributos}
            type="time"
            step={300}
            value={hasta}
            onChange={(e) => setHasta(e.target.value)}
          />
        )}
      </Campo>
    </DialogoFormulario>
  );
}

/** Sección de horarios de atención de la configuración (RN-HB-01, DD-27). */
export default function PantallaHorarios() {
  const idSinProfesional = useId();
  const [parametros, setParametros] = useSearchParams();
  const catalogo = useListado<ProfesionalFicha[]>("/profesionales");
  const solicitado = parametros.get("profesional");
  // Un id mal formado o ausente del catálogo se ignora (D9)
  const profesional =
    solicitado !== null &&
    esUuid(solicitado) &&
    (catalogo.datos?.some((p) => p.id === solicitado) ?? false)
      ? solicitado
      : null;
  const franjas = useListado<Franja[]>(
    profesional === null ? null : `/profesionales/${profesional}/horarios`,
  );
  const formulario = useDialogo<Destino>();
  const borrar = useDialogo<Franja>();
  const [aviso, setAviso] = useState<string | null>(null);

  function elegir(id: string) {
    setAviso(null);
    setParametros(id === "" ? {} : { profesional: id });
  }

  return (
    <section>
      <h2>Horarios de atención</h2>
      {catalogo.error !== null ? (
        <div role="alert">
          <p>
            {catalogo.error.status === 403
              ? TEXTO_SIN_PERMISO_LEER
              : catalogo.error.mensaje}
          </p>
          <button type="button" onClick={catalogo.reintentar}>
            Reintentar
          </button>
        </div>
      ) : catalogo.datos === null ? (
        <p role="status">Cargando…</p>
      ) : (
        <Campo etiqueta="Profesional">
          {(atributos) => (
            <select
              {...atributos}
              value={profesional ?? ""}
              onChange={(e) => elegir(e.target.value)}
            >
              <option value="">Sin elegir</option>
              {(catalogo.datos ?? []).map((p) => (
                <option key={p.id} value={p.id}>
                  {nombreProfesional(p)}
                  {p.activo ? "" : " (inactivo)"}
                </option>
              ))}
            </select>
          )}
        </Campo>
      )}
      <button
        type="button"
        disabled={profesional === null}
        aria-describedby={profesional === null ? idSinProfesional : undefined}
        onClick={() => {
          setAviso(null);
          formulario.abrir("nueva");
        }}
      >
        Nueva franja
      </button>
      {profesional === null && (
        <p id={idSinProfesional}>{TEXTO_SIN_PROFESIONAL}</p>
      )}
      {aviso !== null && <p role="status">{aviso}</p>}
      {profesional !== null && (
        <ListadoDeFranjas
          listado={franjas}
          alEditar={(f) => {
            setAviso(null);
            formulario.abrir(f);
          }}
          alBorrar={(f) => {
            setAviso(null);
            borrar.abrir(f);
          }}
        />
      )}
      {profesional !== null && (
        <>
          <FormularioFranja
            key={`formulario-${formulario.clave}`}
            profesionalId={profesional}
            destino={formulario.valor}
            alGuardado={() => {
              formulario.cerrar();
              setAviso("Franja guardada.");
              franjas.recargar();
            }}
            alCerrar={formulario.cerrar}
            alRegistroInexistente={franjas.recargar}
          />
          <ConfirmarAccion
            key={`borrar-${borrar.clave}`}
            accion={
              borrar.valor === null
                ? null
                : {
                    titulo: "Borrar franja",
                    textoConfirmar: "Confirmar borrado",
                    metodo: "DELETE",
                    ruta: `/profesionales/${profesional}/horarios/${borrar.valor.id}`,
                    aviso: "Franja borrada.",
                    contenido: (
                      <>
                        <p>
                          ¿Borrar la franja del{" "}
                          {NOMBRES_DIAS[borrar.valor.dia_semana]?.toLowerCase()}{" "}
                          de <strong>{textoFranja(borrar.valor)}</strong>?
                        </p>
                        <p>Los turnos ya agendados no cambian.</p>
                      </>
                    ),
                  }
            }
            alHecho={(texto) => {
              borrar.cerrar();
              setAviso(texto);
              franjas.recargar();
            }}
            alCerrar={borrar.cerrar}
            alFallar={(error) => {
              if (error.codigo === "recurso_inexistente") franjas.recargar();
            }}
          />
        </>
      )}
    </section>
  );
}

interface PropsListado {
  listado: ReturnType<typeof useListado<Franja[]>>;
  alEditar: (franja: Franja) => void;
  alBorrar: (franja: Franja) => void;
}

function ListadoDeFranjas({ listado, alEditar, alBorrar }: PropsListado) {
  const { datos, error, cargando, reintentar } = listado;
  if (error !== null)
    return (
      <div role="alert">
        <p>{error.status === 403 ? TEXTO_SIN_PERMISO_LEER : error.mensaje}</p>
        <button type="button" onClick={reintentar}>
          Reintentar
        </button>
      </div>
    );
  if (cargando || datos === null) return <p role="status">Cargando…</p>;
  return (
    <div className={estilos.dias}>
      {datos.length === 0 && (
        <p>Este profesional no tiene horario cargado: no admite turnos.</p>
      )}
      {agruparPorDia(datos).map((dia) => (
        <DiaDeAtencion
          key={dia.dia}
          nombre={dia.nombre}
          franjas={dia.franjas}
          alEditar={alEditar}
          alBorrar={alBorrar}
        />
      ))}
    </div>
  );
}

interface PropsDia {
  nombre: string;
  franjas: Franja[];
  alEditar: (franja: Franja) => void;
  alBorrar: (franja: Franja) => void;
}

function DiaDeAtencion({ nombre, franjas, alEditar, alBorrar }: PropsDia) {
  const idTitulo = useId();
  const dia = nombre.toLowerCase();
  return (
    <section aria-labelledby={idTitulo} className={estilos.dia}>
      <h3 id={idTitulo}>{nombre}</h3>
      {franjas.length === 0 ? (
        <p>Sin atención</p>
      ) : (
        <ul>
          {franjas.map((f) => (
            <li key={f.id}>
              <span>{textoFranja(f)}</span>
              <button type="button" onClick={() => alEditar(f)}>
                Editar {dia} {textoFranja(f)}
              </button>
              <button type="button" onClick={() => alBorrar(f)}>
                Borrar {dia} {textoFranja(f)}
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
