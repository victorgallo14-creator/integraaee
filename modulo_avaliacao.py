# -*- coding: utf-8 -*-

"""Módulo Avaliação e Aprendizagem para o Sistema Integra.

Integração mínima esperada no app principal::

    elif app_mode_regular == "📊 Avaliação e Aprendizagem":
        from modulo_avaliacao import renderizar_avaliacao
        renderizar_avaliacao(supabase)

O módulo mantém sua lógica isolada e lê a base pedagógica de ``dados_avaliacao_completo.py``. Lê usuário da sessão do Streamlit, busca a matriz de professores
na tabela ``Config_Ata`` (chave ``matriz_professores``), usa ``Carometro`` como lista de
estudantes e persiste na tabela ``Avaliacao``. O app principal não precisa conhecer a
estrutura interna da avaliação. O arquivo de dados deve permanecer na mesma pasta do módulo.

O desenho pedagógico é currículo -> pré-requisitos -> diagnóstico/recomposição ->
cobertura da avaliação -> evidências por estudante -> sugestão de conceito -> decisão
profissional do docente.
"""
from __future__ import annotations
MODULO_AVALIACAO_VERSAO = "2026.09.24-r2-base-completa"
import io
import json
import math
import re
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple
import pandas as pd
import streamlit as st
from fpdf import FPDF

# Base pedagógica externa: 1º ao 5º ano, 1º/2º/3º trimestres.
from dados_avaliacao_completo import AVALIACAO_DB, METADADOS_AVALIACAO
STATUS_APRENDIZAGEM = {'NE': 'Evidência insuficiente', 'NC': 'Não consolidado', 'EP': 'Em processo', 'C': 'Consolidado', 'AA': 'Aprendizagem ampliada'}
PERCURSOS = {'P1': 'Recomposição intensiva', 'P2': 'Recomposição articulada ao ano corrente', 'P3': 'Currículo do ano predominante', 'P4': 'Currículo do período consolidado / em ampliação'}
SITUACAO_CURRICULAR = {'AT': 'Trabalhada e avaliada', 'ED': 'Em desenvolvimento', 'RP': 'Reprogramada'}
CONCEITOS = ['AB', 'B', 'AD', 'A']
TABLE_NAME = 'Avaliacao'
GESTAO_MATRICULAS = {'8257601', '8844051', '8084912', '8829405', '8011512', '8258411', '7047682', '88286861'}
STATUS_OPCOES = ['', 'NE', 'NC', 'EP', 'C', 'AA']
PERCURSO_OPCOES = ['', 'P1', 'P2', 'P3', 'P4']
SITUACAO_OPCOES = ['AT', 'ED', 'RP']

def _norm(texto: Any) -> str:
    s = str(texto or '').strip().upper()
    s = unicodedata.normalize('NFKD', s)
    s = ''.join((c for c in s if not unicodedata.combining(c)))
    s = re.sub('\\s+', ' ', s)
    return s

def _slug(texto: Any) -> str:
    s = _norm(texto)
    s = re.sub('[^A-Z0-9]+', '_', s).strip('_')
    return s or 'SEM_VALOR'

def _agora_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _ano_da_turma(turma: str) -> Optional[int]:
    """Extrai o ano escolar de nomes de turma usados no Integra.

    Aceita, entre outras variações:
    5º Ano 1, 5º Ano 01, 5° Ano 1, 5o Ano 1, 5 Ano 1 e 5ANO1.
    A normalização Unicode pode transformar o ordinal masculino em 'o'
    minúsculo; por isso a busca é case-insensitive.
    """
    texto = _norm(turma)
    m = re.search(r'(?<!\\d)([1-5])\\s*(?:[Oº°])?\\s*ANO\\b', texto, flags=re.IGNORECASE)
    if m:
        return int(m.group(1))

    if 'ANO' in texto:
        m = re.search(r'(?<!\\d)([1-5])(?!\\d)', texto)
        if m:
            return int(m.group(1))
    return None

def _clean_pdf(texto: Any) -> str:
    s = str(texto or '')
    tr = str.maketrans({'–': '-', '—': '-', '“': '"', '”': '"', '‘': "'", '’': "'", '•': '-', '→': '->', 'º': 'o', 'ª': 'a'})
    return s.translate(tr).encode('latin-1', 'replace').decode('latin-1')

def _componente_slug(componente: str) -> str:
    """Retorna uma sigla estável sem depender de um ano/trimestre específico."""
    mapa = {
        'Língua Portuguesa': 'LP',
        'Matemática': 'MAT',
        'Ciências': 'CIE',
        'História': 'HIS',
        'Geografia': 'GEO',
    }
    if componente in mapa:
        return mapa[componente]
    for ano in sorted(AVALIACAO_DB):
        for trimestre in sorted(AVALIACAO_DB.get(ano, {})):
            base = AVALIACAO_DB.get(ano, {}).get(trimestre, {}).get(componente)
            if isinstance(base, Mapping) and base.get('slug'):
                return str(base['slug'])
    return _slug(componente)[:12]

def _chave_registro(tipo: str, ano_letivo: int, ano_escolar: int, trimestre: int, turma: str, componente: str='', aluno: str='') -> str:
    partes = [tipo, ano_letivo, ano_escolar, trimestre, _slug(turma)]
    if componente:
        partes.append(_componente_slug(componente))
    if aluno:
        partes.append(_slug(aluno))
    return '|'.join(map(str, partes))

@dataclass
class Contexto:
    ano_letivo: int
    ano_escolar: int
    trimestre: int
    turma: str
    componente: str

class AvaliacaoRepo:

    def __init__(self, supabase: Any, usuario: str):
        self.supabase = supabase
        self.usuario = usuario or 'Usuário'

    def disponivel(self) -> Tuple[bool, str]:
        try:
            self.supabase.table(TABLE_NAME).select('id').limit(1).execute()
            return (True, '')
        except Exception as exc:
            return (False, str(exc))

    def _payload(self, chave: str, tipo: str, ctx: Contexto, dados: Mapping[str, Any], aluno: str='') -> Dict[str, Any]:
        return {'chave': chave, 'tipo': tipo, 'ano_letivo': int(ctx.ano_letivo), 'ano_escolar': int(ctx.ano_escolar), 'trimestre': int(ctx.trimestre), 'turma': ctx.turma, 'componente': ctx.componente, 'aluno_nome': aluno or None, 'dados_json': dict(dados), 'atualizado_por': self.usuario, 'atualizado_em': _agora_iso()}

    def obter(self, tipo: str, ctx: Contexto, aluno: str='') -> Dict[str, Any]:
        chave = _chave_registro(tipo, ctx.ano_letivo, ctx.ano_escolar, ctx.trimestre, ctx.turma, ctx.componente, aluno)
        try:
            res = self.supabase.table(TABLE_NAME).select('dados_json').eq('chave', chave).limit(1).execute()
            rows = getattr(res, 'data', None) or []
            if not rows:
                return {}
            dados = rows[0].get('dados_json', {})
            if isinstance(dados, str):
                try:
                    dados = json.loads(dados)
                except Exception:
                    dados = {}
            return dados or {}
        except Exception:
            return {}

    def salvar(self, tipo: str, ctx: Contexto, dados: Mapping[str, Any], aluno: str='') -> None:
        chave = _chave_registro(tipo, ctx.ano_letivo, ctx.ano_escolar, ctx.trimestre, ctx.turma, ctx.componente, aluno)
        payload = self._payload(chave, tipo, ctx, dados, aluno)
        self.supabase.table(TABLE_NAME).upsert(payload, on_conflict='chave').execute()

    def salvar_varios(self, registros: Sequence[Tuple[str, Contexto, Mapping[str, Any], str]]) -> None:
        payloads: List[Dict[str, Any]] = []
        for tipo, ctx, dados, aluno in registros:
            chave = _chave_registro(tipo, ctx.ano_letivo, ctx.ano_escolar, ctx.trimestre, ctx.turma, ctx.componente, aluno)
            payloads.append(self._payload(chave, tipo, ctx, dados, aluno))
        if payloads:
            self.supabase.table(TABLE_NAME).upsert(payloads, on_conflict='chave').execute()

    def listar_alunos(self, ctx: Contexto) -> Dict[str, Dict[str, Any]]:
        try:
            q = self.supabase.table(TABLE_NAME).select('aluno_nome,dados_json').eq('tipo', 'aluno').eq('ano_letivo', ctx.ano_letivo).eq('ano_escolar', ctx.ano_escolar).eq('trimestre', ctx.trimestre).eq('turma', ctx.turma).eq('componente', ctx.componente)
            res = q.execute()
            out: Dict[str, Dict[str, Any]] = {}
            for row in getattr(res, 'data', None) or []:
                nome = row.get('aluno_nome') or ''
                dados = row.get('dados_json') or {}
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

    def listar_turma_todos_componentes(self, ano_letivo: int, ano_escolar: int, trimestre: int, turma: str) -> List[Dict[str, Any]]:
        try:
            res = self.supabase.table(TABLE_NAME).select('componente,aluno_nome,dados_json').eq('tipo', 'aluno').eq('ano_letivo', ano_letivo).eq('ano_escolar', ano_escolar).eq('trimestre', trimestre).eq('turma', turma).execute()
            return getattr(res, 'data', None) or []
        except Exception:
            return []

