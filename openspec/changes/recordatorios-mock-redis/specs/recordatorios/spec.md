# Spec Delta

## Purpose

Generar un recordatorio previo a cada turno activo, programado con la anticipación configurada y ajustado de forma atómica cuando el turno se cancela o se reprograma. Un worker asincrónico lo procesa desde una cola Redis y lo envía por el puerto de notificación (adaptador mock), con reintentos acotados y sin exponer datos clínicos (RN-NO-01..05, US-012).

## ADDED Requirements

### Requirement: Programación del recordatorio al crear un turno
Cada alta de turno exitosa con una anticipación de `REMINDER_LEAD_HOURS` horas o más (por defecto 24) MUST crear exactamente un recordatorio con `estado = pendiente`, `canal = mock`, `intentos = 0` y `programado_para = inicio - REMINDER_LEAD_HOURS`, en UTC. Si la anticipación es menor, MUST NOT crearse ningún recordatorio y el alta MUST confirmarse igual (RN-NO-01, RN-NO-03, DD-13).

#### Scenario: Alta con más de 24 h de anticipación
- **GIVEN** dado un profesional A, un paciente P, el sillón 1 y la prestación "Limpieza" (45 min, requiere sillón) activos, una recepcionista autenticada, `REMINDER_LEAD_HOURS` en su valor por defecto y que el reloj marca 2026-10-07 09:00 hora local
- **WHEN** cuando la recepcionista envía `POST /turnos` con esos recursos e inicio 2026-10-09T10:00-03:00
- **THEN** entonces la respuesta es `201` y en la base existe exactamente un recordatorio para ese turno, con `estado` `pendiente`, `canal` `mock`, `intentos` 0 y `programado_para` 2026-10-08T13:00Z

#### Scenario: Anticipación exactamente igual a 24 h
- **GIVEN** dados los mismos recursos y que el reloj marca 2026-10-07 10:00 hora local
- **WHEN** cuando la recepcionista crea un turno con inicio 2026-10-08T10:00-03:00
- **THEN** entonces la respuesta es `201` y el turno tiene exactamente un recordatorio `pendiente` con `programado_para` 2026-10-07T13:00Z

#### Scenario: Alta con menos de 24 h de anticipación
- **GIVEN** dados los mismos recursos y que el reloj marca 2026-10-07 09:01 hora local
- **WHEN** cuando la recepcionista crea un turno con inicio 2026-10-08T09:00-03:00 (23 h 59 min después)
- **THEN** entonces la respuesta es `201`, el turno queda `programado` y no existe ningún recordatorio para ese turno

#### Scenario: Anticipación configurada en 48 h
- **GIVEN** dado `REMINDER_LEAD_HOURS=48` y que el reloj marca 2026-10-07 10:00 hora local
- **WHEN** cuando se crea un turno con inicio 2026-10-09T09:00-03:00 (47 h después) y otro, de otro paciente, con inicio 2026-10-09T11:00-03:00 (49 h después)
- **THEN** entonces ambas respuestas son `201`, el primero no tiene recordatorio y el segundo tiene un recordatorio `pendiente` con `programado_para` 2026-10-07T14:00Z

### Requirement: Cancelar el turno cancela su recordatorio pendiente
Cada cancelación exitosa de un turno MUST pasar a `estado = cancelado` su recordatorio `pendiente`, si lo tiene. Los recordatorios en `enviado`, `fallido` o `cancelado` MUST NOT modificarse (RN-NO-02).

#### Scenario: Cancelación con recordatorio pendiente
- **GIVEN** dado un turno `programado` con inicio 2026-10-09 10:00 hora local y su recordatorio `pendiente` con `programado_para` 2026-10-08T13:00Z, una recepcionista autenticada y que el reloj marca 2026-10-07 09:00 hora local
- **WHEN** cuando la recepcionista envía `POST /turnos/{id}/cancelar`
- **THEN** entonces la respuesta es `200` y el recordatorio queda en `estado` `cancelado`, con su `programado_para` y sus `intentos` sin cambios

#### Scenario: Cancelación de un turno sin recordatorio
- **GIVEN** dado un turno `programado` con inicio 2026-10-07 15:00 hora local, creado sin recordatorio porque faltaba menos de 24 h, y que el reloj marca 2026-10-07 09:00 hora local
- **WHEN** cuando una recepcionista lo cancela
- **THEN** entonces la respuesta es `200` y el turno sigue sin recordatorios

