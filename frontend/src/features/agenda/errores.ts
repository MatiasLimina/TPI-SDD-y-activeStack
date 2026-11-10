import { ErrorApi, MENSAJE_GENERICO } from "../../shared/api/errorApi";

/** El cliente HTTP solo lanza `ErrorApi`; cualquier otra cosa es una falla inesperada. */
export function comoErrorApi(causa: unknown): ErrorApi {
  return causa instanceof ErrorApi
    ? causa
    : new ErrorApi({ status: 0, codigo: null, mensaje: MENSAJE_GENERICO });
}
