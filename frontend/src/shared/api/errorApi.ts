export const MENSAJE_GENERICO = "Ocurrió un error. Intentá de nuevo.";
export const MENSAJE_VALIDACION = "Revisá los datos ingresados.";
export const MENSAJE_SIN_CONEXION = "No se pudo conectar con el servidor.";

/** Error de validación de un campo (`422`). `campo` nulo: error general del formulario. */
export interface ErrorCampo {
  campo: string | null;
  mensaje: string;
}

export interface DatosErrorApi {
  status: number;
  codigo: string | null;
  mensaje: string;
  errores?: ErrorCampo[];
  datos?: Record<string, unknown>;
}

/** Único tipo de error del cliente HTTP: `status` 0 es una falla de red. */
export class ErrorApi extends Error {
  readonly status: number;
  readonly codigo: string | null;
  readonly mensaje: string;
  readonly errores: ErrorCampo[];
  /** El resto de `detail` (p. ej. `recursos` o `turnos`), para que las pantallas lo lean. */
  readonly datos: Record<string, unknown>;

  constructor({
    status,
    codigo,
    mensaje,
    errores = [],
    datos = {},
  }: DatosErrorApi) {
    super(mensaje);
    this.name = "ErrorApi";
    this.status = status;
    this.codigo = codigo;
    this.mensaje = mensaje;
    this.errores = errores;
    this.datos = datos;
  }
}