#### Scenario: Recordatorio ya enviado no se modifica al cancelar
- **GIVEN** dado un turno `programado` con inicio 2026-10-09 10:00 hora local cuyo recordatorio ya está `enviado` con `intentos` 1, y que el reloj marca 2026-10-08 11:00 hora local
- **WHEN** cuando una recepcionista lo cancela
- **THEN** entonces la respuesta es `200`, el recordatorio sigue `enviado` con `intentos` 1 y no se crea ningún recordatorio nuevo

### Requirement: Reprogramar el turno reprograma su recordatorio
Cuando una reprogramación exitosa cambia el `inicio` del turno, su recordatorio `pendiente` MUST pasar a `cancelado` y MUST crearse uno nuevo `pendiente` si el nuevo inicio cumple la anticipación configurada, con la misma regla del alta. Si el `inicio` no cambia, el recordatorio MUST NOT modificarse. Los recordatorios en `enviado` o `fallido` MUST NOT modificarse (RN-NO-02, RN-NO-03).

#### Scenario: Nuevo inicio con 24 h o más
- **GIVEN** dado un turno `programado` con inicio 2026-10-09 10:00 hora local y su recordatorio `pendiente` con `programado_para` 2026-10-08T13:00Z, y que el reloj marca 2026-10-07 09:00 hora local
- **WHEN** cuando una recepcionista lo reprograma a `inicio` 2026-10-12T15:00-03:00
- **THEN** entonces la respuesta es `200`, el recordatorio anterior queda `cancelado` y el turno tiene exactamente un recordatorio `pendiente`, nuevo, con `programado_para` 2026-10-11T18:00Z e `intentos` 0

#### Scenario: Nuevo inicio con menos de 24 h
- **GIVEN** dado el mismo turno con su recordatorio `pendiente` y que el reloj marca 2026-10-07 09:00 hora local
- **WHEN** cuando una recepcionista lo reprograma a `inicio` 2026-10-07T15:00-03:00
- **THEN** entonces la respuesta es `200`, el recordatorio anterior queda `cancelado` y el turno no tiene ningún recordatorio `pendiente`

#### Scenario: Turno sin recordatorio reprogramado con 24 h o más
- **GIVEN** dado un turno `programado` con inicio 2026-10-07 15:00 hora local, creado sin recordatorio porque faltaba menos de 24 h, y que el reloj marca 2026-10-07 09:00 hora local
- **WHEN** cuando una recepcionista lo reprograma a `inicio` 2026-10-09T10:00-03:00
- **THEN** entonces la respuesta es `200` y el turno tiene exactamente un recordatorio `pendiente` con `programado_para` 2026-10-08T13:00Z

#### Scenario: Reprogramación sin cambio de inicio
- **GIVEN** dado un turno `programado` con inicio 2026-10-09 10:00 hora local en el sillón 1 y su recordatorio `pendiente` con `programado_para` 2026-10-08T13:00Z, el sillón 2 activo y libre en ese horario, y que el reloj marca 2026-10-07 09:00 hora local
- **WHEN** cuando una recepcionista lo reprograma informando solo `sillon_id` del sillón 2
- **THEN** entonces la respuesta es `200` y el turno conserva el mismo recordatorio `pendiente` (mismo id, mismo `programado_para`), sin que se cree ninguno nuevo

#### Scenario: Recordatorio ya enviado y nuevo inicio con 24 h o más
- **GIVEN** dado un turno `programado` con inicio 2026-10-09 10:00 hora local, cuyo recordatorio ya está `enviado` con `intentos` 1, y que el reloj marca 2026-10-08 11:00 hora local
- **WHEN** cuando una recepcionista lo reprograma a `inicio` 2026-10-12T10:00-03:00
- **THEN** entonces la respuesta es `200`, el recordatorio anterior sigue `enviado` con `intentos` 1 y el turno tiene además un recordatorio `pendiente`, nuevo, con `programado_para` 2026-10-11T13:00Z

