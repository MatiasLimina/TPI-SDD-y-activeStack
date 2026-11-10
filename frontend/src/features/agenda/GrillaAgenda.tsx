import { diaYMes, instanteALocal } from "../../shared/tiempo/zonaConsultorio";
import type { Columna, ItemColumna } from "./grilla";
import type { Nombres } from "./nombres";
import type { VistaAgenda } from "./vistaAgenda";

interface PropsGrilla {
  columnas: Columna[];
  vista: VistaAgenda;
  nombres: Nombres;
}

/** Hora de un extremo: `HH:MM`, o `DD/MM HH:MM` si el elemento abarca más de un día. */
function extremo(instante: string, conFecha: boolean): string {
  const local = instanteALocal(instante);
  return conFecha ? `${diaYMes(local.fecha)} ${local.hora}` : local.hora;
}

function Horario({ inicio, fin }: { inicio: string; fin: string }) {
  // La API entrega el elemento completo: si cruza días, se indican fechas y horas reales
  const cruzaDias = instanteALocal(inicio).fecha !== instanteALocal(fin).fecha;
  return (
    <span>
      <span>{extremo(inicio, cruzaDias)}</span> –{" "}
      <span>{extremo(fin, cruzaDias)}</span>
    </span>
  );
}

function posicion(item: ItemColumna) {
  return {
    gridRow: `${item.segmento.fila + 1} / span ${item.segmento.filas}`,
    gridColumn: item.carril + 1,
  };
}

function Item({
  item,
  vista,
  nombres,
}: {
  item: ItemColumna;
  vista: VistaAgenda;
  nombres: Nombres;
}) {
  // La columna ya dice el profesional (por profesional) o el sillón (por sillón)
  const porProfesional =
    vista.vista === "dia" && vista.columnas === "profesional";
  const porSillon = vista.vista === "dia" && vista.columnas === "sillon";
  if (item.tipo === "bloqueo") {
    const { bloqueo } = item;
    return (
      <li style={posicion(item)} data-tipo="bloqueo">
        <div>
          <strong>Bloqueo</strong>
          <Horario inicio={bloqueo.inicio} fin={bloqueo.fin} />
          {bloqueo.motivo !== null && <span>{bloqueo.motivo}</span>}
          {!porProfesional && (
            <span>{nombres.profesional(bloqueo.profesional_id)}</span>
          )}
        </div>
      </li>
    );
  }
  const { turno } = item;
  return (
    <li style={posicion(item)} data-tipo="turno" data-estado={turno.estado}>
      <button type="button">
        {turno.estado === "cancelado" && <strong>Cancelado</strong>}
        <Horario inicio={turno.inicio} fin={turno.fin} />
        <span>
          {turno.paciente.apellido}, {turno.paciente.nombre}
        </span>
        <span>{nombres.prestacion(turno.prestacion_id)}</span>
        {!porProfesional && (
          <span>{nombres.profesional(turno.profesional_id)}</span>
        )}
        {!porSillon && turno.sillon_id !== null && (
          <span>{nombres.sillon(turno.sillon_id)}</span>
        )}
      </button>
    </li>
  );
}

/** Columnas de la agenda: `<section>` con nombre y elementos en orden cronológico (D17). */
export function GrillaAgenda({ columnas, vista, nombres }: PropsGrilla) {
  return (
    <div>
      {columnas.map((columna) => (
        <section key={columna.clave} aria-label={columna.nombre}>
          <h2>{columna.nombre}</h2>
          <ol
            style={{
              display: "grid",
              gridTemplateRows: "repeat(288, 6px)",
              gridTemplateColumns: `repeat(${Math.max(columna.carriles, 1)}, minmax(90px, 1fr))`,
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
                  vista={vista}
                  nombres={nombres}
                />
              ))}
          </ol>
        </section>
      ))}
    </div>
  );
}
