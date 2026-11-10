import {
  diasEntre,
  etiquetaDia,
  instanteALocal,
  lunesDeLaSemana,
  sumarDias,
} from "../../shared/tiempo/zonaConsultorio";
import type { Rol } from "../sesion/claims";
import type {
  Bloqueo,
  Profesional,
  RespuestaAgenda,
  Sillon,
  TurnoAgenda,
} from "./tipos";
import type { VistaAgenda } from "./vistaAgenda";

const MINUTOS_POR_FILA = 5;
const MINUTOS_POR_DIA = 24 * 60;

/** Todo lo que ocupa tiempo en la agenda: un turno o un bloqueo. */
export interface Intervalo {
  inicio: string;
  fin: string;
}

/** Tramo de un elemento dentro de un día local, con minutos recortados a `[0, 1440]` (D4). */
export interface Segmento {
  /** `YYYY-MM-DD` del día local. */
  fecha: string;
  /** Minutos reales dentro del día, para mostrar la hora sin redondear. */
  desdeMin: number;
  hastaMin: number;
  /** Fila de 5 minutos desde 0: inicio redondeado hacia abajo. */
  fila: number;
  /** Cantidad de filas: el fin se redondea hacia arriba. */
  filas: number;
  continuaAntes: boolean;
  continuaDespues: boolean;
}

/** Minutos de un instante respecto de la medianoche de `dia`, en la zona del consultorio. */
function minutosDesde(dia: string, instante: string): number {
  const local = instanteALocal(instante);
  return diasEntre(dia, local.fecha) * MINUTOS_POR_DIA + local.minutosDelDia;
}

/**
 * Un segmento por cada día visible que toca el elemento. Con `[)` (RN-AG-03), un fin exacto a
 * las 00:00 no genera un segmento de 0 minutos en el día siguiente.
 */
export function segmentosPorDia(
  elemento: Intervalo,
  dias: string[],
): Segmento[] {
  const segmentos: Segmento[] = [];
  for (const fecha of dias) {
    const inicio = minutosDesde(fecha, elemento.inicio);
    const fin = minutosDesde(fecha, elemento.fin);
    if (fin <= 0 || inicio >= MINUTOS_POR_DIA) continue;
    const desdeMin = Math.max(inicio, 0);
    const hastaMin = Math.min(fin, MINUTOS_POR_DIA);
    const fila = Math.floor(desdeMin / MINUTOS_POR_FILA);
    segmentos.push({
      fecha,
      desdeMin,
      hastaMin,
      fila,
      filas: Math.ceil(hastaMin / MINUTOS_POR_FILA) - fila,
      continuaAntes: inicio < 0,
      continuaDespues: fin > MINUTOS_POR_DIA,
    });
  }
  return segmentos;
}

export interface Colocable {
  /** Identifica al elemento y desempata: el resultado no depende del orden de entrada. */
  clave: string;
  segmento: Segmento;
}

/**
 * Carriles paralelos dentro de una columna: por orden de inicio, cada segmento toma el primer
 * carril libre, con criterio `[)` (RN-AG-03) sobre las filas ya redondeadas (D4, P6).
 */
export function asignarCarriles<T extends Colocable>(
  items: T[],
): { items: Array<T & { carril: number }>; carriles: number } {
  const ordenados = [...items].sort(
    (a, b) =>
      a.segmento.fila - b.segmento.fila ||
      b.segmento.filas - a.segmento.filas ||
      a.clave.localeCompare(b.clave),
  );
  /** Primera fila libre de cada carril. */
  const libreDesde: number[] = [];
  const colocados = ordenados.map((item) => {
    const { fila, filas } = item.segmento;
    let carril = libreDesde.findIndex((libre) => libre <= fila);
    if (carril === -1) carril = libreDesde.length;
    libreDesde[carril] = fila + filas;
    return { ...item, carril };
  });
  return { items: colocados, carriles: libreDesde.length };
}

export const PROFESIONAL_NO_DISPONIBLE = "Profesional no disponible";
export const SILLON_NO_DISPONIBLE = "Sillón no disponible";
export const SIN_SILLON = "Sin sillón";
const BLOQUEOS = "Bloqueos";

export function nombreProfesional(p: Profesional): string {
  return `${p.apellido}, ${p.nombre}`;
}

export type ItemColumna = Colocable & {
  carril: number;
} & (
    | { tipo: "turno"; turno: TurnoAgenda }
    | { tipo: "bloqueo"; bloqueo: Bloqueo }
  );

export interface Columna {
  /** Id del recurso, o la fecha en la vista semanal. */
  clave: string;
  /** Nombre visible y accesible: `Ficticia, Ana`, `Sillón 1`, `Lunes 09/11`. */
  nombre: string;
  items: ItemColumna[];
  carriles: number;
}

export interface EntradaColumnas {
  vista: VistaAgenda;
  rol: Rol;
  /** Claim `profesional_id` del odontólogo. */
  profesionalPropio: string | null;
  datos: RespuestaAgenda;
  profesionales: Profesional[];
  sillones: Sillon[];
}

type Elemento =
  { tipo: "turno"; turno: TurnoAgenda } | { tipo: "bloqueo"; bloqueo: Bloqueo };
type Visible = Elemento & Colocable;

function diasVisibles(vista: VistaAgenda): string[] {
  if (vista.vista === "dia") return [vista.fecha];
  const lunes = lunesDeLaSemana(vista.fecha);
  return Array.from({ length: 7 }, (_, i) => sumarDias(lunes, i));
}

