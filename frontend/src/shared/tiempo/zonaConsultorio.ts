/** Zona del consultorio: constante del frontend, el sistema es monotenant (SU-07, RN-CU-04). */
export const ZONA_CONSULTORIO = "America/Argentina/Buenos_Aires";

export interface InstanteLocal {
  /** `YYYY-MM-DD` en la zona del consultorio. */
  fecha: string;
  /** `HH:MM` de 24 horas, de `00:00` a `23:59`. */
  hora: string;
  minutosDelDia: number;
}

const formateadorLocal = new Intl.DateTimeFormat("en-CA", {
  timeZone: ZONA_CONSULTORIO,
  hourCycle: "h23",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
});

function partes(instante: Date): Record<string, string> {
  const resultado: Record<string, string> = {};
  for (const parte of formateadorLocal.formatToParts(instante))
    resultado[parte.type] = parte.value;
  return resultado;
}

/** Fecha y hora de un instante en la zona del consultorio, nunca en la del navegador (D14). */
export function instanteALocal(instante: string | Date): InstanteLocal {
  const { year, month, day, hour, minute } = partes(new Date(instante));
  return {
    fecha: `${year!.padStart(4, "0")}-${month}-${day}`,
    hora: `${hour}:${minute}`,
    minutosDelDia: Number(hour) * 60 + Number(minute),
  };
}

/** Día actual del consultorio a partir del reloj, no del navegador (RN-CU-04). */
export function hoyLocal(ahora: Date = new Date()): string {
  return instanteALocal(ahora).fecha;
}

// Las fechas son texto `YYYY-MM-DD` y el calendario se resuelve con `Date.UTC` y getters UTC,
// independientes de la zona de la máquina (D14)
// Solo se usa con fechas ya validadas (años de 1000 a 9998): `Date.UTC` toma los años 0 a 99 como 19xx
function aMsUtc(fecha: string): number {
  const [anio, mes, dia] = fecha.split("-").map(Number) as [
    number,
    number,
    number,
  ];
  return Date.UTC(anio, mes - 1, dia);
}

function deMsUtc(ms: number): string {
  const f = new Date(ms);
  const anio = String(f.getUTCFullYear()).padStart(4, "0");
  const mes = String(f.getUTCMonth() + 1).padStart(2, "0");
  const dia = String(f.getUTCDate()).padStart(2, "0");
  return `${anio}-${mes}-${dia}`;
}

const MS_POR_DIA = 24 * 60 * 60 * 1000;

export function sumarDias(fecha: string, dias: number): string {
  return deMsUtc(aMsUtc(fecha) + dias * MS_POR_DIA);
}

/** Lunes de la semana de la fecha: la semana va de lunes a domingo (D2). */
export function lunesDeLaSemana(fecha: string): string {
  const diaDeLaSemana = new Date(aMsUtc(fecha)).getUTCDay(); // 0 = domingo
  return sumarDias(fecha, -((diaDeLaSemana + 6) % 7));
}

// Tabla propia: la salida de `es-AR` depende de la versión de ICU (D14)
const NOMBRES_DIAS = [
  "Domingo",
  "Lunes",
  "Martes",
  "Miércoles",
  "Jueves",
  "Viernes",
  "Sábado",
] as const;

/** `DD/MM` de una fecha `YYYY-MM-DD`. */
export function diaYMes(fecha: string): string {
  return `${fecha.slice(8, 10)}/${fecha.slice(5, 7)}`;
}

/** Nombre de una columna de la semana, por ejemplo `Lunes 09/11`. */
export function etiquetaDia(fecha: string): string {
  const nombre = NOMBRES_DIAS[new Date(aMsUtc(fecha)).getUTCDay()]!;
  return `${nombre} ${diaYMes(fecha)}`;
}

const formateadorDesfasaje = new Intl.DateTimeFormat("en-US", {
  timeZone: ZONA_CONSULTORIO,
  timeZoneName: "longOffset",
});

/** Desfasaje de la zona en un instante, en segundos con signo (`GMT-03:00` da -10800). */
function desfasajeEnSegundos(ms: number): number {
  const nombre = formateadorDesfasaje
    .formatToParts(new Date(ms))
    .find((parte) => parte.type === "timeZoneName")?.value;
  const coincidencia = /^GMT(?:([+-])(\d{2}):(\d{2})(?::(\d{2}))?)?$/.exec(
    nombre ?? "",
  );
  if (coincidencia === null) return 0;
  const [, signo, horas, minutos, segundos] = coincidencia;
  if (signo === undefined) return 0;
  const total =
    Number(horas) * 3600 + Number(minutos) * 60 + Number(segundos ?? 0);
  return signo === "-" ? -total : total;
}

function formatearDesfasaje(segundos: number): string {
  const signo = segundos < 0 ? "-" : "+";
  const absoluto = Math.abs(segundos);
  const dos = (n: number) => String(n).padStart(2, "0");
  const base = `${signo}${dos(Math.floor(absoluto / 3600))}:${dos(Math.floor((absoluto % 3600) / 60))}`;
  // Un desfasaje con segundos (antes de 1920) se conserva: la API lo rechaza con un 422 de
  // validación sobre `inicio`, y esa fecha igual se rechazaría por estar en el pasado (D14)
  return absoluto % 60 === 0 ? base : `${base}:${dos(absoluto % 60)}`;
}

/**
 * Fecha y hora ingresadas en el consultorio a instante con desfasaje explícito. El desfasaje
 * sale de la zona IANA en dos pasadas, no de un `-03:00` fijo (SU-08, D14).
 */
export function aInstanteConDesfasaje(fecha: string, hora: string): string {
  const [horas, minutos] = hora.split(":").map(Number) as [number, number];
  const comoUtc = aMsUtc(fecha) + (horas * 60 + minutos) * 60 * 1000;
  const primera = desfasajeEnSegundos(comoUtc);
  const segunda = desfasajeEnSegundos(comoUtc - primera * 1000);
  return `${fecha}T${hora}:00${formatearDesfasaje(segunda)}`;
}

/** Días de calendario de `desde` a `hasta` (negativo si `hasta` es anterior). */
export function diasEntre(desde: string, hasta: string): number {
  return Math.round((aMsUtc(hasta) - aMsUtc(desde)) / MS_POR_DIA);
}
