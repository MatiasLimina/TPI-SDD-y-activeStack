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

export const ID_USUARIO_OTRO = "00000000-0000-4000-8000-0000000000b2";
export const ID_FRANJA = "00000000-0000-4000-8000-0000000000aa";

/** Profesional con matrícula, como lo devuelve `GET /profesionales` (DD-26). */
export function profesionalConMatricula(
  cambios: Partial<{
    id: string;
    nombre: string;
    apellido: string;
    matricula: string | null;
    activo: boolean;
  }> = {},
) {
  return {
    ...profesional(),
    matricula: "MN-0001" as string | null,
    ...cambios,
  };
}

/** Ficha completa de paciente, como la devuelve `GET /pacientes` (DD-31). */
export function pacienteFicha(
  cambios: Partial<{
    id: string;
    nombre: string;
    apellido: string;
    documento: string;
    telefono: string;
    email: string | null;
    activo: boolean;
  }> = {},
) {
  return {
    ...paciente(),
    telefono: "011-0000-0104",
    email: null as string | null,
    ...cambios,
  };
}

/** Franja de atención: lunes de 09:00 a 13:00, con horas `HH:MM:SS` (DD-27). */
export function franja(
  cambios: Partial<{
    id: string;
    profesional_id: string;
    dia_semana: number;
    hora_inicio: string;
    hora_fin: string;
  }> = {},
) {
  return {
    id: ID_FRANJA,
    profesional_id: ID_ANA,
    dia_semana: 0,
    hora_inicio: "09:00:00",
    hora_fin: "13:00:00",
    ...cambios,
  };
}

interface ValoresTurnoAuditoria {
  profesional_id: string;
  paciente_id: string;
  prestacion_id: string;
  sillon_id: string | null;
  inicio: string;
  fin: string;
  duracion_min: number;
  estado: string;
  motivo_cancelacion: string | null;
}

function valoresDeAuditoria(
  cambios: Partial<ValoresTurnoAuditoria> = {},
): ValoresTurnoAuditoria {
  return {
    profesional_id: ID_ANA,
    paciente_id: ID_CARLA,
    prestacion_id: ID_LIMPIEZA,
    sillon_id: ID_SILLON_1,
    inicio: "2026-11-12T10:00:00-03:00",
    fin: "2026-11-12T10:45:00-03:00",
    duracion_min: 45,
    estado: "programado",
    motivo_cancelacion: null,
    ...cambios,
  };
}

type AccionAuditoria = "crear" | "reprogramar" | "cancelar";

function registroDeAuditoria(
  accion: AccionAuditoria,
  base: {
    id: string;
    usuario_id: string | null;
    valores_previos: ValoresTurnoAuditoria | null;
    valores_nuevos: ValoresTurnoAuditoria;
  },
  cambios: Partial<{
    id: string;
    usuario_id: string | null;
    ocurrido_en: string;
    valores_previos: ValoresTurnoAuditoria | null;
    valores_nuevos: ValoresTurnoAuditoria;
  }>,
) {
  return {
    turno_id: ID_TURNO,
    accion,
    ocurrido_en: "2026-11-09T12:00:00Z",
    ...base,
    ...cambios,
  };
}

/** Registro `crear` de la auditoría (DD-25): sin valores previos. */
export function auditoriaCrear(
  cambios: Partial<{
    id: string;
    usuario_id: string | null;
    ocurrido_en: string;
    valores_nuevos: ValoresTurnoAuditoria;
  }> = {},
) {
  return registroDeAuditoria(
    "crear",
    {
      id: "00000000-0000-4000-8000-000000000a01",
      usuario_id: ID_USUARIO_PRUEBA,
      valores_previos: null,
      valores_nuevos: valoresDeAuditoria(),
    },
    cambios,
  );
}

/** Registro `reprogramar`: por defecto, un cambio de horario de 10:00 a 11:00. */
export function auditoriaReprogramar(
  cambios: Partial<{
    id: string;
    usuario_id: string | null;
    ocurrido_en: string;
    valores_previos: ValoresTurnoAuditoria;
    valores_nuevos: ValoresTurnoAuditoria;
  }> = {},
) {
  const registro = registroDeAuditoria(
    "reprogramar",
    {
      id: "00000000-0000-4000-8000-000000000a02",
      usuario_id: ID_USUARIO_OTRO,
      valores_previos: valoresDeAuditoria(),
      valores_nuevos: valoresDeAuditoria({
        inicio: "2026-11-12T11:00:00-03:00",
        fin: "2026-11-12T11:45:00-03:00",
      }),
    },
    cambios,
  );
  return {
    ...registro,
    valores_previos: registro.valores_previos ?? valoresDeAuditoria(),
  };
}

/** Registro `cancelar` con motivo "Viaje". */
export function auditoriaCancelar(
  cambios: Partial<{
    id: string;
    usuario_id: string | null;
    ocurrido_en: string;
    valores_previos: ValoresTurnoAuditoria;
    valores_nuevos: ValoresTurnoAuditoria;
  }> = {},
) {
  const registro = registroDeAuditoria(
    "cancelar",
    {
      id: "00000000-0000-4000-8000-000000000a03",
      usuario_id: ID_USUARIO_OTRO,
      valores_previos: valoresDeAuditoria(),
      valores_nuevos: valoresDeAuditoria({
        estado: "cancelado",
        motivo_cancelacion: "Viaje",
      }),
    },
    cambios,
  );
  return {
    ...registro,
    valores_previos: registro.valores_previos ?? valoresDeAuditoria(),
  };
}

export { valoresDeAuditoria };
export const ID_USUARIO_PRUEBA = "00000000-0000-4000-8000-0000000000b1";
