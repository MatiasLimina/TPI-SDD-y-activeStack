/** Resultado de `GET /pacientes` (solo la recepcionista, DD-31 b). */
export interface PacienteBusqueda {
  id: string;
  nombre: string;
  apellido: string;
  documento: string;
  activo: boolean;
}
