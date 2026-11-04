## ADDED Requirements

### Requirement: Sin envío para turnos ya iniciados
El worker MUST NOT invocar el puerto de notificación si, al verificar el recordatorio bloqueado, el inicio del turno es igual o anterior al momento de la verificación según el reloj (`inicio <= ahora`, el mismo criterio de "iniciado" que RN-AG-13 y DD-23). En ese caso el recordatorio `pendiente` MUST pasar a `cancelado` conservando sus `intentos` y MUST NOT volver a encolarse (design D1, a registrar en DD-29).

#### Scenario: Turno que empieza en el momento de procesar
- **GIVEN** dado un turno `programado` con inicio 2026-10-09T13:00Z y su recordatorio `pendiente`, vencido, con `intentos` 0 en la cola
- **WHEN** cuando el worker lo procesa con el reloj en 2026-10-09T13:00Z
- **THEN** entonces el puerto de notificación no se invoca, el recordatorio queda `cancelado` con `intentos` 0 y la cola ya no lo contiene

#### Scenario: Recordatorio atrasado que todavía llega antes del inicio
- **GIVEN** dado un turno `programado` con inicio 2026-10-09T13:00Z y su recordatorio `pendiente` con `programado_para` 2026-10-08T13:00Z en la cola
- **WHEN** cuando el worker lo procesa con el reloj en 2026-10-09T12:59Z, un minuto antes del inicio
- **THEN** entonces el puerto de notificación se invoca exactamente una vez y el recordatorio queda `enviado` con `intentos` 1

#### Scenario: Recordatorio re-encolado después de una caída larga
- **GIVEN** dado un turno `programado` con inicio 2026-10-09T13:00Z y su recordatorio `pendiente` con `programado_para` 2026-10-08T13:00Z solo en la base, porque Redis y el worker estuvieron caídos más de 24 h
- **WHEN** cuando el worker inicia y procesa la cola con el reloj en 2026-10-09T15:00Z
- **THEN** entonces el puerto de notificación no se invoca y el recordatorio queda `cancelado` con `intentos` 0

#### Scenario: Reintento pendiente de un turno ya iniciado
- **GIVEN** dado un turno `programado` con inicio 2026-10-09T13:00Z y su recordatorio `pendiente` con `intentos` 1 y `programado_para` 2026-10-08T13:01Z en la cola
- **WHEN** cuando el worker lo procesa con el reloj en 2026-10-09T13:05Z
- **THEN** entonces el puerto de notificación no se invoca y el recordatorio queda `cancelado` con `intentos` 1

### Requirement: Devolución a la cola de lo tomado y no procesado
Si el procesamiento de un recordatorio tomado de la cola termina con un error que no es una falla del envío, el worker MUST devolver a la cola, antes de terminar, los recordatorios que tomó en ese ciclo y no llegó a procesar, con vencimiento en el momento en que los tomó, y MUST propagar el error original aunque la devolución falle. El recordatorio del error MUST NOT devolverse: se recupera de la base al reiniciar (design D4, a registrar en DD-29).

#### Scenario: Error a mitad de lote
- **GIVEN** dados los recordatorios `pendiente` R1, R2 y R3, de turnos `programado`, vencidos a las 2026-10-08T13:00Z, 13:01Z y 13:02Z en la cola, un puerto de notificación que falla solo con R2 y una cola que rechaza con un error de conexión el reintento de R2 y acepta el resto de las operaciones
- **WHEN** cuando el worker procesa la cola con el reloj en 2026-10-08T13:05Z
- **THEN** entonces el error de la cola se propaga fuera del ciclo; R1 queda `enviado` con `intentos` 1; R2 queda `pendiente` con `intentos` 1 y `programado_para` 2026-10-08T13:06Z en la base y no está en la cola; y R3 sigue `pendiente` con `intentos` 0 y está de nuevo en la cola con vencimiento 2026-10-08T13:05Z

#### Scenario: La devolución también falla
- **GIVEN** dados los mismos R1, R2 y R3 y un puerto que falla solo con R2, pero una cola que rechaza toda operación de encolado a partir del reintento de R2
- **WHEN** cuando el worker procesa la cola con el reloj en 2026-10-08T13:05Z y después se reinicia con la cola disponible
- **THEN** entonces el error que se propaga fuera del ciclo es el del reintento de R2; R3 sigue `pendiente` con `intentos` 0 en la base; y al reiniciar la cola contiene R2 con vencimiento 2026-10-08T13:06Z y R3 con vencimiento 2026-10-08T13:02Z

