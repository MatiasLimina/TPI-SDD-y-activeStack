import type { Rol } from "./claims";

/** Pantalla de inicio de cada rol (D7): hoy coincide, pero el mapa deja diferenciarla. */
export const RUTA_INICIAL_POR_ROL: Record<Rol, string> = {
  recepcionista: "/agenda",
  odontologo: "/agenda",
};

export const ETIQUETA_POR_ROL: Record<Rol, string> = {
  recepcionista: "Recepcionista",
  odontologo: "Odontólogo",
};
