/** Valores que viajan en el cuerpo de un alta o de un `PATCH`. */
export type Valor = string | number | boolean | null;

/** Obligatorios vacíos o en blanco, en el orden en que se declararon (D6). */
export function camposVacios(
  valores: Record<string, string>,
  obligatorios: readonly string[],
): string[] {
  return obligatorios.filter((campo) => (valores[campo] ?? "").trim() === "");
}

const FORMATO_HORA = /^\d{2}:\d{2}(:\d{2})?$/;

/** La API responde `HH:MM:SS` y el formulario trabaja con `HH:MM`: se comparan los cinco primeros. */
function normalizar(valor: Valor): Valor {
  return typeof valor === "string" && FORMATO_HORA.test(valor)
    ? valor.slice(0, 5)
    : valor;
}

/**
 * Edición parcial (D5): solo los campos cuyo valor, recortado, difiere del actual. Un opcional
 * vaciado vale `null`.
 */
export function calcularCambios(
  actual: Record<string, Valor>,
  editado: Record<string, Valor>,
  opcionales: readonly string[],
): Record<string, Valor> {
  const cambios: Record<string, Valor> = {};
  for (const [campo, crudo] of Object.entries(editado)) {
    let nuevo: Valor = typeof crudo === "string" ? crudo.trim() : crudo;
    if (nuevo === "" && opcionales.includes(campo)) nuevo = null;
    const previo = actual[campo] ?? null;
    if (normalizar(nuevo) !== normalizar(previo)) cambios[campo] = nuevo;
  }
  return cambios;
}
