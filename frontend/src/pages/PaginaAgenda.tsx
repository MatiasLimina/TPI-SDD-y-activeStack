import { useState } from "react";
import { useSearchParams } from "react-router";

import { BarraAgenda } from "../features/agenda/BarraAgenda";

import { DialogoCancelar } from "../features/turnos/DialogoCancelar";
import { FormularioReprogramar } from "../features/turnos/FormularioReprogramar";
import { FormularioNuevoTurno } from "../features/turnos/FormularioNuevoTurno";
import { HistorialTurno } from "../features/auditoria/HistorialTurno";
import { DetalleTurno } from "../features/agenda/DetalleTurno";
import { GrillaAgenda } from "../features/agenda/GrillaAgenda";
import { armarColumnas, contarElementos } from "../features/agenda/grilla";
import type { TurnoAgenda } from "../features/agenda/tipos";
import { crearNombres } from "../features/agenda/nombres";
import { useAgenda } from "../features/agenda/useAgenda";
import { useCatalogos } from "../features/agenda/useCatalogos";
import {
  aParametros,
  aRango,
  leerVista,
  type VistaAgenda,
  vistaTrasGuardar,
} from "../features/agenda/vistaAgenda";
import { useSesion } from "../features/sesion/ProveedorSesion";
import {
  diaYMes,
  hoyLocal,
  instanteALocal,
} from "../shared/tiempo/zonaConsultorio";

const TEXTO_VACIO = "No hay turnos ni bloqueos en este período.";
const TEXTO_SOLO_CANCELADOS =
  "Solo hay turnos cancelados en este período. Activá Mostrar cancelados para verlos.";

export default function PaginaAgenda() {
  const { sesion } = useSesion();
  const [parametros, setParametros] = useSearchParams();
  const rol = sesion?.claims.rol ?? "odontologo";
  const hoy = hoyLocal();
  const vista = leerVista(parametros, rol, hoy);
  const { desde, hasta } = aRango(vista);
  const agenda = useAgenda({
    desde,
    hasta,
    profesionalId: vista.profesionalId,
    sillonId: vista.sillonId,
  });
  const {
    catalogos,
    error: errorCatalogos,
    reintentar,
    recargar: recargarCatalogos,
  } = useCatalogos();
  const { datos } = agenda;

  // La carga inicial de catálogos o la lectura de la agenda sin datos previos ofrecen Reintentar
  const error = errorCatalogos ?? agenda.error;
  const sinDatos = datos === null || catalogos === null;
  const conteo = datos === null ? null : contarElementos(datos, vista);
  const [nuevoAbierto, setNuevoAbierto] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);
  // Sin diálogos apilados: el detalle se cierra al abrir una operación (P15). Se guarda el
  // turno entero, para que una relectura no cierre el formulario si el turno desaparece
  const [reprogramando, setReprogramando] = useState<TurnoAgenda | null>(null);
  const [cancelando, setCancelando] = useState<TurnoAgenda | null>(null);
  const [historial, setHistorial] = useState<TurnoAgenda | null>(null);
  const [detalleId, setDetalleId] = useState<string | null>(null);
  const turnoDetalle = datos?.turnos.find((t) => t.id === detalleId) ?? null;
  const esRecepcionista = rol === "recepcionista";
  const cambiarVista = (nueva: VistaAgenda) =>
    setParametros(aParametros(nueva));
  // Un turno guardado fuera del período visible se sigue con la agenda (D20); si no, se relee
  const irAlTurno = (inicio: string) => {
    const destino = vistaTrasGuardar(vista, inicio);
    if (destino === null) agenda.recargar();
    else cambiarVista(destino);
  };
  const reintentarTodo = () => {
    if (errorCatalogos !== null) reintentar();
    if (agenda.error !== null) agenda.recargar();
  };
  const nombres = crearNombres(
    catalogos ?? { profesionales: [], sillones: [], prestaciones: [] },
  );
  const columnas =
    datos === null || catalogos === null
      ? []
      : armarColumnas({
          vista,
          rol,
          profesionalPropio: sesion?.claims.profesionalId ?? null,
          datos,
          profesionales: catalogos.profesionales,
          sillones: catalogos.sillones,
        });
  return (
    <main>
      <h1>Agenda</h1>
      <BarraAgenda
        vista={vista}
        rol={rol}
        catalogos={catalogos}
        hoy={hoy}
        alCambiar={cambiarVista}
        alActualizar={agenda.recargar}
      />
      {esRecepcionista && (
        <button type="button" onClick={() => setNuevoAbierto(true)}>
          Nuevo turno
        </button>
      )}
      {aviso !== null && <p role="status">{aviso}</p>}
      {error !== null && (
        <div role="alert">
          <p>{error.mensaje}</p>
          {sinDatos && (
            <button type="button" onClick={reintentarTodo}>
              Reintentar
            </button>
          )}
        </div>
      )}
      {sinDatos && error === null && <p>Cargando agenda…</p>}
      {conteo !== null && catalogos !== null && conteo.visibles === 0 && (
        <p>
          {conteo.canceladosOcultos > 0 ? TEXTO_SOLO_CANCELADOS : TEXTO_VACIO}
        </p>
      )}
      {catalogos !== null && (
        <GrillaAgenda
          columnas={columnas}
          vista={vista}
          nombres={nombres}
          alElegirTurno={(turno) => setDetalleId(turno.id)}
        />
      )}
      {esRecepcionista && catalogos !== null && (
        <FormularioNuevoTurno
          abierto={nuevoAbierto}
          catalogos={catalogos}
          fechaInicial={vista.fecha}
          profesionalInicial={vista.profesionalId}
          alCrear={(inicio) => {
            const local = instanteALocal(inicio);
            setNuevoAbierto(false);
            setAviso(
              `Turno creado para el ${diaYMes(local.fecha)} a las ${local.hora}.`,
            );
            irAlTurno(inicio);
          }}
          alCerrar={() => setNuevoAbierto(false)}
          alReleerCatalogos={recargarCatalogos}
          alReleerAgenda={agenda.recargar}
        />
      )}
      <DetalleTurno
        turno={turnoDetalle}
        nombres={nombres}
        puedeOperar={esRecepcionista}
        alCerrar={() => setDetalleId(null)}
        alReprogramar={(t) => {
          setDetalleId(null);
          setReprogramando(t);
        }}
        alCancelar={(t) => {
          setDetalleId(null);
          setCancelando(t);
        }}
        alVerHistorial={(t) => {
          setDetalleId(null);
          setHistorial(t);
        }}
      />
      {esRecepcionista && (
        <HistorialTurno
          turno={historial}
          nombres={nombres}
          usuarioSesion={sesion?.claims.usuarioId ?? null}
          alCerrar={() => setHistorial(null)}
        />
      )}
      {esRecepcionista && catalogos !== null && (
        <FormularioReprogramar
          turno={reprogramando}
          catalogos={catalogos}
          nombres={nombres}
          alReprogramado={(inicio) => {
            setReprogramando(null);
            setAviso("Turno reprogramado.");
            irAlTurno(inicio);
          }}
          alCerrar={() => setReprogramando(null)}
          alReleerCatalogos={recargarCatalogos}
          alReleerAgenda={agenda.recargar}
        />
      )}
      {esRecepcionista && (
        <DialogoCancelar
          turno={cancelando}
          alCancelado={() => {
            setCancelando(null);
            setAviso("Turno cancelado.");
            agenda.recargar();
          }}
          alCerrar={() => setCancelando(null)}
          alReleerAgenda={agenda.recargar}
        />
      )}
    </main>
  );
}