def _base_curricular(ano: int, trimestre: int, componente: str) -> Dict[str, Any]:
    return AVALIACAO_DB.get(ano, {}).get(trimestre, {}).get(componente, {})

def _anos_disponiveis() -> List[int]:
    return sorted(AVALIACAO_DB)

def _trimestres_disponiveis(ano: int) -> List[int]:
    return sorted(AVALIACAO_DB.get(ano, {}))

def _componentes_disponiveis(ano: int, trimestre: int) -> List[str]:
    return list(AVALIACAO_DB.get(ano, {}).get(trimestre, {}).keys())

def _config_valor(supabase: Any, chave: str) -> Any:
    """Lê uma configuração diretamente da tabela Config_Ata do Integra."""
    try:
        res = supabase.table('Config_Ata').select('valor').eq('chave', chave).limit(1).execute()
        rows = getattr(res, 'data', None) or []
        return rows[0].get('valor') if rows else None
    except Exception:
        return None

def _config_json(supabase: Any, chave: str) -> Any:
    valor = _config_valor(supabase, chave)
    if valor in (None, ''):
        return None
    if isinstance(valor, (dict, list)):
        return valor
    try:
        return json.loads(valor)
    except Exception:
        return None

def _carregar_matriz_professores(supabase: Any) -> pd.DataFrame:
    """Busca a mesma matriz configurável já usada pelo Ensino Regular."""
    dados = _config_json(supabase, 'matriz_professores')
    if isinstance(dados, list):
        try:
            return pd.DataFrame(dados)
        except Exception:
            pass
    return pd.DataFrame(columns=['Ciclo', 'Turma', 'Disciplina', 'Professor'])

def _nomes_gestao_configurados(supabase: Any) -> set[str]:
    dados = _config_json(supabase, 'matriz_gestao')
    nomes: set[str] = set()
    if isinstance(dados, list):
        for item in dados:
            if isinstance(item, dict) and item.get('Nome'):
                nomes.add(_norm(item.get('Nome')))
    return nomes

def _eh_gestor(matricula: str, nome: str='', supabase: Any=None) -> bool:
    if str(matricula or '').strip() in GESTAO_MATRICULAS:
        return True
    nome_norm = _norm(nome)
    if supabase is not None and nome_norm in _nomes_gestao_configurados(supabase):
        return True
    if str(st.session_state.get('user_role', '')).strip().lower() in {'admin', 'gestor', 'diretor', 'coordenador'}:
        return True
    return nome_norm in {_norm('José Victor Souza Gallo'), _norm('Luciana Lopes Faber'), _norm('Oelen Fernando Pedro'), _norm('Luciana Martinati Tetzner'), _norm('Noreh Cristina Heldt Aldrigui'), _norm('Marília Motta Camargo dos Reis')}

def _turmas_permitidas(matriz_professores: Optional[pd.DataFrame], usuario_nome: str, gestor: bool, supabase: Any, ano_escolar: int) -> List[str]:
    turmas: List[str] = []
    if isinstance(matriz_professores, pd.DataFrame) and (not matriz_professores.empty):
        df = matriz_professores.copy()
        if 'Turma' in df.columns:
            if not gestor and 'Professor' in df.columns:
                df = df[df['Professor'].map(_norm) == _norm(usuario_nome)]
            turmas = [str(x).strip() for x in df.get('Turma', pd.Series(dtype=str)).dropna().tolist()]
            turmas = [t for t in turmas if _ano_da_turma(t) == ano_escolar]
    if gestor or not turmas:
        try:
            res = supabase.table('Carometro').select('turma').execute()
            for row in getattr(res, 'data', None) or []:
                t = str(row.get('turma', '')).strip()
                if _ano_da_turma(t) == ano_escolar:
                    turmas.append(t)
        except Exception:
            pass
    seen = set()
    out = []
    for t in turmas:
        k = _norm(t)
        if k and k not in seen:
            seen.add(k)
            out.append(t)
    return sorted(out, key=_norm)

def _alunos_da_turma(supabase: Any, turma: str) -> List[str]:
    try:
        res = supabase.table('Carometro').select('nome,turma').execute()
        alunos = []
        for row in getattr(res, 'data', None) or []:
            if _norm(row.get('turma')) == _norm(turma):
                nome = str(row.get('nome', '')).strip()
                if nome:
                    alunos.append(nome)
        return sorted(set(alunos), key=_norm)
    except Exception:
        return []

def _componentes_permitidos(matriz_professores: Optional[pd.DataFrame], usuario_nome: str, gestor: bool, turma: str, disponiveis: List[str]) -> List[str]:
    if gestor or not isinstance(matriz_professores, pd.DataFrame) or matriz_professores.empty:
        return disponiveis
    df = matriz_professores.copy()
    if not {'Professor', 'Turma', 'Disciplina'}.issubset(df.columns):
        return disponiveis
    df = df[(df['Professor'].map(_norm) == _norm(usuario_nome)) & (df['Turma'].map(_norm) == _norm(turma))]
    discs = {_norm(x) for x in df['Disciplina'].dropna().astype(str)}
    if 'POLIVALENTE' in discs:
        return disponiveis
    mapa = {'LINGUA PORTUGUESA': 'Língua Portuguesa', 'MATEMATICA': 'Matemática', 'CIENCIAS': 'Ciências', 'HISTORIA': 'História', 'GEOGRAFIA': 'Geografia', 'CIENCIAS, HIST. E GEO.': None}
    allowed: List[str] = []
    for d in discs:
        if d == 'CIENCIAS, HIST. E GEO.':
            allowed += [c for c in ['Ciências', 'História', 'Geografia'] if c in disponiveis]
        elif d in mapa and mapa[d] in disponiveis:
            allowed.append(mapa[d])
    return list(dict.fromkeys(allowed)) or disponiveis

