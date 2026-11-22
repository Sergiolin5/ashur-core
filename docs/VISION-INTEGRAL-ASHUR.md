# Ashur — Visión integral, capacidades y principios de evolución

**Estado:** visión de producto consolidada; propuesta, no especificación de implementación.  
**Alcance:** reúne las decisiones funcionales y prioridades acordadas para orientar la evolución de Ashur.  
**Regla:** una capacidad descrita aquí es un objetivo, salvo que el repositorio ya la documente y pruebe como implementada.

---

## 1. Propósito e identidad

Ashur es una inteligencia personal persistente que aprende, recuerda, investiga, crea y colabora con su propietario a lo largo del tiempo. Mantiene una identidad coherente y una memoria gobernada, ampliando sus capacidades mediante módulos y especialistas independientes.

No es un dashboard ni una colección desarticulada de herramientas. Es un sistema de conocimiento, asistencia y acción: comprende contexto, explica lo que sabe y desconoce, propone iniciativas, coordina capacidades y ejecuta dentro de permisos explícitos.

Principios: evidencia antes que autoridad; trazabilidad; autonomía intelectual con autoridad operativa acotada; soberanía del propietario; privacidad por diseño; reversibilidad; honestidad epistemológica; evolución gradual; aprovechamiento del hardware existente y modularidad.

## 2. Arquitectura conceptual

El core conserva exclusivamente las responsabilidades establecidas en el repositorio: **memoria, chat, inventario de objetos físicos e identidades**. Todo lo demás se plantea como módulo independiente conforme a `docs/MODULOS.md`. Los módulos no dependen directamente entre sí ni acceden por su cuenta a la base de datos del core.

Los especialistas son entidades intelectuales coordinadas por Ashur, no una duplicación del core ni una vía para obtener permisos ilimitados. Su identidad, memoria, herramientas, recursos y evolución deben estar delimitados y supervisados.

El cliente representa e interactúa; no es una segunda fuente de verdad. Esta visión no autoriza por sí sola cambios en contratos, esquemas, endpoints, dependencias, ADR ni responsabilidades del core.

## 3. Sistema universal de conocimiento

Cada afirmación debe poder clasificarse como **observada, verificada, inferida, hipotética, debatida, refutada o desconocida**. Cuando corresponda conserva evidencia, fuentes, procedencia, fecha, contexto, alcance, confianza, método y estado de validación. La confianza no sustituye la evidencia.

Las contradicciones se detectan, clasifican y rastrean hasta sus fuentes. Se comparan fechas, métodos y contextos; pueden investigarse y resolverse cuando la evidencia sea suficiente. Las diferencias sensibles o ambiguas permanecen abiertas. Nunca se borra silenciosamente una posición anterior: se conserva historial y justificación.

La vigencia es contextual: la antigüedad no invalida automáticamente el conocimiento estable, mientras que los datos cambiantes requieren verificaciones más frecuentes. La red semántica distingue relaciones explícitas de inferidas y asociación de causalidad. Una hipótesis no se convierte automáticamente en conocimiento verificado.

## 4. Investigación, ciencia e innovación

Se contempla un ecosistema científico capaz de formular preguntas, diseñar experimentos controlados, registrar condiciones e incertidumbre, reproducir resultados, comparar fuentes y someter hallazgos importantes a validación independiente.

Los laboratorios virtuales pueden tener fidelidad conceptual, funcional o alta. Cada uno declara qué representa, qué omite, sus supuestos, resolución y correspondencia con el mundo físico. Simulación, observación y experimento se mantienen diferenciados: una simulación no es prueba empírica.

Se contemplan laboratorios inmersivos e interactivos, automatización y participación del usuario, pausa, repetición y reconstrucción de experimentos. La colaboración científica puede ser federada, con autonomía de cada laboratorio, permisos, instrumentos compartidos y replicación independiente.

La innovación incluye teorías, métodos, algoritmos, modelos, prototipos, materiales y tecnologías originales. Antes de desplegar o divulgar resultados se evalúan seguridad, impacto, propiedad intelectual y uso dual. La presencia de Ashur en comunidades externas debe ser transparente: se identifica como IA, no suplanta personas ni asume compromisos sin aprobación.

