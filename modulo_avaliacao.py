# -*- coding: utf-8 -*-
"""
Integra | Avaliação e Aprendizagem
Versão 3 — impacto pedagógico, fluxo guiado e interface centrada em decisões de ensino.

Integração mínima no app_pei.py::

    elif app_mode_regular == "📊 Avaliação e Aprendizagem":
        from avaliacao import renderizar_avaliacao
        renderizar_avaliacao(supabase)

Arquivos esperados na mesma pasta:
- app_pei.py
- avaliacao.py
- dados_avaliacao_completo.py

A versão 2 mantém compatibilidade com os registros já gravados na tabela
``Avaliacao``: cobertura, blueprint e registros individuais dos estudantes.
Não gera PDF: o próprio sistema passa a ser o instrumento de orientação,
registro, análise e fechamento do trimestre.
"""
from __future__ import annotations

import html
import json
import math
import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import pandas as pd
import streamlit as st

from dados_avaliacao_completo import AVALIACAO_DB, METADADOS_AVALIACAO

MODULO_AVALIACAO_VERSAO = "2026.09.24-v3-impacto-pedagogico"
TABLE_NAME = "Avaliacao"

STATUS_APRENDIZAGEM = {
    "NE": "Evidência insuficiente",
    "NC": "Não consolidado",
    "EP": "Em processo",
    "C": "Consolidado",
    "AA": "Aprendizagem ampliada",
}
STATUS_DESCRICAO = {
    "NE": "Ainda não há evidência suficiente para julgar esta aprendizagem.",
    "NC": "A aprendizagem foi ensinada/retomada, mas ainda não foi demonstrada de forma suficiente.",
    "EP": "A aprendizagem aparece parcialmente, oscila ou ainda depende de apoio.",
    "C": "A aprendizagem esperada é demonstrada com autonomia compatível com o ano.",
    "AA": "O estudante amplia o esperado, relacionando, justificando ou transferindo a aprendizagem.",
}
PERCURSOS = {
    "P1": "Recomposição intensiva",
    "P2": "Recomposição articulada ao ano corrente",
    "P3": "Currículo do ano predominante",
    "P4": "Currículo do período consolidado / em ampliação",
}
SITUACAO_CURRICULAR = {
    "AT": "Trabalhada e avaliada",
    "ED": "Em desenvolvimento",
    "RP": "Reprogramada",
}
SITUACAO_DESCRICAO = {
    "AT": "Foi suficientemente desenvolvida e produzirá evidência para o fechamento.",
    "ED": "Ainda está sendo desenvolvida; não deve ser forçada no conceito final.",
    "RP": "Será retomada/reprogramada; não pode ser convertida automaticamente em NC.",
}
CONCEITOS = ["AB", "B", "AD", "A"]
STATUS_OPCOES = ["", "NE", "NC", "EP", "C", "AA"]
PERCURSO_OPCOES = ["", "P1", "P2", "P3", "P4"]
SITUACAO_OPCOES = ["ED", "AT", "RP"]

GESTAO_MATRICULAS = {
    "8257601", "8844051", "8084912", "8829405",
    "8011512", "8258411", "7047682", "88286861",
}

COMPONENTE_META = {
    "Língua Portuguesa": {"icone": "📖", "cor": "#7c3aed", "suave": "#f5f3ff"},
    "Matemática": {"icone": "➗", "cor": "#2563eb", "suave": "#eff6ff"},
    "Ciências": {"icone": "🔬", "cor": "#059669", "suave": "#ecfdf5"},
    "História": {"icone": "🏺", "cor": "#b45309", "suave": "#fffbeb"},
    "Geografia": {"icone": "🌎", "cor": "#0f766e", "suave": "#f0fdfa"},
}


# -----------------------------------------------------------------------------
# Utilitários
# -----------------------------------------------------------------------------

def _norm(texto: Any) -> str:
    s = str(texto or "").strip().upper()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s)


def _slug(texto: Any) -> str:
    s = re.sub(r"[^A-Z0-9]+", "_", _norm(texto)).strip("_")
    return s or "SEM_VALOR"


def _esc(texto: Any) -> str:
    return html.escape(str(texto or ""), quote=True)


def _agora_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ano_da_turma(turma: str) -> Optional[int]:
    texto = _norm(turma)
    m = re.search(r"(?<!\d)([1-5])\s*(?:[Oº°])?\s*ANO\b", texto, flags=re.IGNORECASE)
    if m:
        return int(m.group(1))
    if "ANO" in texto:
        m = re.search(r"(?<!\d)([1-5])(?!\d)", texto)
        if m:
            return int(m.group(1))
    return None


def _componente_slug(componente: str) -> str:
    mapa = {
        "Língua Portuguesa": "LP",
        "Matemática": "MAT",
        "Ciências": "CIE",
        "História": "HIS",
        "Geografia": "GEO",
    }
    return mapa.get(componente, _slug(componente)[:12])


def _chave_registro(
    tipo: str,
    ano_letivo: int,
    ano_escolar: int,
    trimestre: int,
    turma: str,
    componente: str = "",
    aluno: str = "",
) -> str:
    partes = [tipo, ano_letivo, ano_escolar, trimestre, _slug(turma)]
    if componente:
        partes.append(_componente_slug(componente))
    if aluno:
        partes.append(_slug(aluno))
    return "|".join(map(str, partes))


def _percentual(parte: int, total: int) -> int:
    return int(round((parte / total) * 100)) if total else 0


def _format_status(status: str) -> str:
    if not status:
        return "— selecionar —"
    return f"{status} · {STATUS_APRENDIZAGEM.get(status, status)}"


def _format_situacao(status: str) -> str:
    icones = {"AT": "✅", "ED": "🟡", "RP": "↪️"}
    return f"{icones.get(status, '')} {SITUACAO_CURRICULAR.get(status, status)}"


def _status_badge(status: str) -> str:
    estilos = {
        "NE": ("#475569", "#f1f5f9"),
        "NC": ("#b91c1c", "#fef2f2"),
        "EP": ("#a16207", "#fefce8"),
        "C": ("#047857", "#ecfdf5"),
        "AA": ("#6d28d9", "#f5f3ff"),
        "AB": ("#b91c1c", "#fef2f2"),
        "B": ("#a16207", "#fefce8"),
        "AD": ("#047857", "#ecfdf5"),
        "A": ("#6d28d9", "#f5f3ff"),
    }
    fg, bg = estilos.get(status, ("#64748b", "#f8fafc"))
    return f'<span class="av-badge" style="color:{fg};background:{bg};">{_esc(status or "—")}</span>'


@dataclass
class Contexto:
    ano_letivo: int
    ano_escolar: int
    trimestre: int
    turma: str
    componente: str


# -----------------------------------------------------------------------------
# Persistência
# -----------------------------------------------------------------------------

class AvaliacaoRepo:
    def __init__(self, supabase: Any, usuario: str):
        self.supabase = supabase
        self.usuario = usuario or "Usuário"

    def disponivel(self) -> Tuple[bool, str]:
        try:
            self.supabase.table(TABLE_NAME).select("id").limit(1).execute()
            return True, ""
        except Exception as exc:
            return False, str(exc)

    def _payload(
        self,
        chave: str,
        tipo: str,
        ctx: Contexto,
        dados: Mapping[str, Any],
        aluno: str = "",
    ) -> Dict[str, Any]:
        return {
            "chave": chave,
            "tipo": tipo,
            "ano_letivo": int(ctx.ano_letivo),
            "ano_escolar": int(ctx.ano_escolar),
            "trimestre": int(ctx.trimestre),
            "turma": ctx.turma,
            "componente": ctx.componente,
            "aluno_nome": aluno or None,
            "dados_json": dict(dados),
            "atualizado_por": self.usuario,
            "atualizado_em": _agora_iso(),
        }

    def obter(self, tipo: str, ctx: Contexto, aluno: str = "") -> Dict[str, Any]:
        chave = _chave_registro(
            tipo, ctx.ano_letivo, ctx.ano_escolar, ctx.trimestre,
            ctx.turma, ctx.componente, aluno,
        )
        try:
            res = self.supabase.table(TABLE_NAME).select("dados_json").eq("chave", chave).limit(1).execute()
            rows = getattr(res, "data", None) or []
            if not rows:
                return {}
            dados = rows[0].get("dados_json", {})
            if isinstance(dados, str):
                try:
                    dados = json.loads(dados)
                except Exception:
                    dados = {}
            return dados or {}
        except Exception:
            return {}

    def salvar(self, tipo: str, ctx: Contexto, dados: Mapping[str, Any], aluno: str = "") -> None:
        chave = _chave_registro(
            tipo, ctx.ano_letivo, ctx.ano_escolar, ctx.trimestre,
            ctx.turma, ctx.componente, aluno,
        )
        payload = self._payload(chave, tipo, ctx, dados, aluno)
        self.supabase.table(TABLE_NAME).upsert(payload, on_conflict="chave").execute()

    def salvar_varios(self, registros: Sequence[Tuple[str, Contexto, Mapping[str, Any], str]]) -> None:
        payloads: List[Dict[str, Any]] = []
        for tipo, ctx, dados, aluno in registros:
            chave = _chave_registro(
                tipo, ctx.ano_letivo, ctx.ano_escolar, ctx.trimestre,
                ctx.turma, ctx.componente, aluno,
            )
            payloads.append(self._payload(chave, tipo, ctx, dados, aluno))
        if payloads:
            self.supabase.table(TABLE_NAME).upsert(payloads, on_conflict="chave").execute()

    def listar_alunos(self, ctx: Contexto) -> Dict[str, Dict[str, Any]]:
        try:
            q = (
                self.supabase.table(TABLE_NAME)
                .select("aluno_nome,dados_json")
                .eq("tipo", "aluno")
                .eq("ano_letivo", ctx.ano_letivo)
                .eq("ano_escolar", ctx.ano_escolar)
                .eq("trimestre", ctx.trimestre)
                .eq("turma", ctx.turma)
                .eq("componente", ctx.componente)
            )
            res = q.execute()
            out: Dict[str, Dict[str, Any]] = {}
            for row in getattr(res, "data", None) or []:
                nome = row.get("aluno_nome") or ""
                dados = row.get("dados_json") or {}
                if isinstance(dados, str):
                    try:
                        dados = json.loads(dados)
                    except Exception:
                        dados = {}
                if nome:
                    out[nome] = dados
            return out
        except Exception:
            return {}


# -----------------------------------------------------------------------------
# Base curricular e permissões
# -----------------------------------------------------------------------------

def _base_curricular(ano: int, trimestre: int, componente: str) -> Dict[str, Any]:
    return AVALIACAO_DB.get(ano, {}).get(trimestre, {}).get(componente, {})


def _anos_disponiveis() -> List[int]:
    return sorted(AVALIACAO_DB)


def _trimestres_disponiveis(ano: int) -> List[int]:
    return sorted(AVALIACAO_DB.get(ano, {}))


def _componentes_disponiveis(ano: int, trimestre: int) -> List[str]:
    preferencia = ["Língua Portuguesa", "Matemática", "Ciências", "História", "Geografia"]
    existentes = list(AVALIACAO_DB.get(ano, {}).get(trimestre, {}).keys())
    return [x for x in preferencia if x in existentes] + [x for x in existentes if x not in preferencia]


def _config_valor(supabase: Any, chave: str) -> Any:
    try:
        res = supabase.table("Config_Ata").select("valor").eq("chave", chave).limit(1).execute()
        rows = getattr(res, "data", None) or []
        return rows[0].get("valor") if rows else None
    except Exception:
        return None


def _config_json(supabase: Any, chave: str) -> Any:
    valor = _config_valor(supabase, chave)
    if valor in (None, ""):
        return None
    if isinstance(valor, (dict, list)):
        return valor
    try:
        return json.loads(valor)
    except Exception:
        return None


def _carregar_matriz_professores(supabase: Any) -> pd.DataFrame:
    dados = _config_json(supabase, "matriz_professores")
    if isinstance(dados, list):
        try:
            return pd.DataFrame(dados)
        except Exception:
            pass
    return pd.DataFrame(columns=["Ciclo", "Turma", "Disciplina", "Professor"])


def _nomes_gestao_configurados(supabase: Any) -> set[str]:
    dados = _config_json(supabase, "matriz_gestao")
    nomes: set[str] = set()
    if isinstance(dados, list):
        for item in dados:
            if isinstance(item, dict) and item.get("Nome"):
                nomes.add(_norm(item.get("Nome")))
    return nomes


def _eh_gestor(matricula: str, nome: str = "", supabase: Any = None) -> bool:
    if str(matricula or "").strip() in GESTAO_MATRICULAS:
        return True
    nome_norm = _norm(nome)
    if supabase is not None and nome_norm in _nomes_gestao_configurados(supabase):
        return True
    if str(st.session_state.get("user_role", "")).strip().lower() in {"admin", "gestor", "diretor", "coordenador"}:
        return True
    nomes_fallback = {
        "José Victor Souza Gallo", "Luciana Lopes Faber", "Oelen Fernando Pedro",
        "Luciana Martinati Tetzner", "Noreh Cristina Heldt Aldrigui",
        "Marília Motta Camargo dos Reis",
    }
    return nome_norm in {_norm(x) for x in nomes_fallback}