def _codigos_estruturantes(base: Mapping[str, Any]) -> List[str]:
    return [d['codigo'] for d in base.get('dimensoes', []) if _norm(d.get('peso')) == 'ESTRUTURANTE']

def _blueprint_avancado(blueprint_estado: Mapping[str, Any], base: Mapping[str, Any]) -> Tuple[bool, int]:
    avancados = 0
    for item in base.get('blueprint', []):
        sid = str(item.get('id', ''))
        incluido = bool((blueprint_estado.get(sid) or {}).get('incluida', False))
        bloom = _norm(item.get('bloom'))
        if incluido and any((p in bloom for p in ['ANALIS', 'JUSTIFIC', 'AVALI', 'CRIAR', 'TRANSFER'])):
            avancados += 1
    return (avancados >= 2, avancados)

def sugerir_percurso(cobertura: Mapping[str, Any]) -> str:
    situacoes = [str((v or {}).get('situacao', '')) for v in cobertura.values()]
    if not situacoes:
        return ''
    at = situacoes.count('AT')
    ed = situacoes.count('ED')
    rp = situacoes.count('RP')
    total = max(1, len(situacoes))
    if rp >= math.ceil(total / 2):
        return 'P1'
    if rp > 0 or ed >= math.ceil(total / 3):
        return 'P2'
    if at == total:
        return 'P4'
    return 'P3'

def calcular_conceito_sugerido(status_por_dimensao: Mapping[str, str], base: Mapping[str, Any], cobertura: Mapping[str, Any], percurso: str='', blueprint_estado: Optional[Mapping[str, Any]]=None) -> Dict[str, Any]:
    """Sugere AB/B/AD/A sem substituir a decisão do professor.

    A função ignora dimensões RP e só usa como base de julgamento dimensões marcadas AT.
    ED fica fora do cálculo principal porque ainda está em desenvolvimento. NE não é NC.
    """
    blueprint_estado = blueprint_estado or {}
    dims = [d['codigo'] for d in base.get('dimensoes', [])]
    estruturantes = set(_codigos_estruturantes(base))
    at = [c for c in dims if (cobertura.get(c) or {}).get('situacao', 'AT') == 'AT']
    ed = [c for c in dims if (cobertura.get(c) or {}).get('situacao', 'AT') == 'ED']
    rp = [c for c in dims if (cobertura.get(c) or {}).get('situacao', 'AT') == 'RP']
    if not at:
        return {'conceito': '', 'motivo': 'Ainda não há dimensões marcadas como trabalhadas e avaliadas (AT).', 'alertas': ['Defina a cobertura curricular antes de fechar o conceito.'], 'metricas': {}}
    validos = {c: str(status_por_dimensao.get(c, '')).strip() for c in at}
    sem_evidencia = [c for c, s in validos.items() if s in ('', 'NE')]
    julgaveis = {c: s for c, s in validos.items() if s in {'NC', 'EP', 'C', 'AA'}}
    min_evid = max(1, math.ceil(len(at) * 0.7))
    if len(julgaveis) < min_evid:
        return {'conceito': '', 'motivo': f'Há evidência julgável em {len(julgaveis)} de {len(at)} dimensões AT.', 'alertas': ['Produza novas evidências antes da conceituação final.'], 'metricas': {'at': len(at), 'julgaveis': len(julgaveis), 'ne': len(sem_evidencia)}}
    total = len(julgaveis)
    nc = sum((1 for s in julgaveis.values() if s == 'NC'))
    ep = sum((1 for s in julgaveis.values() if s == 'EP'))
    c = sum((1 for s in julgaveis.values() if s == 'C'))
    aa = sum((1 for s in julgaveis.values() if s == 'AA'))
    consolidados = c + aa
    pct_cons = consolidados / total
    pct_nc = nc / total
    estr_status = {x: julgaveis.get(x) for x in estruturantes if x in at}
    alertas: List[str] = []
    if rp:
        alertas.append('Há aprendizagens reprogramadas; o conceito não deve ser lido como domínio integral do currículo previsto.')
    if ed:
        alertas.append('Há aprendizagens em desenvolvimento que ainda não compõem o núcleo do cálculo.')
    if sem_evidencia:
        alertas.append('Há dimensões AT com NE/sem registro; produza evidências adicionais quando possível.')
    if any((s == 'NC' for s in estr_status.values())) or pct_nc >= 0.25 or (nc > 0 and pct_cons < 0.5):
        conceito = 'AB'
        motivo = 'Há lacunas relevantes no núcleo avaliado, especialmente quando aprendizagens estruturantes permanecem não consolidadas.'
    elif nc > 0 or pct_cons < 0.75 or any((s in {'EP', 'NC'} for s in estr_status.values())):
        conceito = 'B'
        motivo = 'Há conhecimentos importantes demonstrados, mas aprendizagens essenciais ainda estão em processo ou instáveis e exigem intervenção para consolidação.'
    else:
        conceito = 'AD'
        motivo = 'Predominam aprendizagens consolidadas, sem lacunas estruturais significativas no que foi efetivamente trabalhado e avaliado.'
    avancado_ok, qtd_avancadas = _blueprint_avancado(blueprint_estado, base)
    percurso_efetivo = percurso or sugerir_percurso(cobertura)
    todos_at_c_aa = all((julgaveis.get(x) in {'C', 'AA'} for x in at if x in julgaveis)) and (not sem_evidencia)
    todos_estruturantes_at = all((x in at for x in estruturantes))
    if conceito == 'AD' and todos_at_c_aa and (aa / total >= 0.5) and avancado_ok and (percurso_efetivo in {'P3', 'P4'}) and todos_estruturantes_at and (not rp):
        conceito = 'A'
        motivo = 'Além de consolidar o esperado, há evidências consistentes de aprendizagem ampliada e oportunidades de análise/justificação/transferência.'
    elif aa / total >= 0.5 and conceito == 'AD' and (not avancado_ok):
        alertas.append('Há muitos registros AA, mas o mapa da avaliação ainda não comprova oportunidades avançadas suficientes para sustentar A.')
    return {'conceito': conceito, 'motivo': motivo, 'alertas': alertas, 'metricas': {'AT': len(at), 'ED': len(ed), 'RP': len(rp), 'NE': len(sem_evidencia), 'NC': nc, 'EP': ep, 'C': c, 'AA': aa, 'pct_consolidado': round(pct_cons * 100, 1), 'blueprint_avancado': qtd_avancadas}}

def construir_perfil_aluno(base: Mapping[str, Any], dados: Mapping[str, Any]) -> Tuple[List[str], List[str]]:
    status = dados.get('status', {}) or {}
    nomes = {d['codigo']: d['nome'] for d in base.get('dimensoes', [])}
    fortes = []
    prioridades = []
    for codigo, nome in nomes.items():
        s = status.get(codigo, '')
        if s in {'C', 'AA'}:
            fortes.append(f'{nome} ({s})')
        elif s in {'NC', 'EP'}:
            prioridades.append(f'{nome} ({s})')
    return (fortes, prioridades)

class _PDF(FPDF):

    def header(self):
        self.set_font('Arial', 'B', 9)
        self.set_text_color(30, 64, 175)
        self.cell(0, 6, _clean_pdf('SISTEMA INTEGRA | Avaliação e Aprendizagem'), 0, 1, 'L')
        self.set_draw_color(203, 213, 225)
        self.line(10, 17, 200, 17)
        self.ln(2)

    def footer(self):
        self.set_y(-12)
        self.set_font('Arial', 'I', 7)
        self.set_text_color(100, 116, 139)
        self.cell(0, 5, _clean_pdf(f'CEIEF Rafael Affonso Leite | Página {self.page_no()}'), 0, 0, 'C')

