import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { instalarApiFalsa } from "../../test/apiFalsa";
import {
  auditoriaCancelar,
  auditoriaCrear,
  auditoriaReprogramar,
  ID_ANA,
  ID_LIMPIEZA,
  ID_SILLON_1,
  ID_TURNO,
  ID_USUARIO_OTRO,
  ID_USUARIO_PRUEBA,
  prestacion,
  profesional,
  sillon,
  turno,
  valoresDeAuditoria,
} from "../../test/fabricas";
import { usarRelojFijo } from "../../test/reloj";
import { AHORA_SEGUNDOS, tokenDeRecepcionista } from "../../test/tokens";
import { crearNombres } from "../agenda/nombres";
import { CLAVE_TOKEN } from "../sesion/almacenamiento";
import { ProveedorSesion } from "../sesion/ProveedorSesion";
import { HistorialTurno } from "./HistorialTurno";

usarRelojFijo();

const RUTA = `GET /turnos/${ID_TURNO}/auditoria`;
const NOMBRES = crearNombres({
  profesionales: [profesional({ id: ID_ANA })],
  sillones: [sillon({ id: ID_SILLON_1, nombre: "Sillón 1" })],
  prestaciones: [prestacion({ id: ID_LIMPIEZA, nombre: "Limpieza" })],
});

function montar(usuarioSesion: string | null = ID_USUARIO_PRUEBA) {
  sessionStorage.setItem(
    CLAVE_TOKEN,
    tokenDeRecepcionista(AHORA_SEGUNDOS + 3600),
  );
  const alCerrar = vi.fn();
  const user = userEvent.setup();
  render(
    <ProveedorSesion>
      <HistorialTurno
        turno={turno()}
        nombres={NOMBRES}
        usuarioSesion={usuarioSesion}
        alCerrar={alCerrar}
      />
    </ProveedorSesion>,
  );
  return { user, alCerrar };
}

