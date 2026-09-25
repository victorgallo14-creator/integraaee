# -*- coding: utf-8 -*-

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
AVALIACAO_DB = {5: {1: {'Língua Portuguesa': {'slug': 'LP', 'curriculo_chegada': 'Leitura fluente e compreensiva; estratégias de leitura; oralidade/argumentação; análise discursiva e textual; conhecimentos linguísticos; produção escrita; leitura literária.', 'nucleo_estruturante': 'Fluência/compreensão, inferência, produção textual e domínio do sistema linguístico esperado.', 'pre_requisitos_principais': '4º: leitura autônoma e inferencial, comparação de textos, fato/opinião, produção/revisão. 3º: fluência, informações explícitas, sequência, estrutura básica e coesão.', 'ancora': 'ÂNCORA PARA A SÍNTESE LP1, LP2 e LP6 são dimensões estruturantes para a síntese do componente.', 'dimensoes': [{'codigo': 'LP1', 'nome': 'Leitura fluente e autônoma', 'demonstrar': 'Lê silenciosamente e em voz alta com fluência, precisão, entonação e compreensão. A meta anual indica 140 palavras/minuto como referência, sempre articulada à compreensão.', 'focos': 'Fluência; autonomia; compreensão global; leitura expressiva.', 'peso': 'ESTRUTURANTE'}, {'codigo': 'LP2', 'nome': 'Compreensão e estratégias de leitura', 'demonstrar': 'Localiza informações explícitas e nucleares, infere informações implícitas, identifica tema/finalidade, compara textos e distingue fatos/opiniões, mobilizando elementos verbais e não verbais.', 'focos': 'Inferência; comparação; finalidade; tema; fato/opinião; informações relevantes; material gráfico.', 'peso': 'ESTRUTURANTE'}, {'codigo': 'LP3', 'nome': 'Oralidade, escuta e argumentação', 'demonstrar': 'Produz e compreende gêneros orais do período, respeita turnos, adequa vocabulário e sustenta pontos de vista com informações estudadas.', 'focos': 'Regra de jogo, poema e outras situações orais previstas; interação discursiva; argumentação.', 'peso': 'REGULAR'}, {'codigo': 'LP4', 'nome': 'Discursividade e textualidade', 'demonstrar': 'Reconhece contexto de produção, finalidade, estrutura dos gêneros e utiliza coesão, coerência, paragrafação e pontuação para construir sentidos.', 'focos': 'Contexto de produção; estrutura composicional; coesão; coerência; parágrafo; pontuação.', 'peso': 'REGULAR'}, {'codigo': 'LP5', 'nome': 'Análise linguística e ortografia', 'demonstrar': 'Analisa e emprega conhecimentos gramaticais e ortográficos previstos no período, sem dissociá-los do uso real da língua.', 'focos': 'Concordância; acentuação/paroxítonas; substantivos/adjetivos; ortografia e consulta ao dicionário, conforme o período.', 'peso': 'REGULAR'}, {'codigo': 'LP6', 'nome': 'Produção escrita e revisão', 'demonstrar': 'Planeja, produz, revisa e reescreve textos considerando interlocutor, finalidade, gênero, organização, coesão, coerência e convenções da escrita.', 'focos': 'Texto instrucional e gêneros do período; verbete/relato de experimento quando trabalhados; revisão e reescrita.', 'peso': 'ESTRUTURANTE'}, {'codigo': 'LP7', 'nome': 'Leitura literária e efeitos de sentido', 'demonstrar': 'Aprecia textos literários e interpreta linguagem figurada, humor/ironia, relações entre texto e leitor e elementos narrativos.', 'focos': 'Conto, mito, poema, HQ e outros gêneros literários previstos no trimestre.', 'peso': 'REGULAR'}], 'pre_requisitos': [{'codigo': 'LP1', 'pre_4ano': '4º ano: leitura fluente e autônoma com compreensão (meta anual: 125 palavras/minuto).', 'pre_antigo': '3º ano: leitura fluente e autônoma (meta anual: 110 palavras/minuto); reconhecimento de palavras e estruturas silábicas não canônicas.', 'diagnostico': 'Amostra curta de leitura oral + perguntas de compreensão; observar precisão, ritmo e manutenção de sentido.', 'recomposicao': 'Recompor decodificação/fluência sem abandonar textos do 5º ano: leitura assistida, repetida e compartilhada, com progressiva autonomia.'}, {'codigo': 'LP2', 'pre_4ano': '4º ano: inferir, localizar explícitas, comparar textos, distinguir fato/opinião, identificar tema/finalidade e aspectos nucleares.', 'pre_antigo': '3º ano: localizar explícitas e sequência temporal, comparar textos, inferir significados, identificar tema e causa/consequência.', 'diagnostico': 'Texto narrativo + texto informativo curto: localizar, inferir, explicar finalidade e comparar informação.', 'recomposicao': 'Retomar estratégia específica ausente (localização, inferência, comparação) usando textos mais acessíveis e depois migrar para gêneros do 5º ano.'}, {'codigo': 'LP3', 'pre_4ano': '4º ano: debate regrado, exposição oral, recuperação de ideias principais, perguntas/respostas pertinentes.', 'pre_antigo': '3º ano: diálogo argumentativo, escuta atenta, exposição oral e relato de experimento.', 'diagnostico': 'Situação oral breve: explicar regra, sustentar opinião ou relatar procedimento; registrar rubricamente.', 'recomposicao': 'Modelagem de fala, roteiro de apoio, ensaio oral, escuta e reformulação; reduzir apoio gradualmente.'}, {'codigo': 'LP4', 'pre_4ano': '4º ano: contexto de produção, estrutura de gêneros, coesão/coerência, paragrafação e pontuação em textos do ano.', 'pre_antigo': '3º ano: estrutura de narrativas, sequência de acontecimentos, parágrafo e sinais básicos de pontuação.', 'diagnostico': 'Apresentar trecho e pedir identificação de finalidade/estrutura + reorganização de parágrafos ou pontuação com justificativa.', 'recomposicao': 'Retomar organização textual e relação entre partes antes de exigir análise mais refinada dos gêneros do 5º ano.'}, {'codigo': 'LP5', 'pre_4ano': '4º ano: uso funcional de classes gramaticais, concordância, acentuação e regularidades ortográficas em contexto.', 'pre_antigo': '3º ano: substantivo/adjetivo/verbo, concordância básica, ortografia e pontuação em textos.', 'diagnostico': 'Pequeno trecho para revisar/corrigir e explicar decisões; ditado contextualizado apenas como evidência complementar.', 'recomposicao': 'Recompor regularidade ou classe gramatical que bloqueia a escrita, sempre dentro de leitura/produção de texto.'}, {'codigo': 'LP6', 'pre_4ano': '4º ano: planejar, produzir e revisar textos com autonomia crescente, mantendo tema, estrutura, parágrafos e convenções.', 'pre_antigo': '3º ano: produção de textos com começo-meio-fim, sequência lógica, parágrafos e revisão orientada.', 'diagnostico': 'Produção curta a partir de situação comunicativa real + revisão posterior; comparar versão inicial e final.', 'recomposicao': 'Usar planejamento guiado, banco de recursos e revisão por etapas; retirar andaimes conforme o estudante avança.'}, {'codigo': 'LP7', 'pre_4ano': '4º ano: apreciação literária, inferência, humor/ironia e leitura de poemas/narrativas.', 'pre_antigo': '3º ano: apreciação, linguagem figurada básica, conto/fábula/poema e elementos de narrativa.', 'diagnostico': 'Leitura literária curta seguida de resposta interpretativa e justificativa com evidência do texto.', 'recomposicao': 'Retomar compreensão literal e elementos narrativos antes de exigir leitura figurada/irônica mais complexa.'}], 'blueprint': [{'id': '1', 'dimensao': 'LP1', 'situacao': 'Amostra individual de leitura oral + 3 perguntas de compreensão', 'bloom': 'Compreender / Aplicar', 'evidencia': 'fluência + sentido; não usar velocidade isoladamente'}, {'id': '2', 'dimensao': 'LP2', 'situacao': 'Texto informativo: localizar explícita, ideia principal e inferir informação', 'bloom': 'Compreender / Analisar', 'evidencia': 'respostas com indicação de evidência textual'}, {'id': '3', 'dimensao': 'LP2', 'situacao': 'Dois textos sobre tema semelhante: comparar enfoque e distinguir fato/opinião', 'bloom': 'Analisar / Justificar', 'evidencia': 'comparação sustentada por trechos/informações'}, {'id': '4', 'dimensao': 'LP3', 'situacao': 'Produção oral: explicar regra de jogo ou sustentar ponto de vista', 'bloom': 'Aplicar / Justificar', 'evidencia': 'clareza, adequação, turnos e argumento'}, {'id': '5', 'dimensao': 'LP4', 'situacao': 'Analisar gênero/trecho: finalidade, contexto, estrutura, coesão e pontuação', 'bloom': 'Compreender / Analisar', 'evidencia': 'identificação + explicação do efeito'}, {'id': '6', 'dimensao': 'LP5', 'situacao': 'Revisar trecho com concordância/acentuação/ortografia do período', 'bloom': 'Aplicar / Justificar', 'evidencia': 'correção + explicação de pelo menos uma escolha'}, {'id': '7', 'dimensao': 'LP6', 'situacao': 'Produção escrita com planejamento, versão inicial, revisão e versão final', 'bloom': 'Aplicar / Criar', 'evidencia': 'adequação ao gênero, textualidade e convenções'}, {'id': '8', 'dimensao': 'LP7', 'situacao': 'Texto literário: interpretar efeito de sentido, humor/figuração ou elemento narrativo', 'bloom': 'Analisar / Justificar', 'evidencia': 'resposta interpretativa apoiada no texto'}]}, 'Matemática': {'slug': 'MAT', 'curriculo_chegada': 'SND e decimais; situações-problema e operações; igualdade; geometria; grandezas; estatística/probabilidade; raciocínio matemático.', 'nucleo_estruturante': 'SND/decimais e resolução de problemas com as quatro operações.', 'pre_requisitos_principais': '4º: valor posicional, decimais, operações, problemas, medidas e gráficos. 3º: números até dezena de milhar, quatro operações e problemas de até 2 passos.', 'ancora': 'ÂNCORA PARA A SÍNTESE M1 e M2 são dimensões estruturantes. M7 deve aparecer como evidência transversal nas demais dimensões.', 'dimensoes': [{'codigo': 'M1', 'nome': 'Sistema de Numeração Decimal e números decimais', 'demonstrar': 'Lê, escreve, compara e representa números até milhão; trabalha ordens/classes, valor posicional, composição/decomposição inclusive polinomial, décimos/centésimos/milésimos e reta numérica.', 'focos': 'Números naturais/racionais; SND; decimais; reta numérica.', 'peso': 'ESTRUTURANTE'}, {'codigo': 'M2', 'nome': 'Operações e situações-problema', 'demonstrar': 'Resolve e elabora situações de até 3 passos com números naturais; utiliza algoritmos das quatro operações; opera adição/subtração com decimais e multiplicação de decimal por natural; usa produto por 10, 100 e 1.000.', 'focos': 'Quatro operações; cálculo mental/estratégias; problemas; decimais.', 'peso': 'ESTRUTURANTE'}, {'codigo': 'M3', 'nome': 'Álgebra e equivalência', 'demonstrar': 'Reconhece equivalência e resolve igualdades com termo desconhecido, explicando a relação entre os membros.', 'focos': 'Igualdade; equivalência; termo desconhecido.', 'peso': 'REGULAR'}, {'codigo': 'M4', 'nome': 'Geometria e localização', 'demonstrar': 'Interpreta mapas/plantas e 1º quadrante; localiza/movimenta objetos; reconhece propriedades de polígonos, poliedros e corpos redondos; usa modelos geométricos em problemas.', 'focos': 'Localização; plano cartesiano; figuras 2D/3D; propriedades.', 'peso': 'REGULAR'}, {'codigo': 'M5', 'nome': 'Grandezas e medidas', 'demonstrar': 'Estima e utiliza unidades de medida, resolve situações de tempo/intervalo e sistema monetário, selecionando procedimentos/instrumentos adequados.', 'focos': 'Comprimento, massa, capacidade, tempo, temperatura, dinheiro.', 'peso': 'REGULAR'}, {'codigo': 'M6', 'nome': 'Estatística e probabilidade', 'demonstrar': 'Analisa espaço amostral, lê/representa dados, realiza pesquisa e comunica conclusões.', 'focos': 'Chances; tabelas; gráficos; pesquisa; síntese de resultados.', 'peso': 'REGULAR'}, {'codigo': 'M7', 'nome': 'Raciocínio e comunicação matemática', 'demonstrar': 'Explica estratégias, verifica resultados, compara procedimentos e justifica conclusões.', 'focos': 'Eixo transversal de resolução de problemas.', 'peso': 'TRANSVERSAL'}], 'pre_requisitos': [{'codigo': 'M1', 'pre_4ano': '4º ano: leitura/escrita até centena de milhar; ordens/classes; valor posicional; composição/decomposição; números decimais e equivalências básicas.', 'pre_antigo': '3º ano: números até dezena de milhar; valor relativo/absoluto; composição/decomposição; reta numérica.', 'diagnostico': 'Ditado/registro de números, composição/decomposição, comparação e leitura de decimal simples.', 'recomposicao': 'Retomar quadro de ordens, agrupamentos/base 10 e composição/decomposição; ampliar gradualmente para milhão e decimais do 5º.'}, {'codigo': 'M2', 'pre_4ano': '4º ano: problemas de até 3 passos, quatro operações, multiplicação com 2/3 algarismos, divisão com 1/2 dígitos, adição/subtração de decimais.', 'pre_antigo': '3º ano: problemas de até 2 passos, algoritmos das quatro operações, tabuada 1-10, divisão com 1 dígito.', 'diagnostico': 'Problemas sem indicação de operação + cálculo escrito e explicação da estratégia.', 'recomposicao': 'Recompor significados das operações e fatos básicos antes de exigir algoritmo mais complexo; manter problemas do 5º em níveis graduais.'}, {'codigo': 'M3', 'pre_4ano': '4º ano: igualdade com termo desconhecido; propriedades da igualdade; conferência por operações inversas.', 'pre_antigo': '3º ano: diferentes sentenças de adição/subtração com mesma soma/diferença e padrões.', 'diagnostico': 'Sentenças como 136 + ? = 200 e situação-problema correspondente.', 'recomposicao': 'Usar balança/equivalência, operações inversas e sentenças simples antes de ampliar.'}, {'codigo': 'M4', 'pre_4ano': '4º ano: pontos de referência, croquis, trajetos, propriedades de polígonos/poliedros.', 'pre_antigo': '3º ano: deslocamentos, coordenadas simples, planificações, lados/vértices.', 'diagnostico': 'Leitura de planta/mapa, localização e classificação de figuras.', 'recomposicao': 'Retomar orientação espacial e propriedades observáveis antes de formalizar coordenadas/cartesiano.'}, {'codigo': 'M5', 'pre_4ano': '4º ano: medidas padronizadas, tempo, dinheiro, estimativa e resolução de problemas.', 'pre_antigo': '3º ano: medição/estimativa de comprimento, massa, capacidade, tempo e dinheiro.', 'diagnostico': 'Situações de medida/tempo/dinheiro com escolha de unidade e justificativa.', 'recomposicao': 'Recompor significado de medir, equivalências usuais e leitura de instrumentos em contexto.'}, {'codigo': 'M6', 'pre_4ano': '4º ano: espaço amostral; tabelas de dupla entrada; gráficos de colunas, barras e setores.', 'pre_antigo': '3º ano: tabelas/gráficos e ideia de acaso em situações cotidianas.', 'diagnostico': 'Leitura de gráfico/tabela + pergunta de chance simples + organização de pequena pesquisa.', 'recomposicao': 'Retomar leitura de eixos/categorias e vocabulário de chance antes de avançar para síntese.'}, {'codigo': 'M7', 'pre_4ano': '4º/3º anos: comunicar estratégias, comparar procedimentos, estimar e verificar resultados.', 'pre_antigo': '2º/3º anos: uso de estratégias pessoais e explicação oral/escrita.', 'diagnostico': 'Pedir “como você pensou?”, “há outra estratégia?” e “como conferir?”.', 'recomposicao': 'Incorporar justificativa em tarefas regulares, não como atividade separada.'}], 'blueprint': [{'id': '1', 'dimensao': 'M1', 'situacao': 'Leitura/escrita e composição/decomposição de números naturais e decimais', 'bloom': 'Compreender / Aplicar', 'evidencia': 'representação correta e explicação do valor posicional'}, {'id': '2', 'dimensao': 'M1', 'situacao': 'Comparar/ordenar e localizar números em reta', 'bloom': 'Aplicar / Analisar', 'evidencia': 'uso de relações e justificativa'}, {'id': '3', 'dimensao': 'M2', 'situacao': 'Problema de 2-3 passos com operações naturais', 'bloom': 'Aplicar', 'evidencia': 'seleção de operações e estratégia'}, {'id': '4', 'dimensao': 'M2', 'situacao': 'Problema com decimal + adição/subtração ou multiplicação decimal x natural', 'bloom': 'Aplicar / Analisar', 'evidencia': 'compreensão da vírgula e coerência do resultado'}, {'id': '5', 'dimensao': 'M2/M7', 'situacao': 'Comparar duas estratégias ou identificar erro de resolução', 'bloom': 'Analisar / Justificar', 'evidencia': 'argumentação matemática'}, {'id': '6', 'dimensao': 'M3', 'situacao': 'Igualdade com termo desconhecido + problema correspondente', 'bloom': 'Aplicar', 'evidencia': 'equivalência e operação inversa'}, {'id': '7', 'dimensao': 'M4', 'situacao': 'Mapa/planta/coordenação e propriedades de figuras', 'bloom': 'Aplicar / Analisar', 'evidencia': 'localização e vocabulário geométrico'}, {'id': '8', 'dimensao': 'M5', 'situacao': 'Situação de tempo/medida/dinheiro', 'bloom': 'Aplicar', 'evidencia': 'escolha adequada de unidade/procedimento'}, {'id': '9', 'dimensao': 'M6', 'situacao': 'Tabela/gráfico e espaço amostral', 'bloom': 'Compreender / Analisar', 'evidencia': 'interpretação e conclusão'}, {'id': '10', 'dimensao': 'M6/M7', 'situacao': 'Organizar dados de pequena pesquisa e comunicar conclusão', 'bloom': 'Aplicar / Criar', 'evidencia': 'representação adequada + síntese'}]}, 'Ciências': {'slug': 'CIE', 'curriculo_chegada': 'Biomas; atmosfera/água; energia; Terra e exploração espacial; biodiversidade/cadeias; sistemas humanos; saúde/nutrição.', 'nucleo_estruturante': 'Relações sistêmicas, explicação de processos e uso de evidências.', 'pre_requisitos_principais': '4º: ecossistemas, poluição, energia, sistema solar, cadeias, sistemas do corpo e alimentação. 3º: atmosfera, água, litosfera, cadeia e saúde.', 'ancora': 'ÂNCORA PARA A SÍNTESE C1 e C5 são dimensões estruturantes; explicações causais e uso de evidências devem atravessar o componente.', 'dimensoes': [{'codigo': 'C1', 'nome': 'Biomas, fatores bióticos/abióticos e preservação', 'demonstrar': 'Explica relações de interdependência entre seres vivos, ar, água, solo, luz e calor nos biomas e reconhece ações de preservação.', 'focos': 'Ecossistemas/biomas; interdependência; preservação.', 'peso': 'ESTRUTURANTE'}, {'codigo': 'C2', 'nome': 'Atmosfera e água', 'demonstrar': 'Reconhece condições para a vida, camadas da atmosfera, efeito estufa/aquecimento global, principais gases e diferencia água doce/salgada.', 'focos': 'Atmosfera; gases; efeito estufa; água.', 'peso': 'REGULAR'}, {'codigo': 'C3', 'nome': 'Fontes e tipos de energia', 'demonstrar': 'Distingue fontes renováveis/não renováveis e tipos de energia, relacionando usos e impactos.', 'focos': 'Solar, eólica, hidráulica, combustão, nuclear; térmica, elétrica, sonora, luminosa, química, movimento.', 'peso': 'REGULAR'}, {'codigo': 'C4', 'nome': 'Planeta Terra e exploração espacial', 'demonstrar': 'Identifica camadas do planeta e reconhece instrumentos e marcos da exploração espacial.', 'focos': 'Camadas da Terra; satélite, foguete, luneta, telescópio.', 'peso': 'REGULAR'}, {'codigo': 'C5', 'nome': 'Biodiversidade e relações alimentares', 'demonstrar': 'Identifica fauna/flora, causas de redução da biodiversidade e organiza relações entre produtores, consumidores e decompositores.', 'focos': 'Flora/fauna; extinção; desequilíbrio; cadeia alimentar.', 'peso': 'ESTRUTURANTE'}, {'codigo': 'C6', 'nome': 'Sistemas do corpo humano', 'demonstrar': 'Reconhece estrutura/função dos sistemas reprodutivo, endócrino e nervoso e sua integração ao organismo.', 'focos': 'Anatomia e fisiologia humana.', 'peso': 'REGULAR'}, {'codigo': 'C7', 'nome': 'Saúde e nutrição', 'demonstrar': 'Relaciona fatores ambientais a doenças e reconhece princípios de alimentação saudável/equilibrada.', 'focos': 'Radiação/poluição; prevenção; pirâmide alimentar.', 'peso': 'REGULAR'}], 'pre_requisitos': [{'codigo': 'C1', 'pre_4ano': '4º ano: relações biótico/abiótico em ambientes rurais/urbanos e influência humana no equilíbrio.', 'pre_antigo': '3º ano: relações em ambientes da cidade e necessidade de preservação.', 'diagnostico': 'Classificar elementos de um ambiente e explicar uma relação entre eles e uma ação humana.', 'recomposicao': 'Retomar conceito de ecossistema e relações locais antes de ampliar para biomas brasileiros.'}, {'codigo': 'C2', 'pre_4ano': '4º ano: poluição do ar/água/solo e consequências; tratamento/uso da água.', 'pre_antigo': '3º ano: composição da atmosfera, propriedades do ar, ciclo da água, litosfera.', 'diagnostico': 'Esquema simples de atmosfera/água com perguntas causais.', 'recomposicao': 'Recompor ar-atmosfera, ciclo/qualidade da água e solo; depois avançar para camadas/efeito estufa.'}, {'codigo': 'C3', 'pre_4ano': '4º ano: fontes renováveis/não renováveis, eletricidade, luz e calor.', 'pre_antigo': '3º ano: Sol como fonte primária e transformações materiais/energia em situações simples.', 'diagnostico': 'Classificar fontes e tipos de energia em situações do cotidiano, justificando.', 'recomposicao': 'Retomar fonte x forma de energia e impactos antes de comparar matrizes energéticas.'}, {'codigo': 'C4', 'pre_4ano': '4º ano: Sistema Solar, planetas/satélites e grandezas.', 'pre_antigo': '3º ano: rotação/translação, Sol como fonte de luz/calor.', 'diagnostico': 'Identificar camadas da Terra e função de instrumentos de exploração/observação.', 'recomposicao': 'Recompor Terra/Sistema Solar e diferença entre corpo celeste/instrumento.'}, {'codigo': 'C5', 'pre_4ano': '4º ano: fotossíntese, animais por alimentação, cadeia alimentar e produtores/consumidores/decompositores.', 'pre_antigo': '3º ano: cadeia alimentar e classificação básica de seres vivos.', 'diagnostico': 'Montar cadeia e explicar o que ocorre se um elo diminui; reconhecer fator de risco à biodiversidade.', 'recomposicao': 'Retomar papel de produtores/consumidores/decompositores e dependência entre seres.'}, {'codigo': 'C6', 'pre_4ano': '4º ano: células-tecidos-órgãos-sistemas; sistemas esquelético, muscular, digestório, circulatório, respiratório e excretório.', 'pre_antigo': '3º ano: sistemas esquelético/muscular e funções básicas.', 'diagnostico': 'Relacionar órgão/sistema/função e explicar integração simples.', 'recomposicao': 'Recompor organização do corpo e noção de sistema antes de estudar sistemas novos.'}, {'codigo': 'C7', 'pre_4ano': '4º ano: alimentação saudável, doenças relacionadas ao ambiente e à alimentação.', 'pre_antigo': '3º ano: vacinas, higiene, prevenção e leitura de rótulos/alimentos industrializados.', 'diagnostico': 'Situação-problema de saúde/nutrição com justificativa de prevenção ou escolha alimentar.', 'recomposicao': 'Retomar fatores de prevenção e nutrientes/alimentação em situações concretas.'}], 'blueprint': [{'id': '1', 'dimensao': 'C1', 'situacao': 'Analisar um bioma e relacionar fatores bióticos/abióticos', 'bloom': 'Compreender / Analisar', 'evidencia': 'relações, não apenas listas'}, {'id': '2', 'dimensao': 'C2', 'situacao': 'Esquema da atmosfera/efeito estufa e situação sobre água doce/salgada', 'bloom': 'Compreender / Aplicar', 'evidencia': 'explicação causal simples'}, {'id': '3', 'dimensao': 'C3', 'situacao': 'Classificar fontes e tipos de energia em situações reais', 'bloom': 'Aplicar / Justificar', 'evidencia': 'critério + impacto'}, {'id': '4', 'dimensao': 'C4', 'situacao': 'Camadas da Terra e instrumentos de exploração espacial', 'bloom': 'Compreender / Aplicar', 'evidencia': 'função e relação com investigação'}, {'id': '5', 'dimensao': 'C5', 'situacao': 'Cadeia alimentar + cenário de desequilíbrio/extinção', 'bloom': 'Aplicar / Analisar', 'evidencia': 'prever consequência'}, {'id': '6', 'dimensao': 'C6', 'situacao': 'Relacionar sistema, órgãos e função; explicar integração', 'bloom': 'Compreender / Analisar', 'evidencia': 'relação funcional'}, {'id': '7', 'dimensao': 'C7', 'situacao': 'Caso de saúde/nutrição para propor prevenção/decisão', 'bloom': 'Aplicar / Avaliar', 'evidencia': 'decisão justificada'}, {'id': '8', 'dimensao': 'C1-C7', 'situacao': 'Questão integradora com gráfico, imagem, experimento ou notícia curta', 'bloom': 'Analisar / Justificar', 'evidencia': 'uso de evidências científicas'}]}, 'História': {'slug': 'HIST', 'curriculo_chegada': 'Primeiros grupos humanos; nomadismo/sedentarismo; fontes anteriores à escrita; agricultura e primeiras cidades; cultura/religião na Antiguidade.', 'nucleo_estruturante': 'Temporalidade, causa/consequência e uso de fontes para explicar mudanças.', 'pre_requisitos_principais': '4º/3º: leitura de fontes, mudanças/permanências, organização de sociedades, temporalidade e relação entre espaço, trabalho e cultura.', 'ancora': 'ÂNCORA PARA A SÍNTESE H1 e H2 são dimensões estruturantes. H5 deve aparecer transversalmente em toda a avaliação.', 'dimensoes': [{'codigo': 'H1', 'nome': 'Primeiros grupos humanos: nomadismo e sedentarismo', 'demonstrar': 'Explica relações entre espaço/recursos e modos de vida, reconhecendo causas e consequências da passagem do nomadismo ao sedentarismo.', 'focos': 'Primeiros grupos; nomadismo; sedentarização.', 'peso': 'ESTRUTURANTE'}, {'codigo': 'H2', 'nome': 'Fontes e História antes da escrita', 'demonstrar': 'Reconhece registros anteriores à escrita e utiliza fontes para inferir aspectos da vida de grupos humanos.', 'focos': 'Pinturas rupestres, registros, transmissão de cultura.', 'peso': 'ESTRUTURANTE'}, {'codigo': 'H3', 'nome': 'Agricultura, pastoreio e primeiras cidades', 'demonstrar': 'Relaciona domínio de técnicas agrícolas/pastoris às transformações sociais e à formação de cidades/culturas sedentárias.', 'focos': 'Agricultura; pastoreio; tecnologias; primeiras cidades.', 'peso': 'REGULAR'}, {'codigo': 'H4', 'nome': 'Cultura e religião na Antiguidade', 'demonstrar': 'Reconhece o papel da cultura e da religião na composição identitária de povos antigos, comparando sem anacronismos simplistas.', 'focos': 'Religião e cultura na Antiguidade.', 'peso': 'REGULAR'}, {'codigo': 'H5', 'nome': 'Raciocínio histórico', 'demonstrar': 'Organiza temporalmente, compara mudanças/permanências, estabelece causa/consequência e sustenta interpretações com fontes.', 'focos': 'Sujeito histórico; temporalidade; fatos/fontes.', 'peso': 'TRANSVERSAL'}], 'pre_requisitos': [{'codigo': 'H1', 'pre_4ano': '4º ano: compreender organização de sociedades em diferentes períodos e relações entre economia, poder e modos de vida.', 'pre_antigo': '3º ano: mudanças/permanências, modos de vida e relações entre atividades humanas e espaço local.', 'diagnostico': 'Comparar dois modos de vida e explicar uma causa/consequência sem depender de memorização de datas.', 'recomposicao': 'Retomar comparação de modos de vida e noções de mudança/permanência antes de introduzir longa duração histórica.'}, {'codigo': 'H2', 'pre_4ano': '4º ano: uso de fontes para estudar Brasil Colônia/Império/República; leitura contextualizada de registros.', 'pre_antigo': '3º ano: fontes orais, escritas e iconográficas e sua função na investigação do passado.', 'diagnostico': 'Apresentar imagem/objeto/registro e perguntar o que é possível inferir e o que não é possível afirmar.', 'recomposicao': 'Recompor diferença entre fonte e opinião; ensinar a sustentar resposta com evidência.'}, {'codigo': 'H3', 'pre_4ano': '4º ano: relações entre trabalho, economia e organização social em processos históricos.', 'pre_antigo': '3º ano: atividades econômicas e transformações sociais/espaciais em escala local.', 'diagnostico': 'Sequência de imagens/textos sobre agricultura e formação de aldeia/cidade; pedir relação causal.', 'recomposicao': 'Retomar noção de transformação técnica e impacto sobre organização coletiva.'}, {'codigo': 'H4', 'pre_4ano': '4º ano: contato entre culturas e diversidade cultural ao longo da história.', 'pre_antigo': '3º ano: contribuições de diferentes grupos e respeito à diversidade cultural.', 'diagnostico': 'Comparar prática cultural/religiosa de dois povos com foco em contexto e função social.', 'recomposicao': 'Recompor cultura como construção histórica e evitar julgamentos pelo presente.'}, {'codigo': 'H5', 'pre_4ano': '4º/3º anos: anterioridade/posteridade, linha do tempo, causa/consequência, mudança/permanência e leitura de fontes.', 'pre_antigo': '2º/3º anos: sequência temporal, passado/presente e fontes do cotidiano.', 'diagnostico': 'Mini linha do tempo + uma pergunta causal + uma pergunta baseada em fonte.', 'recomposicao': 'Trabalhar operadores do pensamento histórico junto ao conteúdo, não como capítulo isolado.'}], 'blueprint': [{'id': '1', 'dimensao': 'H1', 'situacao': 'Comparar nomadismo e sedentarismo e explicar relação com recursos/ambiente', 'bloom': 'Compreender / Analisar', 'evidencia': 'comparação causal'}, {'id': '2', 'dimensao': 'H2', 'situacao': 'Analisar uma pintura rupestre/registro e inferir aspectos da vida', 'bloom': 'Analisar / Justificar', 'evidencia': 'evidência e limite da inferência'}, {'id': '3', 'dimensao': 'H3', 'situacao': 'Ordenar transformações: agricultura/pastoreio -> fixação -> cidades', 'bloom': 'Aplicar / Analisar', 'evidencia': 'sequência + relação de causa/consequência'}, {'id': '4', 'dimensao': 'H3', 'situacao': 'Situação-problema: como uma inovação agrícola pode mudar a organização do grupo?', 'bloom': 'Analisar', 'evidencia': 'explicação histórica'}, {'id': '5', 'dimensao': 'H4', 'situacao': 'Comparar práticas culturais/religiosas de povos antigos', 'bloom': 'Compreender / Analisar', 'evidencia': 'contextualização e respeito à diversidade'}, {'id': '6', 'dimensao': 'H5', 'situacao': 'Linha do tempo ou quadro de mudanças/permanências', 'bloom': 'Aplicar', 'evidencia': 'organização temporal'}, {'id': '7', 'dimensao': 'H1-H5', 'situacao': 'Resposta argumentada usando uma fonte e um conhecimento do conteúdo', 'bloom': 'Justificar / Avaliar', 'evidencia': 'interpretação sustentada por evidência'}]}, 'Geografia': {'slug': 'GEO', 'curriculo_chegada': 'Migração e população; trabalho/tecnologia e êxodo rural; transformação de paisagens urbanas; tipos de cidades; interação campo-cidade e urbanização.', 'nucleo_estruturante': 'Leitura espacial e análise de relações população-trabalho-paisagem.', 'pre_requisitos_principais': '4º: processos migratórios, setores econômicos, campo/cidade, mapas e paisagens. 3º: rural/urbano, atividades econômicas e transformações da paisagem.', 'ancora': 'ÂNCORA PARA A SÍNTESE G1 e G2 são dimensões estruturantes. G6 deve aparecer transversalmente nas situações de avaliação.', 'dimensoes': [{'codigo': 'G1', 'nome': 'Dinâmica populacional e migrações', 'demonstrar': 'Descreve características da população brasileira e analisa fluxos migratórios, migração interna e imigração, relacionando deslocamentos a condições de vida/infraestrutura.', 'focos': 'População brasileira; migrações; imigração.', 'peso': 'ESTRUTURANTE'}, {'codigo': 'G2', 'nome': 'Trabalho, tecnologia e êxodo rural', 'demonstrar': 'Compara mudanças no trabalho e na tecnologia na agropecuária, indústria, comércio e serviços e reconhece relações com o êxodo rural.', 'focos': 'Mundo do trabalho; inovação tecnológica; êxodo rural.', 'peso': 'ESTRUTURANTE'}, {'codigo': 'G3', 'nome': 'Transformações das paisagens urbanas', 'demonstrar': 'Analisa transformações de paisagens urbanas comparando fotografias terrestres, aéreas e imagens de satélite de épocas diferentes.', 'focos': 'Paisagem; tempo; imagens/fotografias.', 'peso': 'REGULAR'}, {'codigo': 'G4', 'nome': 'Tipos de cidades e crescimento urbano', 'demonstrar': 'Identifica formas/funções das cidades e analisa mudanças sociais, econômicas e ambientais provocadas pelo crescimento urbano.', 'focos': 'Cidades turísticas, industriais, planejadas etc.; crescimento urbano.', 'peso': 'REGULAR'}, {'codigo': 'G5', 'nome': 'Campo-cidade, industrialização e urbanização', 'demonstrar': 'Explica interações entre campo e cidade, atividades econômicas e processos de industrialização/urbanização do espaço brasileiro.', 'focos': 'Setores econômicos; campo/cidade; industrialização; urbanização.', 'peso': 'REGULAR'}, {'codigo': 'G6', 'nome': 'Raciocínio espacial com evidências', 'demonstrar': 'Utiliza fotografias, dados e representações espaciais para comparar lugares, identificar relações e justificar conclusões.', 'focos': 'Eixo transversal de leitura espacial.', 'peso': 'TRANSVERSAL'}], 'pre_requisitos': [{'codigo': 'G1', 'pre_4ano': '4º ano: processos migratórios e formação da sociedade brasileira; contribuições culturais.', 'pre_antigo': '3º ano: histórias familiares/migrações e contribuição de grupos em Limeira.', 'diagnostico': 'Mapa/gráfico simples de deslocamentos + pergunta sobre motivo/consequência de uma migração.', 'recomposicao': 'Retomar conceitos de migração, origem/destino e motivos antes de ampliar para escala Brasil.'}, {'codigo': 'G2', 'pre_4ano': '4º ano: trabalho no campo/cidade, setores primário/secundário/terciário, produção-circulação-consumo.', 'pre_antigo': '3º ano: atividades rurais/urbanas e matérias-primas/indústrias.', 'diagnostico': 'Classificar atividades por setor e explicar uma transformação tecnológica no trabalho.', 'recomposicao': 'Recompor cadeias de produção e setores econômicos para compreender mudança tecnológica e êxodo rural.'}, {'codigo': 'G3', 'pre_4ano': '4º ano: leitura de fotografias, imagens, gráficos/mapas e identificação de paisagens naturais/antrópicas.', 'pre_antigo': '3º ano: comparação de paisagens e mudanças/permanências no município.', 'diagnostico': 'Comparar duas imagens da mesma cidade em épocas diferentes e registrar mudanças/permanências.', 'recomposicao': 'Retomar leitura de indícios visuais e noção de paisagem antes de exigir interpretação de processo urbano.'}, {'codigo': 'G4', 'pre_4ano': '4º ano: urbanização do espaço paulista, modos de vida, comércio/serviços e transformações urbanas.', 'pre_antigo': '3º ano: espaço urbano/rurbano/rural e atividades econômicas.', 'diagnostico': 'Apresentar perfis de cidades e pedir classificação/função + efeito do crescimento.', 'recomposicao': 'Recompor diferença entre função urbana, atividade econômica e crescimento físico da cidade.'}, {'codigo': 'G5', 'pre_4ano': '4º ano: interdependência campo-cidade, meios de transporte/comunicação e setores econômicos.', 'pre_antigo': '3º ano: comparação entre campo/cidade e atividades rurais/urbanas.', 'diagnostico': 'Fluxo produto/campo-indústria-comércio-cidade + pergunta causal sobre urbanização.', 'recomposicao': 'Retomar interdependência e circuito produção-circulação-consumo antes de discutir industrialização/urbanização.'}, {'codigo': 'G6', 'pre_4ano': '4º ano: comparação de mapas, pontos cardeais, planos de visão e uso de representações.', 'pre_antigo': '3º ano: mapas, legendas, imagens bi/tridimensionais e pontos de referência.', 'diagnostico': 'Usar imagem/foto/mapa/gráfico como fonte de evidência em pelo menos uma questão.', 'recomposicao': 'Recompor leitura básica de legenda, escala visual e orientação conforme necessidade da turma.'}], 'blueprint': [{'id': '1', 'dimensao': 'G1', 'situacao': 'Interpretar mapa/gráfico de migração e explicar um padrão observado', 'bloom': 'Compreender / Analisar', 'evidencia': 'leitura de dado + explicação'}, {'id': '2', 'dimensao': 'G1', 'situacao': 'Situação sobre migração interna/imigração e infraestrutura', 'bloom': 'Aplicar / Justificar', 'evidencia': 'relação causa-contexto'}, {'id': '3', 'dimensao': 'G2', 'situacao': 'Comparar trabalho/tecnologia em dois setores e relacionar ao êxodo rural', 'bloom': 'Analisar', 'evidencia': 'mudança + consequência'}, {'id': '4', 'dimensao': 'G3', 'situacao': 'Comparar sequência de fotografias/imagem de satélite de uma cidade', 'bloom': 'Analisar / Justificar', 'evidencia': 'mudanças/permanências com evidências visuais'}, {'id': '5', 'dimensao': 'G4', 'situacao': 'Classificar tipos/funções de cidades e analisar impacto do crescimento', 'bloom': 'Aplicar / Analisar', 'evidencia': 'função urbana + consequência'}, {'id': '6', 'dimensao': 'G5', 'situacao': 'Explicar fluxo campo-cidade e relação com industrialização/urbanização', 'bloom': 'Analisar', 'evidencia': 'interdependência'}, {'id': '7', 'dimensao': 'G1-G5', 'situacao': 'Propor explicação/solução para problema urbano simples usando dados fornecidos', 'bloom': 'Avaliar / Criar', 'evidencia': 'argumento espacial baseado em evidência'}]}}}}
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
    m = re.search('([1-5])\\s*[ºO]?\\s*ANO', _norm(turma))
    return int(m.group(1)) if m else None