def _turmas_permitidas(
    matriz_professores: Optional[pd.DataFrame],
    usuario_nome: str,
    gestor: bool,
    supabase: Any,
    ano_escolar: int,
) -> List[str]:
    turmas: List[str] = []
    if isinstance(matriz_professores, pd.DataFrame) and not matriz_professores.empty:
        df = matriz_professores.copy()
        if "Turma" in df.columns:
            if not gestor and "Professor" in df.columns:
                df = df[df["Professor"].map(_norm) == _norm(usuario_nome)]
            turmas = [str(x).strip() for x in df.get("Turma", pd.Series(dtype=str)).dropna().tolist()]
            turmas = [t for t in turmas if _ano_da_turma(t) == ano_escolar]

    if gestor or not turmas:
        try:
            res = supabase.table("Carometro").select("turma").execute()
            for row in getattr(res, "data", None) or []:
                turma = str(row.get("turma", "")).strip()
                if _ano_da_turma(turma) == ano_escolar:
                    turmas.append(turma)
        except Exception:
            pass

    seen: set[str] = set()
    saida: List[str] = []
    for turma in turmas:
        chave = _norm(turma)
        if chave and chave not in seen:
            seen.add(chave)
            saida.append(turma)
    return sorted(saida, key=_norm)


def _alunos_da_turma(supabase: Any, turma: str) -> List[str]:
    try:
        res = supabase.table("Carometro").select("nome,turma").execute()
        alunos = []
        for row in getattr(res, "data", None) or []:
            if _norm(row.get("turma")) == _norm(turma):
                nome = str(row.get("nome", "")).strip()
                if nome:
                    alunos.append(nome)
        return sorted(set(alunos), key=_norm)
    except Exception:
        return []


def _componentes_permitidos(
    matriz_professores: Optional[pd.DataFrame],
    usuario_nome: str,
    gestor: bool,
    turma: str,
    disponiveis: List[str],
) -> List[str]:
    if gestor or not isinstance(matriz_professores, pd.DataFrame) or matriz_professores.empty:
        return disponiveis
    if not {"Professor", "Turma", "Disciplina"}.issubset(matriz_professores.columns):
        return disponiveis

    df = matriz_professores.copy()
    df = df[
        (df["Professor"].map(_norm) == _norm(usuario_nome))
        & (df["Turma"].map(_norm) == _norm(turma))
    ]
    discs = {_norm(x) for x in df["Disciplina"].dropna().astype(str)}
    if "POLIVALENTE" in discs:
        return disponiveis

    mapa = {
        "LINGUA PORTUGUESA": "Língua Portuguesa",
        "MATEMATICA": "Matemática",
        "CIENCIAS": "Ciências",
        "HISTORIA": "História",
        "GEOGRAFIA": "Geografia",
    }
    permitidos: List[str] = []
    for disc in discs:
        if disc in {"CIENCIAS, HIST. E GEO.", "CIENCIAS, HIST E GEO", "CIENCIAS HISTORIA E GEOGRAFIA"}:
            permitidos.extend([x for x in ["Ciências", "História", "Geografia"] if x in disponiveis])
        elif mapa.get(disc) in disponiveis:
            permitidos.append(mapa[disc])
    return list(dict.fromkeys(permitidos)) or disponiveis


# -----------------------------------------------------------------------------
# Motor pedagógico
# -----------------------------------------------------------------------------

def _codigos_estruturantes(base: Mapping[str, Any]) -> List[str]:
    return [d["codigo"] for d in base.get("dimensoes", []) if _norm(d.get("peso")) == "ESTRUTURANTE"]


def _default_cobertura(base: Mapping[str, Any]) -> Dict[str, Any]:
    # ED é o ponto de partida mais seguro: nada entra automaticamente no fechamento.
    return {
        d["codigo"]: {"situacao": "ED", "recomposicao": "", "observacao": ""}
        for d in base.get("dimensoes", [])
    }


def _default_blueprint(base: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        str(item["id"]): {"incluida": False, "instrumento": "", "observacao": ""}
        for item in base.get("blueprint", [])
    }


def _blueprint_avancado(blueprint_estado: Mapping[str, Any], base: Mapping[str, Any]) -> Tuple[bool, int]:
    avancados = 0
    for item in base.get("blueprint", []):
        sid = str(item.get("id", ""))
        incluido = bool((blueprint_estado.get(sid) or {}).get("incluida", False))
        bloom = _norm(item.get("bloom"))
        if incluido and any(p in bloom for p in ["ANALIS", "JUSTIFIC", "AVALI", "CRIAR", "TRANSFER"]):
            avancados += 1
    return avancados >= 2, avancados


def sugerir_percurso(cobertura: Mapping[str, Any]) -> str:
    situacoes = [str((v or {}).get("situacao", "")) for v in cobertura.values()]
    if not situacoes:
        return ""
    at = situacoes.count("AT")
    ed = situacoes.count("ED")
    rp = situacoes.count("RP")
    total = max(1, len(situacoes))
    if rp >= math.ceil(total / 2):
        return "P1"
    if rp > 0 or ed >= math.ceil(total / 3):
        return "P2"
    if at == total:
        return "P4"
    return "P3"