### Requirement: La API depende de Redis en Compose
El servicio `api` de `docker-compose.yml` MUST depender de `redis` con la condición `service_started`, la misma que usa el `worker`, además de depender de `db` con la condición `service_healthy`, porque la API publica los recordatorios en la cola (design D8).

#### Scenario: La API espera a Redis
- **WHEN** se inspecciona el servicio `api` de `docker-compose.yml`
- **THEN** su `depends_on` incluye `db` con la condición `service_healthy` y `redis` con la condición `service_started`

## MODIFIED Requirements

### Requirement: Envío del recordatorio vencido por el worker
El worker MUST tomar de la cola los recordatorios vencidos y, si el recordatorio sigue `pendiente`, su turno sigue `programado` y el turno todavía no inició, MUST invocar una vez el puerto de notificación con el adaptador configurado. Si el envío sale bien, MUST registrar `estado = enviado` e incrementar `intentos`. El adaptador mock MUST NOT acumular en memoria los mensajes enviados (Flujo 6; design D6).

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
- **THEN** entonces el adaptador mock registra el envío en el log con el id del recordatorio y su contenido, sin guardar el mensaje en memoria y sin contactar ningún servicio externo de mensajería

#### Scenario: Envíos repetidos no acumulan estado en el adaptador mock
- **GIVEN** dado el adaptador mock recién creado
- **WHEN** cuando envía 1000 mensajes de recordatorio
- **THEN** entonces su estado interno es igual al que tenía antes del primer envío

### Requirement: Reintentos con backoff exponencial y estado fallido
Si el envío falla, el worker MUST incrementar `intentos`, registrar en `programado_para` el próximo intento (el instante de la falla según el reloj en ese momento, más una espera que se duplica: 1 min y luego 2 min) y volver a encolar el recordatorio con ese vencimiento. Al completar 3 intentos fallidos, MUST quedar `fallido`, con `programado_para` sin cambios, y MUST NOT volver a encolarse. Sin reintento manual (RN-NO-05, DD-19; design D2, a registrar en DD-29).

#### Scenario: Primer intento fallido
- **GIVEN** dado un recordatorio `pendiente` vencido a las 2026-10-08T13:00Z de un turno `programado` y un puerto de notificación que falla
- **WHEN** cuando el worker lo procesa a las 2026-10-08T13:00Z
- **THEN** entonces el recordatorio sigue `pendiente` con `intentos` 1 y `programado_para` 2026-10-08T13:01Z en la base, y vuelve a la cola con vencimiento 2026-10-08T13:01Z

#### Scenario: Segundo intento fallido
- **GIVEN** dado el mismo recordatorio con `intentos` 1 y un puerto que sigue fallando
- **WHEN** cuando el worker lo procesa a las 2026-10-08T13:01Z
- **THEN** entonces el recordatorio sigue `pendiente` con `intentos` 2 y `programado_para` 2026-10-08T13:03Z en la base, y vuelve a la cola con vencimiento 2026-10-08T13:03Z

#### Scenario: Tercer intento fallido
- **GIVEN** dado el mismo recordatorio con `intentos` 2 y un puerto que sigue fallando
- **WHEN** cuando el worker lo procesa a las 2026-10-08T13:03Z
- **THEN** entonces el recordatorio queda `fallido` con `intentos` 3 y `programado_para` 2026-10-08T13:03Z, no vuelve a la cola, y en total el puerto se invocó exactamente 3 veces

#### Scenario: Falla y después éxito
- **GIVEN** dado un recordatorio `pendiente` vencido y un puerto que falla la primera vez y responde bien la segunda
- **WHEN** cuando el worker lo procesa al vencer y otra vez al vencer el reintento
- **THEN** entonces el recordatorio queda `enviado` con `intentos` 2 y no vuelve a la cola

#### Scenario: Un recordatorio fallido no se reintenta
- **GIVEN** dado un recordatorio `fallido` con `intentos` 3 que se vuelve a encolar vencido
- **WHEN** cuando el worker procesa la cola
- **THEN** entonces el puerto de notificación no se invoca y el recordatorio sigue `fallido` con `intentos` 3

