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
