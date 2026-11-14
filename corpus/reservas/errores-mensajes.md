# Códigos de error y mensajes

Cada error del sistema se identifica con un código y se muestra con un mensaje exacto.

Autenticación y registro:

- AUTH-001 (credenciales incorrectas): "Correo o contraseña incorrectos."
- AUTH-002 (cuenta bloqueada): "Cuenta bloqueada temporalmente. Intenta de nuevo en 15 minutos."
- REG-001 (dominio del correo): "El correo debe pertenecer al dominio horizonte.example."
- REG-002 (correo duplicado): "El correo ya está registrado."
- REG-003 (contraseña): "La contraseña debe tener entre 8 y 64 caracteres, con mayúscula, minúscula y dígito."

Creación de reservas:

- RES-001 (horario): "Horario fuera del rango permitido."
- RES-002 (duración): "La duración debe ser de 30 a 240 minutos, en bloques de 30."
- RES-003 (anticipación mínima): "La reserva requiere al menos 60 minutos de anticipación."
- RES-004 (anticipación máxima): "La reserva excede la anticipación máxima permitida para tu rol."
- RES-005 (capacidad): "El número de asistentes excede la capacidad de la sala."
- RES-006 (solapamiento): "La sala ya está reservada en ese horario."
- RES-007 (sala no permitida): "Tu rol no puede reservar esta sala."

Cuotas, suspensión y estado de la reserva:

- RES-008 (reservas activas): "Alcanzaste el máximo de reservas activas."
- RES-009 (horas semanales): "Superarías tu límite semanal de horas."
- RES-010 (suspensión): "Tu cuenta está suspendida para reservar hasta el {fecha}."
- RES-011 (transición inválida): "Esa operación no está permitida en el estado actual de la reserva."
- RES-012 (modificación tardía): "Solo puedes modificar la reserva con 24 horas o más de antelación."
