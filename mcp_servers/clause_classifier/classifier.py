#!/usr/bin/env python3
"""
Clause Classifier - Clasificador de cláusulas legales
Identifica y clasifica automáticamente cláusulas en contratos por tipo y riesgo

CARACTERÍSTICAS:
- Detecta tipos de cláusulas (TERMINACIÓN, RESPONSABILIDAD, etc.)
- Asigna nivel de riesgo (HIGH, MEDIUM, LOW)
- Sugiere artículos legales relevantes
- Análisis de impacto legal
"""

import re
from typing import List, Dict, Tuple
from dataclasses import dataclass
from enum import Enum

# ============================================================
# ENUMERACIONES
# ============================================================

class ClauseType(Enum):
    """Tipos de cláusulas legales."""
    TERMINATION = "TERMINACIÓN"
    LIABILITY = "RESPONSABILIDAD"
    PRIVACY = "PRIVACIDAD"
    PAYMENT = "PAGO"
    MODIFICATION = "MODIFICACIÓN"
    ARBITRATION = "ARBITRAJE"
    DURATION = "DURACIÓN"
    RESTRICTIONS = "RESTRICCIONES"
    INTELLECTUAL_PROPERTY = "PROPIEDAD INTELECTUAL"
    OTHER = "OTRO"


class RiskLevel(Enum):
    """Niveles de riesgo."""
    HIGH = "ALTO"
    MEDIUM = "MEDIO"
    LOW = "BAJO"


# ============================================================
# DATA CLASS
# ============================================================

@dataclass
class ClassifiedClause:
    """Representa una cláusula clasificada."""
    id: str
    clause_text: str
    clause_type: ClauseType
    risk_level: RiskLevel
    risk_score: float  # 0-100
    legal_issue: str
    applicable_laws: List[str]
    recommendations: List[str]
    key_terms: List[str]


# ============================================================
# CLASSIFICADOR DE CLÁUSULAS
# ============================================================