#### Scenario: La espera se cuenta desde el momento de la falla
- **GIVEN** dados los recordatorios `pendiente` R1 y R2, de turnos `programado`, vencidos a las 2026-10-08T13:00Z en la cola, un puerto que envía bien R1 y falla con R2, y un reloj que marca 2026-10-08T13:00:00Z cuando el worker toma los vencidos y 2026-10-08T13:00:40Z cuando falla el envío de R2
- **WHEN** cuando el worker procesa ese lote
- **THEN** entonces R2 queda `pendiente` con `intentos` 1 y `programado_para` 2026-10-08T13:01:40Z, y vuelve a la cola con vencimiento 2026-10-08T13:01:40Z

### Requirement: Re-encolado de pendientes al iniciar el worker
Al iniciar, el worker MUST encolar todos los recordatorios en `pendiente` de la base, cada uno con vencimiento en su `programado_para`, que es el próximo intento programado, antes de procesar la cola: así un reintento conserva su espera. Los recordatorios en otros estados MUST NOT encolarse. El re-encolado MUST ser idempotente (Flujo 6, errores; design D2, a registrar en DD-29).

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

#### Scenario: El reinicio conserva la espera del reintento
- **GIVEN** dado un recordatorio `pendiente` de un turno `programado` cuyo primer intento falló a las 2026-10-08T13:00Z, con `intentos` 1 y `programado_para` 2026-10-08T13:01Z en la base, la cola vacía y un puerto que ahora responde bien
- **WHEN** cuando el worker inicia y procesa la cola a las 2026-10-08T13:00:30Z y otra vez a las 2026-10-08T13:01Z
- **THEN** entonces en el primer procesamiento el puerto no se invoca y el recordatorio sigue `pendiente` con `intentos` 1, y en el segundo se invoca una vez y el recordatorio queda `enviado` con `intentos` 2

### Requirement: Integridad del recordatorio en la base
La base MUST rechazar un recordatorio con `estado` distinto de `pendiente`, `enviado`, `fallido` o `cancelado`, `canal` distinto de `mock`, `intentos` fuera de 0..3, `fallido` sin 3 intentos, `enviado` sin al menos 1 intento, `pendiente` con 3 intentos, `turno_id` inexistente o `programado_para` nulo. Un turno con recordatorios MUST NOT poder borrarse (04 §Recordatorio, DD-08, DD-21; design D2, a registrar en DD-28; design D3, a registrar en DD-29).

#### Scenario: Valores inválidos rechazados
- **GIVEN** dado un turno existente
- **WHEN** cuando se inserta directamente un recordatorio con `estado` `borrador`, o con `canal` `whatsapp`, o con `intentos` 4, o con `intentos` -1, o `fallido` con `intentos` 2, o `enviado` con `intentos` 0, o `pendiente` con `intentos` 3, o con `programado_para` nulo
- **THEN** entonces la base rechaza cada inserción con una violación de CHECK o de NOT NULL

#### Scenario: Un pendiente no llega a 3 intentos
- **GIVEN** dado un recordatorio `pendiente` con `intentos` 2
- **WHEN** cuando se actualiza directamente en la base a `intentos` 3 sin cambiar el `estado`, y por otro lado a `intentos` 3 con `estado` `fallido`
- **THEN** entonces la base rechaza la primera actualización con una violación de CHECK y acepta la segunda

#### Scenario: Restricción reversible
- **GIVEN** dada la base en la última migración
- **WHEN** cuando se revierte la migración que agrega la restricción de los pendientes, se inserta un recordatorio `pendiente` con `intentos` 3 y se la vuelve a aplicar sobre una base sin ese dato
- **THEN** entonces con la migración revertida la base acepta la inserción, y con la migración aplicada de nuevo la vuelve a rechazar

#### Scenario: Referencia al turno garantizada
- **GIVEN** dado un turno con un recordatorio
- **WHEN** cuando se inserta un recordatorio con un `turno_id` inexistente, o se borra el turno
- **THEN** entonces la base rechaza ambas operaciones con una violación de clave foránea

#### Scenario: Instante persistido en UTC
- **GIVEN** dado un recordatorio creado por el alta de un turno con inicio 2026-10-09T10:00-03:00
- **WHEN** cuando se lee `programado_para` directamente de la base
- **THEN** entonces es un `timestamptz` igual a 2026-10-08T13:00Z

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

#### Scenario: Consumidores simultáneos no comparten elementos
- **GIVEN** dados 50 recordatorios vencidos en la cola
- **WHEN** cuando dos consumidores piden los vencidos al mismo tiempo, varias veces, hasta vaciarla
- **THEN** entonces cada recordatorio se entrega a exactamente uno de los dos y entre ambos reciben los 50
