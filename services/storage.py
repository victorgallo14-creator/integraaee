# Arquivo: services/storage.py
# Propósito: Camada de persistência de dados no Supabase para o Master ADE.

import json
from datetime import datetime
from core.models import Attempt, SkillState

class SupabaseStorage:
    def __init__(self, supabase_client):
        """
        Recebe o cliente do Supabase já inicializado no app_pei.py.
        Dessa forma, não precisamos duplicar as chaves de acesso.
        """
        self.db = supabase_client

    def save_attempt(self, attempt: Attempt):
        """Grava uma nova tentativa na tabela attempts do Supabase."""
        data = {
            "question_id": attempt.question_id,
            "competency_id": attempt.competency_id,
            "correct": attempt.correct,
            "difficulty": attempt.difficulty,
            "time_seconds": attempt.time_seconds,
            "confidence": attempt.confidence,
            "error_type": attempt.error_type,
            "timestamp": attempt.timestamp.isoformat()
        }
        
        try:
            self.db.table("attempts").insert(data).execute()
        except Exception as e:
            print(f"Erro ao salvar tentativa no Supabase: {e}")

    def save_skill_state(self, state: SkillState):
        """
        Faz o UPSERT (atualiza se existir, insere se for novo) do estado 
        cognitivo na tabela skill_states do Supabase.
        """
        data = {
            "competency_id": state.competency_id,
            "mastery": state.mastery,
            "retention": state.retention,
            "application": state.application,
            "speed": state.speed,
            "consistency": state.consistency,
            "attempts": state.attempts,
            "correct": state.correct,
            "risk": state.risk,
            "last_seen": state.last_seen.isoformat() if state.last_seen else None,
            "next_review": state.next_review.isoformat() if state.next_review else None,
            "error_counts": state.error_counts
        }
        
        try:
            # O upsert garante que a linha daquela competência seja atualizada com as métricas mais recentes
            self.db.table("skill_states").upsert(data).execute()
        except Exception as e:
            print(f"Erro ao salvar estado cognitivo no Supabase: {e}")
            
    def load_all_skill_states(self) -> dict:
        """
        Carrega toda a sua memória cognitiva do banco ao iniciar o aplicativo,
        restaurando o cérebro da plataforma com o seu progresso exato.
        """
        try:
            response = self.db.table("skill_states").select("*").execute()
            states = {}
            for row in response.data:
                state = SkillState(
                    competency_id=row["competency_id"],
                    mastery=row.get("mastery", 0.0),
                    retention=row.get("retention", 0.0),
                    application=row.get("application", 0.0),
                    speed=row.get("speed", 0.0),
                    consistency=row.get("consistency", 0.0),
                    attempts=row.get("attempts", 0),
                    correct=row.get("correct", 0),
                    risk=row.get("risk", 1.0),
                    error_counts=row.get("error_counts", {})
                )
                
                # Tratamento de datas vindo do banco
                if row.get("last_seen"):
                    state.last_seen = datetime.fromisoformat(row["last_seen"].replace("Z", "+00:00"))
                if row.get("next_review"):
                    state.next_review = datetime.fromisoformat(row["next_review"].replace("Z", "+00:00"))
                    
                states[row["competency_id"]] = state
                
            return states
        except Exception as e:
            print(f"Erro ao carregar estados do Supabase: {e}")
            return {}
