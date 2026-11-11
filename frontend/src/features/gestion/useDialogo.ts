import { useState } from "react";

/**
 * Qué diálogo está abierto y con qué (`null` es cerrado). `clave` cambia en cada apertura: usada
 * como `key` del formulario, descarta lo cargado y los errores de la vez anterior.
 */
export function useDialogo<T>() {
  const [estado, setEstado] = useState<{ valor: T | null; clave: number }>({
    valor: null,
    clave: 0,
  });
  return {
    valor: estado.valor,
    clave: estado.clave,
    abrir: (valor: T) =>
      setEstado((anterior) => ({ valor, clave: anterior.clave + 1 })),
    cerrar: () => setEstado((anterior) => ({ ...anterior, valor: null })),
  };
}
