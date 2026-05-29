"""
AgroAsistente IA — Motor de análisis agronomico con lenguaje natural.
Sistema experto basado en reglas que simula el razonamiento de un agrónomo.
"""
from __future__ import annotations
from datetime import date
from core.data_generator import FENOLOGIA_LABELS

# ── Conocimiento base ──────────────────────────────────────────────────────

_UMBRAL_INTERACCION = {
    # (amenaza_a, amenaza_b): mensaje de sinergia
    ("mosca", "antracnosis"):
        "La combinacion de Mosca y Antracnosis bajo condiciones humedas indica "
        "un estado fitosanitario critico. Los frutos danados por mosca son puertas "
        "de entrada para el hongo Colletotrichum.",
    ("oidio", "trips"):
        "Oidio y Trips comparten las mismas condiciones favorables (calor seco). "
        "Una aplicacion preventiva de azufre mojable puede atenuar ambas amenazas.",
    ("antracnosis", "oidio"):
        "Condiciones de transicion (lluvia seguida de periodo seco) favorecen "
        "simultaneamente Antracnosis y Oidio en distintas partes del dosel.",
}

_CALENDARIO_ALERTAS = {
    # mes: [(amenaza, razon_estacional)]
    1:  [("oidio", "temporada seca + floración inicio")],
    2:  [("oidio", "pico floración + baja humedad"), ("trips", "temperatura alta + floración")],
    3:  [("trips", "máximo riesgo trips: calor y floración"), ("oidio", "floración avanzada")],
    4:  [("mosca", "inicio fruto joven")],
    5:  [("mosca", "fruto joven + lluvias iniciales")],
    6:  [("mosca", "fruto en desarrollo + humedad alta"), ("antracnosis", "lluvias + fruto")],
    7:  [("mosca", "pico mosca: maduración + lluvia")],
    8:  [("mosca", "maduración plena"), ("antracnosis", "lluvia intensa + fruto maduro")],
    9:  [("antracnosis", "máximo riesgo: lluvia + posmaduración"), ("mosca", "frutos caídos")],
    10: [("antracnosis", "lluvia residual + reposo inicio")],
    11: [],
    12: [("oidio", "brotación + inicio seco")],
}

_PREGUNTAS_FAQ = {
    "mosca": (
        "La Mosca del Mango (Anastrepha obliqua) deposita huevos bajo la piel del fruto. "
        "La larva consume la pulpa haciéndola incomercializable. "
        "El umbral de acción económica es 1 adulto por trampa McPhail por semana. "
        "Los periodos de mayor riesgo son mayo-septiembre, coincidiendo con maduración y lluvias."
    ),
    "trips": (
        "Los Trips (Frankliniella spp.) raspan y succionan células florales causando "
        "deformaciones y aborto de panículas. Son más activos en horario fresco (6-9am). "
        "El umbral económico es 10 trips por flor. El control con Spinosad respeta "
        "polinizadores si se aplica al atardecer."
    ),
    "antracnosis": (
        "La Antracnosis (Colletotrichum gloeosporioides) causa manchas negras en frutos, "
        "flores y hojas. Las esporas germinan con humedad libre por más de 12 horas. "
        "Es la enfermedad postcosecha más importante del mango en RD. "
        "Los fungicidas cúpricos actúan como barrera protectora, no curativa."
    ),
    "oidio": (
        "El Oídio (Oidium mangiferae) forma colonias blanquecinas pulverulentas en flores "
        "y brotes jóvenes. Prospera con humedad BAJA y temperaturas moderadas (22-28°C). "
        "En años de floración temprana (dic-ene) el riesgo es crítico. "
        "El azufre mojable es el control más efectivo y económico."
    ),
    "clima": (
        "El sistema consume datos en tiempo real de la API Open-Meteo para las coordenadas "
        "exactas de Baní (lat=18.28, lon=-70.33). Los datos se actualizan cada hora. "
        "En caso de falla de la API, el sistema usa valores de referencia ONAMET para la zona."
    ),
    "modelo": (
        "El motor de predicción usa Random Forest entrenado con datos históricos de 3 años "
        "(2022-2024) para la zona de Peravia. Cada amenaza tiene su propio modelo con 150 "
        "árboles de decisión. Los índices van de 0 a 100 y se traducen en cuatro niveles: "
        "Bajo (0-25), Medio (25-50), Alto (50-75) y Crítico (75-100)."
    ),
}