/** Un segmento por cada día visible que toca cada elemento; los cancelados, solo si se pide. */
function elementosVisibles(
  datos: RespuestaAgenda,
  vista: VistaAgenda,
): Visible[] {
  const dias = diasVisibles(vista);
  const visibles: Visible[] = [];
  for (const turno of datos.turnos) {
    if (turno.estado === "cancelado" && !vista.cancelados) continue;
    for (const segmento of segmentosPorDia(turno, dias))
      visibles.push({
        tipo: "turno",
        turno,
        clave: `${turno.id}|${segmento.fecha}`,
        segmento,
      });
  }
  for (const bloqueo of datos.bloqueos) {
    for (const segmento of segmentosPorDia(bloqueo, dias))
      visibles.push({
        tipo: "bloqueo",
        bloqueo,
        clave: `${bloqueo.id}|${segmento.fecha}`,
        segmento,
      });
  }
  return visibles;
}

/** Elementos que caen en los días visibles, y cancelados que la casilla mantiene ocultos (P1). */
export function contarElementos(
  datos: RespuestaAgenda,
  vista: VistaAgenda,
): { visibles: number; canceladosOcultos: number } {
  const dias = diasVisibles(vista);
  const enLaVista = (e: { inicio: string; fin: string }) =>
    segmentosPorDia(e, dias).length > 0;
  const canceladosOcultos = vista.cancelados
    ? 0
    : datos.turnos.filter((t) => t.estado === "cancelado" && enLaVista(t))
        .length;
  const visibles =
    datos.turnos.filter(
      (t) => (vista.cancelados || t.estado !== "cancelado") && enLaVista(t),
    ).length + datos.bloqueos.filter(enLaVista).length;
  return { visibles, canceladosOcultos };
}

function columna(clave: string, nombre: string, items: Visible[]): Columna {
  const { items: colocados, carriles } = asignarCarriles(items);
  return { clave, nombre, items: colocados, carriles };
}

function idProfesional(e: Elemento): string {
  return e.tipo === "turno" ? e.turno.profesional_id : e.bloqueo.profesional_id;
}

/** Catálogo activo, más lo que tiene elementos visibles, más los ids ausentes del catálogo (P13). */
function columnasPorRecurso<R extends { id: string; activo: boolean }>(
  catalogo: R[],
  visibles: Visible[],
  idDe: (e: Visible) => string | null,
  nombreDe: (r: R) => string,
  nombreAusente: string,
): Columna[] {
  const porId = new Map<string, Visible[]>();
  for (const e of visibles) {
    const id = idDe(e);
    if (id !== null) porId.set(id, [...(porId.get(id) ?? []), e]);
  }
  const columnas: Columna[] = [];
  for (const recurso of catalogo) {
    const items = porId.get(recurso.id) ?? [];
    if (recurso.activo || items.length > 0)
      columnas.push(columna(recurso.id, nombreDe(recurso), items));
    porId.delete(recurso.id);
  }
  for (const [id, items] of porId)
    columnas.push(columna(id, nombreAusente, items));
  return columnas;
}

/**
 * Columnas de la agenda (D1): una por día en la semana; en la vista diaria, una por profesional
 * o por sillón. Para el odontólogo, una sola, la de su profesional (D16).
 */
export function armarColumnas(entrada: EntradaColumnas): Columna[] {
  const { vista, rol, datos, profesionales, sillones } = entrada;
  const visibles = elementosVisibles(datos, vista);

  if (vista.vista === "semana") {
    return diasVisibles(vista).map((fecha) =>
      columna(
        fecha,
        etiquetaDia(fecha),
        visibles.filter((e) => e.segmento.fecha === fecha),
      ),
    );
  }

  if (rol === "odontologo") {
    const propio = entrada.profesionalPropio;
    const perfil = profesionales.find((p) => p.id === propio);
    return [
      columna(
        propio ?? "propio",
        perfil === undefined
          ? PROFESIONAL_NO_DISPONIBLE
          : nombreProfesional(perfil),
        visibles,
      ),
    ];
  }

  if (vista.columnas === "profesional") {
    const todas = columnasPorRecurso(
      profesionales,
      visibles,
      idProfesional,
      nombreProfesional,
      PROFESIONAL_NO_DISPONIBLE,
    );
    return vista.profesionalId === null
      ? todas
      : todas.filter((c) => c.clave === vista.profesionalId);
  }

  const turnos = visibles.filter((e) => e.tipo === "turno");
  const bloqueos = visibles.filter((e) => e.tipo === "bloqueo");
  const sinSillon = turnos.filter(
    (e) => e.tipo === "turno" && e.turno.sillon_id === null,
  );
  const porSillon = columnasPorRecurso(
    sillones,
    turnos,
    (e) => (e.tipo === "turno" ? e.turno.sillon_id : null),
    (s) => s.nombre,
    SILLON_NO_DISPONIBLE,
  );
  const deSillones =
    vista.sillonId === null
      ? porSillon
      : porSillon.filter((c) => c.clave === vista.sillonId);
  return [
    ...deSillones,
    ...(vista.sillonId === null && sinSillon.length > 0
      ? [columna("sin-sillon", SIN_SILLON, sinSillon)]
      : []),
    ...(bloqueos.length > 0 ? [columna("bloqueos", BLOQUEOS, bloqueos)] : []),
  ];
}
