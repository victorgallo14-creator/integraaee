# Arquivo: core/adaptive.py
# Propósito: Adaptive Engine - Gera a missão de estudo focada nas suas maiores fraquezas.

from typing import List, Dict, Any
from core.models import Competency
from core.mastery import MasteryEngine

class AdaptiveEngine:
    def __init__(self, mastery_engine: MasteryEngine, competencies: List[Competency]):
        """
        Recebe o motor de domínio (que sabe os seus riscos) e a lista de 
        todas as competências do edital (que têm o peso da prova).
        """
        self.mastery = mastery_engine
        self.competencies = {c.id: c for c in competencies}

    def calculate_priorities(self) -> List[Dict[str, Any]]:
        """Calcula o índice de letalidade de cada competência para a sua aprovação."""
        priorities = []
        
        for comp_id, comp in self.competencies.items():
            state = self.mastery.get_state(comp_id)
            
            # O Déficit é o quanto falta para dominar o assunto (100% - seu domínio atual)
            deficit = 1.0 - state.mastery
            
            # O Risco é a chance de você errar na prova hoje (calculado no mastery.py)
            risk = state.risk
            
            # O algoritmo implacável de prioridade:
            # Multiplicamos o que você não sabe (déficit) x a chance de errar (risco) x peso no edital (importância)
            priority_score = deficit * risk * comp.importance
            
            # Define o status visual
            status = "🟢 Dominado"
            if state.mastery < 0.4: status = "🔴 Frágil"
            elif state.mastery < 0.65: status = "🟠 Instável"
            elif state.mastery < 0.85: status = "🟡 Proficiente"
            
            # Recomenda a próxima ação com base no diagnóstico do motor cognitivo
            next_action_code = self.mastery.next_action(comp_id)
            action_map = {
                "estudar_teoria": "Ler Teoria + Questões Básicas",
                "revisar": "Revisão Espaçada (Curva de Esquecimento)",
                "questoes_aplicacao": "Treino Prático (Foco em Aplicação)",
                "treino_cronometrado": "Treino de Velocidade (Contra o Relógio)",
                "questoes_desafio": "Questões Nível Hard (Banca Avança SP)"
            }
            
            priorities.append({
                "competency_id": comp_id,
                "name": comp.name,
                "priority_score": priority_score,
                "status": status,
                "mastery": state.mastery,
                "risk": risk,
                "recommended_action": action_map.get(next_action_code, "Estudo Misto"),
                "action_code": next_action_code
            })
            
        # Ordena do maior perigo (maior score) para o menor
        priorities.sort(key=lambda x: x["priority_score"], reverse=True)
        return priorities

    def generate_mission(self, available_minutes: int = 45) -> Dict[str, Any]:
        """
        Pega o seu tempo disponível hoje e fatia entre os seus maiores pontos cegos.
        """
        ranked_priorities = self.calculate_priorities()
        
        # Seleciona os 3 maiores riscos atuais
        top_risks = ranked_priorities[:3]
        
        # Procura 1 competência que você já estudou, mas que a retenção está caindo (Curva de Esquecimento)
        review_targets = [p for p in ranked_priorities[3:] if p["action_code"] == "revisar"]
        review_comp = review_targets[0] if review_targets else ranked_priorities[3]
        
        # Alocação de Tempo Inteligente (em minutos) baseada no tempo disponível
        mission_items = []
        
        # Alvo 1: Maior fraqueza (Leva ~35% do tempo)
        time_1 = int(available_minutes * 0.35)
        mission_items.append({
            "order": 1,
            "type": "Foco Crítico",
            "target": top_risks[0],
            "time_minutes": time_1,
            "questions_target": int(time_1 * 1.2) # Estima 1.2 questões por minuto
        })
        
        # Alvo 2: Segunda maior fraqueza (~25% do tempo)
        time_2 = int(available_minutes * 0.25)
        mission_items.append({
            "order": 2,
            "type": "Reforço",
            "target": top_risks[1],
            "time_minutes": time_2,
            "questions_target": int(time_2 * 1.2)
        })
        
        # Alvo 3: Terceira maior fraqueza (~20% do tempo)
        time_3 = int(available_minutes * 0.20)
        mission_items.append({
            "order": 3,
            "type": "Reforço",
            "target": top_risks[2],
            "time_minutes": time_3,
            "questions_target": int(time_3 * 1.2)
        })
        
        # Alvo 4: Resgate de Memória (~20% do tempo)
        time_4 = available_minutes - (time_1 + time_2 + time_3)
        mission_items.append({
            "order": 4,
            "type": "Revisão Ativa",
            "target": review_comp,
            "time_minutes": time_4,
            "questions_target": int(time_4 * 1.5) # Revisão costuma ser mais rápida
        })
        
        return {
            "total_time": available_minutes,
            "total_questions": sum(m["questions_target"] for m in mission_items),
            "mission_items": mission_items
        }
