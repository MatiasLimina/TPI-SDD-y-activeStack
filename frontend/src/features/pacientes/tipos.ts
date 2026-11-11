/** Resultado de `GET /pacientes` (solo la recepcionista, DD-31 b). */
export interface PacienteBusqueda {
  id: string;
  nombre: string;
  apellido: string;
  documento: string;
  activo: boolean;
}

/** Ficha completa de GET /pacientes (DD-31): lo que lista y edita la pantalla de pacientes. */
export interface PacienteFicha extends PacienteBusqueda {
  telefono: string;
  /** Nulo si el paciente no tiene email. */
  email: string | null;
}