#### Scenario: Recordatorio fallido y nuevo inicio con 24 h o más
- **GIVEN** dado un turno `programado` con inicio 2026-10-09 10:00 hora local, cuyo recordatorio quedó `fallido` con `intentos` 3, y que el reloj marca 2026-10-08 11:00 hora local
- **WHEN** cuando una recepcionista lo reprograma a `inicio` 2026-10-12T10:00-03:00
- **THEN** entonces la respuesta es `200`, el recordatorio anterior sigue `fallido` con `intentos` 3 y el turno tiene además un recordatorio `pendiente`, nuevo, con `programado_para` 2026-10-11T13:00Z e `intentos` 0

### Requirement: Atomicidad del recordatorio con el cambio del turno
La creación, cancelación o reprogramación del recordatorio MUST ocurrir en la misma transacción que el cambio del turno y su registro de auditoría: si el recordatorio no puede registrarse, el cambio del turno MUST revertirse por completo. Una operación rechazada MUST NOT crear ni modificar recordatorios (05 §Excepciones globales; 08 §Patrones aplicados, unidad de trabajo turno + auditoría + recordatorio).

#### Scenario: Falla del recordatorio revierte el alta
- **GIVEN** dado que la base rechaza el registro del recordatorio y que el reloj marca 2026-10-07 09:00 hora local
- **WHEN** cuando se intenta crear un turno con inicio 2026-10-09T09:00-03:00 (48 h después)
- **THEN** entonces, a nivel de caso de uso, se lanza el error de integridad de la base (no se define respuesta HTTP para esta falla), y no quedan ni el turno, ni su registro de auditoría, ni ningún recordatorio

#### Scenario: Falla del recordatorio revierte la reprogramación
- **GIVEN** dado un turno `programado` con inicio 2026-10-09 10:00 hora local y su recordatorio `pendiente`, que la base rechaza el registro del recordatorio nuevo y que el reloj marca 2026-10-07 09:00 hora local
- **WHEN** cuando se intenta reprogramarlo a `inicio` 2026-10-12T15:00-03:00
- **THEN** entonces, a nivel de caso de uso, se lanza el error de integridad de la base (no se define respuesta HTTP para esta falla), el turno conserva su inicio 2026-10-09 10:00 hora local, su recordatorio original sigue `pendiente` con el mismo id y el mismo `programado_para`, y no queda ningún recordatorio nuevo

#### Scenario: Operaciones rechazadas no tocan recordatorios
- **GIVEN** dado un turno `programado` con inicio 2026-10-09 10:00 hora local y su recordatorio `pendiente` con `programado_para` 2026-10-08T13:00Z, y que el reloj marca 2026-10-07 09:00 hora local
- **WHEN** cuando se intenta un alta que solapa con él (`409`), una reprogramación con `duracion_min` 7 (`422`) y, después de cancelarlo con éxito, una segunda cancelación (`409 turno_ya_cancelado`)
- **THEN** entonces las tres operaciones se rechazan; después del `409` y del `422` el recordatorio sigue `pendiente` con el mismo id y el mismo `programado_para`; después de la segunda cancelación sigue `cancelado`; y la cantidad de recordatorios del turno no cambia en ninguna de las tres

### Requirement: Encolado después de confirmar el cambio
Cada recordatorio `pendiente` nuevo MUST publicarse en la cola de recordatorios de Redis, con vencimiento en su `programado_para`, solo después de confirmada la transacción. Si la cola no responde, la operación sobre el turno MUST responder igual con éxito y el recordatorio MUST quedar `pendiente` en la base. Una operación rechazada MUST NOT publicar nada (Flujo 6, errores).

#### Scenario: Recordatorio encolado tras el alta
- **GIVEN** dado que el reloj marca 2026-10-07 09:00 hora local
- **WHEN** cuando una recepcionista crea un turno con inicio 2026-10-09T10:00-03:00
- **THEN** entonces la respuesta es `201` y la cola contiene el id del recordatorio creado con vencimiento 2026-10-08T13:00Z

#### Scenario: Recordatorio nuevo encolado tras reprogramar
- **GIVEN** dado un turno con inicio 2026-10-09 10:00 hora local y su recordatorio `pendiente` ya encolado, y que el reloj marca 2026-10-07 09:00 hora local
- **WHEN** cuando una recepcionista lo reprograma a `inicio` 2026-10-12T15:00-03:00
- **THEN** entonces la respuesta es `200` y la cola contiene el id del recordatorio nuevo con vencimiento 2026-10-11T18:00Z

