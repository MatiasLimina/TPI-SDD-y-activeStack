// Formas de la API que usa la agenda (`TurnoAgendaOut`, `BloqueoOut` y los catálogos), D7

export type EstadoTurno = "programado" | "cancelado";

export interface PacienteEmbebido {
  id: string;
  nombre: string;
  apellido: string;
}

export interface TurnoAgenda {
  id: string;
  profesional_id: string;
  paciente: PacienteEmbebido;
  prestacion_id: string;
  sillon_id: string | null;
  inicio: string;
  fin: string;
  duracion_min: number;
  estado: EstadoTurno;
  creado_por: string;
  motivo_cancelacion: string | null;
}

export interface Bloqueo {
  id: string;
  profesional_id: string;
  inicio: string;
  fin: string;
  motivo: string | null;
  creado_por: string;
}

export interface RespuestaAgenda {
  turnos: TurnoAgenda[];
  bloqueos: Bloqueo[];
}

export interface Profesional {
  id: string;
  nombre: string;
  apellido: string;
  activo: boolean;
}

export interface Sillon {
  id: string;
  nombre: string;
  activo: boolean;
}

export interface Prestacion {
  id: string;
  nombre: string;
  duracion_min: number;
  requiere_sillon: boolean;
  activa: boolean;
}
