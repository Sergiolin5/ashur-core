# La galaxia: glosario visual

La pantalla de inicio de Ashur es una galaxia viva: cada elemento que se ve representa algo real de Ashur. El estado
de la galaxia es un contrato de datos (`contracts/galaxy-state.schema.json`). El core lo produce y el cliente solo lo
dibuja, sin inventar valores.

## Glosario

| Elemento | Qué representa | Cómo se comporta |
| --- | --- | --- |
| **Núcleo** | Ashur y sus recuerdos. | Está en el centro de la galaxia. Tocarlo abre el chat. Los recuerdos no son cuerpos uno por uno: dan masa al núcleo y hacen crecer el polvo. |
| **Electrones** | Los agentes. | Orbitan cerca del núcleo. |
| **Planetas** | Las habilidades, los módulos y las colecciones del core (Identidades, Objetos). | Su masa y su tamaño crecen según la importancia que Ashur aprendió. |
| **Personajes** | Las identidades (personas y mascotas) que viven en el planeta Identidades. | Están sobre su planeta y se ven al acercarse. |
| **Lunas** | Una identidad que se volvió importante. | Orbita el planeta Identidades. |
| **Asteroides** | Los bloqueos. | Orbitan el planeta que bloquean: un módulo caído, un permiso que falta, una duda sin respuesta. |
| **Estrellas fugaces** | Los mensajes y el texto aprendido en tiempo real. | Viajan de un origen a un destino. Al llegar alimentan un planeta, crean uno nuevo o se transforman. |
| **Brazos espirales de polvo** | Lo que Ashur lleva aprendiendo: el tiempo y los recuerdos. | Giran sin parar, y su densidad crece un poco con el tiempo y sobre todo con los recuerdos. |

## Reglas
1. Tocar el núcleo abre el chat.
2. El tamaño de un planeta y el radio de su órbita se derivan solo de su masa.
3. Cada estrella fugaz corresponde a un evento del contrato, con su `origen` y su `destino`.
4. Cada cuerpo que representa una cosa real del sistema la nombra en `ref`, con su tipo y su id.
5. Las escalas son como en la vida real: todo está muy lejos, y se ve más al acercarse (ver «Zoom y nivel de detalle»).

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

con $a$, $b$, $N$ y $\omega$ como parámetros. La densidad del polvo tiene dos fuentes, cada una con su propio
tope para que la galaxia nunca se llene del todo:

$$
\rho = \rho_0
+ \Delta_t\left(1 - e^{-t_A/\tau}\right)
+ \Delta_R\left(1 - e^{-n_R/m}\right),
\qquad
\Delta_t \ll \Delta_R,
\qquad
\Delta_t + \Delta_R = \rho_{\max} - \rho_0
$$

- **Tiempo:** $t_A$ es el tiempo que Ashur lleva aprendiendo. Suma partículas minúsculas que el primer día no se
  notan ($t_A/\tau \approx 0$) y que, por mucho tiempo que pase, nunca aportan más de $\Delta_t$.
- **Recuerdos:** $n_R$ es la cantidad de recuerdos. Es la fuente principal, y $m$ marca cuántos recuerdos hacen falta
  para acercarse a su tope $\Delta_R$.
- Los valores de $\tau$, $m$, $\Delta_t$ y $\Delta_R$ son provisionales y viven en el cliente, no en el contrato.
- Pueden sumarse más fuentes con la misma forma cuando se definan.

El contrato los trae en `aprendizaje`: $t_A$ se mide desde `aprendizaje.inicio` y $n_R$ es `aprendizaje.recuerdos`.

### Evolución de una identidad
Una identidad (una persona o una mascota) es una sola cosa del sistema, y lo que se ve de ella depende de su masa
$m$, la importancia que Ashur aprendió. Con los umbrales $\theta_1 < \theta_2 < \theta_3$, su nivel $k$ es:

