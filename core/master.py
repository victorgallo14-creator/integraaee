# Arquivo: core/mastery.py
# Propósito: Motor Cognitivo para cálculo de domínio, retenção e risco.

from datetime import datetime, timezone
from math import exp
from typing import Dict
from core.models import Attempt, SkillState

class MasteryEngine:
    def __init__(self):
        # Em produção, este dicionário será substituído ou alimentado pelo banco de dados (ex: Supabase)
        self.states: Dict[str, SkillState] = {}

    def get_state(self, competency_id: str) -> SkillState:
        """Recupera ou inicializa o estado cognitivo de uma competência."""
        if competency_id not in self.states:
            self.states[competency_id] = SkillState(competency_id=competency_id)
        return self.states[competency_id]

    def register_attempt(self, attempt: Attempt):
        """Processa uma nova resposta e recalcula todas as métricas do aluno."""
        state = self.get_state(attempt.competency_id)
        state.attempts += 1
        
        if attempt.correct:
            state.correct += 1

        if attempt.error_type:
            state.error_counts[attempt.error_type] = state.error_counts.get(attempt.error_type, 0) + 1

        state.last_seen = attempt.timestamp

        self._update_mastery(state, attempt)
        self._update_speed(state, attempt)
        self._update_consistency(state)
        self._update_retention(state)
        self._update_risk(state)

    def _update_mastery(self, state: SkillState, attempt: Attempt):
        """Calcula o domínio ponderando a dificuldade da questão."""
        performance = 1.0 if attempt.correct else 0.0
        
        # Questões mais difíceis geram maior evidência de aprendizado
        difficulty_factor = 0.7 + (attempt.difficulty / 10.0) * 0.3
        evidence = performance * difficulty_factor
        
        learning_rate = 0.18
        state.mastery += learning_rate * (evidence - state.mastery)
        state.mastery = max(0.0, min(1.0, state.mastery))

    def _update_speed(self, state: SkillState, attempt: Attempt):
        """Mede a velocidade de resolução contra um tempo alvo."""
        if attempt.time_seconds is None:
            return
            
        target = 90.0 # Segundos ideais para uma questão de concurso
        performance = min(1.0, target / max(attempt.time_seconds, 1))
        
        if state.speed == 0:
            state.speed = performance
        else:
            # Média móvel exponencial para suavizar variações de velocidade
            state.speed = (state.speed * 0.8 + performance * 0.2)

    def _update_consistency(self, state: SkillState):
        """Atualiza a taxa histórica de acertos gerais."""
        if state.attempts > 0:
            state.consistency = state.correct / state.attempts

    def _update_retention(self, state: SkillState):
        """Aplica a curva de esquecimento baseada no tempo sem revisar."""
        if state.last_seen is None:
            state.retention = 0.0
            return

        now = datetime.now(timezone.utc)
        days = (now - state.last_seen).total_seconds() / 86400
        
        # Curva simples de decaimento: perde força considerável após 14 dias sem contato
        decay = exp(-days / 14)
        state.retention = state.mastery * decay

    def _update_risk(self, state: SkillState):
        """Mede o perigo de errar a questão na prova cruzando déficit de domínio e esquecimento."""
        deficit = 1 - state.mastery
        retention_deficit = 1 - state.retention
        
        # O risco é composto 60% por não saber a matéria e 40% por estar esquecendo
        risk = (deficit * 0.60 + retention_deficit * 0.40)
        state.risk = max(0.0, min(1.0, risk))

    def level(self, competency_id: str) -> str:
        """Classifica o estágio atual do aluno na competência."""
        state = self.get_state(competency_id)
        if state.mastery < 0.40:
            return "fragil"
        if state.mastery < 0.65:
            return "instavel"
        if state.mastery < 0.85:
            return "proficiente"
        return "dominado"

    def priority(self, competency_id: str, importance: float = 0.5) -> float:
        """Define a urgência de estudo cruzando o risco do aluno com o peso da matéria no edital."""
        state = self.get_state(competency_id)
        return state.risk * importance

    def next_action(self, competency_id: str) -> str:
        """Recomenda o tipo de estudo ideal com base nas fragilidades específicas detectadas."""
        state = self.get_state(competency_id)
        
        if state.mastery < 0.40:
            return "estudar_teoria"
        if state.retention < 0.55:
            return "revisar"
        if state.application < 0.60:
            return "questoes_aplicacao"
        if state.speed < 0.60:
            return "treino_cronometrado"
            
        return "questoes_desafio"
