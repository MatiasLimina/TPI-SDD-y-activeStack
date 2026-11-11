/** Franja de atención como la devuelve `GET /profesionales/{id}/horarios` (DD-27). */
export interface Franja {
  id: string;
  profesional_id: string;
  /** 0 = Lunes … 6 = Domingo. */
  dia_semana: number;
  /** `HH:MM:SS`, hora local del consultorio sin zona. */
  hora_inicio: string;
  hora_fin: string;
}

export const NOMBRES_DIAS = [
  "Lunes",
  "Martes",
  "Miércoles",
  "Jueves",
  "Viernes",
  "Sábado",
  "Domingo",
] as const;

/** `HH:MM` de una hora `HH:MM:SS`: son horas locales, no pasan por `Date` ni por la zona (D9). */
export function horaCorta(hora: string): string {
  return hora.slice(0, 5);
}

export function textoFranja(franja: Franja): string {
  return `${horaCorta(franja.hora_inicio)} a ${horaCorta(franja.hora_fin)}`;
}

export interface DiaDeAtencion {
  dia: number;
  nombre: string;
  franjas: Franja[];
}

/** Los siete días de la semana con sus franjas, en el orden de la API dentro de cada día. */
export function agruparPorDia(franjas: Franja[]): DiaDeAtencion[] {
  const dias: DiaDeAtencion[] = NOMBRES_DIAS.map((nombre, dia) => ({
    dia,
    nombre,
    franjas: [],
  }));
  for (const franja of franjas) dias[franja.dia_semana]?.franjas.push(franja);
  return dias;
}
