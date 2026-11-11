import { Fragment, useEffect, useRef, type ReactNode } from "react";

import {
  cruzaDias,
  diaYMes,
  instanteALocal,
} from "../../shared/tiempo/zonaConsultorio";
import estilos from "./GrillaAgenda.module.css";
import type { Columna, ItemColumna } from "./grilla";
import type { Nombres } from "./nombres";
import type { TurnoAgenda } from "./tipos";
import type { VistaAgenda } from "./vistaAgenda";

interface PropsGrilla {
  columnas: Columna[];
  vista: VistaAgenda;
  nombres: Nombres;
  alElegirTurno: (turno: TurnoAgenda) => void;
}

/** Hora de un extremo: `HH:MM`, o `DD/MM HH:MM` si el elemento abarca más de un día. */
function extremo(instante: string, conFecha: boolean): string {
  const local = instanteALocal(instante);
  return conFecha ? `${diaYMes(local.fecha)} ${local.hora}` : local.hora;
}

function Horario({ inicio, fin }: { inicio: string; fin: string }) {
  // La API entrega el elemento completo: si cruza días, se indican fechas y horas reales
  const conFecha = cruzaDias(inicio, fin);
  return (
    <span>
      <span>{extremo(inicio, conFecha)}</span> –{" "}
      <span>{extremo(fin, conFecha)}</span>
    </span>
  );
}

/**
 * Datos de un elemento en una sola línea, separados por ` · `. Un turno de 25 minutos mide 30 px:
 * con una línea que se recorta con puntos suspensivos nunca queda texto cortado a la mitad.
 */
function Linea({ partes }: { partes: ReactNode[] }) {
  return (
    <span className={estilos.linea} data-linea>
      {partes.map((parte, i) => (
        <Fragment key={i}>
          {i > 0 && " · "}
          {parte}
        </Fragment>
      ))}
    </span>
  );
}

const ALTO_FILA_PX = 6;
const FILA_DE_LAS_OCHO = 96;

function mcd(a: number, b: number): number {
  return b === 0 ? a : mcd(b, a % b);
}

/**
 * Divisiones de la rejilla de una columna: el mínimo común múltiplo de los carriles de cada grupo,
 * para que todo grupo reparta su ancho en partes enteras (2 y 3 carriles dan 6 divisiones).
 */
function divisiones(items: ItemColumna[]): number {
  return items.reduce(
    (m, i) => (m / mcd(m, i.carrilesGrupo)) * i.carrilesGrupo,
    1,
  );
}

function posicion(item: ItemColumna, total: number) {
  const ancho = total / item.carrilesGrupo;
  return {
    gridRow: `${item.segmento.fila + 1} / span ${item.segmento.filas}`,
    gridColumn: `${item.carril * ancho + 1} / span ${ancho}`,
  };
}

function Item({
  item,
  total,
  vista,
  nombres,
  alElegirTurno,
}: {
  item: ItemColumna;
  total: number;
  vista: VistaAgenda;
  nombres: Nombres;
  alElegirTurno: (turno: TurnoAgenda) => void;
}) {
  // La columna ya dice el profesional (por profesional) o el sillón (por sillón)
  const porProfesional =
    vista.vista === "dia" && vista.columnas === "profesional";
  const porSillon = vista.vista === "dia" && vista.columnas === "sillon";
  if (item.tipo === "bloqueo") {
    const { bloqueo } = item;
    return (
      <li
        className={estilos.item}
        style={posicion(item, total)}
        data-tipo="bloqueo"
      >
        <div className={estilos.bloqueo}>
          <Linea
            partes={[
              <strong>Bloqueo</strong>,
              <Horario inicio={bloqueo.inicio} fin={bloqueo.fin} />,
              ...(bloqueo.motivo !== null
                ? [<span>{bloqueo.motivo}</span>]
                : []),
              ...(!porProfesional
                ? [<span>{nombres.profesional(bloqueo.profesional_id)}</span>]
                : []),
            ]}
          />
        </div>
      </li>
    );
  }
  const { turno } = item;
  return (
    <li
      className={estilos.item}
      style={posicion(item, total)}
      data-tipo="turno"
      data-estado={turno.estado}
    >
      <button
        type="button"
        className={`${estilos.turno} ${turno.estado === "cancelado" ? estilos.cancelado : ""}`}
        onClick={() => alElegirTurno(turno)}
      >
        <Linea
          partes={[
            ...(turno.estado === "cancelado"
              ? [<strong>Cancelado</strong>]
              : []),
            <Horario inicio={turno.inicio} fin={turno.fin} />,
            <span>
              {turno.paciente.apellido}, {turno.paciente.nombre}
            </span>,
            <span>{nombres.prestacion(turno.prestacion_id)}</span>,
            ...(!porProfesional
              ? [<span>{nombres.profesional(turno.profesional_id)}</span>]
              : []),
            ...(!porSillon && turno.sillon_id !== null
              ? [<span>{nombres.sillon(turno.sillon_id)}</span>]
              : []),
          ]}
        />
      </button>
    </li>
  );
}

const HORAS = Array.from({ length: 24 }, (_, h) => h);

/** Eje de horas decorativo: cada elemento ya dice su hora, por eso se oculta a lectores de pantalla. */
function EjeHoras() {
  return (
    <div className={estilos.eje} data-eje aria-hidden="true">
      <div className={estilos.cabeceraEje} />
      <div className={estilos.horas}>
        {HORAS.map((h) => (
          <span
            key={h}
            className={estilos.hora}
            data-eje-hora
            style={{ gridRow: `${h * 12 + 1} / span 12` }}
          >
            {String(h).padStart(2, "0")}:00
          </span>
        ))}
      </div>
    </div>
  );
}

/** Columnas de la agenda: `<section>` con nombre y elementos en orden cronológico (D17). */
export function GrillaAgenda({
  columnas,
  vista,
  nombres,
  alElegirTurno,
}: PropsGrilla) {
  const contenedor = useRef<HTMLDivElement>(null);
  const hayColumnas = columnas.length > 0;
  // Desplazamiento a las 08:00 (fila 96 de 6 px) cuando la grilla recibe contenido de un período
  // o vista nuevos. Sin columnas el contenedor no tiene alto y el valor se recortaría a 0; por eso
  // depende de `hayColumnas` y no solo del montaje. `Actualizar` conserva las columnas, así que
  // no repite el efecto y mantiene la posición. La geometría real se verifica a mano (tarea 10.2)
  useEffect(() => {
    if (hayColumnas && contenedor.current !== null)
      contenedor.current.scrollTop = FILA_DE_LAS_OCHO * ALTO_FILA_PX;
  }, [hayColumnas, vista.vista, vista.fecha]);
  return (
    <div ref={contenedor} className={estilos.contenedor}>
      {hayColumnas && <EjeHoras />}
      {columnas.map((columna) => (
        <section
          key={columna.clave}
          className={estilos.columna}
          aria-label={columna.nombre}
        >
          <h2>{columna.nombre}</h2>
          <ol
            className={estilos.lista}
            style={{
              gridTemplateColumns: `repeat(${divisiones(columna.items)}, minmax(0, 1fr))`,
            }}
          >
            {[...columna.items]
              .sort(
                (a, b) =>
                  a.segmento.desdeMin - b.segmento.desdeMin ||
                  a.clave.localeCompare(b.clave),
              )
              .map((item) => (
                <Item
                  key={item.clave}
                  item={item}
                  total={divisiones(columna.items)}
                  vista={vista}
                  nombres={nombres}
                  alElegirTurno={alElegirTurno}
                />
              ))}
          </ol>
        </section>
      ))}
    </div>
  );
}