def _clean_pdf(texto: Any) -> str:
    s = str(texto or '')
    tr = str.maketrans({'–': '-', '—': '-', '“': '"', '”': '"', '‘': "'", '’': "'", '•': '-', '→': '->', 'º': 'o', 'ª': 'a'})
    return s.translate(tr).encode('latin-1', 'replace').decode('latin-1')

def _componente_slug(componente: str) -> str:
    try:
        return AVALIACAO_DB[5][1][componente]['slug']
    except Exception:
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

def _pdf_multiline(pdf: FPDF, titulo: str, texto: str, size: int=9):
    pdf.set_font('Arial', 'B', size)
    pdf.set_text_color(30, 41, 59)
    pdf.multi_cell(0, 5, _clean_pdf(titulo))
    pdf.set_font('Arial', '', size)
    pdf.set_text_color(51, 65, 85)
    pdf.multi_cell(0, 5, _clean_pdf(texto or '-'))
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
        pdf.multi_cell(0, 5, _clean_pdf(f"AB: {cont.get('AB', 0)} | B: {cont.get('B', 0)} | AD: {cont.get('AD', 0)} | A: {cont.get('A', 0)} | Sem fechamento: {cont.get('-', 0)}"))
        prioridades = r.get('prioridades', [])
        if prioridades:
            pdf.multi_cell(0, 5, _clean_pdf('Prioridades coletivas: ' + '; '.join(prioridades[:5])))
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
            recomposicao = st.text_input(f'Recomposição selecionada · {cod}', value=atual.get('recomposicao', ''), placeholder='Ex.: retomar valor posicional do 4º ano', key=f'av_rec_{ctx.turma}_{ctx.componente}_{cod}')
        with st.expander(f'🔎 Pré-requisitos já mapeados para {cod}'):
            st.markdown(f"**4º ano — pré-requisito direto:** {p.get('pre_4ano', '-')}")
            st.markdown(f"**Se a lacuna for mais antiga:** {p.get('pre_antigo', '-')}")
            st.markdown(f"**Diagnóstico rápido sugerido:** {p.get('diagnostico', '-')}")
            st.markdown(f"**Recomposição e ponte para o 5º ano:** {p.get('recomposicao', '-')}")
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

def renderizar_avaliacao(supabase: Any, sql_instalacao: Optional[str]=None) -> None:
    """Renderiza o módulo sem depender de variáveis locais do ``app_pei.py``.

    O único objeto recebido do aplicativo principal é a conexão ``supabase`` já
    inicializada. Usuário, permissões e matriz docente são resolvidos pelo próprio módulo.
    """
    _css()
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
