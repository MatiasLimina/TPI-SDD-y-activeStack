# Casos de borde por dominio

Lista de casos a **buscar** en el spec. No son reglas nuevas: cada caso cita de dónde sale. Si un caso no
tiene fuente en la KB para el comportamiento esperado, el hallazgo es una pregunta abierta, no un
escenario con respuesta inventada.

## Agenda y turnos (RN-AG) — C-03, C-04, C-05, C-10, C-11, C-13
- Turno contiguo a otro (`fin` A = `inicio` B): válido (RN-AG-03).
- Solape de un minuto por profesional, por sillón y por paciente, cada uno por separado (RN-AG-01/02/14).
- Turno cancelado en el mismo horario: no cuenta (RN-AG-07).
- Duración 480 aceptada, 485 rechazada, 0 rechazada, no múltiplo de 5 rechazada (RN-AG-04, DD-15).
- Inicio no alineado a 5 min, con segundos o microsegundos (DD-15).
- Inicio en el pasado o exactamente ahora (RN-AG-12).
- Prestación que no requiere sillón con `sillon_id` informado -> 422 (RN-AG-10, DD-21).
- Reprogramar solapándose consigo mismo: válido (RN-AG-08).
- Dos requests concurrentes al mismo hueco: uno gana, el otro 409 (RN-AG-09, DD-18).

## Autenticación y roles (RN-AU) — C-06 y los changes que protegen endpoints
Fuentes: `03_actores_y_roles.md`, `05_reglas_de_negocio.md` §RN-AU, `07_flujos_principales.md` §Flujo 1,
`08_arquitectura_propuesta.md` §Seguridad, DD-05, DD-16, scope de C-06 en `CHANGES.md`.
- Credenciales inválidas: email inexistente **y** contraseña incorrecta, por separado. Ambos `401`. Si el
  spec no exige la misma respuesta para los dos, señalarlo como pregunta abierta (evita enumerar
  usuarios), no como regla.
- Token vencido -> `401` (Flujo 1). Borde: token que vence en el instante del request; requiere reloj fijo.
- Token con firma alterada, malformado, o firmado con otro algoritmo (`none`): rechazado. Código no fijado
  por la KB (convención HTTP: `401`); confirmarlo como DD del change o dejarlo como pregunta abierta.
- Request sin header `Authorization` a un endpoint protegido: mismo caso; la convención es `401`, pero
  según la versión `HTTPBearer` de FastAPI respondió `403`, así que hace falta decisión explícita.
- Rol insuficiente: `odontologo` intentando crear, cancelar o reprogramar turnos -> `403` (scope C-06).
- Cada endpoint protegido tiene su par de escenarios permitido/prohibido por rol (matriz de
  `03_actores_y_roles.md`).
- `creado_por` se puebla con el usuario del token al crear turno (scope C-06).
- Usuario `activo = false` no inicia sesión (scope C-06 en `CHANGES.md`; la baja lógica es DD-16). El código
  de respuesta no está fijado: pregunta abierta. Pregunta abierta típica: ¿qué pasa con un token
  emitido **antes** de la desactivación?
- Rol `odontologo` sin `profesional_id` -> rechazado al dar de alta (scope C-06).
- Email único: alta duplicada por CLI rechazada (`04_modelo_de_datos.md` §Usuario, scope C-06).
- Contraseña guardada como hash (bcrypt/argon2), nunca en claro (08 §Seguridad).
- `JWT_SECRET` y `JWT_EXPIRE_MINUTES` por entorno; `.env.example` solo con placeholders (RN-CU-03).
- **Fuera de C-06** (no pedirlos): auditoría de acciones (C-07), filtrado de agenda del odontólogo
  (C-13), bloqueos propios (C-11), rol administrador (DD-05). Refresh tokens: la KB no los menciona; si el
  spec los agrega, es scope nuevo y requiere justificación.

## Notificaciones (RN-NO) — C-12
- Turno creado con exactamente 24 h de anticipación, y con 23 h 59 min (RN-NO-03, DD-13).
- Reprogramar de más de 24 h a menos de 24 h: el recordatorio se cancela (RN-NO-02 + RN-NO-03).
- Tercer reintento fallido -> `fallido`, sin cuarto intento (RN-NO-05, DD-19).
- Turno cancelado entre el encolado y el envío: no se envía (scope C-12).
- Contenido sin prestación ni datos clínicos (RN-NO-04).

## Recursos, pacientes, horarios y bloqueos — C-08 a C-11
- Recurso desactivado: no admite turnos nuevos, conserva los existentes (scope C-08).
- Franja de horario: borde exacto de fin, intervalo que cruza dos franjas (scope C-10).
- Bloqueo sobre turnos activos -> 409 con la lista de turnos (RN-HB-03); turno que empieza al terminar
  un bloqueo, válido (RN-AG-06).
