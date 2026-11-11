const FORMATO_UUID =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** Un parámetro de URL con forma de UUID; si no, la pantalla lo ignora. */
export function esUuid(valor: string | null): valor is string {
  return valor !== null && FORMATO_UUID.test(valor);
}