def _safe_multi_cell(pdf: FPDF, texto: Any, altura: float = 5, **kwargs):
    """Renderiza MultiCell sempre a partir da margem esquerda.

    No fpdf2, o cursor X pode permanecer na borda direita depois de uma
    ``multi_cell``. Uma chamada seguinte com largura 0 passa a ter largura
    útil igual a zero e gera ``FPDFException: Not enough horizontal space``.
    Esta função calcula explicitamente a largura útil da página e reposiciona
    o cursor antes e depois da escrita.
    """
    pdf.set_x(pdf.l_margin)
    largura = pdf.w - pdf.l_margin - pdf.r_margin
    pdf.multi_cell(largura, altura, _clean_pdf(texto), **kwargs)
    pdf.set_x(pdf.l_margin)

def _pdf_multiline(pdf: FPDF, titulo: str, texto: str, size: int=9):
    pdf.set_font('Arial', 'B', size)
    pdf.set_text_color(30, 41, 59)
    _safe_multi_cell(pdf, titulo, 5)
    pdf.set_font('Arial', '', size)
    pdf.set_text_color(51, 65, 85)
    _safe_multi_cell(pdf, texto or '-', 5)
    pdf.ln(1)

def gerar_pdf_perfil(aluno: str, turma: str, ano_letivo: int, trimestre: int, componentes: Sequence[str], registros: Mapping[str, Mapping[str, Any]], bases: Mapping[str, Mapping[str, Any]]) -> bytes:
    pdf = _PDF()
    pdf.set_auto_page_break(True, 15)
    pdf.add_page()
    pdf.set_font('Arial', 'B', 16)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 9, _clean_pdf('Perfil Integrado de Aprendizagem'), 0, 1)
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 6, _clean_pdf(f'{aluno} | {turma} | {trimestre}º trimestre/{ano_letivo}'), 0, 1)
    pdf.ln(3)
    for comp in componentes:
        dados = registros.get(comp, {}) or {}
        base = bases.get(comp, {}) or {}
        pdf.set_fill_color(239, 246, 255)
        pdf.set_text_color(30, 64, 175)
        pdf.set_font('Arial', 'B', 11)
        pdf.cell(0, 8, _clean_pdf(comp), 0, 1, fill=True)
        conceito = dados.get('conceito_final') or dados.get('conceito_sugerido') or '-'
        percurso = dados.get('percurso', '-')
        pdf.set_font('Arial', 'B', 9)
        pdf.set_text_color(30, 41, 59)
        pdf.cell(45, 6, _clean_pdf(f'Conceito: {conceito}'), 0, 0)
        pdf.cell(0, 6, _clean_pdf(f"Percurso: {percurso} - {PERCURSOS.get(percurso, '')}"), 0, 1)
        fortes, prioridades = construir_perfil_aluno(base, dados)
        _pdf_multiline(pdf, 'O que já demonstra:', '; '.join(fortes) or 'Ainda não há registros consolidados suficientes.')
        _pdf_multiline(pdf, 'O que precisa consolidar:', '; '.join(prioridades) or 'Sem prioridades registradas nas dimensões julgáveis.')
        _pdf_multiline(pdf, 'Próximo passo:', dados.get('proximo_passo', ''))
        if dados.get('justificativa'):
            _pdf_multiline(pdf, 'Justificativa da decisão profissional:', dados.get('justificativa', ''))
        pdf.ln(2)
    return bytes(pdf.output(dest='S'))

def gerar_pdf_turma(turma: str, ano_letivo: int, trimestre: int, componentes: Sequence[str], resumo: Mapping[str, Mapping[str, Any]]) -> bytes:
    pdf = _PDF()
    pdf.set_auto_page_break(True, 15)
    pdf.add_page()
    pdf.set_font('Arial', 'B', 16)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 9, _clean_pdf('Síntese Integrada da Turma'), 0, 1)
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 6, _clean_pdf(f'{turma} | {trimestre}º trimestre/{ano_letivo}'), 0, 1)
    pdf.ln(4)
    for comp in componentes:
        r = resumo.get(comp, {})
        pdf.set_font('Arial', 'B', 10)
        pdf.set_fill_color(241, 245, 249)
        pdf.cell(0, 7, _clean_pdf(comp), 0, 1, fill=True)
        pdf.set_font('Arial', '', 9)
        cont = r.get('conceitos', {})
        _safe_multi_cell(pdf, f"AB: {cont.get('AB', 0)} | B: {cont.get('B', 0)} | AD: {cont.get('AD', 0)} | A: {cont.get('A', 0)} | Sem fechamento: {cont.get('-', 0)}", 5)
        prioridades = r.get('prioridades', [])
        if prioridades:
            _safe_multi_cell(pdf, 'Prioridades coletivas: ' + '; '.join(prioridades[:5]), 5)
        pdf.ln(2)
    return bytes(pdf.output(dest='S'))

def _css():
    st.markdown('\n        <style>\n        .av-header{padding:18px 22px;border-radius:14px;background:linear-gradient(135deg,#eff6ff,#f8fafc);border:1px solid #dbeafe;margin-bottom:12px}\n        .av-title{font-size:1.55rem;font-weight:800;color:#0f172a;margin:0}.av-sub{color:#475569;margin-top:4px}\n        .av-card{border:1px solid #e2e8f0;border-radius:12px;padding:14px 16px;margin:7px 0;background:#fff}\n        .av-code{display:inline-block;padding:2px 7px;border-radius:6px;background:#dbeafe;color:#1d4ed8;font-weight:800;font-size:.78rem;margin-right:6px}\n        .av-estr{display:inline-block;padding:2px 7px;border-radius:6px;background:#fef3c7;color:#92400e;font-weight:700;font-size:.72rem}\n        .av-muted{color:#64748b;font-size:.88rem}.av-label{font-size:.78rem;color:#64748b;text-transform:uppercase;font-weight:700;letter-spacing:.04em}\n        </style>\n        ', unsafe_allow_html=True)

def _header(ctx: Contexto, usuario: str):
    st.markdown(f'\n        <div class="av-header">\n          <div class="av-title">📊 Avaliação e Aprendizagem</div>\n          <div class="av-sub">{ctx.ano_escolar}º ano · {ctx.trimestre}º trimestre · {ctx.turma} · {ctx.ano_letivo}</div>\n          <div class="av-muted">Currículo → pré-requisitos → recomposição → evidências → conceituação. Usuário: {usuario}</div>\n        </div>\n        ', unsafe_allow_html=True)

def _show_setup(sql_text: str, erro: str):
    st.error('A tabela de avaliação ainda não está disponível no Supabase.')
    st.caption('O restante do Integra permanece intacto. Execute o script SQL abaixo uma única vez no SQL Editor do Supabase e recarregue o aplicativo.')
    with st.expander('Ver SQL de instalação', expanded=True):
        st.code(sql_text, language='sql')
    st.download_button('⬇️ Baixar script SQL', sql_text.encode('utf-8'), '001_avaliacao.sql', 'text/plain')
    if erro:
        with st.expander('Detalhe técnico'):
            st.code(erro)

def _default_cobertura(base: Mapping[str, Any]) -> Dict[str, Any]:
    return {d['codigo']: {'situacao': 'AT', 'recomposicao': '', 'observacao': ''} for d in base.get('dimensoes', [])}