#### Scenario: Cola no disponible al crear
- **GIVEN** dado que la cola de recordatorios no responde y que el reloj marca 2026-10-07 09:00 hora local
- **WHEN** cuando una recepcionista crea un turno con inicio 2026-10-09T10:00-03:00
- **THEN** entonces la respuesta es `201` y el recordatorio existe en la base con `estado` `pendiente`

#### Scenario: Cola no disponible al reprogramar
- **GIVEN** dado un turno `programado` con inicio 2026-10-09 10:00 hora local y su recordatorio `pendiente` con `programado_para` 2026-10-08T13:00Z, que la cola de recordatorios no responde y que el reloj marca 2026-10-07 09:00 hora local
- **WHEN** cuando una recepcionista lo reprograma a `inicio` 2026-10-12T15:00-03:00
- **THEN** entonces la respuesta es `200`, el recordatorio anterior queda `cancelado` y en la base existe un recordatorio `pendiente` nuevo con `programado_para` 2026-10-11T18:00Z

#### Scenario: Alta rechazada no encola
- **GIVEN** dado un turno existente del profesional A de 2026-10-09 10:00 a 10:45 hora local y que el reloj marca 2026-10-07 09:00 hora local
- **WHEN** cuando se intenta crear otro turno de A con inicio 2026-10-09T10:30-03:00 y la respuesta es `409`
- **THEN** entonces la cola no recibe ningún elemento nuevo

#### Scenario: Reprogramación rechazada no encola
- **GIVEN** dados dos turnos del profesional A, uno de 2026-10-09 10:00 a 10:45 hora local con su recordatorio `pendiente` ya encolado y otro de 2026-10-12 15:00 a 15:45 hora local, y que el reloj marca 2026-10-07 09:00 hora local
- **WHEN** cuando se intenta reprogramar el primero a `inicio` 2026-10-12T15:30-03:00 y la respuesta es `409`
- **THEN** entonces la cola no recibe ningún elemento nuevo y el recordatorio del primer turno sigue `pendiente` con el mismo id y el mismo `programado_para`

### Requirement: Cola de recordatorios con vencimiento
La cola MUST entregar un recordatorio recién cuando llega su vencimiento, en orden de vencimiento, y a un solo consumidor. Volver a encolar un recordatorio que ya está en la cola MUST reemplazar su vencimiento y MUST NOT duplicarlo. La cola MUST implementarse sobre Redis (DD-04; 08 §Patrones aplicados, cola de trabajo Redis + worker).

#### Scenario: Solo se entregan los vencidos, en orden
- **GIVEN** dados los recordatorios R1 con vencimiento 2026-10-08T13:05Z, R2 con 2026-10-08T13:00Z y R3 con 2026-10-08T14:00Z en la cola
- **WHEN** cuando un consumidor pide los vencidos a las 2026-10-08T13:10Z
- **THEN** entonces recibe R2 y R1, en ese orden, y R3 queda en la cola

#### Scenario: Un vencido se entrega una sola vez
- **GIVEN** dado un recordatorio vencido en la cola
- **WHEN** cuando dos consumidores piden los vencidos, uno después del otro
- **THEN** entonces solo el primero lo recibe

#### Scenario: Re-encolar reemplaza el vencimiento
- **GIVEN** dado un recordatorio en la cola con vencimiento 2026-10-08T13:00Z
- **WHEN** cuando se lo vuelve a encolar con vencimiento 2026-10-08T13:02Z y se piden los vencidos a las 2026-10-08T13:01Z y después a las 2026-10-08T13:02Z
- **THEN** entonces la primera consulta no lo entrega y la segunda lo entrega una sola vez

### Requirement: Envío del recordatorio vencido por el worker
El worker MUST tomar de la cola los recordatorios vencidos y, si el recordatorio sigue `pendiente` y su turno sigue `programado`, MUST invocar una vez el puerto de notificación con el adaptador configurado. Si el envío sale bien, MUST registrar `estado = enviado` e incrementar `intentos` (Flujo 6).

#### Scenario: Envío exitoso
- **GIVEN** dado un turno `programado` con inicio 2026-10-09 10:00 hora local y su recordatorio `pendiente` con `programado_para` 2026-10-08T13:00Z en la cola
- **WHEN** cuando el worker procesa la cola a las 2026-10-08T13:00Z
- **THEN** entonces el puerto de notificación se invoca exactamente una vez para ese recordatorio y el recordatorio queda `enviado` con `intentos` 1

