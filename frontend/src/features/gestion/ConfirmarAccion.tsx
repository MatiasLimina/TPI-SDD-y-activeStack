import type { ReactNode } from "react";

import type { ErrorApi } from "../../shared/api/errorApi";
import { useClienteApi } from "../sesion/ProveedorSesion";
import { DialogoConfirmacion } from "./DialogoConfirmacion";
import { useEnvioGestion } from "./useEnvioGestion";

export interface AccionConfirmable {
  titulo: string;
  textoConfirmar: string;
  metodo: "POST" | "DELETE";
  ruta: string;
  /** Aviso de éxito de la pantalla (`Sillón desactivado.`). */
  aviso: string;
  /** Nombra el elemento y explica la consecuencia. */
  contenido: ReactNode;
}

interface PropsConfirmarAccion {
  /** La acción a confirmar, o `null` con el diálogo cerrado. */
  accion: AccionConfirmable | null;
  alHecho: (aviso: string) => void;
  alCerrar: () => void;
  /** Se llama ante cualquier error: la pantalla decide si relee el listado. */
  alFallar: (error: ErrorApi) => void;
}

/**
 * Confirmación de una desactivación o un borrado (D4): un solo pedido, con el error en el mismo
 * diálogo. Usar con `key={dialogo.clave}` para que cada apertura empiece limpia.
 */
export function ConfirmarAccion({
  accion,
  alHecho,
  alCerrar,
  alFallar,
}: PropsConfirmarAccion) {
  const cliente = useClienteApi();
  const envio = useEnvioGestion({ campos: {} });

  async function confirmar() {
    if (accion === null) return;
    const exito = await envio.enviar(
      () => cliente.pedir(accion.metodo, accion.ruta),
      alFallar,
    );
    if (exito) alHecho(accion.aviso);
  }

  return (
    <DialogoConfirmacion
      titulo={accion?.titulo ?? ""}
      abierto={accion !== null}
      textoConfirmar={accion?.textoConfirmar ?? ""}
      enviando={envio.enviando}
      deshabilitarConfirmacion={envio.obsoleto}
      alConfirmar={() => void confirmar()}
      alCerrar={alCerrar}
      error={envio.general === null ? null : <p>{envio.general}</p>}
    >
      {accion?.contenido}
    </DialogoConfirmacion>
  );
}
