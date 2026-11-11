import { useState } from "react";

import { Campo } from "../../shared/ui/Campo";
import { DialogoFormulario } from "../gestion/DialogoFormulario";
import { calcularCambios, camposVacios } from "../gestion/formulario";
import { useEnvioGestion } from "../gestion/useEnvioGestion";
import { useClienteApi } from "../sesion/ProveedorSesion";
import type { PacienteFicha } from "./tipos";

const CONFIG_ERRORES = {
  campos: {
    nombre: "nombre",
    apellido: "apellido",
    documento: "documento",
    telefono: "telefono",
    email: "email",
  },
  duplicado: {
    documento: "Ya existe un paciente con ese documento, activo o desactivado.",
  },
} as const;

export type DestinoPaciente = PacienteFicha | "nuevo";

interface PropsFormulario {
  destino: DestinoPaciente | null;
  alGuardado: () => void;
  alCerrar: () => void;
  alRegistroInexistente: () => void;
}

/** Alta y edición de un paciente en un diálogo (DD-31 l, m). */
export function FormularioPaciente({
  destino,
  alGuardado,
  alCerrar,
  alRegistroInexistente,
}: PropsFormulario) {
  const cliente = useClienteApi();
  const envio = useEnvioGestion(CONFIG_ERRORES, alRegistroInexistente);
  const edicion = destino !== null && destino !== "nuevo" ? destino : null;
  const [nombre, setNombre] = useState(edicion?.nombre ?? "");
  const [apellido, setApellido] = useState(edicion?.apellido ?? "");
  const [documento, setDocumento] = useState(edicion?.documento ?? "");
  const [telefono, setTelefono] = useState(edicion?.telefono ?? "");
  const [email, setEmail] = useState(edicion?.email ?? "");

  async function enviar() {
    const vacios = camposVacios({ nombre, apellido, documento, telefono }, [
      "nombre",
      "apellido",
      "documento",
      "telefono",
    ]);
    if (!envio.validarObligatorios(vacios)) return;
    if (edicion === null) {
      const cuerpo: Record<string, string> = {
        nombre: nombre.trim(),
        apellido: apellido.trim(),
        documento: documento.trim(),
        telefono: telefono.trim(),
      };
      if (email.trim() !== "") cuerpo.email = email.trim();
      const exito = await envio.enviar(() =>
        cliente.pedir("POST", "/pacientes", cuerpo),
      );
      if (exito) alGuardado();
      return;
    }
    const cambios = calcularCambios(
      {
        nombre: edicion.nombre,
        apellido: edicion.apellido,
        documento: edicion.documento,
        telefono: edicion.telefono,
        email: edicion.email,
      },
      { nombre, apellido, documento, telefono, email },
      ["email"],
    );
    if (Object.keys(cambios).length === 0) {
      envio.avisarSinCambios();
      return;
    }
    const exito = await envio.enviar(() =>
      cliente.pedir("PATCH", `/pacientes/${edicion.id}`, cambios),
    );
    if (exito) alGuardado();
  }

  return (
    <DialogoFormulario
      titulo={edicion === null ? "Nuevo paciente" : "Editar paciente"}
      abierto={destino !== null}
      alCerrar={alCerrar}
      alEnviar={() => void enviar()}
      enviando={envio.enviando}
      deshabilitarEnvio={envio.obsoleto}
      errorGeneral={envio.general === null ? null : <p>{envio.general}</p>}
      sinCambios={envio.sinCambios}
    >
      <Campo etiqueta="Nombre" error={envio.errores.nombre}>
        {(atributos) => (
          <input
            {...atributos}
            type="text"
            maxLength={100}
            value={nombre}
            onChange={(e) => setNombre(e.target.value)}
          />
        )}
      </Campo>
      <Campo etiqueta="Apellido" error={envio.errores.apellido}>
        {(atributos) => (
          <input
            {...atributos}
            type="text"
            maxLength={100}
            value={apellido}
            onChange={(e) => setApellido(e.target.value)}
          />
        )}
      </Campo>
      <Campo etiqueta="Documento" error={envio.errores.documento}>
        {(atributos) => (
          <input
            {...atributos}
            type="text"
            maxLength={20}
            value={documento}
            onChange={(e) => setDocumento(e.target.value)}
          />
        )}
      </Campo>
      <Campo etiqueta="Teléfono" error={envio.errores.telefono}>
        {(atributos) => (
          <input
            {...atributos}
            type="text"
            maxLength={30}
            value={telefono}
            onChange={(e) => setTelefono(e.target.value)}
          />
        )}
      </Campo>
      <Campo etiqueta="Email" error={envio.errores.email}>
        {(atributos) => (
          <input
            {...atributos}
            type="text"
            inputMode="email"
            maxLength={254}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        )}
      </Campo>
    </DialogoFormulario>
  );
}
