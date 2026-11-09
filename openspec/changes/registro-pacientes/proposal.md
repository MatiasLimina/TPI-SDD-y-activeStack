# Proposal

## Why

La tabla `paciente` existe desde C-02 y los turnos ya la referencian, pero los pacientes solo entran por el seed: la recepcionista no puede registrar a una persona nueva ni buscarla para asignarle un turno (US-009). Sin este change no hay forma de agendar a un paciente real del consultorio, y el selector de paciente de C-15 no tiene de dónde leer. Como son datos personales (Ley 25.326 / 26.529), el acceso tiene que quedar limitado por rol desde el primer endpoint.

## What Changes

- **API de pacientes** con el contrato de C-08 (DD-26) donde aplica: `POST /pacientes`, `GET /pacientes`, `GET /pacientes/{id}`, `PATCH /pacientes/{id}` y `POST /pacientes/{id}/desactivar`.
- **Campos mínimos** (US-009, entidad Paciente): `nombre`, `apellido`, `documento` y `telefono` obligatorios, `email` opcional. Textos sin espacios extremos y con el largo de su columna; sin ficha clínica ni odontograma.
- **Búsqueda** por nombre, apellido o documento con el parámetro `q`: coincidencia parcial, sin distinguir mayúsculas ni acentos, ordenada por apellido y nombre y paginada con un límite máximo.
- **Documento único**: un documento repetido, también ante altas simultáneas, responde `409 recurso_duplicado`.
- **Desactivación lógica e idempotente**: un paciente desactivado no admite turnos nuevos y sus turnos y recordatorios existentes no cambian.
- **Permisos** (matriz de `03_actores_y_roles.md`): la recepcionista escribe y busca; el odontólogo solo lee `id`, `nombre` y `apellido` de los pacientes de sus turnos, por `GET /pacientes/{id}`. Sobre cualquier otro paciente, exista o no: `403 paciente_ajeno`.
- **Datos personales fuera de errores y logs**: los `422` de estas rutas no reproducen lo enviado, y el log de acceso no registra el texto buscado.

Las decisiones que la KB no fija están en `design.md` y fueron aprobadas por el usuario el 2026-11-09; se registran como DD-31. Los specs están escritos con esas opciones.

**Fuera de alcance**: ficha clínica y odontograma; auditoría de pacientes (RN-CU-01 audita solo turnos); reactivación de pacientes (va al backlog de `CHANGES.md`); consulta de agenda (C-13) y frontend (C-14 a C-16). Sin migración: la tabla y su `UNIQUE` ya existen.

## Capabilities

### New Capabilities
- `registro-pacientes`: alta, edición, búsqueda, consulta y desactivación lógica de pacientes, con acceso por rol, lectura mínima del odontólogo y protección de los datos personales en errores y logs.

### Modified Capabilities
<!-- Ninguna: `agenda-turnos` ya exige referencias activas, incluido el paciente, y `catalogo-consultorio` ya exige el documento único. -->

## Impact

- **Backend nuevo**: rutas `app/api/pacientes.py`, reglas `app/domain/pacientes.py` y repositorio `app/infrastructure/db/repositorio_pacientes.py`.
- **Backend existente**: se registra el router en `app/main.py`; `TipoRecurso` suma `paciente`; las bases de los schemas de `app/api/recursos.py` pasan a ser públicas, sin cambiar su comportamiento. Se reutilizan los casos de uso y los manejadores de errores de C-08.
- **API**: 5 rutas nuevas, todas autenticadas. No cambia ninguna ruta existente.
- **Base de datos**: sin cambios; `main` sigue en la revisión `010`.
- **Dependencias**: ninguna nueva.
- **KB**: DD-31 en `09`, fila de Pacientes en `02`, matriz de `03`, preguntas resueltas en `10` y reactivación de pacientes en el backlog de `CHANGES.md`.