| Nivel $k$ | Masa | Qué se ve |
| --- | --- | --- |
| 0 | $m < \theta_1$ | Nada: es un contacto sin peso en la galaxia. |
| 1 | $\theta_1 \le m < \theta_2$ | Un personaje en el planeta Identidades (tipo `personaje`). |
| 2 | $\theta_2 \le m < \theta_3$ | Una luna que orbita Identidades (tipo `luna`). |
| 3 | $\theta_3 \le m$ | Su propio planeta (tipo `planeta`). |

La importancia sube y baja, como en la memoria de una persona. Para que una identidad no parpadee entre dos niveles
cuando su masa ronda un umbral, sube al nivel $j$ cuando $m \ge \theta_j$ y solo baja de él cuando
$m < (1 - \eta)\,\theta_j$, con $0 < \eta < 1$:

$$
k_{t+1} =
\begin{cases}
k_t + 1 & \text{si } k_t < 3 \text{ y } m \ge \theta_{k_t + 1} \\
k_t - 1 & \text{si } k_t > 0 \text{ y } m < (1 - \eta)\,\theta_{k_t} \\
k_t & \text{en otro caso}
\end{cases}
$$

El core calcula el nivel y publica el `tipo`; el cliente solo lo dibuja. Los valores de $\theta_1$, $\theta_2$,
$\theta_3$ y $\eta$ son parámetros provisionales del core, que todavía no lo implementa.

### Zoom y nivel de detalle
La galaxia tiene escalas como las reales: todo está lejos y se ve más al acercarse. Una cámara con zoom $z$
($1 \le z \le z_{\max}$) y desplazamiento $\mathbf{d}$, en píxeles, lleva cada punto $\mathbf{w}$ del mundo a un punto
$\mathbf{s}$ de la pantalla, con $\mathbf{c}$ el centro de la pantalla:

$$
\mathbf{s} = \mathbf{c} + z\left(\mathbf{w} - \mathbf{c}\right) + \mathbf{d},
\qquad
\mathbf{w} = \mathbf{c} + \frac{\mathbf{s} - \mathbf{c} - \mathbf{d}}{z}
$$

Al acercar alrededor de un punto $\mathbf{f}$ de la pantalla (entre los dos dedos, o donde está el puntero), lo que
está debajo de $\mathbf{f}$ no se mueve. Con $\mathbf{w}_f$ el punto del mundo bajo $\mathbf{f}$ y $z'$ el zoom nuevo:

$$
\mathbf{d}' = \mathbf{f} - \mathbf{c} - z'\left(\mathbf{w}_f - \mathbf{c}\right)
$$

- Las posiciones y los radios de los cuerpos se multiplican por $z$; el polvo, las líneas de las órbitas y las
  estrellas fugaces mantienen su tamaño en píxeles, así que el polvo se ve más disperso de cerca.
- En $z = 1$ la galaxia vuelve al centro ($\mathbf{d} = 0$), y $|\mathbf{d}|$ no pasa de un límite para no perderla.
- **Nivel de detalle:** algo con radio $R$ en el mundo mide $zR$ en pantalla, y su opacidad es

$$
\alpha = \operatorname{clamp}\!\left(\frac{zR - r_{\min}}{r_{\text{total}} - r_{\min}},\ 0,\ 1\right)
$$

- Los **personajes** aparecen cuando el planeta Identidades mide al menos $r_P$ en pantalla, como puntos dentro del
  planeta en el ángulo $2\pi\varphi_i$, y con su nombre cuando mide $2r_P$.
- No se dibuja lo que queda fuera de la pantalla ni lo que mide menos de unos $0.3$ px.
- El toque del núcleo se mide en pantalla: $\left|\mathbf{s}_{\text{toque}} - \mathbf{s}_{\text{núcleo}}\right| \le
  \max(zR, 22\,\text{px})$.

Los valores de $z_{\max}$, $r_{\min}$, $r_{\text{total}}$ y $r_P$ son provisionales y viven en
`app/lib/galaxia/camara.dart`.