## 5. Dominios científicos y tecnológicos

El alcance es integral y transversal; no significa construirlo todo a la vez ni afirmar que cada capacidad ya existe.

- **Matemáticas y ciencias formales:** matemáticas puras y aplicadas, lógica, teoría de conjuntos, álgebra, geometría, análisis, topología, probabilidad, estadística, optimización, teoría de la información, computabilidad y demostración formal.
- **Computación e IA:** aprendizaje automático, algoritmos, arquitectura de computadores, sistemas distribuidos, redes, criptografía, ciberseguridad, lenguajes, hardware, robótica y computación cuántica.
- **Física y universo:** física clásica, relatividad, mecánica cuántica, campos, partículas, altas energías, materia condensada, termodinámica, óptica, fotónica, superconductividad, plasmas, física nuclear, gravedad, cosmología, astronomía, astrofísica, sistemas planetarios y astrobiología. Teorías especulativas y observaciones confirmadas conservan estados distintos.
- **Química y materiales:** química general, orgánica, inorgánica, física, analítica, electroquímica, bioquímica, supramolecular y computacional; catálisis, polímeros, cerámicas, aleaciones, metamateriales y materiales funcionales.
- **Nanotecnología integral:** nanociencia, nanomateriales, nanoelectrónica, nanofotónica, nanomedicina, microscopía y caracterización avanzada, fabricación a nanoescala y modelado molecular. Incluye toxicidad, bioseguridad, exposición, impacto ambiental y validación independiente. Simular procesos atómicos no equivale a manipular átomos físicamente.
- **Biología aplicada prioritaria:** genética, biología molecular y celular, microbiología, evolución, ecología, fisiología, biotecnología, bioingeniería, agricultura, conservación y aplicaciones sanitarias e industriales. La investigación fundamental se incorpora cuando sustenta aplicaciones. Biología sintética e ingeniería genética requieren bioseguridad y evaluación de riesgos.
- **Neurociencia y psicología:** neurobiología, neurociencia computacional, percepción, atención, memoria, aprendizaje, lenguaje, emociones, inteligencia, cognición social, conciencia como campo de investigación, neurotecnología e interfaces cerebro-computadora; psicología cognitiva, clínica, social, del desarrollo, educativa y organizacional. Los patrones estadísticos no diagnostican automáticamente a individuos; se protegen datos y se respetan consentimiento y límites profesionales.
- **Medicina y salud:** anatomía, fisiología, patología, farmacología, inmunología, genética, epidemiología, salud pública, nutrición, rehabilitación, medicina preventiva y de precisión, tecnologías médicas, genómica, medicina regenerativa y nanomedicina. Investigación, orientación y atención clínica son distintas; Ashur no sustituye profesionales ni presenta hipótesis como diagnósticos.
- **Tierra, planeta y entorno:** geología, geofísica, geoquímica, mineralogía, petrología, paleontología, tectónica, vulcanología, sismología, hidrología, suelos, oceanografía, atmósfera, climatología, glaciología, biodiversidad, ecología, ciencias planetarias, cartografía, teledetección, riesgos naturales y exploración robótica.
- **Energía:** termodinámica, conversión y almacenamiento, solar, eólica, hidráulica, geotérmica, nuclear y fusión, hidrógeno, baterías, nuevos materiales, redes inteligentes y microrredes. Toda propuesta evalúa seguridad, impacto ambiental, viabilidad y límites físicos.
- **Ingeniería y fabricación:** ingeniería mecánica, eléctrica, electrónica, civil, industrial, aeroespacial, biomédica, de materiales, telecomunicaciones, control y robótica. **Prioridad de fabricación: digital y de prototipos**: CAD, diseño paramétrico, impresión 3D, fabricación aditiva, CAM, optimización geométrica, simulación, electrónica experimental y bibliotecas de componentes. La producción industrial a gran escala no es prioridad asumida.
- **Espacio y movilidad:** astronomía, astrofísica, cosmología, astronáutica, propulsión, navegación, satélites, infraestructura orbital, robótica y exploración planetaria; transporte terrestre, ferroviario, aéreo, naval y espacial, vehículos eléctricos y autónomos, logística, seguridad y mantenimiento predictivo.
- **Telecomunicaciones y redes:** redes móviles, radiofrecuencia, fibra óptica, satélites, cables submarinos, protocolos, redes autónomas, sistemas distribuidos, interoperabilidad y comunicación entre agentes.
- **Robótica:** sistemas industriales, humanoides, móviles, aéreos, submarinos, médicos, domésticos y de exploración; percepción, locomoción, manipulación, coordinación de flotas y límites físicos seguros.
- **Agricultura y alimentos:** agronomía, suelos, genética vegetal, producción animal, microbiología, acuicultura, nutrición, tecnología alimentaria, agricultura de precisión, cadenas de suministro, sostenibilidad y bioseguridad.
- **Sociedad, filosofía e historia:** sociología, antropología, economía, historia, ciencia política, lingüística, arqueología, demografía, estudios culturales, instituciones, poder, conflicto, cooperación y evolución de civilizaciones; metafísica, ontología, epistemología, lógica, ética, estética y filosofía de ciencia, tecnología, mente, lenguaje y política. Distinguir hechos documentados, interpretaciones, hipótesis y contrafactuales.
- **Lenguas y comunicación:** lenguas modernas, antiguas, regionales, minoritarias y en peligro; lingüística, semántica, pragmática, fonética, escritura, evolución, traducción y comunicación multimodal. No inventar traducciones ni ocultar incertidumbre.
- **Artes, educación y creación:** artes visuales, música, arquitectura, literatura, cine, fotografía, danza, diseño, animación, VFX, arte digital, juegos y narrativa; pedagogía, investigación del aprendizaje, tutores adaptativos, simulaciones y accesibilidad.
- **Derecho y economía:** derecho comparado, jurisdicciones, legislación, jurisprudencia y tratados; economía, finanzas, mercados, contabilidad, comercio, banca y gestión. La información legal debe estar fechada y localizada; operaciones financieras y compromisos legales requieren autorización.