#### Scenario: Recordatorio todavía no vencido
- **GIVEN** dado el mismo recordatorio `pendiente` en la cola con vencimiento 2026-10-08T13:00Z
- **WHEN** cuando el worker procesa la cola a las 2026-10-08T12:59Z
- **THEN** entonces el puerto de notificación no se invoca y el recordatorio sigue `pendiente` con `intentos` 0

#### Scenario: El adaptador mock registra el envío
- **GIVEN** dado `NOTIFICATION_ADAPTER=mock` y un recordatorio vencido de un turno `programado`
- **WHEN** cuando el worker lo procesa
- **THEN** entonces el adaptador mock registra el envío con el id del recordatorio y su contenido, sin contactar ningún servicio externo de mensajería

### Requirement: Sin envío para turnos cancelados ni recordatorios no pendientes
El worker MUST NOT invocar el puerto de notificación si el recordatorio ya no está `pendiente` o ya no existe, o si su turno no está `programado`. En el último caso, el recordatorio MUST pasar a `cancelado`. El estado se MUST verificar en la base, con el recordatorio bloqueado, en el momento del envío (Flujo 6, paso 1; RN-NO-02).

#### Scenario: Turno cancelado no envía
- **GIVEN** dado un recordatorio `pendiente` y vencido en la cola cuyo turno está `cancelado`
- **WHEN** cuando el worker lo procesa
- **THEN** entonces el puerto de notificación no se invoca y el recordatorio queda `cancelado` con `intentos` 0

#### Scenario: Recordatorio cancelado que seguía en la cola
- **GIVEN** dado un turno con su recordatorio encolado, que después se canceló por `POST /turnos/{id}/cancelar`
- **WHEN** cuando el worker procesa la cola al vencer el recordatorio
- **THEN** entonces el puerto de notificación no se invoca y el recordatorio sigue `cancelado` con `intentos` 0

#### Scenario: Recordatorio ya enviado encolado de nuevo
- **GIVEN** dado un recordatorio que el worker ya envió y que se vuelve a encolar vencido
- **WHEN** cuando el worker procesa la cola otra vez
- **THEN** entonces el puerto de notificación no se invoca de nuevo y el recordatorio sigue `enviado` con `intentos` 1

#### Scenario: Procesamiento simultáneo del mismo recordatorio
- **GIVEN** dado un recordatorio `pendiente` vencido de un turno `programado`, confirmado en la base
- **WHEN** cuando dos procesos del worker lo procesan al mismo tiempo
- **THEN** entonces el puerto de notificación se invoca exactamente una vez y el recordatorio queda `enviado` con `intentos` 1

#### Scenario: Recordatorio inexistente en la cola
- **GIVEN** dado un id de recordatorio vencido en la cola que no existe en la base
- **WHEN** cuando el worker procesa la cola
- **THEN** entonces el elemento se descarta sin invocar el puerto, el worker sigue procesando el resto y la cola ya no lo contiene

### Requirement: Reintentos con backoff exponencial y estado fallido
Si el envío falla, el worker MUST incrementar `intentos` y volver a encolar el recordatorio con un vencimiento que se duplica en cada intento (1 min y luego 2 min). Al completar 3 intentos fallidos, el recordatorio MUST quedar `fallido` y MUST NOT volver a encolarse. No hay reintento manual (RN-NO-05, DD-19).

#### Scenario: Primer intento fallido
- **GIVEN** dado un recordatorio `pendiente` vencido a las 2026-10-08T13:00Z de un turno `programado` y un puerto de notificación que falla
- **WHEN** cuando el worker lo procesa a las 2026-10-08T13:00Z
- **THEN** entonces el recordatorio sigue `pendiente` con `intentos` 1 y vuelve a la cola con vencimiento 2026-10-08T13:01Z

#### Scenario: Segundo intento fallido
- **GIVEN** dado el mismo recordatorio con `intentos` 1 y un puerto que sigue fallando
- **WHEN** cuando el worker lo procesa a las 2026-10-08T13:01Z
- **THEN** entonces el recordatorio sigue `pendiente` con `intentos` 2 y vuelve a la cola con vencimiento 2026-10-08T13:03Z

