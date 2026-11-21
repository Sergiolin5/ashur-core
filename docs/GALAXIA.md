# La galaxia: glosario visual

La pantalla de inicio de Ashur es una galaxia viva: cada elemento que se ve representa algo real de Ashur. El estado
de la galaxia es un contrato de datos (`contracts/galaxy-state.schema.json`). El core lo produce y el cliente solo lo
dibuja, sin inventar valores.

## Glosario

| Elemento | Qué representa | Cómo se comporta |
| --- | --- | --- |
| **Núcleo** | Ashur y sus memorias. | Está en el centro de la galaxia. Tocarlo abre el chat. |
| **Electrones** | Los agentes. | Orbitan cerca del núcleo. |
| **Planetas** | Las habilidades y los módulos. | Su masa y su tamaño crecen según la importancia que Ashur aprendió. |
| **Asteroides** | Los bloqueos. | Orbitan el planeta que bloquean: un módulo caído, un permiso que falta, una duda sin respuesta. |
| **Estrellas fugaces** | Los mensajes y el texto aprendido en tiempo real. | Viajan de un origen a un destino. Al llegar alimentan un planeta, crean uno nuevo o se transforman. |
| **Brazos espirales de polvo** | El tiempo que Ashur lleva aprendiendo. | Giran sin parar, y su densidad crece con el tiempo. |

## Reglas
1. Tocar el núcleo abre el chat.
2. El tamaño de un planeta y el radio de su órbita se derivan solo de su masa.
3. Cada estrella fugaz corresponde a un evento del contrato, con su `origen` y su `destino`.

## Modelo matemático
Esta sección traduce el glosario a fórmulas para que el dibujo sea predecible. Las constantes marcadas como
**parámetros** son del cliente; sus valores se fijan en la fase 2 y se registran en `docs/adr/0002-render-galaxia.md`.

### Notación
| Símbolo | Significado | Origen |
| --- | --- | --- |
| $m_i$ | Masa del cuerpo $i$ ($m_i \ge 0$). | Campo `masa` del contrato. |
| $\varphi_i$ | Fase inicial de su órbita ($0 \le \varphi_i \le 1$, en fracciones de vuelta). | Campo `orbita.fase`. |
| $\mathbf{c}_i$ | Posición del cuerpo alrededor del cual orbita. | Campo `orbita.centro`. |
| $t$ | Tiempo de animación, en segundos. | Reloj del cliente. |
| $R_{\min}, R_{\max}$ | Radios mínimo y máximo de un planeta en pantalla. | Parámetros. |
| $d_{\min}, d_{\max}$ | Distancias mínima y máxima de una órbita al núcleo. | Parámetros. |

### Masa normalizada
La masa de cada planeta se compara con la del planeta más pesado, para que la galaxia ocupe siempre la pantalla sin
importar la escala de las masas:

$$
\hat{m}_i = \frac{m_i}{\max_j m_j} \in [0, 1]
$$

donde $j$ recorre solo los planetas.

### Tamaño de un planeta
El **área** del planeta es proporcional a su masa, así que el radio crece con la raíz cuadrada:

$$
R_i = R_{\min} + \left(R_{\max} - R_{\min}\right)\sqrt{\hat{m}_i}
$$

Así un planeta con el doble de masa ocupa el doble de área, no el cuádruple.

### Radio de la órbita
Los planetas más importantes orbitan más cerca del núcleo:

$$
d_i = d_{\min} + \left(d_{\max} - d_{\min}\right)\left(1 - \hat{m}_i\right)
$$

### Posición en la órbita
Cada cuerpo gira alrededor de su centro $\mathbf{c}_i$. Su ángulo avanza con el tiempo a partir de su fase inicial:

$$
\theta_i(t) = 2\pi\left(\varphi_i + \frac{t}{T_i}\right),
\qquad
\mathbf{p}_i(t) = \mathbf{c}_i + d_i\begin{pmatrix}\cos\theta_i(t)\\ \sin\theta_i(t)\end{pmatrix}
$$

Todos los planetas tienen el mismo periodo, así que giran a la misma velocidad angular (decisión de Sergio,
2026-11-21):

$$
T_i = T_0, \qquad \dot{\theta}_i = \frac{2\pi}{T_0}
$$

con $T_0$ como parámetro. La galaxia gira entonces como un disco: los planetas no cambian de posición entre sí.
Los electrones y los asteroides usan las mismas fórmulas con sus propias distancias y periodos, cortos y fijos,
porque orbitan muy cerca de su centro (el núcleo o el planeta que bloquean).

### Estrellas fugaces
Una estrella fugaz sale del cuerpo `origen` en el instante $t_0$ y llega al cuerpo `destino` tras una duración
$\tau$ (parámetro). Con el avance $s \in [0, 1]$:

$$
s(t) = \min\!\left(1,\ \frac{t - t_0}{\tau}\right),
\qquad
\mathbf{e}(t) = \left(1 - s\right)\mathbf{p}_{\text{origen}}(t) + s\,\mathbf{p}_{\text{destino}}(t)
$$

Como los dos extremos se mueven, la estrella persigue a su destino en lugar de ir hacia donde estaba. Cuando
$s = 1$ el evento termina según su `tipo`: `llega` alimenta el planeta, `crea` hace aparecer el planeta destino y
`transforma` convierte la estrella en otra cosa.

### Brazos espirales de polvo
Cada uno de los $N$ brazos es una espiral logarítmica que gira lentamente con velocidad angular $\omega$:

$$
r_k(\theta) = a\,e^{b\theta},
\qquad
\theta \mapsto \theta + \frac{2\pi k}{N} + \omega t,
\qquad
k = 0, 1, \dots, N - 1
$$

con $a$, $b$, $N$ y $\omega$ como parámetros. La densidad del polvo crece con el tiempo de aprendizaje $t_A$ y se
satura, para que la galaxia nunca se llene del todo:

$$
\rho(t_A) = \rho_0 + \left(\rho_{\max} - \rho_0\right)\left(1 - e^{-t_A / \lambda}\right)
$$

donde $\lambda$ marca qué tan rápido se llena. El contrato todavía no trae $t_A$; está anotado en
`docs/DECISIONES-ABIERTAS.md`.