def _default_blueprint(base: Mapping[str, Any]) -> Dict[str, Any]:
    return {str(x['id']): {'incluida': False, 'instrumento': '', 'observacao': ''} for x in base.get('blueprint', [])}

def _curriculo_tab(repo: AvaliacaoRepo, ctx: Contexto, base: Mapping[str, Any]):
    st.subheader(f'🧭 Currículo, pré-requisitos e percurso · {ctx.componente}')
    c1, c2 = st.columns([1, 1])
    with c1:
        st.markdown('**Currículo de chegada**')
        st.write(base.get('curriculo_chegada', ''))
    with c2:
        st.markdown('**Núcleo estruturante**')
        st.write(base.get('nucleo_estruturante', ''))
    st.info(base.get('ancora', ''))
    salvo = repo.obter('cobertura', ctx)
    cobertura = salvo.get('dimensoes', {}) or _default_cobertura(base)
    percurso_salvo = salvo.get('percurso_turma', '')
    novos: Dict[str, Any] = {}
    pres = {p['codigo']: p for p in base.get('pre_requisitos', [])}
    for d in base.get('dimensoes', []):
        cod = d['codigo']
        atual = cobertura.get(cod, {}) or {}
        badge = '<span class="av-estr">ESTRUTURANTE</span>' if _norm(d.get('peso')) == 'ESTRUTURANTE' else ''
        st.markdown(f"""<div class="av-card"><span class="av-code">{cod}</span>{badge}<b>{d['nome']}</b><br><span class="av-muted">{d['demonstrar']}</span></div>""", unsafe_allow_html=True)
        c1, c2 = st.columns([1, 2])
        with c1:
            situacao = st.selectbox(f'Situação curricular · {cod}', SITUACAO_OPCOES, index=SITUACAO_OPCOES.index(atual.get('situacao', 'AT')) if atual.get('situacao', 'AT') in SITUACAO_OPCOES else 0, format_func=lambda x: f'{x} — {SITUACAO_CURRICULAR[x]}', key=f'av_cov_{ctx.turma}_{ctx.componente}_{cod}')
        p = pres.get(cod, {})
        with c2:
            recomposicao = st.text_input(f'Recomposição selecionada · {cod}', value=atual.get('recomposicao', ''), placeholder=f'Ex.: retomar pré-requisito do {max(1, ctx.ano_escolar - 1)}º ano ou da Educação Infantil', key=f'av_rec_{ctx.turma}_{ctx.componente}_{cod}')
        with st.expander(f'🔎 Pré-requisitos já mapeados para {cod}'):
            pre_direto = p.get('pre_ano_anterior') or p.get('pre_4ano') or '-'
            if ctx.ano_escolar == 1:
                rotulo_pre = 'Educação Infantil / experiências anteriores'
            else:
                rotulo_pre = f'{ctx.ano_escolar - 1}º ano — pré-requisito direto'
            st.markdown(f"**{rotulo_pre}:** {pre_direto}")
            st.markdown(f"**Se a lacuna for mais antiga:** {p.get('pre_antigo', '-')}")
            st.markdown(f"**Diagnóstico rápido sugerido:** {p.get('diagnostico', '-')}")
            st.markdown(f"**Recomposição e ponte para o {ctx.ano_escolar}º ano:** {p.get('recomposicao', '-')}")
        obs = st.text_area(f'Observação pedagógica · {cod}', value=atual.get('observacao', ''), height=60, key=f'av_covobs_{ctx.turma}_{ctx.componente}_{cod}')
        novos[cod] = {'situacao': situacao, 'recomposicao': recomposicao, 'observacao': obs}
    percurso_sugerido = sugerir_percurso(novos)
    st.divider()
    c1, c2 = st.columns([1, 2])
    with c1:
        percurso = st.selectbox('Percurso curricular predominante da turma', PERCURSO_OPCOES, index=PERCURSO_OPCOES.index(percurso_salvo) if percurso_salvo in PERCURSO_OPCOES else PERCURSO_OPCOES.index(percurso_sugerido), format_func=lambda x: '— selecione —' if not x else f'{x} — {PERCURSOS[x]}', key=f'av_percurso_turma_{ctx.turma}_{ctx.componente}')
    with c2:
        st.caption(f"Sugestão a partir da cobertura registrada: **{percurso_sugerido} — {PERCURSOS.get(percurso_sugerido, '')}**")
        st.caption('RP descreve a situação curricular. NE descreve a situação de evidência de um estudante. Um conteúdo RP não vira NC.')
    if st.button('💾 Salvar currículo e percurso', type='primary', key=f'save_cov_{ctx.turma}_{ctx.componente}'):
        repo.salvar('cobertura', ctx, {'dimensoes': novos, 'percurso_turma': percurso or percurso_sugerido})
        st.success('Cobertura curricular e recomposição salvas.')
        st.rerun()

def _blueprint_tab(repo: AvaliacaoRepo, ctx: Contexto, base: Mapping[str, Any]):
    st.subheader(f'📝 Mapa da avaliação · {ctx.componente}')
    st.caption('Marque o que realmente estará presente na avaliação de fechamento ou em outro instrumento válido do trimestre. A intenção é verificar cobertura e profundidade cognitiva, não padronizar uma prova única.')
    salvo = repo.obter('blueprint', ctx)
    estado = salvo.get('itens', {}) or _default_blueprint(base)
    rows = []
    for item in base.get('blueprint', []):
        sid = str(item['id'])
        e = estado.get(sid, {}) or {}
        rows.append({'Sit.': sid, 'Dimensão': item['dimensao'], 'Situação/evidência mínima recomendada': item['situacao'], 'Bloom': item['bloom'], 'O que deve revelar': item['evidencia'], 'Incluída': bool(e.get('incluida', False)), 'Instrumento/questão': e.get('instrumento', '')})
    df = pd.DataFrame(rows)
    edited = st.data_editor(df, hide_index=True, use_container_width=True, disabled=['Sit.', 'Dimensão', 'Situação/evidência mínima recomendada', 'Bloom', 'O que deve revelar'], column_config={'Incluída': st.column_config.CheckboxColumn('Incluída?'), 'Instrumento/questão': st.column_config.TextColumn('Onde aparece?', width='medium'), 'Situação/evidência mínima recomendada': st.column_config.TextColumn(width='large'), 'O que deve revelar': st.column_config.TextColumn(width='large')}, key=f'av_blue_editor_{ctx.turma}_{ctx.componente}')
    incluido = edited[edited['Incluída'] == True] if not edited.empty else edited
    c1, c2, c3 = st.columns(3)
    c1.metric('Situações previstas', len(df))
    c2.metric('Cobertas', len(incluido))
    advanced = 0
    for _, r in incluido.iterrows():
        b = _norm(r.get('Bloom', ''))
        if any((x in b for x in ['ANALIS', 'JUSTIFIC', 'AVALI', 'CRIAR', 'TRANSFER'])):
            advanced += 1
    c3.metric('Evidências de maior complexidade', advanced)
    if len(incluido) < len(df):
        st.warning('O mapa ainda não cobre todas as situações mínimas recomendadas. Isso não obriga uma prova única, mas as dimensões desenvolvidas precisam produzir evidência válida em algum instrumento.')
    if advanced < 2:
        st.info('Para sustentar A — Avançado, o sistema exigirá oportunidades reais de análise, justificação, avaliação, criação ou transferência. Inclua pelo menos duas evidências de maior complexidade quando pertinente.')
    if st.button('💾 Salvar mapa da avaliação', type='primary', key=f'save_blue_{ctx.turma}_{ctx.componente}'):
        itens = {}
        for _, r in edited.iterrows():
            itens[str(r['Sit.'])] = {'incluida': bool(r['Incluída']), 'instrumento': str(r.get('Instrumento/questão', '') or '')}
        repo.salvar('blueprint', ctx, {'itens': itens})
        st.success('Mapa da avaliação salvo.')
        st.rerun()