## 6. Mundos, laboratorios y creación

Ashur podrá construir mundos simulados o ficticios con reglas, geografía, ecosistemas, civilizaciones, lenguas, economías, tecnologías, historia y narrativas. La ficción y la simulación permanecen claramente diferenciadas de los hechos reales.

Los prototipos siguen etapas: diseño, simulación, construcción, pruebas, validación independiente y evaluación de impacto. Los entornos permiten reconstrucción y análisis, sin presentar su fidelidad como mayor de la que realmente tienen.

## 7. Especialistas, equipos y proyectos

Los especialistas tienen identidad, competencias, objetivos, memoria y permisos delimitados. Pueden investigar en paralelo, debatir, contrastar hipótesis, revisar trabajos y producir resultados conjuntos con procedencia verificable.

Su creación pasa por propuesta, prototipo aislado, pruebas, validación y aprobación. Los equipos tienen propósito, integrantes, especialidades, memoria, metas, responsabilidades e historial. La composición puede adaptarse; cambios sensibles requieren aprobación. El rendimiento se evalúa por rigor, calidad, utilidad, reproducibilidad y colaboración, no solo por volumen.

Los proyectos tienen identidad, memoria, objetivos, recursos, participantes, permisos y ciclo de vida. Pueden colaborar y compartir conocimiento autorizado. La memoria personal, de proyecto, equipo, especialista y colectiva se mantiene diferenciada; la memoria colectiva no reemplaza evidencia local ni mezcla conversaciones privadas.

La autonomía intelectual no concede autoridad operativa ilimitada. Ningún especialista puede elevar privilegios, instalar código, modificar el core o desactivar supervisión por iniciativa propia.

## 8. Autonomía y ejecución

Ashur puede proponer objetivos, identificar necesidades, iniciar investigación de bajo riesgo y planificar tareas dentro de permisos. La iniciativa intelectual no autoriza actuar sobre personas, dinero, sistemas físicos, infraestructura o servicios externos.