describe("Historial de un turno", () => {
  it("es un diálogo titulado Historial del turno que pide la auditoría del turno", async () => {
    const api = instalarApiFalsa();
    api.responder(RUTA, { status: 200, cuerpo: [auditoriaCrear()] });

    montar();

    expect(
      screen.getByRole("dialog", { name: "Historial del turno" }),
    ).toBeInTheDocument();
    await screen.findByText("Creación");
    expect(api.pedidos(RUTA)).toHaveLength(1);
  });

  it("muestra los registros en el orden de la API con su autor, sin ids", async () => {
    const api = instalarApiFalsa();
    api.responder(RUTA, {
      status: 200,
      cuerpo: [
        auditoriaCrear({ usuario_id: ID_USUARIO_PRUEBA }),
        auditoriaReprogramar({ usuario_id: ID_USUARIO_OTRO }),
        auditoriaCancelar({ usuario_id: ID_USUARIO_OTRO }),
      ],
    });

    montar();

    const registros = await screen.findAllByRole("listitem");
    expect(registros).toHaveLength(3);
    expect(within(registros[0]!).getByText("Creación")).toBeInTheDocument();
    expect(within(registros[0]!).getByText("Vos")).toBeInTheDocument();
    expect(
      within(registros[1]!).getByText("Reprogramación"),
    ).toBeInTheDocument();
    expect(within(registros[1]!).getByText("Otro usuario")).toBeInTheDocument();
    expect(within(registros[2]!).getByText("Cancelación")).toBeInTheDocument();
    expect(within(registros[2]!).getByText("Otro usuario")).toBeInTheDocument();
    const texto = document.body.textContent ?? "";
    expect(texto).not.toContain(ID_USUARIO_PRUEBA);
    expect(texto).not.toContain(ID_USUARIO_OTRO);
  });

  it("muestra el instante en hora local aunque la suite corra en otra zona", async () => {
    const api = instalarApiFalsa();
    api.responder(RUTA, {
      status: 200,
      cuerpo: [auditoriaCrear({ ocurrido_en: "2026-11-09T12:00:00Z" })],
    });

    montar();

    expect(await screen.findByText("09/11/2026 09:00")).toBeInTheDocument();
  });

  it("una sesión sin usuario muestra Otro usuario", async () => {
    const api = instalarApiFalsa();
    api.responder(RUTA, { status: 200, cuerpo: [auditoriaCrear()] });

    montar(null);

    expect(await screen.findByText("Otro usuario")).toBeInTheDocument();
    expect(screen.queryByText("Vos")).not.toBeInTheDocument();
  });

  it("una creación muestra los valores iniciales con los nombres de los catálogos", async () => {
    const api = instalarApiFalsa();
    api.responder(RUTA, { status: 200, cuerpo: [auditoriaCrear()] });

    montar();

    expect(await screen.findByText("12/11/2026 10:00 a 10:45")).toBeVisible();
    expect(screen.getByText("Ficticia, Ana")).toBeVisible();
    expect(screen.getByText("Limpieza")).toBeVisible();
    expect(screen.getByText("Sillón 1")).toBeVisible();
    expect(screen.getByText("45 min")).toBeVisible();
  });

  it("un sillón fuera del catálogo se ve como Sillón no disponible, sin el id", async () => {
    const ID_FUERA = "00000000-0000-4000-8000-0000000000ee";
    const api = instalarApiFalsa();
    api.responder(RUTA, {
      status: 200,
      cuerpo: [
        auditoriaCrear({
          valores_nuevos: valoresDeAuditoria({ sillon_id: ID_FUERA }),
        }),
      ],
    });

    montar();

    expect(await screen.findByText("Sillón no disponible")).toBeVisible();
    expect(document.body.textContent).not.toContain(ID_FUERA);
  });

  it("una reprogramación muestra solo los datos que cambiaron", async () => {
    const api = instalarApiFalsa();
    api.responder(RUTA, { status: 200, cuerpo: [auditoriaReprogramar()] });

    montar();

    expect(
      await screen.findByText(
        "Horario: 12/11/2026 10:00 a 10:45 → 12/11/2026 11:00 a 11:45",
      ),
    ).toBeVisible();
    expect(screen.queryByText(/Profesional:/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Duración:/)).not.toBeInTheDocument();
  });

  it("una reprogramación sin cambios lo dice", async () => {
    const api = instalarApiFalsa();
    api.responder(RUTA, {
      status: 200,
      cuerpo: [
        auditoriaReprogramar({
          valores_previos: valoresDeAuditoria(),
          valores_nuevos: valoresDeAuditoria(),
        }),
      ],
    });

    montar();

    expect(await screen.findByText("Sin cambios en los datos.")).toBeVisible();
  });

  it("una cancelación muestra el motivo, o Sin motivo", async () => {
    const api = instalarApiFalsa();
    api.responder(RUTA, {
      status: 200,
      cuerpo: [
        auditoriaCancelar(),
        auditoriaCancelar({
          valores_nuevos: valoresDeAuditoria({
            estado: "cancelado",
            motivo_cancelacion: null,
          }),
        }),
      ],
    });

    montar();

    expect(await screen.findByText("Motivo: Viaje")).toBeVisible();
    expect(screen.getByText("Sin motivo")).toBeVisible();
  });

  it("no muestra el paciente ni pide /pacientes", async () => {
    const api = instalarApiFalsa();
    api.responder(RUTA, {
      status: 200,
      cuerpo: [auditoriaCrear(), auditoriaReprogramar()],
    });

    montar();

    await screen.findAllByRole("listitem");
    expect(document.body.textContent).not.toContain(
      auditoriaCrear().valores_nuevos.paciente_id,
    );
    expect(
      api.pedidos().filter((p) => p.ruta.startsWith("/pacientes")),
    ).toHaveLength(0);
  });

  it("un historial vacío lo dice", async () => {
    const api = instalarApiFalsa();
    api.responder(RUTA, { status: 200, cuerpo: [] });

    montar();

    expect(
      await screen.findByText("Este turno no tiene registros de auditoría."),
    ).toBeVisible();
  });

  it("un 404 turno_inexistente dice que el turno ya no existe", async () => {
    const api = instalarApiFalsa();
    api.responder(RUTA, {
      status: 404,
      cuerpo: { detail: { codigo: "turno_inexistente", mensaje: "..." } },
    });

    montar();

    expect(await screen.findByText("Este turno ya no existe.")).toBeVisible();
  });

  it("un 403 muestra la falta de permiso sin cerrar la sesión", async () => {
    const api = instalarApiFalsa();
    api.responder(RUTA, {
      status: 403,
      cuerpo: { detail: { codigo: "rol_insuficiente", mensaje: "..." } },
    });

    montar();

    expect(
      await screen.findByText("No tenés permiso para ver esta información."),
    ).toBeVisible();
    expect(sessionStorage.getItem(CLAVE_TOKEN)).not.toBeNull();
  });

  it("una falla de red se muestra con Reintentar, que repite el pedido", async () => {
    const api = instalarApiFalsa();
    api.responder(RUTA, { red: true });
    const { user } = montar();
    await screen.findByText("No se pudo conectar con el servidor.");

    api.responder(RUTA, { status: 200, cuerpo: [auditoriaCrear()] });
    await user.click(screen.getByRole("button", { name: "Reintentar" }));

    expect(await screen.findByText("Creación")).toBeVisible();
    expect(
      screen.queryByText("No se pudo conectar con el servidor."),
    ).not.toBeInTheDocument();
  });

  it("Cerrar llama a alCerrar", async () => {
    const api = instalarApiFalsa();
    api.responder(RUTA, { status: 200, cuerpo: [] });
    const { user, alCerrar } = montar();

    await user.click(screen.getByRole("button", { name: "Cerrar" }));

    expect(alCerrar).toHaveBeenCalledTimes(1);
  });
});