def _tabulacao_tab(repo: AvaliacaoRepo, ctx: Contexto, base: Mapping[str, Any], alunos: List[str]):
    st.subheader(f'👥 Tabulação das aprendizagens · {ctx.componente}')
    if not alunos:
        st.warning('Nenhum estudante foi localizado na tabela Carometro para esta turma. Cadastre/atualize o Carômetro Escolar e retorne a este módulo.')
        return
    cobertura_reg = repo.obter('cobertura', ctx)
    cobertura = cobertura_reg.get('dimensoes', {}) or _default_cobertura(base)
    blueprint = repo.obter('blueprint', ctx).get('itens', {}) or _default_blueprint(base)
    existentes = repo.listar_alunos(ctx)
    codigos = [d['codigo'] for d in base.get('dimensoes', [])]
    rows = []
    for nome in alunos:
        dado = existentes.get(nome, {}) or {}
        row = {'Estudante': nome}
        for cod in codigos:
            row[cod] = (dado.get('status', {}) or {}).get(cod, '')
        perc = dado.get('percurso', '') or sugerir_percurso(cobertura)
        sug = calcular_conceito_sugerido(row, base, cobertura, perc, blueprint)
        row['Sugestão'] = sug.get('conceito', '')
        rows.append(row)
    df = pd.DataFrame(rows)
    cfg = {cod: st.column_config.SelectboxColumn(cod, options=STATUS_OPCOES, width='small') for cod in codigos}
    cfg['Estudante'] = st.column_config.TextColumn(width='large')
    cfg['Sugestão'] = st.column_config.TextColumn(width='small')
    edited = st.data_editor(df, hide_index=True, use_container_width=True, disabled=['Estudante', 'Sugestão'], column_config=cfg, key=f'av_tab_{ctx.turma}_{ctx.componente}')
    st.caption('NE = ainda não há evidência válida; NC = foi ensinado/retomado e ainda não consolidou. Não use NC para conteúdo não suficientemente desenvolvido.')
    if st.button('💾 Salvar tabulação e recalcular sugestões', type='primary', key=f'save_tab_{ctx.turma}_{ctx.componente}'):
        registros = []
        for _, row in edited.iterrows():
            nome = str(row['Estudante'])
            antigo = existentes.get(nome, {}) or {}
            statuses = {cod: '' if pd.isna(row.get(cod, '')) else str(row.get(cod, '') or '') for cod in codigos}
            perc = antigo.get('percurso', '') or sugerir_percurso(cobertura)
            sug = calcular_conceito_sugerido(statuses, base, cobertura, perc, blueprint)
            novo = dict(antigo)
            novo.update({'status': statuses, 'conceito_sugerido': sug.get('conceito', ''), 'motor': sug, 'percurso': perc})
            registros.append(('aluno', ctx, novo, nome))
        repo.salvar_varios(registros)
        st.success('Tabulação salva e sugestões recalculadas.')
        st.rerun()

def _conceituacao_tab(repo: AvaliacaoRepo, ctx: Contexto, base: Mapping[str, Any], alunos: List[str]):
    st.subheader(f'🧠 Conceituação assistida · {ctx.componente}')
    st.caption('O Integra sugere uma leitura fundamentada. O conceito final continua sendo uma decisão profissional do professor; divergências são possíveis e devem ser justificadas.')
    if not alunos:
        st.warning('Sem estudantes para conceituar.')
        return
    cobertura = repo.obter('cobertura', ctx).get('dimensoes', {}) or _default_cobertura(base)
    blueprint = repo.obter('blueprint', ctx).get('itens', {}) or _default_blueprint(base)
    existentes = repo.listar_alunos(ctx)
    rows = []
    motores = {}
    for nome in alunos:
        d = existentes.get(nome, {}) or {}
        perc = d.get('percurso', '') or sugerir_percurso(cobertura)
        motor = calcular_conceito_sugerido(d.get('status', {}) or {}, base, cobertura, perc, blueprint)
        motores[nome] = motor
        rows.append({'Estudante': nome, 'Sugestão': motor.get('conceito', ''), 'Percurso': perc, 'Conceito final': d.get('conceito_final', '') or motor.get('conceito', ''), 'Próximo passo': d.get('proximo_passo', ''), 'Justificativa (se divergir)': d.get('justificativa', '')})
    df = pd.DataFrame(rows)
    edited = st.data_editor(df, hide_index=True, use_container_width=True, disabled=['Estudante', 'Sugestão'], column_config={'Estudante': st.column_config.TextColumn(width='large'), 'Sugestão': st.column_config.TextColumn(width='small'), 'Percurso': st.column_config.SelectboxColumn(options=PERCURSO_OPCOES), 'Conceito final': st.column_config.SelectboxColumn(options=[''] + CONCEITOS, width='small'), 'Próximo passo': st.column_config.TextColumn(width='large'), 'Justificativa (se divergir)': st.column_config.TextColumn(width='large')}, key=f'av_conc_{ctx.turma}_{ctx.componente}')
    diffs = []
    for _, r in edited.iterrows():
        if r['Conceito final'] and r['Sugestão'] and (r['Conceito final'] != r['Sugestão']) and (not str(r['Justificativa (se divergir)']).strip()):
            diffs.append(str(r['Estudante']))
    if diffs:
        st.warning('Para alterar a sugestão do sistema, registre justificativa pedagógica: ' + ', '.join(diffs[:8]) + ('...' if len(diffs) > 8 else ''))
    with st.expander('Como o sistema chegou às sugestões'):
        nome_det = st.selectbox('Estudante', alunos, key=f'av_motivo_{ctx.turma}_{ctx.componente}')
        mot = motores.get(nome_det, {})
        st.markdown(f"**Sugestão:** {mot.get('conceito', '—') or '—'}")
        st.write(mot.get('motivo', 'Ainda não há evidência suficiente.'))
        for alerta in mot.get('alertas', []):
            st.warning(alerta)
        if mot.get('metricas'):
            st.json(mot['metricas'], expanded=False)
    if st.button('✅ Confirmar conceitos e percursos', type='primary', disabled=bool(diffs), key=f'save_conc_{ctx.turma}_{ctx.componente}'):
        registros = []
        for _, r in edited.iterrows():
            nome = str(r['Estudante'])
            d = existentes.get(nome, {}) or {}
            perc = '' if pd.isna(r['Percurso']) else str(r['Percurso'] or '')
            motor = calcular_conceito_sugerido(d.get('status', {}) or {}, base, cobertura, perc, blueprint)
            d.update({'conceito_sugerido': motor.get('conceito', ''), 'conceito_final': '' if pd.isna(r['Conceito final']) else str(r['Conceito final'] or ''), 'percurso': perc, 'proximo_passo': '' if pd.isna(r['Próximo passo']) else str(r['Próximo passo'] or ''), 'justificativa': '' if pd.isna(r['Justificativa (se divergir)']) else str(r['Justificativa (se divergir)'] or ''), 'motor': motor})
            registros.append(('aluno', ctx, d, nome))
        repo.salvar_varios(registros)
        st.success('Conceitos finais registrados.')
        st.rerun()