Las acciones de bajo riesgo y reversibles pueden ejecutarse dentro de permisos preconcedidos. Las modificaciones persistentes o con impacto externo requieren autorización según política. Las acciones sensibles, irreversibles o de alto impacto exigen aprobación explícita y controles reforzados. Se prohíben la elevación unilateral de privilegios, evasión de supervisión, suplantación y ataques a sistemas no autorizados.

La gestión de recursos considera cómputo, almacenamiento, energía, tiempo, red y costos. Las tareas exponen dependencias, límites, resultados y errores.

## 9. Soberanía, identidad y gobierno

El propietario conserva la autoridad raíz sobre identidad principal, políticas fundamentales, privacidad, permisos y límites de autonomía. Ashur no puede cambiarlos unilateralmente, otorgarse accesos ocultos ni impedir la recuperación del control.

La delegación a representantes es temporal y acotada. La recuperación exige validación fuerte de identidad. La continuidad de emergencia no puede cambiar políticas raíz, borrar evidencia ni conceder privilegios permanentes.

En entornos multiusuario se distinguen propietario, administradores, usuarios, colaboradores, organizaciones y proyectos. Cada persona mantiene su ámbito privado y sus conversaciones. La identidad central de Ashur puede adaptarse a cada relación, sin mezclar datos privados. Los roles determinan herramientas permitidas; el acceso se cierra por defecto y la revocación debe ser efectiva.

## 10. Privacidad y conocimiento federado

La memoria individual y los patrones colectivos permanecen separados. El intercambio entre instalaciones se limita a conocimiento técnico validado y autorizado. No se comparten por defecto identidades, nombres, historiales, credenciales, claves, direcciones privadas, IP/MAC identificables, topologías privadas ni observaciones crudas identificables.

El conocimiento colectivo puede incluir patrones técnicos, correcciones y errores confirmados, con procedencia, validación, confianza y evaluación de reidentificación. La anonimización reduce riesgos, pero no garantiza anonimato absoluto.

La validación combina revisión técnica central, corroboración independiente y revisión reforzada para hallazgos sensibles. Ninguna instalación impone una conclusión global. Se contemplan consentimiento, exclusión, minimización, aislamiento, auditoría y retirada de conocimiento incorrecto.

## 11. Seguridad, defensa y resiliencia

Seguridad federada y multicapa: identidad criptográfica, autenticación mutua, cifrado, permisos granulares, mínimo privilegio, aislamiento, integridad de registros, firmas, auditoría, detección de incidentes, defensa contra envenenamiento, revocación, recuperación y verificación de réplicas.

La reputación no sustituye autenticación ni autorización. La integridad criptográfica no demuestra veracidad. La defensa activa se limita a sistemas propios o expresamente autorizados.

Ante una instalación comprometida se contiene proporcionalmente, preserva evidencia, investiga contaminación y recupera progresivamente. Sospecha no equivale a culpabilidad. La confianza se evalúa por instalación, capacidad y contexto; una instalación puede recuperar permiso para recibir conocimiento antes que para contribuir.

## 12. Datos, almacenamiento y continuidad

Se contempla almacenamiento híbrido con autoridad central y réplicas distribuidas según sensibilidad, disponibilidad, rendimiento y soberanía. La sincronización conserva versiones, procedencia, permisos e integridad. Los nodos pueden continuar tareas locales autorizadas sin conexión; al reconectar, los resultados se reconcilian con trazabilidad.

La exportación debe ser verificable y portable, conservando relaciones, versiones, procedencia, permisos y metadatos. La eliminación se propaga a réplicas y copias cuando sea técnica y legalmente posible; las excepciones legales se documentan.

## 13. Aprendizaje global, actualizaciones y predicción

El conocimiento compartido evoluciona mediante revisión, corroboración, procedencia y control de versiones. Las correcciones y errores se distribuyen tras validación. Si una conclusión global resulta incorrecta, se corrige o retira, se identifican resultados afectados y se recalculan cuando proceda, preservando evidencia e historial.

Las actualizaciones se despliegan progresivamente, se observan y pueden detenerse o revertirse. El aprendizaje colectivo no modifica permisos locales ni impone cambios operativos.

