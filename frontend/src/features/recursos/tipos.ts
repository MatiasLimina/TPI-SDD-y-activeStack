// Formas de la API de gestión de recursos (DD-26) que usan las secciones de configuración

export interface ProfesionalFicha {
  id: string;
  nombre: string;
  apellido: string;
  /** Nula si el profesional no tiene matrícula cargada. */
  matricula: string | null;
  activo: boolean;
}
