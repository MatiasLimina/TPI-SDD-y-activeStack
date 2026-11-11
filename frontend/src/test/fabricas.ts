// Datos ficticios para los tests de la agenda: nada de esto es real.

export const ID_ANA = "00000000-0000-4000-8000-0000000000a1";
export const ID_LUIS = "00000000-0000-4000-8000-0000000000a2";
export const ID_SILLON_1 = "00000000-0000-4000-8000-0000000000c1";
export const ID_SILLON_2 = "00000000-0000-4000-8000-0000000000c2";
export const ID_LIMPIEZA = "00000000-0000-4000-8000-0000000000d1";
export const ID_CONTROL = "00000000-0000-4000-8000-0000000000d2";
export const ID_CARLA = "00000000-0000-4000-8000-0000000000e1";
export const ID_TURNO = "00000000-0000-4000-8000-0000000000f1";
export const ID_BLOQUEO = "00000000-0000-4000-8000-0000000000f9";

export function profesional(
  cambios: Partial<{
    id: string;
    nombre: string;
    apellido: string;
    activo: boolean;
  }> = {},
) {
  return {
    id: ID_ANA,
    nombre: "Ana",
    apellido: "Ficticia",
    activo: true,
    ...cambios,
  };
}

export function sillon(
  cambios: Partial<{ id: string; nombre: string; activo: boolean }> = {},
) {
  return { id: ID_SILLON_1, nombre: "Sillón 1", activo: true, ...cambios };
}

export function prestacion(
  cambios: Partial<{
    id: string;
    nombre: string;
    duracion_min: number;
    requiere_sillon: boolean;
    activa: boolean;
  }> = {},
) {
  return {
    id: ID_LIMPIEZA,
    nombre: "Limpieza",
    duracion_min: 45,
    requiere_sillon: true,
    activa: true,
    ...cambios,
  };
}

export function paciente(
  cambios: Partial<{
    id: string;
    nombre: string;
    apellido: string;
    documento: string;
    activo: boolean;
  }> = {},
) {
  return {
    id: ID_CARLA,
    nombre: "Carla",
    apellido: "Imaginaria",
    documento: "00000104",
    activo: true,
    ...cambios,
  };
}

/** Turno de la agenda: 2026-11-09 de 10:00 a 10:45 hora local, de Ana, con Carla. */
export function turno(
  cambios: Partial<{
    id: string;
    profesional_id: string;
    paciente: { id: string; nombre: string; apellido: string };
    prestacion_id: string;
    sillon_id: string | null;
    inicio: string;
    fin: string;
    duracion_min: number;
    estado: "programado" | "cancelado";
    creado_por: string;
    motivo_cancelacion: string | null;
  }> = {},
) {
  return {
    id: ID_TURNO,
    profesional_id: ID_ANA,
    paciente: { id: ID_CARLA, nombre: "Carla", apellido: "Imaginaria" },
    prestacion_id: ID_LIMPIEZA,
    sillon_id: ID_SILLON_1 as string | null,
    inicio: "2026-11-09T10:00:00-03:00",
    fin: "2026-11-09T10:45:00-03:00",
    duracion_min: 45,
    estado: "programado" as "programado" | "cancelado",
    creado_por: "00000000-0000-4000-8000-0000000000b1",
    motivo_cancelacion: null as string | null,
    ...cambios,
  };
}

/** Bloqueo de la agenda de Ana el 2026-11-09 de 15:00 a 16:00 hora local. */
export function bloqueo(
  cambios: Partial<{
    id: string;
    profesional_id: string;
    inicio: string;
    fin: string;
    motivo: string | null;
  }> = {},
) {
  return {
    id: ID_BLOQUEO,
    profesional_id: ID_ANA,
    inicio: "2026-11-09T15:00:00-03:00",
    fin: "2026-11-09T16:00:00-03:00",
    motivo: "Congreso" as string | null,
    creado_por: "00000000-0000-4000-8000-0000000000b1",
    ...cambios,
  };
}