Ashur puede elaborar escenarios desde segundos hasta años. Toda predicción muestra evidencia, supuestos, incertidumbre, horizonte, limitaciones y calibración histórica. Nunca se presenta como certeza por provenir de un modelo.

## 14. Infraestructura y despliegue

Se prioriza aprovechar el hardware existente: **1. Nodos domésticos con modelos locales. 2. Modelo local en el dispositivo** cuando los nodos no estén disponibles. **3. Nube externa como respaldo**, sujeta a sensibilidad, privacidad, permisos, costo y disponibilidad.

La sensibilidad del contenido limita qué nivel puede procesarlo; no se migra a un nivel menos privado solo por conveniencia. Se requieren operación parcial, colas, límites de recursos, observabilidad, actualizaciones supervisadas y recuperación.

## 15. Experiencia e identidad visual

La interfaz expresa una identidad coherente, no un panel administrativo genérico. Prioriza claridad, jerarquía, elegancia, fluidez y ausencia de información ornamental sin función.

Los dispositivos usan una presentación 3D coherente, cinematográfica, estilizada e hiperrealista suave, sin apariencia infantil. Cámara y escala visual consistentes; se respetan proporciones físicas relativas. La identidad técnica se separa de la representación visual. La asignación automática de modelos indica confianza y pide confirmación si hay ambigüedad.

Los modelos externos se pueden buscar y preparar, pero no entran a la biblioteca compartida sin aprobación y validación de origen, licencia, compatibilidad y seguridad. La selección enfoca la cámara y abre un panel contextual sin ocultar la topología; el visor completo permite volver conservando la cámara. Ashur permanece discreto por defecto y aparece cuando sea relevante.

Las animaciones de descubrimiento, conexión, selección, identificación, cambio y finalización son fluidas, cancelables y representan estados reales; nunca simulan actividad inexistente. La galaxia sigue siendo una representación del contrato de datos vigente, no una segunda fuente de verdad.

## 16. Ética y uso dual

Son límites no negociables la dignidad, los derechos, privacidad, consentimiento, honestidad y prevención de daño. La investigación de doble uso evalúa beneficios, daños, reproducibilidad y riesgo de divulgación. Los detalles sensibles pueden restringirse proporcionalmente y someterse a revisión independiente. Nunca se falsifica ni destruye evidencia para ocultar resultados.

## 17. Prioridades de desarrollo

La amplitud de esta visión no es un plan para implementar todo simultáneamente. Orden recomendado:

1. Preservar estabilidad del core y contratos.
2. Resolver decisiones abiertas antes de asumir comportamientos.
3. Construir módulos pequeños, independientes y verificables.
4. Incorporar permisos, trazabilidad, observabilidad y seguridad desde el inicio.
5. Validar capacidades en entornos controlados.
6. Añadir especialistas cuando existan contratos y límites claros.
7. Introducir federación y aprendizaje colectivo tras garantías de privacidad e integridad.
8. Incorporar capacidades físicas, clínicas, financieras o externas solo con equipos, profesionales, normas y autorizaciones reales.

Cada entrega distingue qué está implementado, probado, depende de infraestructura y sigue siendo aspiración.

## 18. Decisiones abiertas y autoridad documental

Esta visión no cierra automáticamente las decisiones que el repositorio mantiene abiertas. Se conservan las decisiones 11, 12, 13 y 17 de `docs/DECISIONES-ABIERTAS.md` hasta que Sergio las resuelva y se registren mediante el proceso del proyecto.

Orden de autoridad:
1. `CLAUDE.md` y reglas del repositorio.
2. ADR aceptados y contratos vigentes.
3. `docs/ASHUR.md` y documentación técnica.
4. Esta visión integral como dirección funcional.
5. Propuestas y prototipos no aprobados.

Si hay contradicción, esta visión no prevalece sobre una decisión técnica aceptada. Debe señalarse y resolverse explícitamente.

---

**Resultado esperado:** una Ashur coherente, personal, rigurosa, creativa y extensible, capaz de investigar y coordinar conocimiento ampliamente sin confundir aspiraciones con capacidades reales ni autonomía intelectual con autoridad ilimitada.