def _resumo_componente(repo: AvaliacaoRepo, ctx: Contexto, base: Mapping[str, Any], alunos: List[str]) -> Dict[str, Any]:
    registros = repo.listar_alunos(ctx)
    conceitos = {'AB': 0, 'B': 0, 'AD': 0, 'A': 0, '-': 0}
    prioridade_contagem: Dict[str, int] = {}
    for nome in alunos:
        d = registros.get(nome, {}) or {}
        conc = d.get('conceito_final') or d.get('conceito_sugerido') or '-'
        conceitos[conc if conc in conceitos else '-'] += 1
        stt = d.get('status', {}) or {}
        for dim in base.get('dimensoes', []):
            if stt.get(dim['codigo']) in {'NC', 'EP'}:
                prioridade_contagem[dim['nome']] = prioridade_contagem.get(dim['nome'], 0) + 1
    prioridades = [x[0] for x in sorted(prioridade_contagem.items(), key=lambda kv: (-kv[1], kv[0]))]
    return {'conceitos': conceitos, 'prioridades': prioridades, 'registros': registros}

def _painel_tab(repo: AvaliacaoRepo, ctx_base: Contexto, componentes: List[str], alunos: List[str]):
    st.subheader('📊 Painel da turma')
    if not alunos:
        st.warning('Sem estudantes vinculados à turma no Carômetro.')
        return
    cols = st.columns(len(componentes)) if componentes else []
    resumos = {}
    for i, comp in enumerate(componentes):
        ctx = Contexto(ctx_base.ano_letivo, ctx_base.ano_escolar, ctx_base.trimestre, ctx_base.turma, comp)
        base = _base_curricular(ctx.ano_escolar, ctx.trimestre, comp)
        r = _resumo_componente(repo, ctx, base, alunos)
        resumos[comp] = r
        cont = r['conceitos']
        with cols[i]:
            st.markdown(f'**{comp}**')
            st.metric('Fechados', len(alunos) - cont.get('-', 0), delta=f"{cont.get('AB', 0)} AB · {cont.get('B', 0)} B")
            st.caption(f"AD {cont.get('AD', 0)} · A {cont.get('A', 0)}")
    st.divider()
    linhas = []
    for comp, r in resumos.items():
        c = r['conceitos']
        linhas.append({'Componente': comp, 'AB': c['AB'], 'B': c['B'], 'AD': c['AD'], 'A': c['A'], 'Sem fechamento': c['-'], 'Prioridades coletivas': '; '.join(r['prioridades'][:3])})
    st.dataframe(pd.DataFrame(linhas), hide_index=True, use_container_width=True)
    pdf = gerar_pdf_turma(ctx_base.turma, ctx_base.ano_letivo, ctx_base.trimestre, componentes, resumos)
    st.download_button('📄 Baixar síntese da turma em PDF', pdf, f'Sintese_Avaliacao_{_slug(ctx_base.turma)}_{ctx_base.trimestre}Tri.pdf', 'application/pdf')

def _perfil_tab(repo: AvaliacaoRepo, ctx_base: Contexto, componentes: List[str], alunos: List[str]):
    st.subheader('🔎 Perfil integrado do estudante')
    if not alunos:
        st.warning('Sem estudantes para exibir.')
        return
    aluno = st.selectbox('Estudante', alunos, key=f'av_perfil_{ctx_base.turma}')
    registros: Dict[str, Dict[str, Any]] = {}
    bases = {}
    linhas = []
    for comp in componentes:
        ctx = Contexto(ctx_base.ano_letivo, ctx_base.ano_escolar, ctx_base.trimestre, ctx_base.turma, comp)
        base = _base_curricular(ctx.ano_escolar, ctx.trimestre, comp)
        bases[comp] = base
        d = repo.obter('aluno', ctx, aluno)
        registros[comp] = d
        fortes, prioridades = construir_perfil_aluno(base, d)
        linhas.append({'Componente': comp, 'Conceito': d.get('conceito_final') or d.get('conceito_sugerido') or '—', 'Percurso': d.get('percurso', '—'), 'O que já sabe': '; '.join(fortes[:4]), 'O que precisa consolidar': '; '.join(prioridades[:4]), 'Próximo passo': d.get('proximo_passo', '')})
    st.dataframe(pd.DataFrame(linhas), hide_index=True, use_container_width=True)
    pdf = gerar_pdf_perfil(aluno, ctx_base.turma, ctx_base.ano_letivo, ctx_base.trimestre, componentes, registros, bases)
    st.download_button('📄 Baixar perfil individual em PDF', pdf, f'Perfil_Aprendizagem_{_slug(aluno)}_{ctx_base.trimestre}Tri.pdf', 'application/pdf')

def _conselho_tab(repo: AvaliacaoRepo, ctx_base: Contexto, componentes: List[str], alunos: List[str]):
    st.subheader('🏛️ Conselho de Ciclo')
    st.caption('Consolida os cinco componentes e pode enviar a síntese para a estrutura já usada pela tela Nova Ata de Conselho do Integra.')
    if not alunos:
        st.warning('Sem estudantes para consolidar.')
        return
    por_aluno = []
    comp_col = {'Língua Portuguesa': 'LP', 'Matemática': 'M', 'História': 'H', 'Geografia': 'G', 'Ciências': 'C'}
    registros_comp: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for comp in componentes:
        ctx = Contexto(ctx_base.ano_letivo, ctx_base.ano_escolar, ctx_base.trimestre, ctx_base.turma, comp)
        registros_comp[comp] = repo.listar_alunos(ctx)
    for nome in alunos:
        row = {'Estudante': nome}
        percursos = []
        for comp in componentes:
            d = registros_comp.get(comp, {}).get(nome, {}) or {}
            row[comp_col.get(comp, comp)] = d.get('conceito_final') or d.get('conceito_sugerido') or ''
            if d.get('percurso'):
                percursos.append(d['percurso'])
        row['Percurso'] = max(set(percursos), key=percursos.count) if percursos else ''
        por_aluno.append(row)
    df = pd.DataFrame(por_aluno)
    st.dataframe(df, hide_index=True, use_container_width=True)
    abaixo = df[df[[c for c in ['LP', 'M', 'H', 'G', 'C'] if c in df.columns]].eq('AB').any(axis=1)] if not df.empty else df
    basico = df[df[[c for c in ['LP', 'M', 'H', 'G', 'C'] if c in df.columns]].eq('B').any(axis=1)] if not df.empty else df
    c1, c2 = st.columns(2)
    c1.metric('Estudantes com ao menos um AB', len(abaixo))
    c2.metric('Estudantes com ao menos um B', len(basico))
    if st.button('➡️ Enviar síntese para Nova Ata de Conselho', type='primary', key=f'av_to_ata_{ctx_base.turma}'):
        rows_ab = []
        for _, r in abaixo.iterrows():
            rows_ab.append({'Estudante': r.get('Estudante', ''), 'LP': r.get('LP', ''), 'M': r.get('M', ''), 'H': r.get('H', ''), 'G': r.get('G', ''), 'C': r.get('C', ''), 'A': '', 'EF': '', 'LT': '', 'LIBRAS': ''})
        rows_b = []
        for _, r in basico.iterrows():
            if r.get('LP') == 'B' or r.get('M') == 'B':
                acoes = []
                if r.get('LP') == 'B':
                    acoes.append('LP')
                if r.get('M') == 'B':
                    acoes.append('Matemática')
                rows_b.append({'Estudante': r.get('Estudante', ''), 'Ações (LP e Mat)': 'Intervenção/recomposição em ' + ' e '.join(acoes)})
        atual = st.session_state.get('data_ata_ef', {}) or {}
        atual['abaixo_basico'] = rows_ab or [{'Estudante': '', 'LP': '', 'M': '', 'H': '', 'G': '', 'C': '', 'A': '', 'EF': '', 'LT': '', 'LIBRAS': ''}]
        atual['basico'] = rows_b or [{'Estudante': '', 'Ações (LP e Mat)': ''}]
        atual['turma'] = ctx_base.turma
        atual['trimestre'] = f'{ctx_base.trimestre}º Trimestre'
        st.session_state.data_ata_ef = atual
        st.session_state.ata_turma_confirmada = ctx_base.turma
        st.success("Síntese preparada na sessão. Abra '📝 Nova Ata de Conselho' para revisar e completar a ata antes de salvar.")

