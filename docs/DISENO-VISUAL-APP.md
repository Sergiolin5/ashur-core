# Dirección visual de la app Ashur

## Identidad aprobada

- Elegancia tecnológica etérea, con precisión de instrumento.
- Interfaz oscura, adaptable a Mac y móvil.
- Azul y plata como paleta principal; brillos cian equilibrados en focos y estados activos.
- Vidrio oscuro, bordes metálicos finos y esquinas suavemente redondeadas.
- Marca abstracta de núcleo y órbitas. Sans serif para controles y texto; serif en el nombre y títulos grandes.
- Galaxia solo en Inicio. Chat y paneles conservan fondos oscuros limpios.
- El chat usa pequeños acentos ámbar para aportar calidez.
- La respuesta táctil combina cambio nítido y halo suave; iconos geométricos se rellenan al activarse.
- En Mac hay una burbuja flotante discreta por encima de otras ventanas; al tocarla, Ashur pasa al frente. En móvil,
  la presencia de Ashur vive dentro de la app.

## Referencia Roamies

Repo público: <https://github.com/KenKaiii/Roamies> (AGPL-3.0).

Se toma como referencia de interacción la presencia de un compañero persistente, respuestas contextuales y paneles
compactos. Ashur traduce esa presencia al núcleo abstracto elegido por Sergio; no adopta criatura pixel art ni copia
código, ilustraciones, marca o recursos del proyecto. Roamies está construido con Tauri, JavaScript y Rust; Ashur
mantiene su cliente Flutter multiplataforma.

## Límites de esta primera pasada

El cliente actual aún tiene Chat, Casa y Workbench como pantallas vacías (`app/lib/main.dart`). La capa visual puede
darles identidad y estados vacíos, pero no debe inventar funciones que el cliente o el core no implementan. La
burbuja flotante de macOS se dibuja con AppKit, sin paquetes nuevos. Trae la ventana Flutter principal al frente; no
simula un chat compacto porque el cliente aún no tiene chat implementado. El botón de cierre oculta la burbuja.

## Tokens iniciales

Los valores concretos de color son una base de implementación y pueden ajustarse al revisar la app en pantalla:

| Token | Valor |
| --- | --- |
| Fondo | `#05060B` |
| Superficie | `#111520` |
| Superficie elevada | `#171D2A` |
| Texto | `#E8EDF5` |
| Plata | `#C9D2E0` |
| Azul | `#5C9FC7` |
| Cian | `#3CC7E6` |
| Ámbar del chat | `#D8A977` |
