# ADR 0005: la pestaña Workbench y WhatsApp como conexión aplazada

- **Estado:** Aceptada
- **Fecha:** 2026-11-21

## Contexto
Quedaban abiertos el nombre de la tercera pestaña de la app (decisión 1) y el vínculo con WhatsApp (decisión 5).

## Decisión
- **La tercera pestaña se llama Workbench.** Las pestañas son Estado, Casa y Workbench (`app/lib/main.dart`).
- **WhatsApp es una conexión adicional y queda aplazada.** Más adelante Ashur podrá escribirle a Sergio por WhatsApp
  como un bot, pero la conversación, las llamadas y las notificaciones pasan dentro de la app. Hoy no se configura
  nada.

## Pendiente
- **Vía para el bot de WhatsApp:** la API oficial de WhatsApp Business (Cloud API) o un cliente no oficial, que
  arriesga el bloqueo de la cuenta. Se decide cuando se configure.
