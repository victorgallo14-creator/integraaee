"""Módulo Avaliação e Aprendizagem para o Sistema Integra.

Integração mínima esperada no app principal::

    elif app_mode_regular == "📊 Avaliação e Aprendizagem":
        from avaliacao import renderizar_avaliacao
        renderizar_avaliacao(supabase)

O módulo é autocontido: lê usuário da sessão do Streamlit, busca a matriz de professores
na tabela ``Config_Ata`` (chave ``matriz_professores``), usa ``Carometro`` como lista de
estudantes e persiste na tabela ``Avaliacao``. O app principal não precisa conhecer a
estrutura interna da avaliação.

O desenho pedagógico é currículo -> pré-requisitos -> diagnóstico/recomposição ->
cobertura da avaliação -> evidências por estudante -> sugestão de conceito -> decisão
profissional do docente.
"""

from __future__ import annotations

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

# Base pedagógica incorporada ao próprio módulo para implantação em arquivo único.
AVALIACAO_DB = {5: {1: {'Língua Portuguesa': {'slug': 'LP',
                               'curriculo_chegada': 'Leitura fluente e compreensiva; estratégias de leitura; '
                                                    'oralidade/argumentação; análise discursiva e textual; '
                                                    'conhecimentos linguísticos; produção escrita; leitura literária.',
                               'nucleo_estruturante': 'Fluência/compreensão, inferência, produção textual e domínio do '
                                                      'sistema linguístico esperado.',
                               'pre_requisitos_principais': '4º: leitura autônoma e inferencial, comparação de textos, '
                                                            'fato/opinião, produção/revisão. 3º: fluência, informações '
                                                            'explícitas, sequência, estrutura básica e coesão.',
                               'ancora': 'ÂNCORA PARA A SÍNTESE LP1, LP2 e LP6 são dimensões estruturantes para a '
                                         'síntese do componente.',
                               'dimensoes': [{'codigo': 'LP1',
                                              'nome': 'Leitura fluente e autônoma',
                                              'demonstrar': 'Lê silenciosamente e em voz alta com fluência, precisão, '
                                                            'entonação e compreensão. A meta anual indica 140 '
                                                            'palavras/minuto como referência, sempre articulada à '
                                                            'compreensão.',
                                              'focos': 'Fluência; autonomia; compreensão global; leitura expressiva.',
                                              'peso': 'ESTRUTURANTE'},
                                             {'codigo': 'LP2',
                                              'nome': 'Compreensão e estratégias de leitura',
                                              'demonstrar': 'Localiza informações explícitas e nucleares, infere '
                                                            'informações implícitas, identifica tema/finalidade, '
                                                            'compara textos e distingue fatos/opiniões, mobilizando '
                                                            'elementos verbais e não verbais.',
                                              'focos': 'Inferência; comparação; finalidade; tema; fato/opinião; '
                                                       'informações relevantes; material gráfico.',
                                              'peso': 'ESTRUTURANTE'},
                                             {'codigo': 'LP3',
                                              'nome': 'Oralidade, escuta e argumentação',
                                              'demonstrar': 'Produz e compreende gêneros orais do período, respeita '
                                                            'turnos, adequa vocabulário e sustenta pontos de vista com '
                                                            'informações estudadas.',
                                              'focos': 'Regra de jogo, poema e outras situações orais previstas; '
                                                       'interação discursiva; argumentação.',
                                              'peso': 'REGULAR'},
                                             {'codigo': 'LP4',
                                              'nome': 'Discursividade e textualidade',
                                              'demonstrar': 'Reconhece contexto de produção, finalidade, estrutura dos '
                                                            'gêneros e utiliza coesão, coerência, paragrafação e '
                                                            'pontuação para construir sentidos.',
                                              'focos': 'Contexto de produção; estrutura composicional; coesão; '
                                                       'coerência; parágrafo; pontuação.',
                                              'peso': 'REGULAR'},
                                             {'codigo': 'LP5',
                                              'nome': 'Análise linguística e ortografia',
                                              'demonstrar': 'Analisa e emprega conhecimentos gramaticais e '
                                                            'ortográficos previstos no período, sem dissociá-los do '
                                                            'uso real da língua.',
                                              'focos': 'Concordância; acentuação/paroxítonas; substantivos/adjetivos; '
                                                       'ortografia e consulta ao dicionário, conforme o período.',
                                              'peso': 'REGULAR'},
                                             {'codigo': 'LP6',
                                              'nome': 'Produção escrita e revisão',
                                              'demonstrar': 'Planeja, produz, revisa e reescreve textos considerando '
                                                            'interlocutor, finalidade, gênero, organização, coesão, '
                                                            'coerência e convenções da escrita.',
                                              'focos': 'Texto instrucional e gêneros do período; verbete/relato de '
                                                       'experimento quando trabalhados; revisão e reescrita.',
                                              'peso': 'ESTRUTURANTE'},
                                             {'codigo': 'LP7',
