/** El token vive solo en `sessionStorage` (se borra al cerrar la pestaña): nunca en `localStorage` (D3). */
export const CLAVE_TOKEN = "token";

export function guardarToken(token: string): void {
  sessionStorage.setItem(CLAVE_TOKEN, token);
}

export function eliminarToken(): void {
  sessionStorage.removeItem(CLAVE_TOKEN);
}
