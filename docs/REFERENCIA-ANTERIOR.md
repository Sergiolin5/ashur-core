# Referencia: repo anterior (Jarvis/Ashur)

Repo de solo lectura en `/Users/sermolin/Developer/ashur` (último commit `acd3fc3`). Las rutas son relativas a esa
carpeta. Solo aprendizajes: no se copia código. Cada punto es algo que se leyó en el archivo citado.

1. **El core vive en un servidor siempre encendido; los demás dispositivos son nodos que van y vienen.** `README.md`.
2. **Los nodos siempre llaman al core; el core nunca llama a un nodo.** Un nodo queda offline tras tres latidos
   perdidos, $T_{\text{offline}} = 3 \times 15\,\text{s} = 45\,\text{s}$, y sus tareas vuelven a la cola.
   `README.md` (Rules), `shared/protocol.py` (`OFFLINE_AFTER_S`).
3. **Un solo archivo de protocolo compartido por core y nodos** para que los dos lados no se separen. Es la idea
   detrás de `contracts/` en este repo. `shared/protocol.py`.
4. **Sergio siempre gana en sus máquinas:** cada nodo ofrece `full`, `light`, `busy` u `off` según inactividad, carga
   ajena, pantalla bloqueada y batería. `node/policy.py`, `shared/protocol.py` (`Mode`).
5. **Las decisiones son funciones puras y se prueban en cualquier sistema;** solo los lectores de señales son
   específicos de cada OS. `node/policy.py` (docstring).
6. **Cada módulo declara un manifiesto con nombre, versión, sistemas y nivel (`tier`),** y trae su autoprueba.
   `modules/inventory/module.yaml`, `modules/inventory/selftest.py`.
7. **El inventario de archivos varía la profundidad por carpeta:** los archivos sensibles (llaves, bóvedas, perfiles
   de navegador) se listan solo por nombre y nunca se siguen enlaces simbólicos. `modules/inventory/action.py`.
8. **La personalidad y la memoria viven solo en el servidor;** el código solo tiene el mecanismo y una persona
   por defecto. `core/brain.py` (docstring), `core/persona/default.md`.
9. **Cerebro "auto": Claude si funciona y un modelo local si no,** con presupuesto mensual en dólares. Antecedente de
   los tres niveles de inferencia. `core/brain.py` (`BrainSettings`), `README.md` (Local model), `.env.example`.
10. **Los datos de salud nunca salen a Claude,** y lo que parece un secreto no se guarda como recuerdo.
    `core/brain.py` (`health_split`, `looks_like_secret`), `docs/ios/ETAPA3.md` (Reglas).
11. **Toda acción que escribe pasa por una aprobación de Sergio** ("Pedidos"). `docs/ios/ETAPA3.md` (Reglas).
12. **Dos puertas:** una para la red privada (nodos y administración) y otra pública que solo abre el panel, con
    bloqueo tras diez claves erróneas. `README.md` (Reaching the panel from the internet), `core/serve.py`.
13. **Un conector MCP propio, con su clave, su bloqueo y sus límites por hora.** `core/mcp.py`.
14. **Actualizaciones con vuelta atrás automática:** si una versión nueva se cae en menos de dos minutos, el nodo
    vuelve a la anterior y la marca como mala. `node/boot.py` (docstring), `README.md` (Updates).
15. **Mantener dos clientes (web y nativo) iguales exigió una lista de paridad con chequeo en CI.** Un cliente único
    evita ese costo. `docs/ios/NATIVO.md` (Decisiones), `ios/paridad.json`, `.github/workflows/ios.yml`.
