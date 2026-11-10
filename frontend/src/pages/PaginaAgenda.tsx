import { useState } from "react";
import { useSearchParams } from "react-router";

import { BarraAgenda } from "../features/agenda/BarraAgenda";

import { FormularioNuevoTurno } from "../features/turnos/FormularioNuevoTurno";
import { DetalleTurno } from "../features/agenda/DetalleTurno";
import { GrillaAgenda } from "../features/agenda/GrillaAgenda";
import { armarColumnas, contarElementos } from "../features/agenda/grilla";
import { crearNombres } from "../features/agenda/nombres";
import { useAgenda } from "../features/agenda/useAgenda";
import { useCatalogos } from "../features/agenda/useCatalogos";
import {
  aParametros,
  aRango,
  leerVista,
  type VistaAgenda,
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
  const { catalogos, error: errorCatalogos, reintentar } = useCatalogos();
  const { datos } = agenda;

  // La carga inicial de catálogos o la lectura de la agenda sin datos previos ofrecen Reintentar
  const error = errorCatalogos ?? agenda.error;
  const sinDatos = datos === null || catalogos === null;
  const conteo = datos === null ? null : contarElementos(datos, vista);
  const [nuevoAbierto, setNuevoAbierto] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);
  const [detalleId, setDetalleId] = useState<string | null>(null);
  const turnoDetalle = datos?.turnos.find((t) => t.id === detalleId) ?? null;
  const esRecepcionista = rol === "recepcionista";
  const cambiarVista = (nueva: VistaAgenda) =>
    setParametros(aParametros(nueva));
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
      {aviso !== null && <p role="status">{aviso}</p>}
      {esRecepcionista && (
        <button type="button" onClick={() => setNuevoAbierto(true)}>
          Nuevo turno
        </button>
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
            agenda.recargar();
          }}
          alCerrar={() => setNuevoAbierto(false)}
          alReleerCatalogos={() => Promise.resolve(null)}
          alReleerAgenda={agenda.recargar}
        />
      )}
      <DetalleTurno
        turno={turnoDetalle}
        nombres={nombres}
        puedeOperar={esRecepcionista}
        alCerrar={() => setDetalleId(null)}
        alReprogramar={() => setDetalleId(null)}
        alCancelar={() => setDetalleId(null)}
      />
    </main>
  );
}
