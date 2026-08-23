# Arquivo: core/models.py
# Propósito: Definição estrutural de todos os dados do Master ADE.

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any

# ==========================================
# 1. ESTRUTURA DO EDITAL E CONTEÚDO
# ==========================================

@dataclass
class Discipline:
    """Representa uma disciplina do edital (ex: Língua Portuguesa, Específicos)."""
    id: str
    name: str
    total_questions_expected: Optional[int] = None
    weight: Optional[float] = 1.0

@dataclass
class Topic:
    """Representa um tema dentro da disciplina (ex: LDB, Porcentagem)."""
    id: str
    discipline_id: str
    name: str

@dataclass
class Competency:
    """Microcompetência específica que pode ser dominada e avaliada."""
    id: str
    topic_id: str
    name: str
    description: str
    prerequisites: List[str] = field(default_factory=list) # IDs de outras competências
    importance: float = 0.5 # Peso para o algoritmo de prioridade

@dataclass
class ContentNode:
    """A estrutura fragmentada de conteúdo (conceito, pegadinha, etc)."""
    id: str
    competency_id: str
    concept: str
    simple_explanation: str
    deep_explanation: str
    example: str
    contrast: Optional[str] = None
    trap_warning: Optional[str] = None # A "pegadinha" da banca

# ==========================================
# 2. MOTOR DE QUESTÕES E AVALIAÇÃO
# ==========================================

@dataclass
class Question:
    """Estrutura rígida e inteligente de uma questão do banco."""
    id: str
    competency_ids: List[str] # Uma questão pode avaliar várias competências
    difficulty: float # 0.0 a 10.0
    question_type: str # ex: "aplicacao", "conceitual"
    target_time_seconds: int
    statement: str
    options: List[str]
    correct_option_index: int
    explanation: str
    distractors: Dict[int, str] = field(default_factory=dict) # Mapeia o índice da opção errada para o TIPO de erro
    source_bank: str = "Avança SP"
    metadata: Dict[str, Any] = field(default_factory=dict)

# ==========================================
# 3. ESTADOS COGNITIVOS E TENTATIVAS
# ==========================================

@dataclass
class Attempt:
    """O registro puro de uma interação do candidato com uma questão."""
    id: str
    question_id: str
    competency_id: str
    correct: bool
    difficulty: float
    time_seconds: float
    confidence: Optional[int] = None # 1 (Chute) a 5 (Absoluta)
    error_type: Optional[str] = None # KNOWLEDGE_GAP, CARELESS, etc.
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass
class Error:
    """Classificação detalhada de um erro para acionar o Tutor IA."""
    id: str
    attempt_id: str
    error_type: str
    suspected_cause: str
    recommended_action: str
    resolved: bool = False

@dataclass
class SkillState:
    """A memória do motor de domínio para uma competência específica."""
    competency_id: str
    mastery: float = 0.0
    retention: float = 0.0
    application: float = 0.0
    speed: float = 0.0
    consistency: float = 0.0
    attempts: int = 0
    correct: int = 0
    risk: float = 1.0
    last_seen: Optional[datetime] = None
    next_review: Optional[datetime] = None
    error_counts: Dict[str, int] = field(default_factory=dict)

# ==========================================
# 4. SESSÕES, REVISÕES E SIMULADOS
# ==========================================

@dataclass
class Candidate:
    """Perfil global do estudante e suas métricas de prontidão."""
    id: str
    name: str
    target_exam: str = "ADE Limeira"
    overall_readiness: float = 0.0
    xp_points: int = 0
    weakest_competencies: List[str] = field(default_factory=list)

@dataclass
class StudySession:
    """Sessão de estudo dinâmica gerada pelo Adaptive Engine."""
    id: str
    candidate_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    planned_missions: List[Dict[str, Any]] = field(default_factory=list)
    completed_missions: int = 0

@dataclass
class Review:
    """Agendamento de repetição espaçada."""
    id: str
    competency_id: str
    scheduled_date: datetime
    urgency_level: str # "HIGH", "MEDIUM", "LOW"
    status: str = "PENDING"

@dataclass
class Simulation:
    """Resultado de um simulado no modo 'Provar'."""
    id: str
    candidate_id: str
    timestamp: datetime
    total_questions: int
    correct_answers: int
    time_taken_seconds: float
    estimated_score: float
    projected_interval_min: float
    projected_interval_max: float
    risk_areas: List[str] = field(default_factory=list)
    opportunities: List[str] = field(default_factory=list)