_KEYWORDS = {
    "mosca":       ["mosca", "anastrepha", "trampa", "mcphail", "larva", "fruto"],
    "trips":       ["trips", "frankliniella", "flor", "panicula", "pétalo"],
    "antracnosis": ["antracnosis", "colletotrichum", "hongo", "mancha", "fungicida"],
    "oidio":       ["oidio", "oidium", "polvo", "blanco", "azufre"],
    "clima":       ["clima", "lluvia", "temperatura", "humedad", "pronóstico", "api", "meteo"],
    "modelo":      ["modelo", "predicción", "random forest", "índice", "score", "nivel"],
}


class AgroAsistente:
    """Motor de análisis agronomico contextual."""

    def __init__(self) -> None:
        self._historial: list[dict] = []

    # ── Análisis completo del estado actual ───────────────────────
    def analizar(
        self,
        resultados: dict,
        clima: dict,
        fenologia_idx: int,
        mes: int,
    ) -> dict:
        """
        Devuelve un dict con:
          - resumen: párrafo ejecutivo
          - prioridades: lista ordenada de amenazas a atender
          - alertas_estacionales: advertencias del calendario
          - sinergias: interacciones entre amenazas detectadas
          - plan_accion: pasos concretos priorizados
          - nivel_alerta_global: Bajo/Moderado/Elevado/Critico
        """
        feno_label = FENOLOGIA_LABELS[fenologia_idx]
        scores = {a: resultados[a]["score"] for a in resultados}
        niveles = {a: resultados[a]["nivel"] for a in resultados}

        # Nivel global
        max_score = max(scores.values())
        nivel_global = self._nivel_global(max_score)

        # Prioridades ordenadas
        prioridades = sorted(scores, key=lambda a: scores[a], reverse=True)

        # Sinergias
        sinergias = []
        amenazas_activas = [a for a in scores if scores[a] >= 40]
        for (a, b), msg in _UMBRAL_INTERACCION.items():
            if a in amenazas_activas and b in amenazas_activas:
                sinergias.append(msg)

        # Alertas estacionales
        alertas_est = []
        for amenaza, razon in _CALENDARIO_ALERTAS.get(mes, []):
            alertas_est.append(
                f"{_nombre(amenaza)}: vigilancia especial en este periodo "
                f"({razon})."
            )

        # Resumen ejecutivo
        resumen = self._generar_resumen(
            scores, niveles, clima, feno_label, mes, nivel_global
        )

        # Plan de acción
        plan = self._generar_plan(prioridades, resultados, feno_label)

        return {
            "resumen":              resumen,
            "prioridades":          prioridades,
            "alertas_estacionales": alertas_est,
            "sinergias":            sinergias,
            "plan_accion":          plan,
            "nivel_alerta_global":  nivel_global,
            "max_score":            max_score,
        }

    # ── Chat contextual ────────────────────────────────────────────
    def responder(
        self,
        pregunta: str,
        resultados: dict | None = None,
        clima: dict | None = None,
    ) -> str:
        """Responde preguntas del técnico con contexto del estado actual."""
        pregunta_lower = pregunta.lower().strip()

        # Detectar tema
        tema = self._detectar_tema(pregunta_lower)

        if tema and tema in _PREGUNTAS_FAQ:
            base = _PREGUNTAS_FAQ[tema]
            # Enriquecer con contexto actual
            if resultados and tema in resultados:
                d = resultados[tema]
                contexto = (
                    f"\n\nEN EL DIA DE HOY el indice de {_nombre(tema)} es "
                    f"{d['score']:.1f}/100 (Nivel {d['nivel']}). "
                    f"{d['recomendacion']}"
                )
                return base + contexto
            return base

        # Preguntas sobre el estado general
        if any(w in pregunta_lower for w in ["estado", "hoy", "actual", "riesgo general", "como esta"]):
            if resultados:
                return self._resumen_corto(resultados)
            return "Aun no tengo datos del estado actual. Actualice el dashboard primero."

        # Preguntas sobre qué hacer
        if any(w in pregunta_lower for w in ["que hago", "que debo", "qué hacer", "accion", "aplicar", "tratar"]):
            if resultados:
                return self._que_hacer(resultados)
            return "Consulte el Dashboard para ver el estado actual y obtener recomendaciones."

        # Preguntas sobre clima
        if any(w in pregunta_lower for w in ["lluvia", "temperatura", "humedad", "calor"]):
            if clima:
                return (
                    f"Las condiciones actuales en Bani son: temperatura {clima.get('temp_media', '?')} °C, "
                    f"humedad relativa {clima.get('humedad', '?')}%, "
                    f"precipitacion {clima.get('precipitacion', '?')} mm. "
                    f"Fuente: {clima.get('source', 'N/D').upper()}. "
                    f"Estas condiciones son relevantes porque la humedad alta favorece Antracnosis "
                    f"mientras que la temperatura elevada con baja humedad favorece Trips y Oidio."
                )

        # Saludo
        if any(w in pregunta_lower for w in ["hola", "buenas", "buenos", "saludos"]):
            return (
                "Buenos dias. Soy el Asistente Agronomico AgroRisk. "
                "Estoy aqui para ayudarle a interpretar los indices de riesgo fitosanitario "
                "de su parcela de mango en Peravia. "
                "Puede preguntarme sobre cualquier amenaza (mosca, trips, antracnosis, oidio), "
                "sobre el clima actual, o sobre que acciones tomar hoy."
            )

        # Respuesta generica con contexto
        if resultados:
            amenaza_mayor = max(resultados, key=lambda a: resultados[a]["score"])
            d = resultados[amenaza_mayor]
            return (
                f"No tengo una respuesta especifica para esa consulta, pero puedo decirle que "
                f"la principal preocupacion hoy es {_nombre(amenaza_mayor)} "
                f"con un indice de {d['score']:.1f}/100 (Nivel {d['nivel']}). "
                f"Puede preguntarme directamente sobre mosca, trips, antracnosis u oidio, "
                f"o consultar el Simulador para explorar escenarios."
            )

        return (
            "Puede preguntarme sobre: mosca de las frutas, trips, antracnosis, oidio, "
            "condiciones climaticas, el modelo de prediccion, o que acciones tomar hoy."
        )

    # ── Helpers privados ───────────────────────────────────────────

    def _nivel_global(self, max_score: float) -> str:
        if max_score < 25:  return "Bajo"
        if max_score < 50:  return "Moderado"
        if max_score < 75:  return "Elevado"
        return "Critico"

    def _detectar_tema(self, texto: str) -> str | None:
        for tema, palabras in _KEYWORDS.items():
            if any(p in texto for p in palabras):
                return tema
        return None

    def _generar_resumen(
        self, scores, niveles, clima, feno_label, mes, nivel_global
    ) -> str:
        amenaza_mayor = max(scores, key=lambda a: scores[a])
        amenaza_menor = min(scores, key=lambda a: scores[a])
        n_alto = sum(1 for n in niveles.values() if n in ("Alto", "Critico"))
        mes_nombre = [
            "enero", "febrero", "marzo", "abril", "mayo", "junio",
            "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
        ][mes - 1]

        partes = [
            f"El estado fitosanitario general de la parcela en {mes_nombre} "
            f"(etapa: {feno_label}) es de alerta {nivel_global.upper()}. "
        ]

        if n_alto > 0:
            partes.append(
                f"Se registran {n_alto} amenaza(s) en nivel Alto o Critico, "
                f"siendo {_nombre(amenaza_mayor)} la de mayor urgencia "
                f"con un indice de {scores[amenaza_mayor]:.1f}/100. "
            )
        else:
            partes.append(
                f"Ninguna amenaza supera el umbral critico. "
                f"La de mayor indice es {_nombre(amenaza_mayor)} "
                f"({scores[amenaza_mayor]:.1f}/100). "
            )

        if clima:
            hum = clima.get("humedad", 0)
            temp = clima.get("temp_media", 0)
            if hum > 80:
                partes.append(
                    f"La humedad relativa de {hum}% es un factor de riesgo "
                    f"determinante para Antracnosis. "
                )
            elif hum < 60:
                partes.append(
                    f"La humedad baja ({hum}%) favorece Trips y Oidio "
                    f"sobre hongos foliares. "
                )
            if temp > 30:
                partes.append(f"La temperatura elevada ({temp} °C) incrementa la actividad de la Mosca. ")

        partes.append(
            f"La condicion de menor riesgo actual es {_nombre(amenaza_menor)} "
            f"({scores[amenaza_menor]:.1f}/100)."
        )
        return "".join(partes)

    def _generar_plan(self, prioridades: list, resultados: dict, feno_label: str) -> list[str]:
        plan = []
        for i, amenaza in enumerate(prioridades, 1):
            d = resultados[amenaza]
            if d["nivel"] in ("Alto", "Critico"):
                plan.append(f"[URGENTE] {_nombre(amenaza)}: {d['recomendacion']}")
            elif d["nivel"] == "Medio":
                plan.append(f"[PREVENTIVO] {_nombre(amenaza)}: {d['recomendacion']}")
            else:
                plan.append(f"[MONITOREO] {_nombre(amenaza)}: Vigilancia rutinaria semanal.")
        return plan

    def _resumen_corto(self, resultados: dict) -> str:
        partes = ["Estado actual:\n"]
        for amenaza, d in resultados.items():
            partes.append(f"  • {_nombre(amenaza)}: {d['nivel']} ({d['score']:.1f}/100)\n")
        amenaza_mayor = max(resultados, key=lambda a: resultados[a]["score"])
        partes.append(
            f"\nPrioridad: {_nombre(amenaza_mayor)} con {resultados[amenaza_mayor]['score']:.1f}/100."
        )
        return "".join(partes)

    def _que_hacer(self, resultados: dict) -> str:
        urgentes = [
            (a, d) for a, d in resultados.items() if d["nivel"] in ("Alto", "Critico")
        ]
        preventivos = [
            (a, d) for a, d in resultados.items() if d["nivel"] == "Medio"
        ]

        if not urgentes and not preventivos:
            return (
                "El riesgo actual es bajo en todas las amenazas. "
                "Mantenga el monitoreo preventivo semanal y asegurese de que "
                "el historial de trampas esté actualizado."
            )

        resp = []
        if urgentes:
            resp.append("ACCIONES URGENTES:")
            for amenaza, d in urgentes:
                resp.append(f"  {_nombre(amenaza)}: {d['recomendacion']}")
        if preventivos:
            resp.append("\nACCIONES PREVENTIVAS:")
            for amenaza, d in preventivos:
                resp.append(f"  {_nombre(amenaza)}: {d['recomendacion']}")
        return "\n".join(resp)


def _nombre(amenaza: str) -> str:
    m = {
        "mosca":        "Mosca de las Frutas",
        "trips":        "Trips",
        "antracnosis":  "Antracnosis",
        "oidio":        "Oidio",
    }
    return m.get(amenaza, amenaza.title())