#### Scenario: Tercer intento fallido
- **GIVEN** dado el mismo recordatorio con `intentos` 2 y un puerto que sigue fallando
- **WHEN** cuando el worker lo procesa a las 2026-10-08T13:03Z
- **THEN** entonces el recordatorio queda `fallido` con `intentos` 3, no vuelve a la cola, y en total el puerto se invocó exactamente 3 veces

#### Scenario: Falla y después éxito
- **GIVEN** dado un recordatorio `pendiente` vencido y un puerto que falla la primera vez y responde bien la segunda
- **WHEN** cuando el worker lo procesa al vencer y otra vez al vencer el reintento
- **THEN** entonces el recordatorio queda `enviado` con `intentos` 2 y no vuelve a la cola

#### Scenario: Un recordatorio fallido no se reintenta
- **GIVEN** dado un recordatorio `fallido` con `intentos` 3 que se vuelve a encolar vencido
- **WHEN** cuando el worker procesa la cola
- **THEN** entonces el puerto de notificación no se invoca y el recordatorio sigue `fallido` con `intentos` 3

### Requirement: Contenido del recordatorio sin datos clínicos
El mensaje entregado al puerto de notificación MUST contener solo la fecha (`dd/mm/aaaa`) y la hora (`HH:MM`) de inicio del turno en `APP_TIMEZONE` y el nombre del consultorio (`CONSULTORIO_NOMBRE`), dirigido al paciente por su id. MUST NOT incluir la prestación, el profesional, el nombre o documento del paciente ni el motivo de una cancelación (RN-NO-04).

#### Scenario: Texto del recordatorio
- **GIVEN** dado `CONSULTORIO_NOMBRE` "Consultorio Odontológico Ejemplo" y un turno `programado` del paciente P con inicio 2026-10-09T13:00Z
- **WHEN** cuando el worker envía su recordatorio
- **THEN** entonces el mensaje está dirigido al id de P y su texto es exactamente "Recordatorio: tiene un turno el 09/10/2026 a las 10:00 en Consultorio Odontológico Ejemplo."

#### Scenario: Sin datos clínicos ni personales
- **GIVEN** dado un turno de la prestación "Limpieza" con el profesional "Ficticio Pérez" para la paciente ficticia "Ana Prueba" con DNI ficticio "30111222"
- **WHEN** cuando el worker envía su recordatorio
- **THEN** entonces el mensaje no contiene "Limpieza", "Pérez", "Ana", "Prueba" ni "30111222", ni el id de la prestación ni el del profesional

#### Scenario: Fecha y hora en la zona local
- **GIVEN** dado un inicio de turno 2026-10-10T02:00Z, que en `America/Argentina/Buenos_Aires` es el viernes 09/10/2026 a las 23:00
- **WHEN** cuando se arma el mensaje del recordatorio para ese inicio
- **THEN** entonces el texto informa la fecha "09/10/2026" y la hora "23:00"

### Requirement: Re-encolado de pendientes al iniciar el worker
Al iniciar, el worker MUST encolar todos los recordatorios en `pendiente` de la base, cada uno con vencimiento en su `programado_para`, antes de procesar la cola. Los recordatorios en otros estados MUST NOT encolarse. El re-encolado MUST ser idempotente (Flujo 6, errores).

#### Scenario: Pendientes perdidos por la cola se recuperan
- **GIVEN** dados en la base un recordatorio `pendiente` con `programado_para` 2026-10-08T13:00Z, otro `pendiente` con 2026-10-09T13:00Z, uno `cancelado`, uno `enviado` y uno `fallido`, y la cola vacía
- **WHEN** cuando el worker inicia
- **THEN** entonces la cola contiene exactamente los dos `pendiente`, con vencimientos 2026-10-08T13:00Z y 2026-10-09T13:00Z

#### Scenario: Re-encolado idempotente
- **GIVEN** dado un recordatorio `pendiente` que ya está en la cola
- **WHEN** cuando el worker inicia dos veces seguidas
- **THEN** entonces la cola contiene ese recordatorio una sola vez y el worker lo envía una sola vez al vencer

