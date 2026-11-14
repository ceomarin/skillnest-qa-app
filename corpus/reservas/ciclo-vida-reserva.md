# Ciclo de vida de una reserva

Una reserva puede estar en uno de cinco estados: pendiente, confirmada, cancelada, completada o no_asistida.

Transiciones permitidas:

- De pendiente a confirmada: un administrador la aprueba.
- De pendiente a cancelada: el usuario la cancela o un administrador la rechaza.
- De confirmada a cancelada: el usuario o un administrador la cancela.
- De confirmada a completada: el usuario hizo check-in y la reserva terminó.
- De confirmada a no_asistida: no hubo check-in a los 15 minutos del inicio.

Cualquier otra transición se rechaza. Los estados cancelada, completada y no_asistida son finales: no se pueden modificar ni reactivar.

El check-in se permite desde 10 minutos antes hasta 15 minutos después de la hora de inicio de la reserva.

Solo se pueden modificar las reservas pendientes o confirmadas, y únicamente con 24 horas o más de antelación al inicio. Al modificar el horario se vuelven a validar el horario permitido, la duración, la anticipación, la capacidad y la ausencia de solapamientos.