def calcular_conceito_sugerido(
    status_por_dimensao: Mapping[str, str],
    base: Mapping[str, Any],
    cobertura: Mapping[str, Any],
    percurso: str = "",
    blueprint_estado: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Sugere AB/B/AD/A sem substituir a decisão profissional do professor."""
    blueprint_estado = blueprint_estado or {}
    dims = [d["codigo"] for d in base.get("dimensoes", [])]
    estruturantes = set(_codigos_estruturantes(base))

    at = [c for c in dims if (cobertura.get(c) or {}).get("situacao", "ED") == "AT"]
    ed = [c for c in dims if (cobertura.get(c) or {}).get("situacao", "ED") == "ED"]
    rp = [c for c in dims if (cobertura.get(c) or {}).get("situacao", "ED") == "RP"]

    if not at:
        return {
            "conceito": "",
            "motivo": "Ainda não há aprendizagens marcadas como trabalhadas e avaliadas.",
            "alertas": ["Conclua primeiro o planejamento curricular do período."],
            "metricas": {},
        }

    validos = {c: str(status_por_dimensao.get(c, "")).strip() for c in at}
    sem_evidencia = [c for c, status in validos.items() if status in ("", "NE")]
    julgaveis = {c: status for c, status in validos.items() if status in {"NC", "EP", "C", "AA"}}
    min_evid = max(1, math.ceil(len(at) * 0.70))

    if len(julgaveis) < min_evid:
        return {
            "conceito": "",
            "motivo": f"Há evidência julgável em {len(julgaveis)} de {len(at)} aprendizagens trabalhadas e avaliadas.",
            "alertas": ["Produza novas evidências antes de fechar o conceito."],
            "metricas": {"AT": len(at), "julgaveis": len(julgaveis), "NE": len(sem_evidencia)},
        }

    total = len(julgaveis)
    nc = sum(1 for status in julgaveis.values() if status == "NC")
    ep = sum(1 for status in julgaveis.values() if status == "EP")
    c = sum(1 for status in julgaveis.values() if status == "C")
    aa = sum(1 for status in julgaveis.values() if status == "AA")
    consolidados = c + aa
    pct_cons = consolidados / total
    pct_nc = nc / total
    estr_status = {codigo: julgaveis.get(codigo) for codigo in estruturantes if codigo in at}

    alertas: List[str] = []
    if rp:
        alertas.append("Há aprendizagens reprogramadas; o conceito não representa domínio integral de tudo o que estava previsto inicialmente.")
    if ed:
        alertas.append("Há aprendizagens ainda em desenvolvimento que não entram no núcleo do fechamento.")
    if sem_evidencia:
        alertas.append("Há aprendizagem AT com NE/sem registro. Novas evidências podem ser necessárias.")

    if any(status == "NC" for status in estr_status.values()) or pct_nc >= 0.25 or (nc > 0 and pct_cons < 0.5):
        conceito = "AB"
        motivo = "Há lacunas relevantes no conjunto avaliado, especialmente quando aprendizagens estruturantes permanecem não consolidadas."
    elif nc > 0 or pct_cons < 0.75 or any(status in {"EP", "NC"} for status in estr_status.values()):
        conceito = "B"
        motivo = "Há conhecimentos importantes demonstrados, mas aprendizagens essenciais ainda aparecem parcialmente ou de forma instável."
    else:
        conceito = "AD"
        motivo = "Predominam aprendizagens consolidadas, sem lacunas estruturais significativas no que foi efetivamente trabalhado e avaliado."

    avancado_ok, qtd_avancadas = _blueprint_avancado(blueprint_estado, base)
    percurso_efetivo = percurso or sugerir_percurso(cobertura)
    todos_at_c_aa = all(julgaveis.get(codigo) in {"C", "AA"} for codigo in at if codigo in julgaveis) and not sem_evidencia
    todos_estruturantes_at = all(codigo in at for codigo in estruturantes)

    if (
        conceito == "AD"
        and todos_at_c_aa
        and aa / total >= 0.5
        and avancado_ok
        and percurso_efetivo in {"P3", "P4"}
        and todos_estruturantes_at
        and not rp
    ):
        conceito = "A"
        motivo = "Além de consolidar o esperado, há evidências consistentes de aprendizagem ampliada em situações de maior complexidade."
    elif aa / total >= 0.5 and conceito == "AD" and not avancado_ok:
        alertas.append("Há muitos registros AA, mas o mapa de evidências ainda não comprova oportunidades avançadas suficientes para sustentar A.")

    return {
        "conceito": conceito,
        "motivo": motivo,
        "alertas": alertas,
        "metricas": {
            "AT": len(at), "ED": len(ed), "RP": len(rp), "NE": len(sem_evidencia),
            "NC": nc, "EP": ep, "C": c, "AA": aa,
            "pct_consolidado": round(pct_cons * 100, 1),
            "blueprint_avancado": qtd_avancadas,
        },
    }


def construir_perfil_aluno(base: Mapping[str, Any], dados: Mapping[str, Any]) -> Tuple[List[str], List[str]]:
    status = dados.get("status", {}) or {}
    nomes = {d["codigo"]: d["nome"] for d in base.get("dimensoes", [])}
    fortes: List[str] = []
    prioridades: List[str] = []
    for codigo, nome in nomes.items():
        nivel = status.get(codigo, "")
        if nivel in {"C", "AA"}:
            fortes.append(f"{nome} ({nivel})")
        elif nivel in {"NC", "EP"}:
            prioridades.append(f"{nome} ({nivel})")
    return fortes, prioridades


# -----------------------------------------------------------------------------
# Progresso e leitura do fluxo
# -----------------------------------------------------------------------------

def _progresso_componente(repo: AvaliacaoRepo, ctx: Contexto, base: Mapping[str, Any], alunos: Sequence[str]) -> Dict[str, Any]:
    dims = base.get("dimensoes", [])
    total_dims = len(dims)

    cobertura_doc = repo.obter("cobertura", ctx)
    cobertura = cobertura_doc.get("dimensoes", {}) or {}
    definidos = sum(
        1 for d in dims
        if (cobertura.get(d["codigo"]) or {}).get("situacao") in {"AT", "ED", "RP"}
    )
    p_curriculo = _percentual(definidos, total_dims)

    blueprint_doc = repo.obter("blueprint", ctx)
    blueprint = blueprint_doc.get("itens", {}) or {}
    itens = base.get("blueprint", [])
    total_bp = len(itens)
    bp_ok = sum(1 for item in itens if bool((blueprint.get(str(item.get("id"))) or {}).get("incluida")))
    p_evidencias = _percentual(bp_ok, total_bp)

    at = [
        d["codigo"] for d in dims
        if (cobertura.get(d["codigo"]) or {}).get("situacao") == "AT"
    ]
    registros = repo.listar_alunos(ctx)
    total_lancamentos = len(at) * len(alunos)
    preenchidos = 0
    for aluno in alunos:
        status = (registros.get(aluno, {}) or {}).get("status", {}) or {}
        preenchidos += sum(1 for codigo in at if status.get(codigo) in {"NE", "NC", "EP", "C", "AA"})
    p_tabulacao = _percentual(preenchidos, total_lancamentos) if at else 0

    fechados = sum(
        1 for aluno in alunos
        if str((registros.get(aluno, {}) or {}).get("conceito_final", "")).strip() in CONCEITOS
    )
    p_fechamento = _percentual(fechados, len(alunos))

    progresso_total = int(round((p_curriculo + p_evidencias + p_tabulacao + p_fechamento) / 4))

    if p_curriculo < 100:
        proxima = "1 · Organizar currículo"
        etapa = 1
    elif p_evidencias < 100:
        proxima = "2 · Planejar evidências"
        etapa = 2
    elif p_tabulacao < 100:
        proxima = "3 · Registrar aprendizagens"
        etapa = 3
    elif p_fechamento < 100:
        proxima = "4 · Fechar conceitos"
        etapa = 4
    else:
        proxima = "Concluído"
        etapa = 4

    return {
        "curriculo": p_curriculo,
        "evidencias": p_evidencias,
        "tabulacao": p_tabulacao,
        "fechamento": p_fechamento,
        "total": progresso_total,
        "proxima": proxima,
        "etapa": etapa,
        "cobertura": cobertura,
        "blueprint": blueprint,
        "registros": registros,
        "at": at,
    }


def _resumo_componente(repo: AvaliacaoRepo, ctx: Contexto, base: Mapping[str, Any], alunos: Sequence[str]) -> Dict[str, Any]:
    registros = repo.listar_alunos(ctx)
    conceitos = {"AB": 0, "B": 0, "AD": 0, "A": 0, "-": 0}
    prioridades: Dict[str, int] = {}
    for aluno in alunos:
        dados = registros.get(aluno, {}) or {}
        conceito = dados.get("conceito_final") or dados.get("conceito_sugerido") or "-"
        conceitos[conceito if conceito in conceitos else "-"] += 1
        status = dados.get("status", {}) or {}
        for dim in base.get("dimensoes", []):
            if status.get(dim["codigo"]) in {"NC", "EP"}:
                prioridades[dim["nome"]] = prioridades.get(dim["nome"], 0) + 1
    prioridades_ordenadas = [
        nome for nome, _ in sorted(prioridades.items(), key=lambda item: (-item[1], item[0]))
    ]
    return {"conceitos": conceitos, "prioridades": prioridades_ordenadas, "registros": registros}


# -----------------------------------------------------------------------------
# Aparência
# -----------------------------------------------------------------------------


def _css() -> None:
    st.markdown(
        """
        <style>
        .av-shell{max-width:1400px;margin:auto}
        .av-hero{
            position:relative;overflow:hidden;
            padding:34px 36px;border-radius:28px;
            background:
              radial-gradient(circle at 88% 18%,rgba(56,189,248,.34),transparent 25%),
              radial-gradient(circle at 15% 105%,rgba(99,102,241,.35),transparent 34%),
              linear-gradient(135deg,#071b35 0%,#0d3d73 48%,#1168a7 100%);
            color:white;margin:4px 0 22px 0;
            box-shadow:0 22px 55px rgba(2,25,56,.22)
        }
        .av-hero:after{
            content:"";position:absolute;right:-70px;bottom:-90px;width:260px;height:260px;
            border-radius:50%;border:1px solid rgba(255,255,255,.10);
            box-shadow:0 0 0 35px rgba(255,255,255,.035),0 0 0 70px rgba(255,255,255,.025)
        }
        .av-hero-kicker{font-size:.76rem;font-weight:850;letter-spacing:.14em;text-transform:uppercase;opacity:.78}
        .av-hero-title{font-size:2.55rem;font-weight:900;line-height:1.02;margin:8px 0 12px 0;max-width:900px}
        .av-hero-sub{font-size:1.02rem;opacity:.92;max-width:920px;line-height:1.6}
        .av-context{display:flex;gap:8px;flex-wrap:wrap;margin-top:18px;position:relative;z-index:2}
        .av-chip{
            padding:7px 11px;border-radius:999px;background:rgba(255,255,255,.12);
            border:1px solid rgba(255,255,255,.16);font-size:.79rem;font-weight:650;
            backdrop-filter:blur(6px)
        }

        .av-section-title{font-size:1.38rem;font-weight:900;color:#0f172a;margin:.3rem 0 .25rem 0}
        .av-section-sub{color:#64748b;font-size:.94rem;line-height:1.55;margin-bottom:1rem;max-width:1050px}
        .av-eyebrow{font-size:.69rem;font-weight:850;letter-spacing:.10em;text-transform:uppercase;color:#64748b;margin-bottom:4px}

        .av-guide{
            padding:16px 18px;border-radius:16px;
            background:linear-gradient(135deg,#f8fbff,#f5f9ff);
            border:1px solid #dce9f8;margin:8px 0 18px 0;
            box-shadow:0 4px 16px rgba(15,61,115,.035)
        }
        .av-guide b{color:#0f3f78}
        .av-guide-title{font-size:.72rem;text-transform:uppercase;letter-spacing:.08em;font-weight:850;color:#2563eb;margin-bottom:3px}

        .av-impact-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:11px;margin:12px 0 20px}
        .av-impact{
            background:#fff;border:1px solid #e5edf7;border-radius:18px;padding:17px 17px 16px;
            box-shadow:0 6px 22px rgba(15,23,42,.045);min-height:150px
        }
        .av-impact-icon{
            width:38px;height:38px;border-radius:12px;background:#eff6ff;
            display:flex;align-items:center;justify-content:center;font-size:1.12rem;margin-bottom:11px
        }
        .av-impact-title{font-size:.93rem;font-weight:850;color:#0f172a;margin-bottom:5px}
        .av-impact-text{font-size:.82rem;line-height:1.48;color:#64748b}

        .av-next{
            display:grid;grid-template-columns:auto 1fr auto;gap:14px;align-items:center;
            padding:18px 20px;border-radius:20px;background:linear-gradient(135deg,#eff6ff,#f8fbff);
            border:1px solid #bfdbfe;margin:12px 0 20px;box-shadow:0 7px 22px rgba(37,99,235,.07)
        }
        .av-next-icon{
            width:48px;height:48px;border-radius:15px;background:#2563eb;color:#fff;
            display:flex;align-items:center;justify-content:center;font-size:1.35rem
        }
        .av-next-kicker{font-size:.68rem;font-weight:850;letter-spacing:.08em;text-transform:uppercase;color:#2563eb}
        .av-next-title{font-size:1.03rem;font-weight:880;color:#0f172a;margin:2px 0 2px}
        .av-next-text{font-size:.84rem;color:#64748b;line-height:1.45}
        .av-next-pill{font-size:.75rem;font-weight:850;color:#1d4ed8;background:white;border:1px solid #bfdbfe;padding:7px 10px;border-radius:999px}

        .av-practice{
            border:1px solid #dbeafe;background:linear-gradient(135deg,#ffffff,#f8fbff);
            border-radius:18px;padding:16px 18px;margin:10px 0 18px;box-shadow:0 6px 20px rgba(15,23,42,.035)
        }
        .av-practice-head{display:flex;gap:9px;align-items:center;font-size:.93rem;font-weight:850;color:#0f3f78;margin-bottom:8px}
        .av-practice ul{margin:.25rem 0 0 1.1rem;padding:0;color:#475569}
        .av-practice li{margin:.24rem 0;font-size:.86rem;line-height:1.45}

        .av-card{
            border:1px solid #e3ebf5;border-radius:20px;padding:18px 19px;background:#fff;
            box-shadow:0 5px 20px rgba(15,23,42,.045);margin-bottom:11px;transition:.15s ease
        }
        .av-card:hover{transform:translateY(-1px);border-color:#c9d8ea;box-shadow:0 10px 28px rgba(15,23,42,.07)}
        .av-card-title{font-weight:850;color:#0f172a;font-size:1rem;line-height:1.4}
        .av-card-text{color:#475569;font-size:.9rem;line-height:1.55;margin-top:6px}
        .av-code{display:inline-block;padding:4px 8px;border-radius:8px;background:#eff6ff;color:#1d4ed8;font-weight:900;font-size:.69rem;margin-right:7px}
        .av-struct{display:inline-block;padding:4px 8px;border-radius:8px;background:#fff7ed;color:#9a3412;font-weight:850;font-size:.65rem;margin-left:5px}

        .av-progress-shell{height:8px;border-radius:999px;background:#e7edf5;overflow:hidden;margin:8px 0 6px}
        .av-progress-fill{height:100%;border-radius:999px;background:linear-gradient(90deg,#2563eb,#0ea5e9)}
        .av-small{font-size:.78rem;color:#64748b;line-height:1.4}

        .av-stage-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:9px;margin:12px 0 18px}
        .av-stage{padding:12px 13px;border-radius:15px;border:1px solid #e2e8f0;background:#fff}
        .av-stage.done{background:#f0fdf4;border-color:#bbf7d0}
        .av-stage.current{background:#eff6ff;border-color:#bfdbfe;box-shadow:0 5px 18px rgba(37,99,235,.07)}
        .av-stage-num{font-size:.66rem;font-weight:900;color:#64748b;text-transform:uppercase;letter-spacing:.04em}
        .av-stage-name{font-size:.82rem;font-weight:800;color:#1e293b;margin-top:3px}

        .av-badge{display:inline-block;padding:4px 9px;border-radius:999px;font-weight:900;font-size:.72rem}
        .av-concept{font-size:2.35rem;font-weight:950;line-height:1;color:#0f172a}
        .av-concept-label{font-size:.7rem;color:#64748b;font-weight:850;text-transform:uppercase;letter-spacing:.07em}
        .av-kpi{padding:15px 16px;border:1px solid #e2e8f0;border-radius:16px;background:#fff;height:100%}
        .av-kpi-n{font-size:1.5rem;font-weight:950;color:#0f172a}
        .av-kpi-l{font-size:.75rem;color:#64748b;font-weight:800;margin-top:2px}

        .av-callout-ok{padding:14px 16px;border-radius:14px;background:#ecfdf5;border:1px solid #a7f3d0;color:#065f46;margin:9px 0}
        .av-callout-warn{padding:14px 16px;border-radius:14px;background:#fffbeb;border:1px solid #fde68a;color:#92400e;margin:9px 0}
        .av-callout-info{padding:14px 16px;border-radius:14px;background:#eff6ff;border:1px solid #bfdbfe;color:#1e40af;margin:9px 0}

        .av-radar{
            border-radius:20px;padding:18px 20px;
            background:linear-gradient(135deg,#0f172a,#172554);
            color:white;margin:12px 0 18px;box-shadow:0 12px 30px rgba(15,23,42,.14)
        }
        .av-radar-kicker{font-size:.68rem;font-weight:850;letter-spacing:.09em;text-transform:uppercase;color:#93c5fd}
        .av-radar-title{font-size:1.08rem;font-weight:900;margin:3px 0 4px}
        .av-radar-text{font-size:.84rem;opacity:.86;line-height:1.5}

        .av-summary{
            border:1px solid #d9e4f2;border-radius:20px;padding:18px 20px;background:#fff;
            box-shadow:0 6px 22px rgba(15,23,42,.04);margin:10px 0 18px
        }
        .av-summary-title{font-size:.78rem;text-transform:uppercase;letter-spacing:.07em;font-weight:900;color:#64748b;margin-bottom:7px}
        .av-summary-text{font-size:.92rem;color:#334155;line-height:1.62}

        div[data-testid="stMetric"]{
            background:#fff;border:1px solid #e2e8f0;padding:13px 15px;border-radius:16px;
            box-shadow:0 4px 16px rgba(15,23,42,.035)
        }
        div[data-testid="stDataFrame"]{border:1px solid #e2e8f0;border-radius:16px;overflow:hidden}
        div[data-testid="stVerticalBlockBorderWrapper"]{border-radius:19px!important;border-color:#e2e8f0!important;background:#fff}
        div[role="radiogroup"]{gap:.35rem}
        button[kind="primary"]{border-radius:12px!important;font-weight:800!important;min-height:2.65rem}
        button[kind="secondary"]{border-radius:12px!important;min-height:2.55rem}
        textarea{border-radius:13px!important}
        [data-baseweb="select"]>div{border-radius:12px!important}
        .stTabs [data-baseweb="tab-list"]{gap:6px}
        .stTabs [data-baseweb="tab"]{border-radius:10px;padding:8px 12px}

        @media (max-width:1000px){
            .av-impact-grid{grid-template-columns:1fr 1fr}
            .av-stage-grid{grid-template-columns:1fr 1fr}
            .av-hero-title{font-size:2rem}
        }
        @media (max-width:650px){
            .av-impact-grid{grid-template-columns:1fr}
            .av-next{grid-template-columns:auto 1fr}
            .av-next-pill{display:none}
            .av-hero{padding:25px 22px}
            .av-hero-title{font-size:1.7rem}
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _hero(ctx: Contexto, usuario: str) -> None:
    st.markdown(
        f"""
        <div class="av-hero">
          <div class="av-hero-kicker">Integra · Avaliação e Aprendizagem</div>
          <div class="av-hero-title">Avaliar para decidir melhor.<br>Ensinar melhor amanhã.</div>
          <div class="av-hero-sub">
            Esta ferramenta transforma currículo, evidências e registros em decisões pedagógicas:
            mostra o que priorizar, onde recompor, quem precisa de intervenção e qual deve ser o próximo passo.
            Menos relatório por obrigação. Mais informação útil para a prática.
          </div>
          <div class="av-context">
            <span class="av-chip">🏫 {_esc(ctx.turma)}</span>
            <span class="av-chip">🎓 {ctx.ano_escolar}º ano</span>
            <span class="av-chip">🗓️ {ctx.trimestre}º trimestre · {ctx.ano_letivo}</span>
            <span class="av-chip">👤 {_esc(usuario)}</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def _titulo(secao: str, subtitulo: str = "") -> None:
    st.markdown(f'<div class="av-section-title">{_esc(secao)}</div>', unsafe_allow_html=True)
    if subtitulo:
        st.markdown(f'<div class="av-section-sub">{_esc(subtitulo)}</div>', unsafe_allow_html=True)



def _guia(texto: str) -> None:
    st.markdown(
        f"""
        <div class="av-guide">
          <div class="av-guide-title">Seu objetivo nesta etapa</div>
          <div><b>Faça isso agora:</b> {_esc(texto)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _impacto_pratica() -> None:
    st.markdown(
        """
        <div class="av-impact-grid">
          <div class="av-impact">
            <div class="av-impact-icon">🎯</div>
            <div class="av-impact-title">Planejamento mais preciso</div>
            <div class="av-impact-text">Você enxerga o essencial do trimestre e deixa de planejar apenas por sequência de atividades. O foco passa a ser a aprendizagem que precisa aparecer.</div>
          </div>
          <div class="av-impact">
            <div class="av-impact-icon">🧩</div>
            <div class="av-impact-title">Recomposição com propósito</div>
            <div class="av-impact-text">Quando a turma trava, o sistema aponta pré-requisitos relacionados. Você retoma o que realmente bloqueia o avanço, sem “voltar séries inteiras”.</div>
          </div>
          <div class="av-impact">
            <div class="av-impact-icon">🔎</div>
            <div class="av-impact-title">Avaliação que revela</div>
            <div class="av-impact-text">Você confere se suas atividades realmente produzem evidência do que pretende avaliar — e evita decidir conceito por uma prova isolada ou impressão geral.</div>
          </div>
          <div class="av-impact">
            <div class="av-impact-icon">🚀</div>
            <div class="av-impact-title">Próxima aula mais inteligente</div>
            <div class="av-impact-text">Os registros viram mapa de intervenção: quem já consolidou, quem oscila, quem precisa de apoio e qual aprendizagem deve entrar no próximo planejamento.</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _ganho_pratico(titulo: str, itens: Sequence[str], icone: str = "✨") -> None:
    lis = "".join(f"<li>{_esc(item)}</li>" for item in itens)
    st.markdown(
        f"""
        <div class="av-practice">
          <div class="av-practice-head"><span>{_esc(icone)}</span><span>{_esc(titulo)}</span></div>
          <ul>{lis}</ul>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _radar(texto_titulo: str, texto: str) -> None:
    st.markdown(
        f"""
        <div class="av-radar">
          <div class="av-radar-kicker">Radar pedagógico</div>
          <div class="av-radar-title">{_esc(texto_titulo)}</div>
          <div class="av-radar-text">{_esc(texto)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _texto_sintese_individual(
    aluno: str,
    componente: str,
    conceito: str,
    fortes: Sequence[str],
    prioridades: Sequence[str],
    proximo_passo: str = "",
) -> str:
    inicio = f"{aluno}: em {componente}, "
    if conceito:
        inicio += f"o fechamento do período registra conceito {conceito}. "
    else:
        inicio += "o fechamento do período ainda está em construção. "
    if fortes:
        inicio += "Entre as aprendizagens já demonstradas, destacam-se " + "; ".join(str(x) for x in fortes[:3]) + ". "
    if prioridades:
        inicio += "As prioridades de continuidade são " + "; ".join(str(x) for x in prioridades[:3]) + ". "
    if proximo_passo:
        inicio += "Próximo passo pedagógico: " + str(proximo_passo).strip()
    return inicio.strip()


def _barra_progresso(valor: int, cor: str = "#2563eb") -> str:
    valor = max(0, min(100, int(valor)))
    return (
        '<div class="av-progress-shell">'
        f'<div class="av-progress-fill" style="width:{valor}%;background:{cor}"></div>'
        '</div>'
    )


def _etapas_html(progresso: Mapping[str, Any]) -> str:
    etapas = [
        (1, "Currículo", progresso.get("curriculo", 0)),
        (2, "Evidências", progresso.get("evidencias", 0)),
        (3, "Registros", progresso.get("tabulacao", 0)),
        (4, "Fechamento", progresso.get("fechamento", 0)),
    ]
    atual = int(progresso.get("etapa", 1))
    blocos = []
    for num, nome, pct in etapas:
        classe = "done" if pct >= 100 else ("current" if num == atual else "")
        blocos.append(
            f'<div class="av-stage {classe}"><div class="av-stage-num">Etapa {num} · {pct}%</div><div class="av-stage-name">{_esc(nome)}</div></div>'
        )
    return '<div class="av-stage-grid">' + "".join(blocos) + "</div>"



def _componente_card_html(componente: str, progresso: Mapping[str, Any], resumo: Mapping[str, Any]) -> str:
    meta = COMPONENTE_META.get(componente, {"icone": "📘", "cor": "#2563eb", "suave": "#eff6ff"})
    conceitos = resumo.get("conceitos", {})
    pendentes = conceitos.get("-", 0)
    prioridades = resumo.get("prioridades", []) or []
    prioridade_txt = prioridades[0] if prioridades else "Ainda sem prioridade coletiva consolidada"
    return f"""
    <div class="av-card" style="border-top:4px solid {meta['cor']};">
      <div class="av-eyebrow">{meta['icone']} {_esc(componente)}</div>
      <div class="av-card-title">{progresso.get('total', 0)}% do percurso pedagógico registrado</div>
      {_barra_progresso(progresso.get('total', 0), meta['cor'])}
      <div class="av-small">Agora: <b>{_esc(progresso.get('proxima', ''))}</b></div>
      <div class="av-small" style="margin-top:7px">🎯 Prioridade que mais aparece: <b>{_esc(prioridade_txt)}</b></div>
      <div class="av-small" style="margin-top:5px">Fechamentos ainda pendentes: {pendentes}</div>
    </div>
    """


def _painel(repo: AvaliacaoRepo, ctx_base: Contexto, componentes: List[str], alunos: List[str]) -> None:
    _titulo(
        "Seu painel pedagógico",
        "Aqui você não acompanha “formulários preenchidos”. Você acompanha decisões: o que ensinar, o que observar e onde intervir.",
    )
    _impacto_pratica()

    if not alunos:
        st.warning("A turma foi localizada, mas ainda não há estudantes no Carômetro com esse nome de turma. Você pode consultar o currículo, mas não registrar aprendizagens.")

    progresso_comp: Dict[str, Dict[str, Any]] = {}
    resumo_comp: Dict[str, Dict[str, Any]] = {}

    for componente in componentes:
        ctx = Contexto(ctx_base.ano_letivo, ctx_base.ano_escolar, ctx_base.trimestre, ctx_base.turma, componente)
        base = _base_curricular(ctx.ano_escolar, ctx.trimestre, componente)
        progresso_comp[componente] = _progresso_componente(repo, ctx, base, alunos)
        resumo_comp[componente] = _resumo_componente(repo, ctx, base, alunos)

    concluidos = sum(1 for p in progresso_comp.values() if p.get("total", 0) >= 100)
    media = int(round(sum(p.get("total", 0) for p in progresso_comp.values()) / max(1, len(progresso_comp))))
    fechados_total = sum(
        sum(r.get("conceitos", {}).get(c, 0) for c in CONCEITOS)
        for r in resumo_comp.values()
    )
    esperado = len(alunos) * len(componentes)

    if componentes:
        componente_foco = min(
            componentes,
            key=lambda c: (progresso_comp[c].get("total", 0), progresso_comp[c].get("etapa", 1))
        )
        p_foco = progresso_comp[componente_foco]
        meta = COMPONENTE_META.get(componente_foco, {"icone": "📘"})
        st.markdown(
            f"""
            <div class="av-next">
              <div class="av-next-icon">{meta.get('icone','📘')}</div>
              <div>
                <div class="av-next-kicker">Comece por aqui</div>
                <div class="av-next-title">{_esc(componente_foco)} · {_esc(p_foco.get('proxima',''))}</div>
                <div class="av-next-text">É o ponto do fluxo com maior necessidade de continuidade neste momento. Ao avançar aqui, os registros começam a gerar informação útil para o planejamento da turma.</div>
              </div>
              <div class="av-next-pill">{p_foco.get('total',0)}% concluído</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button(
            f"Abrir {componente_foco}",
            type="primary",
            use_container_width=True,
            key=f"av3_focus_{_slug(ctx_base.turma)}_{_slug(componente_foco)}",
        ):
            st.session_state["av_v2_componente"] = componente_foco
            st.session_state["av_v2_force_step"] = int(p_foco.get("etapa", 1))
            st.session_state["av_v2_force_area"] = "📚 Percurso do componente"
            st.rerun()

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Percurso registrado", f"{media}%")
    k2.metric("Componentes concluídos", f"{concluidos}/{len(componentes)}")
    k3.metric("Estudantes", len(alunos))
    k4.metric("Fechamentos realizados", f"{fechados_total}/{esperado}" if esperado else "0")

    _ganho_pratico(
        "Como usar este painel durante o trimestre",
        [
            "No início: abra o componente e confira onde a turma precisa chegar e quais pré-requisitos podem bloquear o avanço.",
            "Durante: atualize o que está AT, ED ou RP e use o mapa de evidências para conferir se suas atividades estão realmente mostrando aprendizagem.",
            "Antes do Conselho: observe as prioridades coletivas e os estudantes que precisam de intervenção; o sistema já organiza essa leitura para você.",
        ],
        "🧭",
    )

    _titulo("Componentes", "Cada card mostra onde você está, qual é a próxima ação e a prioridade coletiva que começa a aparecer nos registros.")
    for inicio in range(0, len(componentes), 3):
        lote = componentes[inicio:inicio + 3]
        colunas = st.columns(3)
        for idx, componente in enumerate(lote):
            with colunas[idx]:
                st.markdown(_componente_card_html(componente, progresso_comp[componente], resumo_comp[componente]), unsafe_allow_html=True)
                if st.button(
                    "Abrir percurso",
                    key=f"av_go_{_slug(ctx_base.turma)}_{_slug(componente)}",
                    use_container_width=True,
                    type="primary" if progresso_comp[componente].get("total", 0) < 100 else "secondary",
                ):
                    st.session_state["av_v2_componente"] = componente
                    st.session_state["av_v2_force_step"] = int(progresso_comp[componente].get("etapa", 1))
                    st.session_state["av_v2_force_area"] = "📚 Percurso do componente"
                    st.rerun()

    ranking = []
    for componente in componentes:
        for prioridade in resumo_comp[componente].get("prioridades", [])[:3]:
            ranking.append((componente, prioridade))
    if ranking:
        comp0, prio0 = ranking[0]
        _radar(
            f"Primeira prioridade visível: {comp0}",
            f"{prio0}. Use esta informação como hipótese de intervenção coletiva: confirme nas produções dos estudantes e planeje uma retomada focalizada, em vez de repetir todo o conteúdo.",
        )
    else:
        _radar(
            "Ainda não há um padrão coletivo consolidado",
            "Isso é esperado no início do processo. Conforme os registros forem feitos, o Integra começará a mostrar quais aprendizagens concentram EP/NC e merecem intervenção da turma.",
        )

    _titulo("Leitura coletiva dos conceitos", "Esta visão serve para localizar padrões; ela não substitui a leitura das evidências de cada estudante.")
    linhas = []
    for componente in componentes:
        resumo = resumo_comp[componente]
        conceitos = resumo["conceitos"]
        linhas.append({
            "Componente": componente,
            "AB": conceitos.get("AB", 0),
            "B": conceitos.get("B", 0),
            "AD": conceitos.get("AD", 0),
            "A": conceitos.get("A", 0),
            "Sem fechamento": conceitos.get("-", 0),
            "Prioridades coletivas": "; ".join(resumo.get("prioridades", [])[:3]) or "—",
        })
    st.dataframe(pd.DataFrame(linhas), hide_index=True, use_container_width=True)

def _etapa_curriculo(repo: AvaliacaoRepo, ctx: Contexto, base: Mapping[str, Any]) -> None:
    _titulo("1 · Organizar o currículo do trimestre", "Primeiro, deixe explícito o que foi efetivamente desenvolvido, o que ainda está em andamento e o que precisará ser reprogramado.")
    _guia("Leia cada aprendizagem, indique AT, ED ou RP e, quando houver lacuna que bloqueie o avanço, use o mapa de pré-requisitos para escolher uma recomposição focalizada.")
    _ganho_pratico(
        "Por que esta etapa melhora seu planejamento",
        [
            "Você separa o que realmente foi desenvolvido do que apenas estava previsto no papel.",
            "Você identifica quais lacunas anteriores estão impedindo a turma de acessar a aprendizagem atual.",
            "Você termina esta etapa sabendo o que precisa ensinar/reensinar — e o que pode deixar de ocupar tempo porque já está avançando.",
        ],
        "🎯",
    )

    a, b = st.columns(2)
    with a:
        with st.container(border=True):
            st.markdown("**🎯 Onde o estudante precisa chegar**")
            st.write(base.get("curriculo_chegada", ""))
    with b:
        with st.container(border=True):
            st.markdown("**🧩 Núcleo estruturante**")
            st.write(base.get("nucleo_estruturante", ""))

    if base.get("ancora"):
        st.info(base.get("ancora"))

    salvo = repo.obter("cobertura", ctx)
    cobertura = salvo.get("dimensoes", {}) or _default_cobertura(base)
    percurso_salvo = salvo.get("percurso_turma", "")
    pres = {p.get("codigo"): p for p in base.get("pre_requisitos", [])}
    novos: Dict[str, Any] = {}

    st.markdown("### Aprendizagens do período")
    st.caption("AT entra no fechamento; ED permanece em desenvolvimento; RP deve ser retomada em outro momento. A situação curricular é da turma — não é o desempenho de um estudante.")

    for numero, dim in enumerate(base.get("dimensoes", []), 1):
        codigo = dim.get("codigo", f"D{numero}")
        atual = cobertura.get(codigo, {}) or {}
        prereq = pres.get(codigo, {}) or {}
        estruturante = _norm(dim.get("peso")) == "ESTRUTURANTE"

        with st.container(border=True):
            titulo = f"{numero}. {dim.get('nome', '')}"
            badge = '<span class="av-struct">ESTRUTURANTE</span>' if estruturante else ""
            st.markdown(
                f'<div class="av-card-title"><span class="av-code">{_esc(codigo)}</span>{_esc(titulo)} {badge}</div>',
                unsafe_allow_html=True,
            )
            st.markdown(f'<div class="av-card-text"><b>O aluno precisa demonstrar:</b> {_esc(dim.get("demonstrar", ""))}</div>', unsafe_allow_html=True)
            if dim.get("focos"):
                with st.expander("Ver conteúdos/focos curriculares"):
                    st.write(dim.get("focos"))

            c1, c2 = st.columns([1.05, 1.95])
            with c1:
                situacao_atual = atual.get("situacao", "ED")
                if situacao_atual not in SITUACAO_OPCOES:
                    situacao_atual = "ED"
                situacao = st.selectbox(
                    "Situação desta aprendizagem",
                    SITUACAO_OPCOES,
                    index=SITUACAO_OPCOES.index(situacao_atual),
                    format_func=_format_situacao,
                    key=f"av2_cov_{_slug(ctx.turma)}_{_slug(ctx.componente)}_{codigo}",
                    help="AT = trabalhada e avaliada; ED = ainda em desenvolvimento; RP = reprogramada.",
                )
                st.caption(SITUACAO_DESCRICAO[situacao])

            with c2:
                recomposicao = st.text_input(
                    "Recomposição focalizada, se necessária",
                    value=str(atual.get("recomposicao", "") or ""),
                    placeholder="Registre apenas a lacuna anterior que realmente bloqueia esta aprendizagem.",
                    key=f"av2_rec_{_slug(ctx.turma)}_{_slug(ctx.componente)}_{codigo}",
                )
                observacao = st.text_input(
                    "Observação pedagógica (opcional)",
                    value=str(atual.get("observacao", "") or ""),
                    placeholder="Ex.: turma avançou após retomada com material manipulável.",
                    key=f"av2_obs_{_slug(ctx.turma)}_{_slug(ctx.componente)}_{codigo}",
                )

            with st.expander("🔎 Se houver defasagem: veja pré-requisitos, diagnóstico e ponte de recomposição"):
                pre_direto = prereq.get("pre_ano_anterior") or prereq.get("pre_4ano") or "—"
                rotulo = "Educação Infantil / experiências anteriores" if ctx.ano_escolar == 1 else f"{ctx.ano_escolar - 1}º ano · pré-requisito direto"
                st.markdown(f"**{rotulo}**")
                st.write(pre_direto)
                st.markdown("**Se a lacuna for mais antiga**")
                st.write(prereq.get("pre_antigo", "—"))
                st.markdown("**Diagnóstico rápido sugerido**")
                st.write(prereq.get("diagnostico", "—"))
                st.markdown(f"**Ponte de volta para o {ctx.ano_escolar}º ano**")
                st.write(prereq.get("recomposicao", "—"))

            novos[codigo] = {
                "situacao": situacao,
                "recomposicao": recomposicao,
                "observacao": observacao,
            }

    percurso_sugerido = sugerir_percurso(novos)
    st.markdown("### Leitura do percurso da turma")
    p1, p2 = st.columns([1, 2])
    with p1:
        percurso_inicial = percurso_salvo if percurso_salvo in PERCURSO_OPCOES else percurso_sugerido
        percurso = st.selectbox(
            "Percurso predominante",
            PERCURSO_OPCOES,
            index=PERCURSO_OPCOES.index(percurso_inicial) if percurso_inicial in PERCURSO_OPCOES else 0,
            format_func=lambda x: "— selecionar —" if not x else f"{x} · {PERCURSOS[x]}",
            key=f"av2_percurso_turma_{_slug(ctx.turma)}_{_slug(ctx.componente)}",
        )
    with p2:
        st.markdown(
            f'<div class="av-callout-info">Pelo que foi marcado acima, o sistema lê o percurso como <b>{_esc(percurso_sugerido)} · {_esc(PERCURSOS.get(percurso_sugerido, ""))}</b>. Você pode ajustar essa leitura se o registro pedagógico da turma indicar outra situação.</div>',
            unsafe_allow_html=True,
        )

    at_q = sum(1 for x in novos.values() if (x or {}).get("situacao") == "AT")
    ed_q = sum(1 for x in novos.values() if (x or {}).get("situacao") == "ED")
    rp_q = sum(1 for x in novos.values() if (x or {}).get("situacao") == "RP")
    if rp_q:
        _radar(
            f"{rp_q} aprendizagem(ns) foi(ram) reprogramada(s)",
            "Isso não significa fracasso da turma. Significa que o planejamento precisa prever quando essas aprendizagens voltarão e quais pré-requisitos devem ser recompostos para que elas não desapareçam do percurso.",
        )
    elif ed_q:
        _radar(
            f"{ed_q} aprendizagem(ns) ainda está(ão) em desenvolvimento",
            "Seu foco agora é produzir boas oportunidades de aprendizagem e não antecipar um julgamento. O conceito só deve ser sustentado pelo que já teve tempo e condições de ser desenvolvido.",
        )
    else:
        _radar(
            "O currículo do período está todo marcado como trabalhado e avaliado",
            "Agora a pergunta muda: suas atividades produziram evidências suficientes e variadas para mostrar o que cada estudante realmente aprendeu?",
        )

    if st.button("Salvar etapa 1 e seguir para as evidências →", type="primary", use_container_width=True, key=f"av2_save_cov_{_slug(ctx.turma)}_{_slug(ctx.componente)}"):
        repo.salvar("cobertura", ctx, {"dimensoes": novos, "percurso_turma": percurso or percurso_sugerido})
        st.session_state["av_v2_force_step"] = 2
        st.success("Planejamento curricular salvo.")
        st.rerun()


# -----------------------------------------------------------------------------
# Tela do componente — Etapa 2: evidências
# -----------------------------------------------------------------------------

def _etapa_evidencias(repo: AvaliacaoRepo, ctx: Contexto, base: Mapping[str, Any]) -> None:
    _titulo("2 · Planejar as evidências", "Agora transforme o currículo trabalhado em evidências observáveis. Não é obrigatório concentrar tudo numa prova única.")
    _guia("Para cada situação recomendada, marque se ela está contemplada e registre onde o professor obterá essa evidência: prova, produção, oralidade, atividade prática, observação intencional, projeto etc.")
    _ganho_pratico(
        "Por que esta etapa melhora sua avaliação",
        [
            "Você verifica se o instrumento mede o que pretende medir — e não apenas aquilo que é mais fácil colocar numa prova.",
            "Você combina diferentes tipos de evidência e reduz o peso de uma única atividade no conceito.",
            "Você enxerga se existem oportunidades de aplicação, análise e justificativa suficientes para distinguir domínio esperado de aprendizagem ampliada.",
        ],
        "🔎",
    )

    cobertura = repo.obter("cobertura", ctx).get("dimensoes", {}) or _default_cobertura(base)
    salvo = repo.obter("blueprint", ctx)
    estado = salvo.get("itens", {}) or _default_blueprint(base)

    at = sum(1 for x in cobertura.values() if (x or {}).get("situacao") == "AT")
    ed = sum(1 for x in cobertura.values() if (x or {}).get("situacao") == "ED")
    rp = sum(1 for x in cobertura.values() if (x or {}).get("situacao") == "RP")

    c1, c2, c3 = st.columns(3)
    c1.metric("Trabalhadas e avaliadas", at)
    c2.metric("Em desenvolvimento", ed)
    c3.metric("Reprogramadas", rp)

    if at == 0:
        st.warning("Nenhuma aprendizagem está marcada como AT. Volte à etapa 1 antes de planejar o fechamento.")

    novos: Dict[str, Any] = {}
    instrumentos = [
        "", "Avaliação escrita", "Produção/atividade", "Oralidade/leitura",
        "Observação intencional", "Atividade prática/experimento",
        "Pesquisa/projeto", "Portfólio", "Outro",
    ]

    st.markdown("### Mapa de evidências")
    for numero, item in enumerate(base.get("blueprint", []), 1):
        sid = str(item.get("id", numero))
        anterior = estado.get(sid, {}) or {}
        dimensao = str(item.get("dimensao", ""))
        situacao_dim = (cobertura.get(dimensao) or {}).get("situacao", "ED")

        with st.container(border=True):
            topo1, topo2 = st.columns([3.2, 1])
            with topo1:
                st.markdown(f"**{numero}. {item.get('situacao', '')}**")
                st.caption(f"Dimensão: {dimensao or '—'} · Demanda cognitiva: {item.get('bloom', '—')}")
            with topo2:
                if situacao_dim == "RP":
                    st.markdown(_status_badge("RP"), unsafe_allow_html=True)
                    st.caption("Reprogramada")
                elif situacao_dim == "ED":
                    st.markdown(_status_badge("EP"), unsafe_allow_html=True)
                    st.caption("Currículo em desenvolvimento")
                else:
                    st.markdown('<span class="av-badge" style="color:#047857;background:#ecfdf5;">AT</span>', unsafe_allow_html=True)
                    st.caption("Precisa produzir evidência")

            st.markdown(f'<div class="av-card-text"><b>O registro precisa revelar:</b> {_esc(item.get("evidencia", ""))}</div>', unsafe_allow_html=True)

            r1, r2, r3 = st.columns([.8, 1.25, 1.7])
            with r1:
                incluida = st.checkbox(
                    "Contemplada",
                    value=bool(anterior.get("incluida", False)),
                    key=f"av2_bp_ck_{_slug(ctx.turma)}_{_slug(ctx.componente)}_{sid}",
                )
            instrumento_salvo = str(anterior.get("instrumento", "") or "")
            tipo_salvo = next((x for x in instrumentos if x and instrumento_salvo.startswith(x)), "")
            detalhe_salvo = instrumento_salvo
            if tipo_salvo and instrumento_salvo.startswith(tipo_salvo):
                detalhe_salvo = instrumento_salvo[len(tipo_salvo):].lstrip(" ·-")
            with r2:
                tipo = st.selectbox(
                    "Tipo de evidência",
                    instrumentos,
                    index=instrumentos.index(tipo_salvo) if tipo_salvo in instrumentos else 0,
                    key=f"av2_bp_tipo_{_slug(ctx.turma)}_{_slug(ctx.componente)}_{sid}",
                )
            with r3:
                detalhe = st.text_input(
                    "Onde aparece?",
                    value=detalhe_salvo,
                    placeholder="Ex.: questão 4; produção do dia 12/05; leitura individual.",
                    key=f"av2_bp_det_{_slug(ctx.turma)}_{_slug(ctx.componente)}_{sid}",
                )
            instrumento = " · ".join(x for x in [tipo, detalhe] if x)
            novos[sid] = {"incluida": bool(incluida), "instrumento": instrumento, "observacao": ""}

    total = len(base.get("blueprint", []))
    cobertas = sum(1 for x in novos.values() if x.get("incluida"))
    avancado_ok, qtd_avancada = _blueprint_avancado(novos, base)
    pct = _percentual(cobertas, total)

    st.markdown("### Conferência antes de seguir")
    st.markdown(_barra_progresso(pct), unsafe_allow_html=True)
    st.caption(f"{cobertas} de {total} situações/evidências estão contempladas.")

    if cobertas < total:
        st.markdown('<div class="av-callout-warn">Ainda existem evidências não contempladas. Isso não exige uma prova única, mas o professor precisa saber onde cada aprendizagem trabalhada será observada.</div>', unsafe_allow_html=True)
    elif qtd_avancada < 2:
        st.markdown('<div class="av-callout-info">O mapa está coberto, mas há poucas oportunidades de maior complexidade. Isso não impede AD; apenas limita a sustentação de A quando o estudante registrar AA.</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="av-callout-ok">Mapa de evidências completo e com oportunidades de maior complexidade.</div>', unsafe_allow_html=True)

    tipos_usados = set()
    for x in novos.values():
        inst = str((x or {}).get("instrumento", "") or "").strip()
        if inst:
            tipos_usados.add(inst.split(" · ")[0].strip())
    if cobertas:
        _radar(
            f"{len(tipos_usados)} tipo(s) de evidência no mapa",
            "Quanto mais a natureza da aprendizagem exigir, combine instrumentos diferentes. Diversidade não é quantidade por si só: é escolher a evidência mais adequada para aquilo que o estudante precisa demonstrar.",
        )

    if st.button("Salvar etapa 2 e registrar os estudantes →", type="primary", use_container_width=True, key=f"av2_save_bp_{_slug(ctx.turma)}_{_slug(ctx.componente)}"):
        repo.salvar("blueprint", ctx, {"itens": novos})
        st.session_state["av_v2_force_step"] = 3
        st.success("Mapa de evidências salvo.")
        st.rerun()


# -----------------------------------------------------------------------------
# Tela do componente — Etapa 3: registros
# -----------------------------------------------------------------------------

def _salvar_status_aluno(
    repo: AvaliacaoRepo,
    ctx: Contexto,
    base: Mapping[str, Any],
    cobertura: Mapping[str, Any],
    blueprint: Mapping[str, Any],
    aluno: str,
    statuses: Mapping[str, str],
) -> None:
    atual = repo.obter("aluno", ctx, aluno) or {}
    percurso = atual.get("percurso", "") or sugerir_percurso(cobertura)
    motor = calcular_conceito_sugerido(statuses, base, cobertura, percurso, blueprint)
    novo = dict(atual)
    novo.update({
        "status": dict(statuses),
        "conceito_sugerido": motor.get("conceito", ""),
        "motor": motor,
        "percurso": percurso,
    })
    repo.salvar("aluno", ctx, novo, aluno)


def _etapa_registros(repo: AvaliacaoRepo, ctx: Contexto, base: Mapping[str, Any], alunos: List[str]) -> None:
    _titulo("3 · Registrar as aprendizagens", "Registre o que cada estudante demonstrou nas aprendizagens que realmente foram trabalhadas e avaliadas.")
    _guia("Use NE quando ainda faltam evidências; NC apenas quando a aprendizagem foi ensinada/retomada e ainda não foi consolidada. ED e RP não entram no julgamento do estudante nesta etapa.")
    _ganho_pratico(
        "Aqui o registro começa a virar intervenção",
        [
            "NC e EP deixam de ser apenas códigos: mostram exatamente qual aprendizagem precisa voltar ao planejamento.",
            "C mostra onde o estudante já trabalha com autonomia e onde você pode elevar a complexidade.",
            "AA indica que vale oferecer desafios de transferência, análise ou elaboração — em vez de repetir exercícios do mesmo nível.",
        ],
        "🧠",
    )

    if not alunos:
        st.warning("Nenhum estudante foi localizado no Carômetro para esta turma.")
        return

    cobertura = repo.obter("cobertura", ctx).get("dimensoes", {}) or _default_cobertura(base)
    blueprint = repo.obter("blueprint", ctx).get("itens", {}) or _default_blueprint(base)
    existentes = repo.listar_alunos(ctx)
    dims = base.get("dimensoes", [])
    dims_at = [d for d in dims if (cobertura.get(d["codigo"]) or {}).get("situacao") == "AT"]

    if not dims_at:
        st.warning("Não há aprendizagens AT. Volte à etapa 1 e defina o que foi trabalhado e avaliado.")
        return

    modo = st.radio(
        "Forma de lançamento",
        ["👤 Por estudante", "⚡ Grade rápida"],
        horizontal=True,
        key=f"av2_modo_tab_{_slug(ctx.turma)}_{_slug(ctx.componente)}",
    )

    if modo == "👤 Por estudante":
        concluido_alunos = []
        for aluno in alunos:
            status = (existentes.get(aluno, {}) or {}).get("status", {}) or {}
            if all(status.get(d["codigo"]) in {"NE", "NC", "EP", "C", "AA"} for d in dims_at):
                concluido_alunos.append(aluno)

        p = _percentual(len(concluido_alunos), len(alunos))
        st.markdown(_barra_progresso(p), unsafe_allow_html=True)
        st.caption(f"{len(concluido_alunos)} de {len(alunos)} estudantes possuem registro em todas as aprendizagens AT.")

        aluno = st.selectbox(
            "Estudante",
            alunos,
            format_func=lambda nome: f"{'✓ ' if nome in concluido_alunos else ''}{nome}",
            key=f"av2_aluno_tab_{_slug(ctx.turma)}_{_slug(ctx.componente)}",
        )
        dados = existentes.get(aluno, {}) or {}
        anterior = dados.get("status", {}) or {}
        novos_status = dict(anterior)

        with st.container(border=True):
            st.markdown(f"### {aluno}")
            st.caption("Selecione o nível que melhor representa a evidência do período. O conceito será apenas sugerido depois do conjunto dos registros.")

            for numero, dim in enumerate(dims_at, 1):
                codigo = dim["codigo"]
                st.markdown(f"**{numero}. {dim.get('nome', '')}**")
                st.caption(dim.get("demonstrar", ""))
                atual = anterior.get(codigo, "")
                opcoes = STATUS_OPCOES
                valor = st.selectbox(
                    f"Evidência · {codigo}",
                    opcoes,
                    index=opcoes.index(atual) if atual in opcoes else 0,
                    format_func=_format_status,
                    key=f"av2_st_{_slug(ctx.turma)}_{_slug(ctx.componente)}_{_slug(aluno)}_{codigo}",
                    label_visibility="collapsed",
                )
                if valor:
                    st.caption(STATUS_DESCRICAO[valor])
                novos_status[codigo] = valor
                if numero < len(dims_at):
                    st.markdown("<hr style='border:none;border-top:1px solid #eef2f7;margin:10px 0'>", unsafe_allow_html=True)

        motor = calcular_conceito_sugerido(novos_status, base, cobertura, dados.get("percurso", "") or sugerir_percurso(cobertura), blueprint)
        if motor.get("conceito"):
            st.markdown(
                f'<div class="av-callout-info">Com os registros atuais, a leitura preliminar é <b>{_esc(motor["conceito"])}</b>. Isso ainda não é o conceito final; o fechamento acontece na etapa 4.</div>',
                unsafe_allow_html=True,
            )
        else:
            st.info(motor.get("motivo", "Ainda faltam evidências para uma leitura preliminar."))

        dados_preview = dict(dados)
        dados_preview["status"] = novos_status
        fortes_preview, prioridades_preview = construir_perfil_aluno(base, dados_preview)
        if prioridades_preview:
            _radar(
                "O que este registro sugere para a próxima intervenção",
                "Priorize " + "; ".join(prioridades_preview[:3]) + ". Antes de propor mais do mesmo, verifique se a dificuldade está no conteúdo atual ou em um pré-requisito relacionado.",
            )
        elif fortes_preview:
            _radar(
                "O estudante já apresenta base para avançar",
                "As aprendizagens registradas aparecem predominantemente consolidadas. Planeje situações de maior autonomia, aplicação e transferência para continuar produzindo evidência de avanço.",
            )

        if st.button("Salvar registros deste estudante", type="primary", use_container_width=True, key=f"av2_save_student_{_slug(ctx.turma)}_{_slug(ctx.componente)}"):
            _salvar_status_aluno(repo, ctx, base, cobertura, blueprint, aluno, novos_status)
            st.success(f"Registros de {aluno} salvos.")
            st.rerun()

    else:
        st.caption("A grade rápida é indicada para quem já conhece a legenda e precisa lançar a turma com agilidade. Para ler as descrições pedagógicas, use o modo “Por estudante”.")
        rows = []
        for aluno in alunos:
            dados = existentes.get(aluno, {}) or {}
            status = dados.get("status", {}) or {}
            row = {"Estudante": aluno}
            for dim in dims_at:
                row[dim["codigo"]] = status.get(dim["codigo"], "")
            motor = calcular_conceito_sugerido(status, base, cobertura, dados.get("percurso", "") or sugerir_percurso(cobertura), blueprint)
            row["Leitura"] = motor.get("conceito", "")
            rows.append(row)

        df = pd.DataFrame(rows)
        cfg: Dict[str, Any] = {
            "Estudante": st.column_config.TextColumn("Estudante", width="large"),
            "Leitura": st.column_config.TextColumn("Leitura", width="small"),
        }
        for dim in dims_at:
            cfg[dim["codigo"]] = st.column_config.SelectboxColumn(
                dim["codigo"], options=STATUS_OPCOES, width="small",
                help=dim.get("nome", ""),
            )
        edited = st.data_editor(
            df,
            hide_index=True,
            use_container_width=True,
            disabled=["Estudante", "Leitura"],
            column_config=cfg,
            key=f"av2_grid_{_slug(ctx.turma)}_{_slug(ctx.componente)}",
        )
        if st.button("Salvar grade rápida", type="primary", use_container_width=True, key=f"av2_save_grid_{_slug(ctx.turma)}_{_slug(ctx.componente)}"):
            registros = []
            for _, row in edited.iterrows():
                aluno = str(row["Estudante"])
                antigo = existentes.get(aluno, {}) or {}
                statuses = dict(antigo.get("status", {}) or {})
                for dim in dims_at:
                    valor = row.get(dim["codigo"], "")
                    statuses[dim["codigo"]] = "" if pd.isna(valor) else str(valor or "")
                percurso = antigo.get("percurso", "") or sugerir_percurso(cobertura)
                motor = calcular_conceito_sugerido(statuses, base, cobertura, percurso, blueprint)
                novo = dict(antigo)
                novo.update({"status": statuses, "conceito_sugerido": motor.get("conceito", ""), "motor": motor, "percurso": percurso})
                registros.append(("aluno", ctx, novo, aluno))
            repo.salvar_varios(registros)
            st.success("Registros da turma salvos.")
            st.rerun()

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    if st.button("Ir para o fechamento dos conceitos →", use_container_width=True, key=f"av2_to_close_{_slug(ctx.turma)}_{_slug(ctx.componente)}"):
        st.session_state["av_v2_force_step"] = 4
        st.rerun()


# -----------------------------------------------------------------------------
# Tela do componente — Etapa 4: fechamento
# -----------------------------------------------------------------------------

def _etapa_fechamento(repo: AvaliacaoRepo, ctx: Contexto, base: Mapping[str, Any], alunos: List[str]) -> None:
    _titulo("4 · Fechar os conceitos", "O Integra organiza as evidências e apresenta uma sugestão explicada. A decisão final continua sendo do professor.")
    _guia("Revise um estudante por vez, leia o motivo da sugestão, confirme ou altere o conceito e registre o próximo passo pedagógico. Se divergir do sistema, justifique com base nas evidências.")
    _ganho_pratico(
        "O fechamento só vale a pena se melhorar o próximo planejamento",
        [
            "O conceito sintetiza o período, mas o campo mais útil para a prática é o próximo passo pedagógico.",
            "A justificativa faz o professor voltar às evidências quando sua leitura profissional diverge da sugestão do sistema.",
            "Ao final, você tem um retrato do que o estudante demonstra e uma decisão concreta sobre o que fazer a seguir.",
        ],
        "🚀",
    )

    if not alunos:
        st.warning("Sem estudantes para o fechamento.")
        return

    cobertura = repo.obter("cobertura", ctx).get("dimensoes", {}) or _default_cobertura(base)
    blueprint = repo.obter("blueprint", ctx).get("itens", {}) or _default_blueprint(base)
    existentes = repo.listar_alunos(ctx)

    fechados = [aluno for aluno in alunos if (existentes.get(aluno, {}) or {}).get("conceito_final") in CONCEITOS]
    p = _percentual(len(fechados), len(alunos))
    st.markdown(_barra_progresso(p), unsafe_allow_html=True)
    st.caption(f"{len(fechados)} de {len(alunos)} estudantes com conceito final registrado.")

    aluno = st.selectbox(
        "Estudante para revisar",
        alunos,
        format_func=lambda nome: f"{'✓ ' if nome in fechados else ''}{nome}",
        key=f"av2_close_student_{_slug(ctx.turma)}_{_slug(ctx.componente)}",
    )
    dados = existentes.get(aluno, {}) or {}
    percurso_atual = dados.get("percurso", "") or sugerir_percurso(cobertura)
    motor = calcular_conceito_sugerido(dados.get("status", {}) or {}, base, cobertura, percurso_atual, blueprint)
    sugestao = motor.get("conceito", "")

    c1, c2 = st.columns([1, 2.5])
    with c1:
        with st.container(border=True):
            st.markdown('<div class="av-concept-label">Sugestão do sistema</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="av-concept">{_esc(sugestao or "—")}</div>', unsafe_allow_html=True)
            if sugestao:
                st.markdown(_status_badge(sugestao), unsafe_allow_html=True)
            else:
                st.caption("Ainda sem evidência suficiente")
    with c2:
        with st.container(border=True):
            st.markdown("**Por que o sistema chegou a esta leitura?**")
            st.write(motor.get("motivo", "Ainda não há evidências suficientes."))
            for alerta in motor.get("alertas", []):
                st.warning(alerta)

    metricas = motor.get("metricas", {}) or {}
    if metricas:
        colunas = st.columns(5)
        for coluna, status in zip(colunas, ["NC", "EP", "C", "AA", "NE"]):
            coluna.metric(status, metricas.get(status, 0))

    fortes, prioridades = construir_perfil_aluno(base, dados)
    f1, f2 = st.columns(2)
    with f1:
        with st.container(border=True):
            st.markdown("**✓ O que já demonstra**")
            if fortes:
                for item in fortes[:8]:
                    st.markdown(f"- {item}")
            else:
                st.caption("Ainda não há aprendizagens registradas como C/AA.")
    with f2:
        with st.container(border=True):
            st.markdown("**→ O que precisa consolidar**")
            if prioridades:
                for item in prioridades[:8]:
                    st.markdown(f"- {item}")
            else:
                st.caption("Sem prioridades NC/EP entre os registros atuais.")

    st.markdown("### Decisão profissional")
    d1, d2 = st.columns(2)
    with d1:
        final_atual = dados.get("conceito_final", "") or sugestao
        final = st.selectbox(
            "Conceito final",
            [""] + CONCEITOS,
            index=([""] + CONCEITOS).index(final_atual) if final_atual in CONCEITOS else 0,
            key=f"av2_final_{_slug(ctx.turma)}_{_slug(ctx.componente)}_{_slug(aluno)}",
        )
    with d2:
        percurso = st.selectbox(
            "Percurso curricular",
            PERCURSO_OPCOES,
            index=PERCURSO_OPCOES.index(percurso_atual) if percurso_atual in PERCURSO_OPCOES else 0,
            format_func=lambda x: "— selecionar —" if not x else f"{x} · {PERCURSOS[x]}",
            key=f"av2_perc_{_slug(ctx.turma)}_{_slug(ctx.componente)}_{_slug(aluno)}",
        )

    proximo = st.text_area(
        "Próximo passo pedagógico",
        value=str(dados.get("proximo_passo", "") or ""),
        placeholder="Ex.: manter produção de problemas de duas etapas e retomar divisão com apoio visual.",
        height=90,
        key=f"av2_next_{_slug(ctx.turma)}_{_slug(ctx.componente)}_{_slug(aluno)}",
    )

    diverge = bool(final and sugestao and final != sugestao)
    justificativa = st.text_area(
        "Justificativa pedagógica" + (" · obrigatória porque o conceito diverge da sugestão" if diverge else " · opcional"),
        value=str(dados.get("justificativa", "") or ""),
        placeholder="Registre as evidências que fundamentam a decisão profissional.",
        height=90,
        key=f"av2_just_{_slug(ctx.turma)}_{_slug(ctx.componente)}_{_slug(aluno)}",
    )

    pode_salvar = bool(final) and not (diverge and not justificativa.strip())
    if diverge and not justificativa.strip():
        st.warning("Como o conceito final diverge da sugestão, registre a justificativa pedagógica antes de salvar.")

    sintese_preview = _texto_sintese_individual(
        aluno,
        ctx.componente,
        final or sugestao,
        fortes,
        prioridades,
        proximo,
    )
    st.markdown(
        f'<div class="av-summary"><div class="av-summary-title">Leitura pedagógica pronta para você usar</div><div class="av-summary-text">{_esc(sintese_preview)}</div></div>',
        unsafe_allow_html=True,
    )

    if st.button("Confirmar fechamento deste estudante", type="primary", use_container_width=True, disabled=not pode_salvar, key=f"av2_save_close_{_slug(ctx.turma)}_{_slug(ctx.componente)}"):
        novo = dict(dados)
        novo.update({
            "conceito_sugerido": sugestao,
            "conceito_final": final,
            "percurso": percurso or percurso_atual,
            "proximo_passo": proximo,
            "justificativa": justificativa,
            "motor": motor,
        })
        repo.salvar("aluno", ctx, novo, aluno)
        st.success(f"Fechamento de {aluno} registrado.")
        st.rerun()

    st.markdown("### Visão rápida da turma")
    linhas = []
    for nome in alunos:
        d = existentes.get(nome, {}) or {}
        mot = calcular_conceito_sugerido(d.get("status", {}) or {}, base, cobertura, d.get("percurso", "") or sugerir_percurso(cobertura), blueprint)
        linhas.append({
            "Estudante": nome,
            "Sugestão": mot.get("conceito", ""),
            "Final": d.get("conceito_final", ""),
            "Percurso": d.get("percurso", ""),
            "Próximo passo": d.get("proximo_passo", ""),
        })
    st.dataframe(pd.DataFrame(linhas), hide_index=True, use_container_width=True)


# -----------------------------------------------------------------------------
# Tela do componente — orquestração
# -----------------------------------------------------------------------------

def _trabalhar_componente(repo: AvaliacaoRepo, ctx_base: Contexto, componentes: List[str], alunos: List[str]) -> None:
    if not componentes:
        st.warning("Nenhum componente disponível para este usuário/turma.")
        return

    comp_default = st.session_state.get("av_v2_componente")
    if comp_default not in componentes:
        comp_default = componentes[0]
        st.session_state["av_v2_componente"] = comp_default

    c1, c2 = st.columns([1.3, 3])
    with c1:
        componente = st.selectbox(
            "Componente curricular",
            componentes,
            index=componentes.index(comp_default),
            key="av_v2_comp_selector",
        )
        st.session_state["av_v2_componente"] = componente

    ctx = Contexto(ctx_base.ano_letivo, ctx_base.ano_escolar, ctx_base.trimestre, ctx_base.turma, componente)
    base = _base_curricular(ctx.ano_escolar, ctx.trimestre, componente)
    if not base:
        st.error("A base curricular desta combinação não foi localizada.")
        return

    progresso = _progresso_componente(repo, ctx, base, alunos)
    with c2:
        meta = COMPONENTE_META.get(componente, {"icone": "📘", "cor": "#2563eb"})
        st.markdown(
            f'<div class="av-card" style="margin-top:0;border-left:4px solid {meta["cor"]};"><div class="av-card-title">{meta["icone"]} {_esc(componente)} · {progresso["total"]}% concluído</div>{_barra_progresso(progresso["total"], meta["cor"])}<div class="av-small">Próxima ação: <b>{_esc(progresso["proxima"])}</b></div></div>',
            unsafe_allow_html=True,
        )

    st.markdown(_etapas_html(progresso), unsafe_allow_html=True)

    opcoes = {
        "1 · Currículo": 1,
        "2 · Evidências": 2,
        "3 · Registros": 3,
        "4 · Fechamento": 4,
    }
    labels = list(opcoes)
    step_key = f"av2_step_radio_{_slug(ctx.turma)}_{_slug(componente)}"
    force_step = st.session_state.pop("av_v2_force_step", None)
    if force_step in {1, 2, 3, 4}:
        force_label = next(label for label, valor in opcoes.items() if valor == force_step)
        st.session_state[step_key] = force_label
    if step_key not in st.session_state:
        etapa_inicial = int(progresso.get("etapa", 1))
        st.session_state[step_key] = next(label for label, valor in opcoes.items() if valor == etapa_inicial)

    escolha = st.radio(
        "Etapa do trabalho",
        labels,
        horizontal=True,
        key=step_key,
        label_visibility="collapsed",
    )
    etapa = opcoes[escolha]

    if etapa == 1:
        _etapa_curriculo(repo, ctx, base)
    elif etapa == 2:
        _etapa_evidencias(repo, ctx, base)
    elif etapa == 3:
        _etapa_registros(repo, ctx, base, alunos)
    else:
        _etapa_fechamento(repo, ctx, base, alunos)


# -----------------------------------------------------------------------------
# Perfil do estudante
# -----------------------------------------------------------------------------

def _perfil_estudante(repo: AvaliacaoRepo, ctx_base: Contexto, componentes: List[str], alunos: List[str]) -> None:
    _titulo("Perfil integrado do estudante", "Uma leitura pedagógica única dos cinco componentes: onde o estudante está, o que já sustenta novos desafios e onde a intervenção precisa ser mais intencional.")
    _guia("Selecione o estudante. Use esta tela para planejar intervenção, conversar com a equipe e preparar devolutivas — não para produzir mais um relatório.")
    _ganho_pratico(
        "O que esta visão te entrega",
        [
            "Forças do estudante que podem ser usadas como ponto de apoio.",
            "Prioridades específicas, evitando intervenções genéricas como “precisa melhorar”.",
            "Próximos passos já registrados em cada componente, reunidos num único lugar.",
        ],
        "👤",
    )

    if not alunos:
        st.warning("Sem estudantes para exibir.")
        return

    aluno = st.selectbox("Estudante", alunos, key=f"av2_perfil_{_slug(ctx_base.turma)}")

    conceitos_validos = 0
    for componente in componentes:
        ctx = Contexto(ctx_base.ano_letivo, ctx_base.ano_escolar, ctx_base.trimestre, ctx_base.turma, componente)
        dados = repo.obter("aluno", ctx, aluno)
        if (dados.get("conceito_final") or dados.get("conceito_sugerido")) in CONCEITOS:
            conceitos_validos += 1

    k1, k2, k3 = st.columns(3)
    k1.metric("Componentes com leitura", f"{conceitos_validos}/{len(componentes)}")
    k2.metric("Turma", ctx_base.turma)
    k3.metric("Período", f"{ctx_base.trimestre}º trimestre")

    for componente in componentes:
        ctx = Contexto(ctx_base.ano_letivo, ctx_base.ano_escolar, ctx_base.trimestre, ctx_base.turma, componente)
        base = _base_curricular(ctx.ano_escolar, ctx.trimestre, componente)
        dados = repo.obter("aluno", ctx, aluno)
        conceito = dados.get("conceito_final") or dados.get("conceito_sugerido") or ""
        percurso = dados.get("percurso", "")
        fortes, prioridades = construir_perfil_aluno(base, dados)
        meta = COMPONENTE_META.get(componente, {"icone": "📘", "cor": "#2563eb"})

        with st.container(border=True):
            c1, c2, c3 = st.columns([2.2, .7, 2.8])
            with c1:
                st.markdown(f"### {meta['icone']} {componente}")
                if percurso:
                    st.caption(f"{percurso} · {PERCURSOS.get(percurso, '')}")
            with c2:
                st.markdown(f'<div class="av-concept-label">Conceito</div><div class="av-concept">{_esc(conceito or "—")}</div>', unsafe_allow_html=True)
            with c3:
                if dados.get("proximo_passo"):
                    st.markdown("**Próximo passo**")
                    st.write(dados.get("proximo_passo"))
                else:
                    st.caption("Próximo passo ainda não registrado.")

            f1, f2 = st.columns(2)
            with f1:
                st.markdown("**✓ Já demonstra**")
                if fortes:
                    for item in fortes[:6]:
                        st.markdown(f"- {item}")
                else:
                    st.caption("Sem registros C/AA suficientes até o momento.")
            with f2:
                st.markdown("**→ Prioridades de aprendizagem**")
                if prioridades:
                    for item in prioridades[:6]:
                        st.markdown(f"- {item}")
                else:
                    st.caption("Sem registros NC/EP entre as dimensões julgadas.")


# -----------------------------------------------------------------------------
# Conselho de Ciclo
# -----------------------------------------------------------------------------


def _conselho(repo: AvaliacaoRepo, ctx_base: Contexto, componentes: List[str], alunos: List[str]) -> None:
    _titulo(
        "Síntese para o Conselho de Ciclo",
        "A ferramenta transforma os registros do trimestre em uma leitura coletiva da turma. O objetivo é apoiar a conversa pedagógica — não preencher a ata automaticamente.",
    )
    _guia("Analise os padrões, confira os estudantes que precisam de maior atenção e, ao final, use o texto sugerido. Se ele for útil para a ata, edite, copie e cole onde desejar.")
    _ganho_pratico(
        "O que o Conselho ganha com esta tela",
        [
            "A discussão parte de aprendizagens concretas, não apenas de uma lista de conceitos.",
            "As prioridades coletivas aparecem antes dos encaminhamentos, ajudando a equipe a decidir o que precisa entrar no próximo planejamento.",
            "O texto para registro é apenas uma síntese editável: o professor e o Conselho continuam responsáveis pela leitura final.",
        ],
        "🏛️",
    )

    if not alunos:
        st.warning("Sem estudantes para consolidar.")
        return

    comp_col = {
        "Língua Portuguesa": "LP", "Matemática": "MAT", "Ciências": "CIE",
        "História": "HIS", "Geografia": "GEO",
    }
    registros_comp: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for componente in componentes:
        ctx = Contexto(ctx_base.ano_letivo, ctx_base.ano_escolar, ctx_base.trimestre, ctx_base.turma, componente)
        registros_comp[componente] = repo.listar_alunos(ctx)

    linhas = []
    for aluno in alunos:
        row: Dict[str, Any] = {"Estudante": aluno}
        percursos: List[str] = []
        for componente in componentes:
            dados = registros_comp.get(componente, {}).get(aluno, {}) or {}
            row[comp_col.get(componente, componente)] = dados.get("conceito_final") or dados.get("conceito_sugerido") or ""
            if dados.get("percurso"):
                percursos.append(dados["percurso"])
        row["Percurso predominante"] = max(set(percursos), key=percursos.count) if percursos else ""
        linhas.append(row)

    df = pd.DataFrame(linhas)
    col_conceitos = [c for c in ["LP", "MAT", "CIE", "HIS", "GEO"] if c in df.columns]
    com_ab = df[df[col_conceitos].eq("AB").any(axis=1)] if col_conceitos else df.iloc[0:0]
    com_b = df[df[col_conceitos].eq("B").any(axis=1)] if col_conceitos else df.iloc[0:0]
    completos = df[df[col_conceitos].isin(CONCEITOS).all(axis=1)] if col_conceitos else df.iloc[0:0]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Estudantes", len(alunos))
    c2.metric("Ao menos um AB", len(com_ab))
    c3.metric("Ao menos um B", len(com_b))
    c4.metric("Fechamento completo", f"{len(completos)}/{len(alunos)}")

    prioridades_contagem: List[Dict[str, Any]] = []
    prioridades_texto: List[str] = []
    for componente in componentes:
        ctx = Contexto(ctx_base.ano_letivo, ctx_base.ano_escolar, ctx_base.trimestre, ctx_base.turma, componente)
        base = _base_curricular(ctx.ano_escolar, ctx.trimestre, componente)
        registros = registros_comp.get(componente, {})
        cont: Dict[str, int] = {}
        for aluno in alunos:
            status = (registros.get(aluno, {}) or {}).get("status", {}) or {}
            for dim in base.get("dimensoes", []):
                if status.get(dim["codigo"]) in {"NC", "EP"}:
                    nome = dim.get("nome", dim["codigo"])
                    cont[nome] = cont.get(nome, 0) + 1
        for nome, qtd in sorted(cont.items(), key=lambda x: (-x[1], x[0]))[:3]:
            prioridades_contagem.append({
                "Componente": componente,
                "Aprendizagem prioritária": nome,
                "Estudantes em NC/EP": qtd,
            })
            prioridades_texto.append(f"{componente}: {nome} ({qtd} estudante(s) em NC/EP)")

    if prioridades_texto:
        _radar(
            "O Conselho já tem um ponto de partida objetivo",
            prioridades_texto[0] + ". Comece a discussão por esse padrão: ele pode indicar necessidade de retomada coletiva, mudança de estratégia ou investigação de pré-requisitos.",
        )
    else:
        _radar(
            "Ainda não há concentração clara de NC/EP",
            "Use a leitura dos perfis individuais para verificar situações pontuais e preservar oportunidades de ampliação para os estudantes que já consolidaram o período.",
        )

    tab1, tab2, tab3 = st.tabs(["🎯 Prioridades da turma", "👥 Estudantes", "📝 Texto para registro"])

    with tab1:
        _titulo("Prioridades coletivas", "Aprendizagens que concentram mais registros EP/NC. Use-as para decidir intervenções da turma.")
        if prioridades_contagem:
            st.dataframe(pd.DataFrame(prioridades_contagem), hide_index=True, use_container_width=True)
        else:
            st.info("Ainda não há prioridades coletivas suficientes para sintetizar.")

    with tab2:
        filtro = st.radio(
            "Exibir",
            ["Todos", "Com AB", "Com B", "Fechamento incompleto"],
            horizontal=True,
            key=f"av3_cons_filtro_{_slug(ctx_base.turma)}",
        )
        exibicao = df
        if filtro == "Com AB":
            exibicao = com_ab
        elif filtro == "Com B":
            exibicao = com_b
        elif filtro == "Fechamento incompleto":
            exibicao = df[~df[col_conceitos].isin(CONCEITOS).all(axis=1)] if col_conceitos else df
        st.dataframe(exibicao, hide_index=True, use_container_width=True)

    with tab3:
        linhas_texto = [
            f"Síntese pedagógica — {ctx_base.turma} — {ctx_base.trimestre}º trimestre/{ctx_base.ano_letivo}.",
            "",
            f"A análise dos registros de aprendizagem contempla {len(alunos)} estudantes do {ctx_base.ano_escolar}º ano.",
        ]
        if len(completos) < len(alunos):
            linhas_texto.append(
                f"No momento desta síntese, {len(completos)} de {len(alunos)} estudantes possuem fechamento completo nos componentes disponíveis; os demais registros ainda devem ser considerados em processo de consolidação."
            )
        if len(com_ab):
            nomes_ab = ", ".join(com_ab["Estudante"].astype(str).tolist()[:10])
            complemento = " e outros" if len(com_ab) > 10 else ""
            linhas_texto.append(
                f"{len(com_ab)} estudante(s) apresenta(m) ao menos um conceito AB no conjunto dos componentes: {nomes_ab}{complemento}. Esses casos requerem análise das evidências e definição de intervenção sistemática."
            )
        if len(com_b):
            linhas_texto.append(
                f"{len(com_b)} estudante(s) apresenta(m) ao menos um conceito B em algum componente, indicando aprendizagens ainda parciais ou instáveis que demandam continuidade de mediação e recomposição."
            )
        if prioridades_texto:
            linhas_texto.append("")
            linhas_texto.append("Prioridades coletivas identificadas nos registros:")
            for item in prioridades_texto[:8]:
                linhas_texto.append(f"- {item}.")
            linhas_texto.append(
                "Como encaminhamento, recomenda-se que essas prioridades sejam retomadas no planejamento subsequente com estratégias focalizadas, produção de novas evidências e reavaliação do avanço dos estudantes."
            )
        else:
            linhas_texto.append(
                "Não foi identificada, até o momento, concentração suficiente de registros NC/EP para caracterizar uma prioridade coletiva única; recomenda-se manter o acompanhamento dos casos individuais e ampliar desafios para aprendizagens já consolidadas."
            )

        linhas_texto.append("")
        linhas_texto.append(
            "Esta síntese é um texto-base produzido a partir dos registros do módulo e deve ser revisado pela equipe antes de qualquer utilização oficial."
        )
        texto_sugerido = "\n".join(linhas_texto)

        key_texto = f"av3_texto_conselho_{_slug(ctx_base.turma)}_{ctx_base.ano_letivo}_{ctx_base.trimestre}"
        if key_texto not in st.session_state:
            st.session_state[key_texto] = texto_sugerido

        st.markdown(
            '<div class="av-callout-info"><b>Sem envio automático:</b> o Integra não encaminha nada para a Ata. Edite o texto abaixo e copie somente se ele fizer sentido para o registro do Conselho.</div>',
            unsafe_allow_html=True,
        )
        st.text_area(
            "Texto sugerido para registro",
            key=key_texto,
            height=360,
            help="O texto é editável. Revise, selecione e copie se quiser utilizá-lo na ata ou em outro registro.",
        )
        c_reset, c_tip = st.columns([1, 2.5])
        with c_reset:
            if st.button("Restaurar texto sugerido", use_container_width=True, key=f"av3_reset_text_{_slug(ctx_base.turma)}"):
                st.session_state[key_texto] = texto_sugerido
                st.rerun()
        with c_tip:
            st.caption("Dica: revise o texto com a equipe. Para copiar, clique no campo, use Ctrl+A e Ctrl+C.")

def _validar_base_externa() -> Tuple[bool, str]:
    esperados = ["Língua Portuguesa", "Matemática", "Ciências", "História", "Geografia"]
    faltas: List[str] = []
    for ano in range(1, 6):
        for trimestre in (1, 2, 3):
            bloco = AVALIACAO_DB.get(ano, {}).get(trimestre, {})
            for componente in esperados:
                base = bloco.get(componente)
                if not isinstance(base, Mapping):
                    faltas.append(f"{ano}º/{trimestre}º/{componente}")
                elif not base.get("dimensoes"):
                    faltas.append(f"{ano}º/{trimestre}º/{componente} sem dimensões")
    if faltas:
        return False, "; ".join(faltas[:12]) + ("..." if len(faltas) > 12 else "")
    return True, ""


def _show_setup(sql_text: str, erro: str) -> None:
    st.error("A tabela de avaliação ainda não está disponível no Supabase.")
    st.caption("Execute o SQL abaixo uma única vez no SQL Editor do Supabase. O restante do Integra não precisa ser alterado.")
    with st.expander("Ver SQL de instalação", expanded=True):
        st.code(sql_text, language="sql")
    if erro:
        with st.expander("Detalhe técnico"):
            st.code(erro)


# -----------------------------------------------------------------------------
# Entrada principal
# -----------------------------------------------------------------------------

def renderizar_avaliacao(supabase: Any, sql_instalacao: Optional[str] = None) -> None:
    _css()

    base_ok, base_erro = _validar_base_externa()
    if not base_ok:
        st.error("A base pedagógica está incompleta ou incompatível com esta versão do módulo.")
        st.code(base_erro)
        st.caption("Confirme que dados_avaliacao_completo.py está na mesma pasta de avaliacao.py.")
        return

    usuario_nome = st.session_state.get("usuario_nome", "Usuário")
    usuario_matricula = st.session_state.get("usuario_matricula", "")
    matriz_professores = _carregar_matriz_professores(supabase)
    gestor = _eh_gestor(usuario_matricula, usuario_nome, supabase)

    # Contexto: compacto e sempre disponível.
    with st.expander("⚙️ Turma e período", expanded=not bool(st.session_state.get("av_v2_context_ready"))):
        a, b, c = st.columns(3)
        with a:
            ano_letivo = int(st.number_input("Ano letivo", min_value=2025, max_value=2035, value=int(st.session_state.get("av_v2_ano_letivo", date.today().year)), step=1, key="av_v2_ano_letivo"))
        with b:
            anos = _anos_disponiveis()
            ano_escolar = st.selectbox("Ano de escolaridade", anos, format_func=lambda x: f"{x}º ano", key="av_v2_ano_escolar")
        with c:
            trimestres = _trimestres_disponiveis(ano_escolar)
            trimestre = st.selectbox("Trimestre", trimestres, format_func=lambda x: f"{x}º trimestre", key="av_v2_trimestre")

        turmas = _turmas_permitidas(matriz_professores, usuario_nome, gestor, supabase, ano_escolar)
        if not turmas:
            st.warning(f"Não encontrei turmas do {ano_escolar}º ano vinculadas ao seu usuário na matriz de professores nem no Carômetro.")
            return
        turma = st.selectbox("Turma", turmas, key="av_v2_turma")
        st.session_state["av_v2_context_ready"] = True

    alunos = _alunos_da_turma(supabase, turma)
    disponiveis = _componentes_disponiveis(ano_escolar, trimestre)
    componentes = _componentes_permitidos(matriz_professores, usuario_nome, gestor, turma, disponiveis)
    ctx_base = Contexto(ano_letivo, ano_escolar, trimestre, turma, "")

    _hero(ctx_base, usuario_nome)

    st.markdown(
        '''
        <div class="av-impact-grid" style="grid-template-columns:repeat(3,minmax(0,1fr));margin-top:-5px">
          <div class="av-impact" style="min-height:112px"><div class="av-eyebrow">ANTES DA AULA</div><div class="av-impact-title">Planeje pelo que o aluno precisa aprender</div><div class="av-impact-text">Use currículo e pré-requisitos para escolher o foco e antecipar possíveis barreiras.</div></div>
          <div class="av-impact" style="min-height:112px"><div class="av-eyebrow">DURANTE O TRIMESTRE</div><div class="av-impact-title">Observe evidências, não impressões</div><div class="av-impact-text">Registre o que o estudante demonstra e transforme dificuldades em decisões de intervenção.</div></div>
          <div class="av-impact" style="min-height:112px"><div class="av-eyebrow">NO FECHAMENTO</div><div class="av-impact-title">Conceitue e já planeje o próximo passo</div><div class="av-impact-text">A síntese final deve alimentar o ensino seguinte, e não encerrar a aprendizagem.</div></div>
        </div>
        ''',
        unsafe_allow_html=True,
    )

    repo = AvaliacaoRepo(supabase, usuario_nome)
    ok, erro = repo.disponivel()
    if not ok:
        _show_setup(sql_instalacao or SQL_INSTALACAO, erro)
        return

    # Navegação principal: poucas escolhas e nomes orientados à tarefa.
    areas = ["🏠 Meu painel", "📚 Percurso do componente", "👤 Perfil do estudante", "🏛️ Síntese do Conselho"]
    force_area = st.session_state.pop("av_v2_force_area", None)
    aliases_area = {
        "🏠 Visão geral": "🏠 Meu painel",
        "📚 Trabalhar componente": "📚 Percurso do componente",
        "🏛️ Conselho de Ciclo": "🏛️ Síntese do Conselho",
    }
    force_area = aliases_area.get(force_area, force_area)
    if force_area in areas:
        st.session_state["av_v2_area_radio"] = force_area
    if "av_v2_area_radio" not in st.session_state:
        st.session_state["av_v2_area_radio"] = areas[0]
    area = st.radio(
        "Navegação",
        areas,
        horizontal=True,
        key="av_v2_area_radio",
        label_visibility="collapsed",
    )

    if area == "🏠 Meu painel":
        _painel(repo, ctx_base, componentes, alunos)
    elif area == "📚 Percurso do componente":
        _trabalhar_componente(repo, ctx_base, componentes, alunos)
    elif area == "👤 Perfil do estudante":
        _perfil_estudante(repo, ctx_base, componentes, alunos)
    else:
        _conselho(repo, ctx_base, componentes, alunos)

    versao_base = str((METADADOS_AVALIACAO or {}).get("versao", "base completa"))
    st.caption(f"Integra · Avaliação e Aprendizagem {MODULO_AVALIACAO_VERSAO} · Base pedagógica {versao_base}")


SQL_INSTALACAO = """
create extension if not exists pgcrypto;

create table if not exists public."Avaliacao" (
    id uuid primary key default gen_random_uuid(),
    chave text not null unique,
    tipo text not null,
    ano_letivo integer not null,
    ano_escolar integer not null,
    trimestre integer not null check (trimestre between 1 and 3),
    turma text not null,
    componente text not null default '',
    aluno_nome text,
    dados_json jsonb not null default '{}'::jsonb,
    atualizado_por text,
    atualizado_em timestamptz not null default now()
);

create index if not exists avaliacao_contexto_idx
on public."Avaliacao" (ano_letivo, ano_escolar, trimestre, turma, componente, tipo);

create index if not exists avaliacao_aluno_idx
on public."Avaliacao" (turma, aluno_nome);

alter table public."Avaliacao" disable row level security;
""".strip()

__all__ = [
    "renderizar_avaliacao",
    "calcular_conceito_sugerido",
    "construir_perfil_aluno",
]