#### Scenario: Alta con la cola caída enviada después de reiniciar
- **GIVEN** dado un turno creado mientras la cola no respondía, con su recordatorio `pendiente` con `programado_para` 2026-10-08T13:00Z solo en la base
- **WHEN** cuando el worker inicia y procesa la cola a las 2026-10-08T13:00Z
- **THEN** entonces el recordatorio queda `enviado` con `intentos` 1

### Requirement: A lo sumo un recordatorio pendiente por turno
La base MUST rechazar un segundo recordatorio `pendiente` para el mismo turno, aunque la aplicación no lo valide. Un turno MUST poder tener a la vez varios recordatorios en `cancelado`, `enviado` o `fallido` (RN-NO-02; design D2, a registrar en DD-28).

#### Scenario: Segundo pendiente rechazado por la base
- **GIVEN** dado un turno con un recordatorio `pendiente`
- **WHEN** cuando se inserta directamente en la base otro recordatorio `pendiente` para ese turno
- **THEN** entonces la base rechaza la inserción con una violación de unicidad

#### Scenario: Históricos más un pendiente aceptados
- **GIVEN** dado un turno con dos recordatorios `cancelado` y uno `enviado`
- **WHEN** cuando se inserta directamente un recordatorio `pendiente` para ese turno
- **THEN** entonces la base acepta la inserción

### Requirement: Integridad del recordatorio en la base
La base MUST rechazar un recordatorio con `estado` distinto de `pendiente`, `enviado`, `fallido` o `cancelado`, `canal` distinto de `mock`, `intentos` fuera de 0..3, `fallido` sin 3 intentos, `enviado` sin al menos 1 intento, `turno_id` inexistente o `programado_para` nulo. Un turno con recordatorios MUST NOT poder borrarse (04 §Recordatorio, DD-08, DD-21; design D2, a registrar en DD-28).

#### Scenario: Valores inválidos rechazados
- **GIVEN** dado un turno existente
- **WHEN** cuando se inserta directamente un recordatorio con `estado` `borrador`, o con `canal` `whatsapp`, o con `intentos` 4, o con `intentos` -1, o `fallido` con `intentos` 2, o `enviado` con `intentos` 0, o con `programado_para` nulo
- **THEN** entonces la base rechaza cada inserción con una violación de CHECK o de NOT NULL

#### Scenario: Referencia al turno garantizada
- **GIVEN** dado un turno con un recordatorio
- **WHEN** cuando se inserta un recordatorio con un `turno_id` inexistente, o se borra el turno
- **THEN** entonces la base rechaza ambas operaciones con una violación de clave foránea

#### Scenario: Instante persistido en UTC
- **GIVEN** dado un recordatorio creado por el alta de un turno con inicio 2026-10-09T10:00-03:00
- **WHEN** cuando se lee `programado_para` directamente de la base
- **THEN** entonces es un `timestamptz` igual a 2026-10-08T13:00Z

### Requirement: Worker desplegado como servicio
`docker-compose.yml` MUST declarar un servicio `worker`, construido con la misma imagen que la API, que ejecute el proceso de recordatorios. El servicio MUST recibir `DATABASE_URL`, `REDIS_URL`, `APP_TIMEZONE`, `NOTIFICATION_ADAPTER`, `REMINDER_LEAD_HOURS` y `CONSULTORIO_NOMBRE`, depender de `db` y `redis`, y reiniciarse si el proceso termina. El worker MUST NOT recibir `JWT_SECRET`, porque no lo necesita (DD-04; 08 §Seguridad, mínimo privilegio; design D14, a registrar en DD-28).

#### Scenario: Servicio worker en Compose
- **WHEN** se inspecciona `docker-compose.yml`
- **THEN** existe el servicio `worker` con el mismo `build` que `api`, un comando que ejecuta el proceso de recordatorios, las seis variables de entorno, `depends_on` con `db` y `redis`, una política `restart` distinta de `no` y sin `JWT_SECRET` en su entorno

#### Scenario: El worker arranca sin el secreto de la API
- **WHEN** se carga la configuración del worker con las seis variables definidas y sin `JWT_SECRET` en el entorno
- **THEN** la carga es exitosa

#### Scenario: La API recibe la anticipación y el consultorio
- **WHEN** se inspecciona el servicio `api` de `docker-compose.yml`
- **THEN** recibe `REMINDER_LEAD_HOURS` y `CONSULTORIO_NOMBRE` además de las variables que ya tenía