class ClauseClassifier:
    """Clasifica cláusulas legales de contratos."""
    
    # Patrones de cláusulas por tipo
    CLAUSE_PATTERNS = {
        ClauseType.TERMINATION: {
            "keywords": [
                "rescisión", "terminación", "despido", "cancelación", "resolución",
                "vencimiento", "finalización", "cese", "extinción", "ruptura",
                "fin del contrato", "conclusión", "término"
            ],
            "red_flags": [
                "sin causa", "sin previo aviso", "unilateral", "a voluntad",
                "inmediatamente", "discrecional", "arbitraria", "sin motivo"
            ]
        },
        ClauseType.LIABILITY: {
            "keywords": [
                "responsabilidad", "limitación", "indemnización", "daños",
                "reclamación", "garantía", "negligencia", "incumplimiento",
                "reparación", "compensación"
            ],
            "red_flags": [
                "sin responsabilidad", "sin garantía", "se proporciona tal cual",
                "limitación de responsabilidad", "exención de responsabilidad",
                "renuncia de derechos", "sin compensación"
            ]
        },
        ClauseType.PRIVACY: {
            "keywords": [
                "datos personales", "privacidad", "confidencialidad", "información",
                "rgpd", "protección de datos", "consentimiento", "tratamiento",
                "procesamiento", "acceso", "portabilidad"
            ],
            "red_flags": [
                "venta de datos", "datos perpetuos", "sin consentimiento",
                "compartir con terceros", "sin derecho a eliminar",
                "vigilancia", "seguimiento indefinido"
            ]
        },
        ClauseType.PAYMENT: {
            "keywords": [
                "salario", "pago", "precio", "tarifa", "compensación", "honorarios",
                "renta", "cuota", "arancel", "remuneración", "sueldo", "horas"
            ],
            "red_flags": [
                "sin pago", "reducción unilateral", "penalización", "deuda perpetua",
                "cambio sin notificación", "aumento ilimitado", "indexado infinito",
                "sin compensación"
            ]
        },
        ClauseType.MODIFICATION: {
            "keywords": [
                "modificación", "cambio", "enmienda", "actualización", "revisión",
                "variación", "ajuste", "alteración", "transformación"
            ],
            "red_flags": [
                "cambio unilateral", "sin consentimiento", "sin notificación",
                "a discreción", "arbitrario", "sin límite", "permanente"
            ]
        },
        ClauseType.ARBITRATION: {
            "keywords": [
                "arbitraje", "mediación", "resolución de disputas", "tribunal",
                "litigio", "reclamación", "jurisdicción", "competencia",
                "ley aplicable", "foro"
            ],
            "red_flags": [
                "arbitraje obligatorio", "sin derecho a juzgado", "costos arbitraje",
                "jurisdicción extranjera", "ley extranjera aplicable",
                "imposible impugnar", "sin apelación"
            ]
        },
        ClauseType.DURATION: {
            "keywords": [
                "duración", "plazo", "término", "vigencia", "validez", "período",
                "años", "meses", "semanas", "días", "tiempo", "renovación",
                "prórroga"
            ],
            "red_flags": [
                "indefinido", "perpetuo", "renovación automática sin salida",
                "duración ilimitada", "sin fecha de finalización"
            ]
        },
        ClauseType.RESTRICTIONS: {
            "keywords": [
                "prohibición", "restricción", "limitación", "exclusión",
                "consentimiento requerido", "competencia", "no compete",
                "confidencialidad"
            ],
            "red_flags": [
                "restricción perpetua", "restricción mundial", "restricción total",
                "sin excepciones", "irrevocable", "inmodificable"
            ]
        }
    }
    
    # Mapeo de tipos de cláusula a leyes españolas aplicables
    APPLICABLE_LAWS = {
        ClauseType.TERMINATION: ["LAB_9", "LAB_14", "LAR_9"],
        ClauseType.LIABILITY: ["TOS_4", "TOS_8", "TOS_10"],
        ClauseType.PRIVACY: ["TOS_6", "TOS_7"],
        ClauseType.PAYMENT: ["LAB_7", "LAB_4", "LAR_6"],
        ClauseType.MODIFICATION: ["TOS_12"],
        ClauseType.ARBITRATION: ["TOS_13", "TOS_14"],
        ClauseType.DURATION: ["LAB_6", "LAR_3"],
        ClauseType.RESTRICTIONS: ["LAB_8"],
    }
    
    @staticmethod
    def split_clauses(contract_text: str) -> List[str]:
        """
        Divide un contrato en cláusulas individuales.
        MEJORADO: Divide mejor por numeración y luego por párrafos.
        
        Args:
            contract_text: Texto del contrato completo
            
        Returns:
            Lista de cláusulas
        """
        clauses = []
        
        # Limpiar el texto
        contract_text = contract_text.strip()
        
        # Intentar dividir por números (1., 2., 3., etc.)
        if re.search(r'^\s*\d+[\.\-]\s+', contract_text, re.MULTILINE):
            # Dividir por patrón de número al inicio de línea
            parts = re.split(r'^\s*(\d+)[\.\-]\s+', contract_text, flags=re.MULTILINE)
            
            # Reconstruir cláusulas (parts[0] es vacío, luego número, texto, número, texto...)
            for i in range(1, len(parts), 2):
                if i + 1 < len(parts):
                    clause_num = parts[i]
                    clause_text = parts[i + 1].strip()
                    if clause_text and len(clause_text) > 10:
                        clauses.append(clause_text)
        
        # Si no hay, intentar dividir por saltos dobles
        elif '\n\n' in contract_text:
            clauses = [c.strip() for c in contract_text.split('\n\n')]
        
        # Si no hay, dividir por puntos seguidos de mayúscula
        elif re.search(r'(?<=[.!?])\s+(?=[A-Z])', contract_text):
            clauses = re.split(r'(?<=[.!?])\s+(?=[A-Z])', contract_text)
        
        # Última opción: dividir por saltos de línea simples
        else:
            clauses = contract_text.split('\n')
        
        # Limpiar cláusulas vacías, muy pequeñas y normalizar
        clauses = [
            c.strip() 
            for c in clauses 
            if c.strip() and len(c.strip()) > 15  # Mínimo 15 caracteres
        ]
        
        return clauses
    
    @staticmethod
    def detect_clause_type(clause_text: str) -> Tuple[ClauseType, float]:
        """
        Detecta el tipo de cláusula basado en palabras clave.
        
        Args:
            clause_text: Texto de la cláusula
            
        Returns:
            Tuple (tipo de cláusula, confianza 0-1)
        """
        text_lower = clause_text.lower()
        scores = {}
        
        for clause_type, patterns in ClauseClassifier.CLAUSE_PATTERNS.items():
            score = 0
            
            # Búsqueda de palabras clave
            for keyword in patterns["keywords"]:
                if keyword in text_lower:
                    score += 1
            
            # Palabras rojas aumentan más el score
            for red_flag in patterns["red_flags"]:
                if red_flag in text_lower:
                    score += 2
            
            if score > 0:
                scores[clause_type] = score
        
        if not scores:
            return ClauseType.OTHER, 0.0
        
        # Retornar tipo con puntuación más alta
        best_type = max(scores, key=scores.get)
        confidence = min(scores[best_type] / 5.0, 1.0)  # Normalizar
        
        return best_type, confidence
    
    @staticmethod
    def calculate_risk_level(clause_text: str, clause_type: ClauseType) -> Tuple[RiskLevel, float]:
        """
        Calcula el nivel de riesgo de una cláusula.
        MEJORADO: Puntuación más agresiva para detectar alto riesgo.
        
        Args:
            clause_text: Texto de la cláusula
            clause_type: Tipo de cláusula
            
        Returns:
            Tuple (nivel de riesgo, puntuación 0-100)
        """
        text_lower = clause_text.lower()
        risk_score = 0
        
        # Palabras rojas de ALTO riesgo (más puntos)
        high_risk_terms = [
            "sin causa", "sin previo aviso", "unilateral", "a discreción",
            "sin responsabilidad", "sin garantía", "sin consentimiento",
            "perpetuo", "indefinido", "irrevocable", "inmodificable",
            "se proporciona tal cual", "renuncia de derechos", "renuncia a",
            "sin compensación", "inmediatamente", "discrecional", "arbitraria",
            "exención", "limitación de responsabilidad"
        ]
        
        for term in high_risk_terms:
            if term in text_lower:
                risk_score += 30  # AUMENTADO de 25
        
        # Palabras de riesgo MEDIO
        medium_risk_terms = [
            "modificación", "cambio", "arbitraje", "limitación",
            "penalización", "actualización", "revisión"
        ]
        
        for term in medium_risk_terms:
            if term in text_lower:
                risk_score += 15
        
        # Longitud anormalmente larga = más riesgo
        if len(clause_text) > 500:
            risk_score += 20  # AUMENTADO de 15
        
        # Terminología confusa o legal compleja
        complex_terms = len(re.findall(r'\b[a-záéíóúñ]+(?:ción|dad|miento)\b', text_lower))
        risk_score += min(complex_terms * 3, 30)  # AUMENTADO
        
        # Si no hay palabras clave pero el tipo es riesgoso, aumentar score
        if risk_score < 10 and clause_type in [ClauseType.TERMINATION, ClauseType.LIABILITY]:
            risk_score = 20  # Mínimo base para tipos riesgosos
        
        # Limitar a 100
        risk_score = min(risk_score, 100)
        
        # Determinar nivel (umbrales más bajos para ser más sensible)
        if risk_score >= 50:  # BAJADO de 60
            risk_level = RiskLevel.HIGH
        elif risk_score >= 25:  # BAJADO de 30
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW
        
        return risk_level, risk_score
    
    @staticmethod
    def extract_key_terms(clause_text: str) -> List[str]:
        """
        Extrae términos clave de una cláusula.
        
        Args:
            clause_text: Texto de la cláusula
            
        Returns:
            Lista de términos clave
        """
        # Palabras a ignorar
        stop_words = {
            "el", "la", "de", "y", "a", "en", "del", "que", "por", "es",
            "se", "los", "las", "al", "una", "un", "este", "esta", "este",
            "será", "puede", "debe", "pueden", "deben", "son", "está",
            "han", "sea", "sin", "con", "para", "por", "como", "más"
        }
        
        # Extraer palabras significativas
        words = re.findall(r'\b[a-záéíóúñ]{4,}\b', clause_text.lower())
        key_terms = list(set(w for w in words if w not in stop_words))[:5]
        
        return sorted(key_terms)
    
    @staticmethod
    def classify_clause(clause_text: str, clause_id: str) -> ClassifiedClause:
        """
        Clasifica una cláusula completa.
        
        Args:
            clause_text: Texto de la cláusula
            clause_id: ID único de la cláusula
            
        Returns:
            Objeto ClassifiedClause con análisis completo
        """
        # Detectar tipo
        clause_type, type_confidence = ClauseClassifier.detect_clause_type(clause_text)
        
        # Calcular riesgo
        risk_level, risk_score = ClauseClassifier.calculate_risk_level(clause_text, clause_type)
        
        # Extraer términos clave
        key_terms = ClauseClassifier.extract_key_terms(clause_text)
        
        # Obtener leyes aplicables
        applicable_laws = ClauseClassifier.APPLICABLE_LAWS.get(clause_type, [])
        
        # Generar problema legal
        legal_issue = ClauseClassifier._generate_legal_issue(clause_text, clause_type, risk_level)
        
        # Generar recomendaciones
        recommendations = ClauseClassifier._generate_recommendations(clause_type, risk_level)
        
        return ClassifiedClause(
            id=clause_id,
            clause_text=clause_text[:200],  # Primeros 200 caracteres
            clause_type=clause_type,
            risk_level=risk_level,
            risk_score=risk_score,
            legal_issue=legal_issue,
            applicable_laws=applicable_laws,
            recommendations=recommendations,
            key_terms=key_terms
        )
    
    @staticmethod
    def _generate_legal_issue(clause_text: str, clause_type: ClauseType, risk_level: RiskLevel) -> str:
        """Genera descripción del problema legal."""
        issues = {
            ClauseType.TERMINATION: {
                RiskLevel.HIGH: "Rescisión unilateral sin causa y sin previo aviso - VIOLACIÓN de derechos laborales",
                RiskLevel.MEDIUM: "Terminación con condiciones no estándar",
                RiskLevel.LOW: "Procedimiento de terminación claro"
            },
            ClauseType.LIABILITY: {
                RiskLevel.HIGH: "Limitación de responsabilidad indebida o injusta - ABUSIVA",
                RiskLevel.MEDIUM: "Limitación de responsabilidad moderada",
                RiskLevel.LOW: "Limitación de responsabilidad razonable"
            },
            ClauseType.PRIVACY: {
                RiskLevel.HIGH: "Recopilación indefinida de datos sin consentimiento - VIOLACIÓN RGPD",
                RiskLevel.MEDIUM: "Tratamiento de datos con limitaciones",
                RiskLevel.LOW: "Protección de datos conforme a RGPD"
            },
            ClauseType.PAYMENT: {
                RiskLevel.HIGH: "Cambio unilateral de precios o reducción sin causa",
                RiskLevel.MEDIUM: "Actualización de precios periódica",
                RiskLevel.LOW: "Precios fijos durante el contrato"
            },
            ClauseType.MODIFICATION: {
                RiskLevel.HIGH: "Modificación unilateral sin consentimiento - ABUSIVA",
                RiskLevel.MEDIUM: "Modificación con previo aviso",
                RiskLevel.LOW: "Modificación por acuerdo mutuo"
            },
            ClauseType.ARBITRATION: {
                RiskLevel.HIGH: "Arbitraje obligatorio sin derecho a tribunal - LIMITACIÓN DE DERECHOS",
                RiskLevel.MEDIUM: "Mediación como primer paso",
                RiskLevel.LOW: "Resolución alternativa de disputas"
            },
            ClauseType.DURATION: {
                RiskLevel.HIGH: "Duración indefinida o perpetua - SIN SALIDA",
                RiskLevel.MEDIUM: "Renovación automática con salida",
                RiskLevel.LOW: "Duración definida con opción de renovación"
            },
            ClauseType.RESTRICTIONS: {
                RiskLevel.HIGH: "Restricción perpetua e ilimitada - ABUSIVA",
                RiskLevel.MEDIUM: "Restricción temporal o limitada",
                RiskLevel.LOW: "Restricción razonable y limitada"
            }
        }
        
        return issues.get(clause_type, {}).get(risk_level, "Problema legal desconocido")
    
    @staticmethod
    def _generate_recommendations(clause_type: ClauseType, risk_level: RiskLevel) -> List[str]:
        """Genera recomendaciones basadas en el tipo y riesgo."""
        recommendations = []
        
        if risk_level == RiskLevel.HIGH:
            recommendations.append("⚠️ CRÍTICO: REVISAR CON ABOGADO - Riesgos significativos")
            recommendations.append("📋 NO FIRMES sin negociar esta cláusula")
            recommendations.append("💬 Solicita cambios ANTES de firmar")
        
        elif risk_level == RiskLevel.MEDIUM:
            recommendations.append("⚠️ REVISAR: Asegúrate de entender esta cláusula")
            recommendations.append("📋 Considera solicitar cambios en los términos")
        
        else:
            recommendations.append("✅ Esta cláusula parece razonable")
            recommendations.append("📋 Pero aún debes revisar según tu contexto")
        
        # Recomendaciones específicas por tipo
        if clause_type == ClauseType.TERMINATION:
            recommendations.append("💡 Exige que se especifiquen los motivos válidos de terminación")
        
        elif clause_type == ClauseType.LIABILITY:
            recommendations.append("💡 Verifica cobertura completa de daños y responsabilidades")
        
        elif clause_type == ClauseType.PRIVACY:
            recommendations.append("💡 Exige derechos de acceso, rectificación y eliminación de datos")
        
        elif clause_type == ClauseType.MODIFICATION:
            recommendations.append("💡 Requiere TU consentimiento para cambios importantes")
        
        return recommendations[:3]  # Máximo 3 recomendaciones
    
    @classmethod
    def classify_contract(cls, contract_text: str) -> List[ClassifiedClause]:
        """
        Clasifica un contrato completo.
        
        Args:
            contract_text: Texto del contrato
            
        Returns:
            Lista de cláusulas clasificadas
        """
        # Dividir en cláusulas
        clauses = cls.split_clauses(contract_text)
        
        # Clasificar cada cláusula
        classified = []
        for idx, clause in enumerate(clauses, 1):
            classified_clause = cls.classify_clause(clause, f"clause_{idx}")
            classified.append(classified_clause)
        
        return classified
    
    @classmethod
    def get_summary(cls, classified_clauses: List[ClassifiedClause]) -> Dict:
        """
        Genera un resumen del análisis.
        
        Args:
            classified_clauses: Cláusulas clasificadas
            
        Returns:
            Dict con estadísticas
        """
        high_risk = len([c for c in classified_clauses if c.risk_level == RiskLevel.HIGH])
        medium_risk = len([c for c in classified_clauses if c.risk_level == RiskLevel.MEDIUM])
        low_risk = len([c for c in classified_clauses if c.risk_level == RiskLevel.LOW])
        
        avg_risk = sum(c.risk_score for c in classified_clauses) / len(classified_clauses) if classified_clauses else 0
        
        return {
            "total_clauses": len(classified_clauses),
            "high_risk": high_risk,
            "medium_risk": medium_risk,
            "low_risk": low_risk,
            "average_risk_score": round(avg_risk, 1),
            "risk_percentage": round((high_risk / len(classified_clauses) * 100) if classified_clauses else 0, 1)
        }