def _render_componente(repo: AvaliacaoRepo, ctx: Contexto, alunos: List[str]):
    base = _base_curricular(ctx.ano_escolar, ctx.trimestre, ctx.componente)
    if not base:
        st.warning('Base curricular ainda não cadastrada para esta combinação.')
        return
    tabs = st.tabs(['🧭 Currículo & percurso', '📝 Mapa da avaliação', '👥 Tabulação', '🧠 Conceituação'])
    with tabs[0]:
        _curriculo_tab(repo, ctx, base)
    with tabs[1]:
        _blueprint_tab(repo, ctx, base)
    with tabs[2]:
        _tabulacao_tab(repo, ctx, base, alunos)
    with tabs[3]:
        _conceituacao_tab(repo, ctx, base, alunos)

def _validar_base_externa() -> Tuple[bool, str]:
    """Valida a estrutura mínima da base externa antes de renderizar a interface."""
    esperados = ['Língua Portuguesa', 'Matemática', 'Ciências', 'História', 'Geografia']
    faltas: List[str] = []
    for ano in range(1, 6):
        for trimestre in (1, 2, 3):
            bloco = AVALIACAO_DB.get(ano, {}).get(trimestre, {})
            for componente in esperados:
                base = bloco.get(componente)
                if not isinstance(base, Mapping):
                    faltas.append(f'{ano}º ano / {trimestre}º trimestre / {componente}')
                    continue
                if not base.get('dimensoes'):
                    faltas.append(f'{ano}º ano / {trimestre}º trimestre / {componente} (sem dimensões)')
    if faltas:
        return False, '; '.join(faltas[:12]) + ('...' if len(faltas) > 12 else '')
    return True, ''


def renderizar_avaliacao(supabase: Any, sql_instalacao: Optional[str]=None) -> None:
    """Renderiza o módulo sem depender de variáveis locais do ``app_pei.py``.

    O único objeto recebido do aplicativo principal é a conexão ``supabase`` já
    inicializada. Usuário, permissões e matriz docente são resolvidos pelo próprio módulo.
    """
    _css()
    base_ok, base_erro = _validar_base_externa()
    if not base_ok:
        st.error('A base pedagógica externa está incompleta ou incompatível com este módulo.')
        st.code(base_erro)
        st.caption('Confirme que dados_avaliacao_completo.py está na mesma pasta do app_pei.py e do modulo_avaliacao.py.')
        return
    usuario_nome = st.session_state.get('usuario_nome', 'Usuário')
    usuario_matricula = st.session_state.get('usuario_matricula', '')
    matriz_professores = _carregar_matriz_professores(supabase)
    gestor = _eh_gestor(usuario_matricula, usuario_nome, supabase)
    if sql_instalacao is None:
        sql_instalacao = SQL_INSTALACAO
    anos = _anos_disponiveis()
    c_top1, c_top2, c_top3 = st.columns([1, 1, 1.3])
    with c_top1:
        ano_letivo = int(st.number_input('Ano letivo', min_value=2025, max_value=2035, value=date.today().year, step=1, key='av_ano_letivo'))
    with c_top2:
        ano_escolar = st.selectbox('Ano de escolaridade', anos, format_func=lambda x: f'{x}º ano', key='av_ano_escolar')
    trimestres = _trimestres_disponiveis(ano_escolar)
    with c_top3:
        trimestre = st.selectbox('Trimestre', trimestres, format_func=lambda x: f'{x}º trimestre', key='av_trimestre')
    turmas = _turmas_permitidas(matriz_professores, usuario_nome, gestor, supabase, ano_escolar)
    if not turmas:
        st.warning(f'Não encontrei turmas do {ano_escolar}º ano vinculadas ao seu usuário na matriz de professores nem no Carômetro.')
        return
    turma = st.selectbox('Turma', turmas, key='av_turma')
    alunos = _alunos_da_turma(supabase, turma)
    disponiveis = _componentes_disponiveis(ano_escolar, trimestre)
    componentes = _componentes_permitidos(matriz_professores, usuario_nome, gestor, turma, disponiveis)
    ctx_base = Contexto(ano_letivo, ano_escolar, trimestre, turma, '')
    _header(ctx_base, usuario_nome)
    versao_base = str((METADADOS_AVALIACAO or {}).get('versao', 'base completa'))
    st.caption(f'Base pedagógica carregada: {versao_base} · 1º ao 5º ano · três trimestres.')
    if not alunos:
        st.info('A turma foi localizada, mas o Carômetro ainda não tem estudantes vinculados exatamente a essa turma. O currículo pode ser consultado, porém a tabulação ficará indisponível até o cadastro dos alunos.')
    repo = AvaliacaoRepo(supabase, usuario_nome)
    ok, erro = repo.disponivel()
    if not ok:
        _show_setup(sql_instalacao, erro)
        return
    menu = st.radio('Área do módulo', ['📊 Painel', '📚 Componente curricular', '🔎 Perfil do estudante', '🏛️ Conselho de Ciclo'], horizontal=True, key='av_area')
    if menu == '📊 Painel':
        _painel_tab(repo, ctx_base, componentes, alunos)
    elif menu == '📚 Componente curricular':
        comp = st.selectbox('Componente', componentes, key='av_comp')
        ctx = Contexto(ano_letivo, ano_escolar, trimestre, turma, comp)
        _render_componente(repo, ctx, alunos)
    elif menu == '🔎 Perfil do estudante':
        _perfil_tab(repo, ctx_base, componentes, alunos)
    elif menu == '🏛️ Conselho de Ciclo':
        _conselho_tab(repo, ctx_base, componentes, alunos)
SQL_INSTALACAO = '\ncreate extension if not exists pgcrypto;\n\ncreate table if not exists public."Avaliacao" (\n    id uuid primary key default gen_random_uuid(),\n    chave text not null unique,\n    tipo text not null,\n    ano_letivo integer not null,\n    ano_escolar integer not null,\n    trimestre integer not null check (trimestre between 1 and 3),\n    turma text not null,\n    componente text not null default \'\',\n    aluno_nome text,\n    dados_json jsonb not null default \'{}\'::jsonb,\n    atualizado_por text,\n    atualizado_em timestamptz not null default now()\n);\n\ncreate index if not exists avaliacao_contexto_idx\non public."Avaliacao" (ano_letivo, ano_escolar, trimestre, turma, componente, tipo);\n\ncreate index if not exists avaliacao_aluno_idx\non public."Avaliacao" (turma, aluno_nome);\n\n-- O Integra atual usa a chave configurada no servidor. Se o projeto adotar RLS,\n-- substitua estas políticas pela política de autenticação oficial da aplicação.\nalter table public."Avaliacao" disable row level security;\n'.strip()
__all__ = ['renderizar_avaliacao', 'calcular_conceito_sugerido', 'construir_perfil_aluno', 'gerar_pdf_perfil', 'gerar_pdf_turma']
