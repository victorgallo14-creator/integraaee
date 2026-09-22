"""Módulo de histórico escolar para integração em aplicação Streamlit.

Versão revisada em 2026-09-22: ajustes de paginação do PDF e dados institucionais padrão.

Uso no aplicativo principal:
    from modulo_historico import renderizar_modulo
    renderizar_modulo()

Arquivo autônomo: não requer pasta de assets, XLS, fontes ou outros módulos locais.
O formulário PDF é desenhado vetorialmente pelo próprio Python. Para o brasão da
Prefeitura, o módulo procura o arquivo existente `logo_prefeitura.png` ao lado do
próprio módulo ou na pasta de execução da aplicação.
Use HISTORICO_DB_PATH ou renderizar_modulo(banco_path=...) para definir o SQLite.
Em hospedagens com disco efêmero, exporte JSON/PDF; o SQLite não substitui um
banco persistente. Não há conexão automática com Supabase ou cadastro externo.
"""
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace

"""Regras documentais baseadas exclusivamente nas fontes fornecidas.

Não presume notas, participação, conclusão, calendário ou duração da aula.
"""
from copy import deepcopy
from datetime import date
from decimal import Decimal, InvalidOperation
import re

BASE = ['LÍNGUA PORTUGUESA', 'GEOGRAFIA', 'MATEMÁTICA', 'CIÊNCIAS', 'HISTÓRIA', 'ED. FÍSICA', 'ARTE']
DIV = ['EIXO INTELECTUAL', 'EIXO ESPORTIVO', 'EIXO CULTURAL', 'LINGUAGENS E TECNOLOGIAS', 'ACOMPANHAMENTO PEDAGÓGICO', 'PRÁTICAS EXPERIMENTAIS E DE TUTORIA DE ESTUDO', 'PRÁTICAS DE ESTUDO', 'LINGUAGENS', 'ESPORTE E EDUCAÇÃO DO MOVIMENTO']
MODOS = ['Parcial', 'APC', 'Complementação extracurricular', 'Integral', 'Bilíngue parcial', 'Bilíngue integral', 'Outra rede / matriz documentada']
SITUACOES = ['Não cursado', 'Concluído', 'Em curso']

# Dados institucionais do CEIEF Rafael Affonso Leite. Novos registros já
# são iniciados com estas informações, que continuam editáveis na interface.
ESCOLA_PADRAO = {
    'nome': 'CEIEF "Rafael Affonso Leite"',
    'ato': 'Decreto nº 416 de 19 de outubro de 2011.',
    'endereco': 'Rua Antonio Alves de Oliveira',
    'bairro': 'Jardim Presidente Dutra',
    'municipio': 'Limeira',
    'cep': '13.485-046',
    'telefone': '(19) 3495-5390',
    'email': 'ceief.rafaelaffonso@edu.limeira.sp.gov.br',
    'secretario': 'Clair Aparecido Mendes Filho - RG 40.034.491-9',
    'diretor': 'José Victor Souza Gallo - RG 55.735.978-8',
}

def novo():
    return {'versao': 1, 'demonstracao': False,
        'escola': deepcopy(ESCOLA_PADRAO),
        'aluno': {k: '' for k in ['nome','ra','ra_escolar','localidade','uf','nacionalidade','nascimento','distrito','livro','cidade_certidao','uf_certidao','matricula_certidao','documento_estrangeiro']},
        'anos': [{'serie': n, 'ano_letivo': '', 'situacao': 'Não cursado', 'modalidade': 'Parcial',
            'conceitos': {k: '' for k in BASE}, 'participacao': {k: '' for k in DIV},
            'ch_base': '', 'ch_div': '', 'unidade_base': 'H/A', 'unidade_div': 'H/A',
            'minutos_aula': '', 'ch_religioso': '', 'aee': False, 'relatorio_fc': False,
            'estabelecimento': '', 'municipio': '', 'uf': '', 'fonte': '',
            'justificativa_matriz': ''} for n in range(1,6)],
        'transferencia': {'ativa': False, 'serie': 1, 'turma': '', 'chamada': '', 'data': '',
            'dias': '', 'ausencias': '', 'compensadas': '', 'frequencia': '',
            'conceitos': {k: ['', '', ''] for k in BASE + DIV[3:]}},
        'observacoes': '', 'certificar': False, 'serie_certificada': 5, 'ano_certificado': '',
        'data_emissao': date.today().isoformat(), 'conferido': False}

def decimal(valor):
    try:
        n = Decimal(str(valor).replace(',', '.'))
        if not n.is_finite() or n < 0: raise ValueError()
        return n
    except (InvalidOperation, ValueError):
        raise ValueError('Informe um número não negativo.') from None

def fmt(n):
    return format(n.normalize(), 'f').replace('.', ',')

def carga(ano, campo):
    v = ano['ch_' + campo]
    return '' if str(v).strip() == '' else fmt(decimal(v)) + ('H/A' if ano['unidade_' + campo] == 'H/A' else 'H')

def total(ano):
    if ano['situacao'] != 'Concluído': return ''
    a, b = decimal(ano['ch_base']), decimal(ano['ch_div'])
    if ano['unidade_base'] == ano['unidade_div']:
        return fmt(a+b) + ('H/A' if ano['unidade_base']=='H/A' else 'H')
    minutos = decimal(ano['minutos_aula'])
    if minutos <= 0: raise ValueError('Duração da hora-aula deve ser maior que zero.')
    a = a * minutos if ano['unidade_base']=='H/A' else a*60
    b = b * minutos if ano['unidade_div']=='H/A' else b*60
    horas, resto = divmod(a+b, Decimal(60))
    return fmt(horas)+'H'+(fmt(resto)+'MIN' if resto else '')

def esperados(ano):
    """Componentes do anexo, não inferência de participação do estudante."""
    letivo = int(ano['ano_letivo'])
    m = ano['modalidade']
    if letivo < 2017 or letivo > 2026: return None
    if m == 'Outra rede / matriz documentada': return None
    if letivo < 2026:
        return set(DIV[:3]) if m != 'Parcial' and m != 'Bilíngue parcial' else set()
    if m in ['Parcial','Bilíngue parcial']: return {DIV[3]}
    if m == 'APC': return {DIV[3],DIV[4],DIV[5]}
    if m == 'Complementação extracurricular': return {DIV[3],DIV[5],DIV[6],DIV[7],DIV[8]}
    return {DIV[3],DIV[4],DIV[5],DIV[7],DIV[8]}

def validar(d, exigir_conferencia=True):
    erros, avisos = [], []
    def falta(valor, mensagem):
        if not str(valor).strip(): erros.append(mensagem)
    def data(v, rotulo):
        try: return date.fromisoformat(v)
        except (ValueError, TypeError): erros.append(rotulo+': data inválida.'); return None
    try:
        if d.get('versao') != 1: return ['Versão de dados não suportada.'], []
        for k in ['nome','ato','endereco','bairro','municipio','cep','telefone','email','secretario','diretor']:
            falta(d['escola'][k], 'Escola: preencha '+k+'.')
        for k in ['nome','ra','localidade','uf','nacionalidade','nascimento']:
            falta(d['aluno'][k], 'Estudante: preencha '+k+'.')
        nasc = data(d['aluno']['nascimento'],'Nascimento')
        emissao = data(d['data_emissao'],'Emissão')
        if nasc and emissao and nasc >= emissao: erros.append('Nascimento deve ser anterior à emissão.')
        a = d['aluno']
        if not (a['matricula_certidao'] or a['documento_estrangeiro'] or (a['distrito'] and a['livro'] and a['cidade_certidao'] and a['uf_certidao'])):
            erros.append('Informe certidão nova, certidão antiga completa ou documento estrangeiro.')
        if len(d['anos']) != 5 or [x['serie'] for x in d['anos']] != [1,2,3,4,5]:
            return erros+['Os anos devem conter exatamente as séries de 1 a 5, em ordem.'], avisos
        ativos=[]
        for ano in d['anos']:
            p = str(ano['serie'])+'º ano: '
            if ano['situacao'] not in SITUACOES: erros.append(p+'situação inválida.'); continue
            if ano['modalidade'] not in MODOS: erros.append(p+'modalidade inválida.'); continue
            if ano['situacao']=='Não cursado':
                if any(ano['conceitos'].values()) or any(ano['participacao'].values()) or ano['ch_base'] or ano['ch_div'] or ano['aee']:
                    erros.append(p+'há resultados para um ano não cursado.')
                continue
            ativos.append(ano)
            try:
                y=int(ano['ano_letivo'])
                if not 1900 <= y <= (emissao.year if emissao else date.today().year): raise ValueError()
            except (ValueError,TypeError): erros.append(p+'ano letivo inválido.'); continue
            for k in ['estabelecimento','municipio','uf','fonte']:
                falta(ano[k],p+'preencha '+k+'.')
            if y < 2017 or y > 2026:
                falta(ano['justificativa_matriz'],p+'ano fora do período das fontes fornecidas: registre a matriz e orientação aplicáveis.')
            if ano['situacao']=='Em curso':
                if any(ano['conceitos'].values()) or any(ano['participacao'].values()) or ano['ch_base'] or ano['ch_div'] or ano['aee']:
                    erros.append(p+'resultados anuais devem ficar vazios enquanto o ano estiver em curso; use a transferência.')
                continue
            for disc in BASE:
                v=ano['conceitos'][disc]
                falta(v,p+'informe o resultado de '+disc+'.')
                if len(v)>8: erros.append(p+'resultado muito longo em '+disc+'.')
                if v=='FC' and not ano['relatorio_fc']: erros.append(p+'FC exige confirmação do relatório pedagógico anual anexo.')
            componentes=esperados(ano)
            for disc in DIV:
                v=ano['participacao'][disc]
                if v not in ['P','-']: erros.append(p+'parte diversificada deve usar P ou traço: '+disc+'.')
                if componentes is not None and disc not in componentes and v=='P' and not ano['justificativa_matriz'].strip():
                    erros.append(p+disc+' diverge do anexo; informe a orientação/documento que fundamenta o registro.')
            if ano['modalidade']=='Complementação extracurricular' and y>=2026:
                avisos.append(p+'Art. 17 e Anexo VII divergem entre Acompanhamento Pedagógico e Práticas de Estudo. Conferir orientação da SME.')
                falta(ano['justificativa_matriz'], p+'registre a orientação adotada para a divergência do Anexo VII.')
            for campo in ['base','div']:
                try:
                    n=decimal(ano['ch_'+campo])
                    if campo=='base' and n==0: raise ValueError()
                except ValueError: erros.append(p+'carga '+campo+' inválida.')
                if ano['unidade_'+campo] not in ['H/A','H']: erros.append(p+'unidade inválida.')
            try: total(ano)
            except ValueError: erros.append(p+'não foi possível somar as cargas: confira valores, unidades e duração da aula.')
            if ano['ch_religioso']:
                if not re.fullmatch(r'\d+(?:[.,]\d+)?\s*(?:H/A|H)',ano['ch_religioso'].upper()):
                    erros.append(p+'carga de Ensino Religioso deve conter valor e unidade H ou H/A.')
            if y>=2026 and ano['modalidade'] in ['APC','Complementação extracurricular']:
                avisos.append(p+'carga anual de APC/CE depende da data de implementação (arts. 16 e 18).')
        if not ativos: erros.append('Informe pelo menos um ano concluído ou em curso.')
        anos_letivos=[int(x['ano_letivo']) for x in ativos if str(x['ano_letivo']).isdigit()]
        if anos_letivos!=sorted(set(anos_letivos)): erros.append('Os anos letivos devem ser distintos e crescentes; trajetórias especiais exigem análise documental.')
        t=d['transferencia']
        if t['ativa']:
            dt=data(t['data'],'Transferência')
            if dt and emissao and dt>emissao: erros.append('Transferência não pode ser posterior à emissão.')
            correspondentes=[x for x in ativos if x['serie']==t['serie'] and x['situacao']=='Em curso']
            if len(correspondentes)!=1: erros.append('A transferência exige a série correspondente marcada Em curso.')
            elif dt and str(dt.year)!=str(correspondentes[0]['ano_letivo']): erros.append('Data da transferência diverge do ano letivo em curso.')
            falta(t['turma'],'Transferência: informe a turma.')
            try:
                dias,aus,comp=[decimal(t[k]) for k in ['dias','ausencias','compensadas']]
                if dias<=0 or comp>aus: raise ValueError()
                if not 0<=decimal(t['frequencia'])<=100: raise ValueError()
            except ValueError: erros.append('Transferência: confira dias, ausências, compensadas e frequência entre 0 e 100.')
            for disc, valores in t['conceitos'].items():
                if len(valores)!=3 or any(len(str(v))>8 for v in valores): erros.append('Transferência: resultados inválidos em '+disc+'.')
            avisos.append('Frequência transcrita do registro escolar; não calculada a partir de dias e ausências com unidades possivelmente diferentes.')
        elif any(x['situacao']=='Em curso' for x in ativos): erros.append('Preencha a transferência para a série Em curso.')
        if d['certificar']:
            correspondentes=[x for x in ativos if x['serie']==d['serie_certificada'] and x['situacao']=='Concluído' and str(x['ano_letivo'])==str(d['ano_certificado'])]
            if not correspondentes: erros.append('O certificado precisa corresponder a um ano concluído registrado.')
        if exigir_conferencia and not d['conferido']: erros.append('Confirme a conferência dos registros antes de emitir.')
        if d['demonstracao']: avisos.append('Exemplo fictício: o PDF será marcado SEM VALIDADE.')
    except (KeyError,TypeError,AttributeError) as exc:
        erros.append('Estrutura de dados incompleta ou inválida: '+str(exc))
    return list(dict.fromkeys(erros)),list(dict.fromkeys(avisos))

def exemplo():
    d=novo();d['demonstracao']=True;d['conferido']=True
    d['escola'].update(nome='ESCOLA MUNICIPAL EXEMPLO',ato='ATO FICTÍCIO - TESTE',endereco='RUA DE EXEMPLO, 100',bairro='CENTRO',municipio='LIMEIRA',cep='00000-000',telefone='(00) 0000-0000',email='exemplo@example.invalid',secretario='SECRETÁRIO EXEMPLO',diretor='DIRETOR EXEMPLO')
    d['aluno'].update(nome='ESTUDANTE FICTÍCIO PARA CONFERÊNCIA',ra='000000000-0',localidade='LIMEIRA',uf='SP',nacionalidade='BRASILEIRA',nascimento='2019-03-12',matricula_certidao='DOCUMENTO FICTÍCIO - SEM VALIDADE')
    a=d['anos'][0];a.update(situacao='Concluído',ano_letivo='2026',ch_base='1120',ch_div='80',estabelecimento=d['escola']['nome'],municipio='LIMEIRA',uf='SP',fonte='EXEMPLO: 28 h/a + 2 h/a por semana; 40 semanas fictícias.')
    a['conceitos']={k:'B' for k in BASE};a['participacao']={k:('P' if k==DIV[3] else '-') for k in DIV}
    d.update(certificar=True,serie_certificada=1,ano_certificado='2026',data_emissao='2026-12-18',observacoes='DOCUMENTO DE DEMONSTRAÇÃO. Dados fictícios, sem validade escolar.\nCargas usadas apenas no teste: 1.120 H/A + 80 H/A = 1.200 H/A. Não representam a vida escolar de um estudante real.')
    return d

"""PDF vetorial de duas páginas, sem XLS ou fontes externas. Usa logo_prefeitura.png se disponível."""
from io import BytesIO
from datetime import date
from xml.sax.saxutils import escape
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.lib.utils import ImageReader, simpleSplit

X_EDGES=[40.0, 41.024, 49.724, 58.423, 67.123, 75.823, 84.523, 93.223, 101.922, 110.622, 119.322, 128.022, 136.722, 145.421, 154.121, 162.821, 171.521, 180.221, 188.92, 197.62, 206.32, 215.02, 223.72, 232.419, 241.119, 249.819, 258.519, 267.219, 275.918, 284.618, 293.318, 302.018, 302.981, 311.681, 320.381, 329.081, 337.781, 346.48, 355.18, 363.88, 372.58, 381.28, 389.979, 398.679, 407.379, 416.079, 424.779, 433.478, 442.178, 450.878, 459.578, 468.278, 476.977, 485.677, 494.377, 503.077, 511.777, 520.476, 529.176, 537.876, 546.576, 555.276]
Y_EDGES=[0.0, 9.607, 19.215, 28.822, 38.43, 48.038, 58.56, 70.455, 83.265, 89.441, 101.794, 114.146, 126.499, 138.851, 151.204, 163.556, 175.909, 188.261, 196.496, 208.849, 221.201, 234.926, 247.965, 263.749, 276.101, 288.454, 300.806, 313.159, 325.511, 337.864, 350.216, 362.569, 387.96, 400.313, 412.665, 425.018, 437.37, 449.723, 462.075, 474.428, 486.78, 499.133, 511.485, 523.838, 540.994, 558.836, 571.189, 583.541, 589.031, 609.619, 622.658, 634.324, 641.873, 654.225, 659.715, 672.068, 684.42, 696.773, 709.125, 721.478, 733.83, 746.183, 751.673, 757.163, 769.058, 772.489, 784.384, 796.736, 803.599, 815.951, 822.814, 835.166, 847.519, 859.414, 871.08, 883.432, 895.785, 908.137, 920.49, 932.842, 945.195, 957.547, 969.9, 982.252, 994.605, 1006.957, 1019.31, 1031.205, 1043.1, 1054.995, 1065.975, 1076.863, 1087.752, 1098.64, 1109.529, 1120.417, 1131.306, 1142.194, 1153.083, 1163.971, 1174.86, 1185.748, 1196.637, 1207.525, 1218.414, 1229.394, 1241.289, 1250.119, 1261.785, 1270.615, 1282.281, 1291.111, 1303.006, 1314.672, 1322.221, 1334.116, 1345.782, 1357.448, 1370.716, 1382.382, 1391.212]
FILLS_0=[(40.0, 728.625, 1.024, 12.81, 0.753, 0.753, 0.753), (40.0, 710.096, 1.024, 12.353, 0.753, 0.753, 0.753), (49.724, 710.096, 8.7, 12.353, 0.753, 0.753, 0.753), (58.423, 710.096, 8.7, 12.353, 0.753, 0.753, 0.753), (67.123, 710.096, 8.7, 12.353, 0.753, 0.753, 0.753), (75.823, 710.096, 8.7, 12.353, 0.753, 0.753, 0.753), (84.523, 710.096, 8.7, 12.353, 0.753, 0.753, 0.753), (93.223, 710.096, 8.7, 12.353, 0.753, 0.753, 0.753), (101.922, 710.096, 8.7, 12.353, 0.753, 0.753, 0.753), (110.622, 710.096, 8.7, 12.353, 0.753, 0.753, 0.753), (119.322, 710.096, 8.7, 12.353, 0.753, 0.753, 0.753), (128.022, 710.096, 8.7, 12.353, 0.753, 0.753, 0.753), (136.722, 710.096, 8.7, 12.353, 0.753, 0.753, 0.753), (145.421, 710.096, 8.7, 12.353, 0.753, 0.753, 0.753), (154.121, 710.096, 8.7, 12.353, 0.753, 0.753, 0.753), (162.821, 710.096, 8.7, 12.353, 0.753, 0.753, 0.753), (171.521, 710.096, 8.7, 12.353, 0.753, 0.753, 0.753), (180.221, 710.096, 8.7, 12.353, 0.753, 0.753, 0.753), (188.92, 710.096, 8.7, 12.353, 0.753, 0.753, 0.753), (197.62, 710.096, 8.7, 12.353, 0.753, 0.753, 0.753), (206.32, 710.096, 8.7, 12.353, 0.753, 0.753, 0.753), (215.02, 710.096, 8.7, 12.353, 0.753, 0.753, 0.753), (223.72, 710.096, 8.7, 12.353, 0.753, 0.753, 0.753), (232.419, 710.096, 8.7, 12.353, 0.753, 0.753, 0.753), (241.119, 710.096, 8.7, 12.353, 0.753, 0.753, 0.753), (249.819, 710.096, 8.7, 12.353, 0.753, 0.753, 0.753), (258.519, 710.096, 8.7, 12.353, 0.753, 0.753, 0.753), (267.219, 710.096, 8.7, 12.353, 0.753, 0.753, 0.753), (275.918, 710.096, 8.7, 12.353, 0.753, 0.753, 0.753), (284.618, 710.096, 8.7, 12.353, 0.753, 0.753, 0.753), (293.318, 710.096, 8.7, 12.353, 0.753, 0.753, 0.753), (302.018, 710.096, 0.964, 12.353, 0.753, 0.753, 0.753), (302.981, 710.096, 8.7, 12.353, 0.753, 0.753, 0.753), (311.681, 710.096, 8.7, 12.353, 0.753, 0.753, 0.753), (320.381, 710.096, 8.7, 12.353, 0.753, 0.753, 0.753), (329.081, 710.096, 8.7, 12.353, 0.753, 0.753, 0.753), (337.781, 710.096, 8.7, 12.353, 0.753, 0.753, 0.753), (346.48, 710.096, 8.7, 12.353, 0.753, 0.753, 0.753), (355.18, 710.096, 8.7, 12.353, 0.753, 0.753, 0.753), (363.88, 710.096, 8.7, 12.353, 0.753, 0.753, 0.753), (372.58, 710.096, 8.7, 12.353, 0.753, 0.753, 0.753), (381.28, 710.096, 8.7, 12.353, 0.753, 0.753, 0.753), (389.979, 710.096, 8.7, 12.353, 0.753, 0.753, 0.753), (398.679, 710.096, 8.7, 12.353, 0.753, 0.753, 0.753), (407.379, 710.096, 8.7, 12.353, 0.753, 0.753, 0.753), (416.079, 710.096, 8.7, 12.353, 0.753, 0.753, 0.753), (424.779, 710.096, 8.7, 12.353, 0.753, 0.753, 0.753), (433.478, 710.096, 8.7, 12.353, 0.753, 0.753, 0.753), (442.178, 710.096, 8.7, 12.353, 0.753, 0.753, 0.753), (450.878, 710.096, 8.7, 12.353, 0.753, 0.753, 0.753), (476.977, 710.096, 8.7, 12.353, 0.588, 0.588, 0.588), (40.0, 660.686, 1.024, 12.352, 0.753, 0.753, 0.753), (40.0, 603.041, 1.024, 12.352, 0.753, 0.753, 0.753), (49.724, 603.041, 8.7, 12.352, 0.753, 0.753, 0.753), (40.0, 590.689, 1.024, 12.352, 0.753, 0.753, 0.753), (49.724, 590.689, 8.7, 12.352, 0.588, 0.588, 0.588), (302.018, 590.689, 0.964, 12.352, 0.588, 0.588, 0.588), (311.681, 590.689, 8.7, 12.352, 1.0, 1.0, 1.0), (40.0, 576.964, 1.024, 13.725, 0.753, 0.753, 0.753), (302.018, 576.964, 0.964, 13.725, 1.0, 1.0, 1.0), (302.018, 548.141, 0.964, 15.784, 0.753, 0.753, 0.753), (346.48, 548.141, 8.7, 15.784, 0.753, 0.753, 0.753), (398.679, 548.141, 8.7, 15.784, 0.753, 0.753, 0.753), (450.878, 548.141, 8.7, 15.784, 0.753, 0.753, 0.753), (503.077, 548.141, 8.7, 15.784, 0.753, 0.753, 0.753), (302.018, 535.789, 0.964, 12.353, 1.0, 1.0, 1.0), (346.48, 535.789, 8.7, 12.353, 1.0, 1.0, 1.0), (398.679, 535.789, 8.7, 12.353, 1.0, 1.0, 1.0), (450.878, 535.789, 8.7, 12.353, 1.0, 1.0, 1.0), (503.077, 535.789, 8.7, 12.353, 1.0, 1.0, 1.0), (302.018, 523.436, 0.964, 12.353, 1.0, 1.0, 1.0), (346.48, 523.436, 8.7, 12.353, 1.0, 1.0, 1.0), (398.679, 523.436, 8.7, 12.353, 1.0, 1.0, 1.0), (450.878, 523.436, 8.7, 12.353, 1.0, 1.0, 1.0), (503.077, 523.436, 8.7, 12.353, 1.0, 1.0, 1.0), (302.018, 511.084, 0.964, 12.353, 1.0, 1.0, 1.0), (346.48, 511.084, 8.7, 12.353, 1.0, 1.0, 1.0), (398.679, 511.084, 8.7, 12.353, 1.0, 1.0, 1.0), (450.878, 511.084, 8.7, 12.353, 1.0, 1.0, 1.0), (503.077, 511.084, 8.7, 12.353, 1.0, 1.0, 1.0), (302.018, 498.731, 0.964, 12.353, 1.0, 1.0, 1.0), (346.48, 498.731, 8.7, 12.353, 1.0, 1.0, 1.0), (398.679, 498.731, 8.7, 12.353, 1.0, 1.0, 1.0), (450.878, 498.731, 8.7, 12.353, 1.0, 1.0, 1.0), (503.077, 498.731, 8.7, 12.353, 1.0, 1.0, 1.0), (302.018, 486.379, 0.964, 12.353, 1.0, 1.0, 1.0), (346.48, 486.379, 8.7, 12.353, 1.0, 1.0, 1.0), (398.679, 486.379, 8.7, 12.353, 1.0, 1.0, 1.0), (450.878, 486.379, 8.7, 12.353, 1.0, 1.0, 1.0), (503.077, 486.379, 8.7, 12.353, 1.0, 1.0, 1.0), (302.018, 474.026, 0.964, 12.353, 1.0, 1.0, 1.0), (346.48, 474.026, 8.7, 12.353, 1.0, 1.0, 1.0), (398.679, 474.026, 8.7, 12.353, 1.0, 1.0, 1.0), (450.878, 474.026, 8.7, 12.353, 1.0, 1.0, 1.0), (503.077, 474.026, 8.7, 12.353, 1.0, 1.0, 1.0), (302.018, 461.674, 0.964, 12.353, 1.0, 1.0, 1.0), (346.48, 461.674, 8.7, 12.353, 1.0, 1.0, 1.0), (398.679, 461.674, 8.7, 12.353, 1.0, 1.0, 1.0), (450.878, 461.674, 8.7, 12.353, 1.0, 1.0, 1.0), (503.077, 461.674, 8.7, 12.353, 1.0, 1.0, 1.0), (302.018, 449.321, 0.964, 12.353, 1.0, 1.0, 1.0), (346.48, 449.321, 8.7, 12.353, 1.0, 1.0, 1.0), (398.679, 449.321, 8.7, 12.353, 1.0, 1.0, 1.0), (450.878, 449.321, 8.7, 12.353, 1.0, 1.0, 1.0), (503.077, 449.321, 8.7, 12.353, 1.0, 1.0, 1.0), (40.0, 411.577, 1.024, 12.353, 0.753, 0.753, 0.753), (49.724, 411.577, 8.7, 12.353, 0.753, 0.753, 0.753), (58.423, 411.577, 8.7, 12.353, 0.753, 0.753, 0.753), (67.123, 411.577, 8.7, 12.353, 0.753, 0.753, 0.753), (75.823, 411.577, 8.7, 12.353, 0.753, 0.753, 0.753), (84.523, 411.577, 8.7, 12.353, 0.753, 0.753, 0.753), (93.223, 411.577, 8.7, 12.353, 0.753, 0.753, 0.753), (101.922, 411.577, 8.7, 12.353, 0.753, 0.753, 0.753), (110.622, 411.577, 8.7, 12.353, 0.753, 0.753, 0.753), (119.322, 411.577, 8.7, 12.353, 0.753, 0.753, 0.753), (128.022, 411.577, 8.7, 12.353, 0.753, 0.753, 0.753), (136.722, 411.577, 8.7, 12.353, 0.753, 0.753, 0.753), (145.421, 411.577, 8.7, 12.353, 0.753, 0.753, 0.753), (154.121, 411.577, 8.7, 12.353, 0.753, 0.753, 0.753), (162.821, 411.577, 8.7, 12.353, 0.753, 0.753, 0.753), (171.521, 411.577, 8.7, 12.353, 0.753, 0.753, 0.753), (180.221, 411.577, 8.7, 12.353, 0.753, 0.753, 0.753), (188.92, 411.577, 8.7, 12.353, 0.753, 0.753, 0.753), (197.62, 411.577, 8.7, 12.353, 0.753, 0.753, 0.753), (206.32, 411.577, 8.7, 12.353, 0.753, 0.753, 0.753), (215.02, 411.577, 8.7, 12.353, 0.753, 0.753, 0.753), (223.72, 411.577, 8.7, 12.353, 0.753, 0.753, 0.753), (232.419, 411.577, 8.7, 12.353, 0.753, 0.753, 0.753), (241.119, 411.577, 8.7, 12.353, 0.753, 0.753, 0.753), (249.819, 411.577, 8.7, 12.353, 0.753, 0.753, 0.753), (258.519, 411.577, 8.7, 12.353, 0.753, 0.753, 0.753), (267.219, 411.577, 8.7, 12.353, 0.753, 0.753, 0.753), (275.918, 411.577, 8.7, 12.353, 0.753, 0.753, 0.753), (284.618, 411.577, 8.7, 12.353, 0.753, 0.753, 0.753), (293.318, 411.577, 8.7, 12.353, 0.753, 0.753, 0.753), (302.018, 411.577, 0.964, 12.353, 0.753, 0.753, 0.753), (346.48, 411.577, 8.7, 12.353, 0.753, 0.753, 0.753), (398.679, 411.577, 8.7, 12.353, 0.753, 0.753, 0.753), (450.878, 411.577, 8.7, 12.353, 0.753, 0.753, 0.753), (503.077, 411.577, 8.7, 12.353, 0.753, 0.753, 0.753), (302.018, 288.052, 0.964, 12.352, 1.0, 1.0, 1.0), (346.48, 288.052, 8.7, 12.352, 1.0, 1.0, 1.0), (398.679, 288.052, 8.7, 12.352, 1.0, 1.0, 1.0), (450.878, 288.052, 8.7, 12.352, 1.0, 1.0, 1.0), (503.077, 288.052, 8.7, 12.352, 1.0, 1.0, 1.0), (40.0, 240.701, 1.024, 12.352, 0.753, 0.753, 0.753), (49.724, 240.701, 8.7, 12.352, 0.753, 0.753, 0.753), (40.0, 202.271, 1.024, 20.587, 0.753, 0.753, 0.753), (49.724, 202.271, 8.7, 20.587, 0.753, 0.753, 0.753), (302.018, 189.232, 0.964, 13.039, 0.588, 0.588, 0.588), (346.48, 189.232, 8.7, 13.039, 0.588, 0.588, 0.588), (398.679, 189.232, 8.7, 13.039, 0.588, 0.588, 0.588), (450.878, 189.232, 8.7, 13.039, 0.588, 0.588, 0.588), (503.077, 189.232, 8.7, 13.039, 0.588, 0.588, 0.588), (40.0, 157.665, 1.024, 12.352, 0.753, 0.753, 0.753), (49.724, 157.665, 8.7, 12.352, 0.753, 0.753, 0.753), (302.018, 157.665, 0.964, 12.352, 1.0, 1.0, 1.0), (346.48, 157.665, 8.7, 12.352, 1.0, 1.0, 1.0), (398.679, 157.665, 8.7, 12.352, 1.0, 1.0, 1.0), (450.878, 157.665, 8.7, 12.352, 1.0, 1.0, 1.0), (503.077, 157.665, 8.7, 12.352, 1.0, 1.0, 1.0), (40.0, 139.822, 1.024, 12.352, 0.753, 0.753, 0.753), (49.724, 139.822, 8.7, 12.352, 0.753, 0.753, 0.753)]
LINES_0=[(215.02, 802.282, 476.977, 802.282), (215.02, 792.675, 476.977, 792.675), (215.02, 783.067, 407.379, 783.067), (424.779, 783.067, 476.977, 783.067), (188.92, 773.46, 337.781, 773.46), (407.379, 773.46, 476.977, 773.46), (162.821, 763.852, 223.72, 763.852), (311.681, 763.852, 372.58, 763.852), (398.679, 763.852, 476.977, 763.852), (180.221, 753.33, 476.977, 753.33), (40.0, 741.435, 555.276, 741.435), (40.0, 728.625, 555.276, 728.625), (40.0, 722.449, 555.276, 722.449), (40.0, 710.096, 555.276, 710.096), (40.0, 697.744, 555.276, 697.744), (136.722, 685.391, 555.276, 685.391), (40.0, 673.039, 555.276, 673.039), (40.0, 660.686, 555.276, 660.686), (40.0, 648.334, 555.276, 648.334), (40.0, 635.981, 555.276, 635.981), (40.0, 623.629, 555.276, 623.629), (40.0, 615.394, 555.276, 615.394), (40.0, 603.041, 555.276, 603.041), (40.0, 590.689, 555.276, 590.689), (302.018, 563.925, 555.276, 563.925), (40.0, 535.789, 555.276, 535.789), (302.018, 548.141, 555.276, 548.141), (40.0, 523.436, 555.276, 523.436), (40.0, 511.084, 555.276, 511.084), (40.0, 498.731, 555.276, 498.731), (40.0, 486.379, 555.276, 486.379), (40.0, 474.026, 555.276, 474.026), (40.0, 461.674, 555.276, 461.674), (40.0, 449.321, 555.276, 449.321), (40.0, 423.93, 555.276, 423.93), (40.0, 411.577, 555.276, 411.577), (40.0, 399.225, 555.276, 399.225), (40.0, 386.872, 555.276, 386.872), (40.0, 374.52, 555.276, 374.52), (40.0, 362.167, 555.276, 362.167), (40.0, 349.815, 555.276, 349.815), (40.0, 337.462, 555.276, 337.462), (40.0, 325.11, 555.276, 325.11), (40.0, 312.757, 555.276, 312.757), (40.0, 300.405, 555.276, 300.405), (40.0, 288.052, 555.276, 288.052), (40.0, 253.054, 555.276, 253.054), (40.0, 240.701, 555.276, 240.701), (40.0, 228.349, 555.276, 228.349), (40.0, 222.859, 555.276, 222.859), (40.0, 202.271, 555.276, 202.271), (302.018, 189.232, 555.276, 189.232), (40.0, 177.566, 555.276, 177.566), (40.0, 170.017, 555.276, 170.017), (40.0, 157.665, 555.276, 157.665), (40.0, 152.175, 555.276, 152.175), (40.0, 139.822, 555.276, 139.822), (40.0, 127.47, 555.276, 127.47), (40.0, 115.117, 555.276, 115.117), (40.0, 102.765, 555.276, 102.765), (40.0, 90.412, 555.276, 90.412), (40.0, 78.06, 555.276, 78.06), (40.0, 65.707, 555.276, 65.707), (40.0, 65.707, 40.0, 152.175), (40.0, 157.665, 40.0, 170.017), (40.0, 177.566, 40.0, 222.859), (40.0, 228.349, 40.0, 253.054), (40.0, 288.052, 40.0, 615.394), (40.0, 623.629, 40.0, 722.449), (40.0, 728.625, 40.0, 741.435), (555.276, 65.707, 555.276, 152.175), (555.276, 157.665, 555.276, 170.017), (555.276, 177.566, 555.276, 222.859), (555.276, 228.349, 555.276, 253.054), (555.276, 288.052, 555.276, 615.394), (555.276, 623.629, 555.276, 722.449), (555.276, 728.625, 555.276, 741.435), (49.724, 139.822, 49.724, 152.175), (49.724, 157.665, 49.724, 170.017), (49.724, 202.271, 49.724, 222.859), (49.724, 240.701, 49.724, 253.054), (49.724, 288.052, 49.724, 300.405), (49.724, 411.577, 49.724, 461.674), (49.724, 590.689, 49.724, 615.394), (49.724, 660.686, 49.724, 673.039), (49.724, 710.096, 49.724, 722.449), (136.722, 65.707, 136.722, 139.822), (136.722, 673.039, 136.722, 697.744), (311.681, 590.689, 311.681, 603.041), (311.681, 673.039, 311.681, 697.744), (372.58, 673.039, 372.58, 697.744), (468.278, 673.039, 468.278, 697.744), (494.377, 673.039, 494.377, 697.744), (520.476, 673.039, 520.476, 697.744), (302.018, 157.665, 302.018, 170.017), (302.018, 177.566, 302.018, 202.271), (302.018, 228.349, 302.018, 240.701), (302.018, 288.052, 302.018, 423.93), (302.018, 449.321, 302.018, 603.041), (346.48, 157.665, 346.48, 170.017), (346.48, 177.566, 346.48, 202.271), (346.48, 228.349, 346.48, 240.701), (346.48, 288.052, 346.48, 423.93), (346.48, 449.321, 346.48, 563.925), (398.679, 157.665, 398.679, 170.017), (398.679, 177.566, 398.679, 202.271), (398.679, 228.349, 398.679, 240.701), (398.679, 288.052, 398.679, 423.93), (398.679, 449.321, 398.679, 563.925), (450.878, 157.665, 450.878, 170.017), (450.878, 177.566, 450.878, 202.271), (450.878, 228.349, 450.878, 240.701), (450.878, 288.052, 450.878, 423.93), (450.878, 449.321, 450.878, 563.925), (503.077, 157.665, 503.077, 170.017), (503.077, 177.566, 503.077, 202.271), (503.077, 228.349, 503.077, 240.701), (503.077, 288.052, 503.077, 423.93), (503.077, 449.321, 503.077, 563.925), (84.523, 65.707, 84.523, 139.822), (363.88, 65.707, 363.88, 139.822), (476.977, 65.707, 476.977, 139.822)]
TEXTS_0=[('ESCOLA:', 136.722, 802.282, 78.298, 9.607, 7.32, 1, 0, 0, 4.7), ('ATO DE CRIAÇÃO: ', 136.722, 792.675, 418.554, 9.607, 7.32, 0, 0, 0, 4.7), ('ENDEREÇO:', 136.722, 783.067, 78.298, 9.607, 7.32, 0, 0, 0, 4.7), ('BAIRRO:', 136.722, 773.46, 52.199, 9.608, 7.32, 0, 0, 0, 4.7), ('MUNICÍPIO:', 337.781, 773.46, 69.598, 9.608, 7.32, 0, 0, 0, 4.7), ('CEP:', 136.722, 763.852, 26.099, 9.608, 7.32, 0, 1, 0, 4.7), ('TELEFONES: ', 232.419, 763.852, 79.262, 9.608, 7.32, 0, 1, 0, 4.7), ('E-MAIL:', 136.722, 753.33, 43.499, 10.523, 7.32, 0, 1, 0, 4.7), ('SECRETARIA MUNICIPAL DE EDUCAÇÃO DE LIMEIRA/SP', 40.0, 741.435, 515.276, 11.895, 9.15, 1, 1, 0, 4.7), ('HISTÓRICO ESCOLAR', 40.0, 728.625, 515.276, 12.81, 10.065, 1, 1, 0, 4.7), ('1.1', 40.0, 710.096, 9.724, 12.353, 8.235, 0, 1, 0, 4.7), ('DADOS  DO  ESTUDANTE', 49.724, 710.096, 401.154, 12.353, 8.235, 1, 0, 0, 4.7), ('RA', 450.878, 710.096, 26.099, 12.353, 8.235, 1, 1, 0, 4.7), ('NOME DO ALUNO:', 40.0, 697.744, 70.622, 12.353, 8.235, 1, 0, 0, 4.7), ('RA ESCOLAR:', 372.58, 697.744, 69.598, 12.353, 7.777, 1, 0, 0, 4.7), ('NASCIMENTO:', 40.0, 673.039, 96.722, 24.705, 8.235, 1, 1, 0, 4.7), ('LOCALIDADE', 136.722, 685.391, 174.96, 12.353, 7.32, 1, 1, 0, 4.7), ('ESTADO', 311.681, 685.391, 60.899, 12.353, 7.32, 1, 1, 0, 4.7), ('NACIONALIDADE', 372.58, 685.391, 95.698, 12.353, 7.32, 1, 1, 0, 4.7), ('DIA', 468.278, 685.391, 26.099, 12.353, 7.32, 1, 1, 0, 4.7), ('MÊS', 494.377, 685.391, 26.099, 12.353, 7.32, 1, 1, 0, 4.7), ('ANO', 520.476, 685.391, 34.799, 12.353, 7.32, 1, 1, 0, 4.7), ('1.2', 40.0, 660.686, 9.724, 12.352, 8.235, 0, 1, 0, 4.7), ('CERTIDÃO DE NASCIMENTO ', 49.724, 660.686, 139.197, 12.352, 9.15, 0, 1, 0, 4.7), ('LIVRO: ', 337.781, 660.686, 69.598, 12.352, 9.15, 0, 0, 0, 4.7), ('(SUB) DISTRITO:', 40.0, 648.334, 61.922, 12.352, 9.15, 0, 1, 0, 4.7), ('CIDADE:', 232.419, 648.334, 43.499, 12.352, 9.15, 0, 1, 0, 4.7), ('ESTADO:', 416.079, 648.334, 43.499, 12.352, 9.15, 0, 1, 0, 4.7), ('CERTIDÃO NOVA - MATRÍCULA:', 40.0, 635.981, 131.521, 12.352, 9.15, 0, 0, 0, 4.7), ('ESTRANGEIRO - DOCUMENTO: ', 40.0, 623.629, 131.521, 12.352, 9.15, 0, 0, 0, 4.7), ('2', 40.0, 603.041, 9.724, 12.352, 8.235, 0, 1, 0, 4.7), ('RESULTADO DOS ESTUDOS REALIZADOS NO ENSINO FUNDAMENTAL', 49.724, 603.041, 505.552, 12.352, 9.15, 1, 1, 0, 4.7), ('2.1', 40.0, 590.689, 9.724, 12.352, 8.235, 0, 1, 0, 4.7), ('2.2', 302.018, 590.689, 9.663, 12.352, 9.15, 0, 1, 0, 4.7), ('ESCOLARIDADE', 311.681, 590.689, 243.594, 12.352, 9.15, 1, 1, 0, 4.7), ('CURRÍCULO', 40.0, 576.964, 262.018, 13.725, 8, 1, 0, 0, 4.7), ('Lei Federal n° 9394/96, art. 26; Deliberação CME nº 02/2016; Resolução SME nº 11/2016; Resolução CNE/CP nº 02/2017; Resolução SME nº 06/2020;Resolução CNE/CEB nº 01/2022; Lei nº 14.640/2023; Resolução CNE/CEB nº 02/ 2025; Resolução CNE/CEB nº 07/25;Decreto Municipal nº 405/2022; Resolução SME nº 03/2026', 40.0, 548.141, 262.018, 28.823, 5.3, 0, 0, 1, 4.7), ('Anos Iniciais', 302.018, 563.925, 253.258, 26.764, 9.15, 1, 1, 0, 4.7), ('1º Ano', 302.018, 548.141, 44.463, 15.784, 8.235, 1, 1, 0, 4.7), ('2º Ano', 346.48, 548.141, 52.199, 15.784, 8.235, 1, 1, 0, 4.7), ('3º Ano', 398.679, 548.141, 52.199, 15.784, 8.235, 1, 1, 0, 4.7), ('4º Ano', 450.878, 548.141, 52.199, 15.784, 8.235, 1, 1, 0, 4.7), ('5º Ano', 503.077, 548.141, 52.199, 15.784, 8.235, 1, 1, 0, 4.7), ('LÍNGUA PORTUGUESA', 40.0, 535.789, 262.018, 12.353, 9.15, 0, 0, 0, 4.7), ('GEOGRAFIA', 40.0, 523.436, 262.018, 12.353, 9.15, 0, 0, 0, 4.7), ('MATEMÁTICA', 40.0, 511.084, 262.018, 12.353, 9.15, 0, 0, 0, 4.7), ('CIÊNCIAS', 40.0, 498.731, 262.018, 12.353, 9.15, 0, 0, 0, 4.7), ('HISTÓRIA', 40.0, 486.379, 262.018, 12.353, 9.15, 0, 0, 0, 4.7), ('ED. FÍSICA', 40.0, 474.026, 262.018, 12.353, 9.15, 0, 0, 0, 4.7), ('ARTE', 40.0, 461.674, 262.018, 12.353, 9.15, 0, 0, 0, 4.7), ('2.3', 40.0, 449.321, 9.724, 12.353, 9.15, 0, 1, 0, 4.7), ('CARGA HORÁRIA', 49.724, 449.321, 252.294, 12.353, 9.15, 1, 0, 0, 4.7), ('2.4', 40.0, 423.93, 9.724, 25.391, 9.15, 0, 1, 1, 4.7), ('Flexibilização Curricular (FC): nomenclatura que deve ser utilizada para o estudante da educação especial cuja avaliação pedagógica identificou necessidade significativa de adequação curricular e diante disso o conteúdo trabalhado foi compatível aos seus processos de aprendizagem e desenvolvimento e não ao previsto no currículo da rede municipal de ensino, no seu ano de escolaridade. Deverá ser anexado relatório pedagógico anual.', 49.724, 423.93, 505.552, 25.391, 7.32, 0, 0, 1, 4.7), ('3', 40.0, 411.577, 9.724, 12.353, 8.235, 0, 1, 0, 4.7), ('PARTE DIVERSIFICADA ', 49.724, 411.577, 252.294, 12.353, 9.15, 1, 0, 0, 4.7), ('1º Ano', 302.018, 411.577, 44.463, 12.353, 8.235, 1, 1, 0, 4.7), ('2º Ano', 346.48, 411.577, 52.199, 12.353, 8.235, 1, 1, 0, 4.7), ('3º Ano', 398.679, 411.577, 52.199, 12.353, 8.235, 1, 1, 0, 4.7), ('4º Ano', 450.878, 411.577, 52.199, 12.353, 8.235, 1, 1, 0, 4.7), ('5º Ano', 503.077, 411.577, 52.199, 12.353, 8.235, 1, 1, 0, 4.7), ('EIXO INTELECTUAL', 40.0, 399.225, 262.018, 12.353, 9.15, 0, 0, 0, 4.7), ('EIXO ESPORTIVO', 40.0, 386.872, 262.018, 12.353, 9.15, 0, 0, 0, 4.7), ('EIXO CULTURAL', 40.0, 374.52, 262.018, 12.353, 9.15, 0, 0, 0, 4.7), ('LINGUAGENS E TECNOLOGIAS', 40.0, 362.167, 262.018, 12.353, 9.15, 0, 0, 0, 4.7), ('ACOMPANHAMENTO PEDAGÓGICO', 40.0, 349.815, 262.018, 12.353, 9.15, 0, 0, 0, 4.7), ('PRÁTICAS EXPERIMENTAIS E DE TUTORIA DE ESTUDO', 40.0, 337.462, 262.018, 12.353, 9.15, 0, 0, 0, 4.7), ('PRÁTICAS DE ESTUDO', 40.0, 325.11, 262.018, 12.353, 9.15, 0, 0, 0, 4.7), ('LINGUAGENS ', 40.0, 312.757, 262.018, 12.353, 9.15, 0, 0, 0, 4.7), ('ESPORTE E EDUCAÇÃO DO MOVIMENTO', 40.0, 300.405, 262.018, 12.353, 9.15, 0, 0, 0, 4.7), ('3.1', 40.0, 288.052, 9.724, 12.352, 9.15, 0, 1, 0, 4.7), ('CARGA HORÁRIA', 49.724, 288.052, 252.294, 12.352, 9.15, 1, 0, 0, 4.7), ('OBS: As escolas de atendimento integral deverão considerar os eixos intelectual, esportivo e cultural até o ano de 2025. A partir do ano de 2026,  para preenchimento deste campo da Parte Diversificada, considerar   os anexos da Resolução SME nº 03/26 que trata da Matriz Curricular. Os campos de disciplinas que não correspondem ao modelo de atendimento adotado pela escola deverão ser preenchido com traço. Para o estudante que frequentou a parte diversificada, indicar P de participação.', 40.0, 253.054, 515.276, 34.999, 6.405, 0, 0, 1, 4.7), ('4', 40.0, 240.701, 9.724, 12.352, 7.32, 0, 1, 0, 4.7), ('ENSINO RELIGIOSO (art.33-LDB e Deliberação CME nº 02/2016)', 49.724, 240.701, 505.552, 12.352, 7.32, 1, 0, 0, 4.7), ('CARGA HORÁRIA', 40.0, 228.349, 262.018, 12.352, 9.15, 0, 0, 0, 4.7), ('5', 40.0, 202.271, 9.724, 20.587, 8.235, 0, 1, 0, 4.7), ('EDUCAÇÃO ESPECIAL- ATENDIMENTO EDUCACIONAL ESPECIALIZADO', 49.724, 202.271, 505.552, 20.587, 8, 1, 0, 0, 4.7), ('Decreto Nº 12.686/2025- Indicação Cme Nº02/2023 -Decreto Municipal Nº 23/2026', 49.724, 202.271, 505.552, 20.587, 5.4, 0, 0, 2, 4.7), ('Indicar a sigla AEE ( Atendimento Educacional Especializado) para o estudante que frequentou esse tipo de atendimento no respectivo ano.', 40.0, 177.566, 262.018, 24.705, 6.405, 0, 0, 1, 4.7), ('1º ano', 302.018, 189.232, 44.463, 13.039, 9.15, 1, 1, 1, 4.7), ('2º ano', 346.48, 189.232, 52.199, 13.039, 9.15, 1, 1, 1, 4.7), ('3º ano', 398.679, 189.232, 52.199, 13.039, 9.15, 1, 1, 1, 4.7), ('4º ano', 450.878, 189.232, 52.199, 13.039, 9.15, 1, 1, 1, 4.7), ('5º ano', 503.077, 189.232, 52.199, 13.039, 9.15, 1, 1, 1, 4.7), ('6', 40.0, 157.665, 9.724, 12.352, 8.235, 0, 1, 0, 4.7), ('TOTAL DA CARGA HORÁRIA (CAMPO 2 + CAMPO 3)', 49.724, 157.665, 252.294, 12.352, 9.15, 1, 0, 0, 4.7), ('7', 40.0, 139.822, 9.724, 12.352, 8.235, 0, 1, 0, 4.7), ('    ESTUDOS REALIZADOS', 49.724, 139.822, 505.552, 12.352, 9.15, 0, 1, 0, 4.7), ('ANO', 40.0, 127.47, 44.523, 12.352, 9.15, 1, 1, 0, 4.7), ('CICLO/ANO', 84.523, 127.47, 52.199, 12.352, 8.235, 1, 1, 0, 4.7), ('ESTABELECIMENTO', 136.722, 127.47, 227.158, 12.352, 9.15, 1, 1, 0, 4.7), ('MUNICÍPIO', 363.88, 127.47, 113.097, 12.352, 9.15, 1, 1, 0, 4.7), ('ESTADO', 476.977, 127.47, 78.298, 12.352, 9.15, 1, 1, 0, 4.7)]
FILLS_63=[(40.0, 799.995, 1.024, 11.895, 0.753, 0.753, 0.753), (49.724, 799.995, 8.7, 11.895, 0.753, 0.753, 0.753), (40.0, 796.564, 1.024, 3.431, 1.0, 1.0, 1.0), (41.024, 796.564, 8.7, 3.431, 1.0, 1.0, 1.0), (49.724, 796.564, 8.7, 3.431, 1.0, 1.0, 1.0), (58.423, 796.564, 8.7, 3.431, 1.0, 1.0, 1.0), (67.123, 796.564, 8.7, 3.431, 1.0, 1.0, 1.0), (75.823, 796.564, 8.7, 3.431, 1.0, 1.0, 1.0), (84.523, 796.564, 8.7, 3.431, 1.0, 1.0, 1.0), (93.223, 796.564, 8.7, 3.431, 1.0, 1.0, 1.0), (101.922, 796.564, 8.7, 3.431, 1.0, 1.0, 1.0), (110.622, 796.564, 8.7, 3.431, 1.0, 1.0, 1.0), (119.322, 796.564, 8.7, 3.431, 1.0, 1.0, 1.0), (128.022, 796.564, 8.7, 3.431, 1.0, 1.0, 1.0), (136.722, 796.564, 8.7, 3.431, 1.0, 1.0, 1.0), (145.421, 796.564, 8.7, 3.431, 1.0, 1.0, 1.0), (154.121, 796.564, 8.7, 3.431, 1.0, 1.0, 1.0), (162.821, 796.564, 8.7, 3.431, 1.0, 1.0, 1.0), (171.521, 796.564, 8.7, 3.431, 1.0, 1.0, 1.0), (180.221, 796.564, 8.7, 3.431, 1.0, 1.0, 1.0), (188.92, 796.564, 8.7, 3.431, 1.0, 1.0, 1.0), (197.62, 796.564, 8.7, 3.431, 1.0, 1.0, 1.0), (206.32, 796.564, 8.7, 3.431, 1.0, 1.0, 1.0), (215.02, 796.564, 8.7, 3.431, 1.0, 1.0, 1.0), (223.72, 796.564, 8.7, 3.431, 1.0, 1.0, 1.0), (232.419, 796.564, 8.7, 3.431, 1.0, 1.0, 1.0), (241.119, 796.564, 8.7, 3.431, 1.0, 1.0, 1.0), (249.819, 796.564, 8.7, 3.431, 1.0, 1.0, 1.0), (258.519, 796.564, 8.7, 3.431, 1.0, 1.0, 1.0), (267.219, 796.564, 8.7, 3.431, 1.0, 1.0, 1.0), (275.918, 796.564, 8.7, 3.431, 1.0, 1.0, 1.0), (284.618, 796.564, 8.7, 3.431, 1.0, 1.0, 1.0), (293.318, 796.564, 8.7, 3.431, 1.0, 1.0, 1.0), (302.018, 796.564, 0.964, 3.431, 1.0, 1.0, 1.0), (302.981, 796.564, 8.7, 3.431, 1.0, 1.0, 1.0), (311.681, 796.564, 8.7, 3.431, 1.0, 1.0, 1.0), (320.381, 796.564, 8.7, 3.431, 1.0, 1.0, 1.0), (329.081, 796.564, 8.7, 3.431, 1.0, 1.0, 1.0), (337.781, 796.564, 8.7, 3.431, 1.0, 1.0, 1.0), (346.48, 796.564, 8.7, 3.431, 1.0, 1.0, 1.0), (355.18, 796.564, 8.7, 3.431, 1.0, 1.0, 1.0), (363.88, 796.564, 8.7, 3.431, 1.0, 1.0, 1.0), (372.58, 796.564, 8.7, 3.431, 1.0, 1.0, 1.0), (381.28, 796.564, 8.7, 3.431, 1.0, 1.0, 1.0), (389.979, 796.564, 8.7, 3.431, 1.0, 1.0, 1.0), (398.679, 796.564, 8.7, 3.431, 1.0, 1.0, 1.0), (407.379, 796.564, 8.7, 3.431, 1.0, 1.0, 1.0), (416.079, 796.564, 8.7, 3.431, 1.0, 1.0, 1.0), (424.779, 796.564, 8.7, 3.431, 1.0, 1.0, 1.0), (433.478, 796.564, 8.7, 3.431, 1.0, 1.0, 1.0), (442.178, 796.564, 8.7, 3.431, 1.0, 1.0, 1.0), (450.878, 796.564, 8.7, 3.431, 1.0, 1.0, 1.0), (459.578, 796.564, 8.7, 3.431, 1.0, 1.0, 1.0), (468.278, 796.564, 8.7, 3.431, 1.0, 1.0, 1.0), (476.977, 796.564, 8.7, 3.431, 1.0, 1.0, 1.0), (485.677, 796.564, 8.7, 3.431, 1.0, 1.0, 1.0), (494.377, 796.564, 8.7, 3.431, 1.0, 1.0, 1.0), (503.077, 796.564, 8.7, 3.431, 1.0, 1.0, 1.0), (511.777, 796.564, 8.7, 3.431, 1.0, 1.0, 1.0), (520.476, 796.564, 8.7, 3.431, 1.0, 1.0, 1.0), (529.176, 796.564, 8.7, 3.431, 1.0, 1.0, 1.0), (537.876, 796.564, 8.7, 3.431, 1.0, 1.0, 1.0), (546.576, 796.564, 8.7, 3.431, 1.0, 1.0, 1.0), (40.0, 784.669, 1.024, 11.895, 0.753, 0.753, 0.753), (49.724, 784.669, 8.7, 11.895, 0.753, 0.753, 0.753), (40.0, 709.639, 1.024, 11.895, 0.753, 0.753, 0.753), (49.724, 709.639, 8.7, 11.895, 0.753, 0.753, 0.753), (346.48, 709.639, 8.7, 11.895, 0.588, 0.588, 0.588), (416.079, 709.639, 8.7, 11.895, 0.588, 0.588, 0.588), (485.677, 709.639, 8.7, 11.895, 0.588, 0.588, 0.588), (346.48, 697.972, 8.7, 11.666, 1.0, 1.0, 1.0), (416.079, 697.972, 8.7, 11.666, 1.0, 1.0, 1.0), (485.677, 697.972, 8.7, 11.666, 1.0, 1.0, 1.0), (346.48, 685.62, 8.7, 12.352, 1.0, 1.0, 1.0), (416.079, 685.62, 8.7, 12.352, 1.0, 1.0, 1.0), (485.677, 685.62, 8.7, 12.352, 1.0, 1.0, 1.0), (346.48, 673.267, 8.7, 12.352, 1.0, 1.0, 1.0), (416.079, 673.267, 8.7, 12.352, 1.0, 1.0, 1.0), (485.677, 673.267, 8.7, 12.352, 1.0, 1.0, 1.0), (346.48, 660.915, 8.7, 12.352, 1.0, 1.0, 1.0), (416.079, 660.915, 8.7, 12.352, 1.0, 1.0, 1.0), (485.677, 660.915, 8.7, 12.352, 1.0, 1.0, 1.0), (346.48, 648.562, 8.7, 12.352, 1.0, 1.0, 1.0), (416.079, 648.562, 8.7, 12.352, 1.0, 1.0, 1.0), (485.677, 648.562, 8.7, 12.352, 1.0, 1.0, 1.0), (346.48, 636.21, 8.7, 12.352, 1.0, 1.0, 1.0), (416.079, 636.21, 8.7, 12.352, 1.0, 1.0, 1.0), (485.677, 636.21, 8.7, 12.352, 1.0, 1.0, 1.0), (346.48, 623.857, 8.7, 12.352, 1.0, 1.0, 1.0), (416.079, 623.857, 8.7, 12.352, 1.0, 1.0, 1.0), (485.677, 623.857, 8.7, 12.352, 1.0, 1.0, 1.0), (346.48, 611.505, 8.7, 12.352, 1.0, 1.0, 1.0), (40.0, 599.152, 1.024, 12.352, 0.753, 0.753, 0.753), (346.48, 586.8, 8.7, 12.352, 1.0, 1.0, 1.0), (416.079, 586.8, 8.7, 12.352, 1.0, 1.0, 1.0), (485.677, 586.8, 8.7, 12.352, 1.0, 1.0, 1.0), (346.48, 574.447, 8.7, 12.352, 1.0, 1.0, 1.0), (355.18, 574.447, 8.7, 12.352, 1.0, 1.0, 1.0), (363.88, 574.447, 8.7, 12.352, 1.0, 1.0, 1.0), (372.58, 574.447, 8.7, 12.352, 1.0, 1.0, 1.0), (381.28, 574.447, 8.7, 12.352, 1.0, 1.0, 1.0), (389.979, 574.447, 8.7, 12.352, 1.0, 1.0, 1.0), (398.679, 574.447, 8.7, 12.352, 1.0, 1.0, 1.0), (407.379, 574.447, 8.7, 12.352, 1.0, 1.0, 1.0), (416.079, 574.447, 8.7, 12.352, 1.0, 1.0, 1.0), (424.779, 574.447, 8.7, 12.352, 1.0, 1.0, 1.0), (433.478, 574.447, 8.7, 12.352, 1.0, 1.0, 1.0), (442.178, 574.447, 8.7, 12.352, 1.0, 1.0, 1.0), (450.878, 574.447, 8.7, 12.352, 1.0, 1.0, 1.0), (459.578, 574.447, 8.7, 12.352, 1.0, 1.0, 1.0), (468.278, 574.447, 8.7, 12.352, 1.0, 1.0, 1.0), (476.977, 574.447, 8.7, 12.352, 1.0, 1.0, 1.0), (485.677, 574.447, 8.7, 12.352, 1.0, 1.0, 1.0), (494.377, 574.447, 8.7, 12.352, 1.0, 1.0, 1.0), (503.077, 574.447, 8.7, 12.352, 1.0, 1.0, 1.0), (511.777, 574.447, 8.7, 12.352, 1.0, 1.0, 1.0), (520.476, 574.447, 8.7, 12.352, 1.0, 1.0, 1.0), (529.176, 574.447, 8.7, 12.352, 1.0, 1.0, 1.0), (537.876, 574.447, 8.7, 12.352, 1.0, 1.0, 1.0), (546.576, 574.447, 8.7, 12.352, 1.0, 1.0, 1.0), (346.48, 562.095, 8.7, 12.352, 1.0, 1.0, 1.0), (355.18, 562.095, 8.7, 12.352, 1.0, 1.0, 1.0), (363.88, 562.095, 8.7, 12.352, 1.0, 1.0, 1.0), (372.58, 562.095, 8.7, 12.352, 1.0, 1.0, 1.0), (381.28, 562.095, 8.7, 12.352, 1.0, 1.0, 1.0), (389.979, 562.095, 8.7, 12.352, 1.0, 1.0, 1.0), (398.679, 562.095, 8.7, 12.352, 1.0, 1.0, 1.0), (407.379, 562.095, 8.7, 12.352, 1.0, 1.0, 1.0), (416.079, 562.095, 8.7, 12.352, 1.0, 1.0, 1.0), (424.779, 562.095, 8.7, 12.352, 1.0, 1.0, 1.0), (433.478, 562.095, 8.7, 12.352, 1.0, 1.0, 1.0), (442.178, 562.095, 8.7, 12.352, 1.0, 1.0, 1.0), (450.878, 562.095, 8.7, 12.352, 1.0, 1.0, 1.0), (459.578, 562.095, 8.7, 12.352, 1.0, 1.0, 1.0), (468.278, 562.095, 8.7, 12.352, 1.0, 1.0, 1.0), (476.977, 562.095, 8.7, 12.352, 1.0, 1.0, 1.0), (485.677, 562.095, 8.7, 12.352, 1.0, 1.0, 1.0), (494.377, 562.095, 8.7, 12.352, 1.0, 1.0, 1.0), (503.077, 562.095, 8.7, 12.352, 1.0, 1.0, 1.0), (511.777, 562.095, 8.7, 12.352, 1.0, 1.0, 1.0), (520.476, 562.095, 8.7, 12.352, 1.0, 1.0, 1.0), (529.176, 562.095, 8.7, 12.352, 1.0, 1.0, 1.0), (537.876, 562.095, 8.7, 12.352, 1.0, 1.0, 1.0), (546.576, 562.095, 8.7, 12.352, 1.0, 1.0, 1.0), (346.48, 549.742, 8.7, 12.352, 1.0, 1.0, 1.0), (416.079, 549.742, 8.7, 12.352, 1.0, 1.0, 1.0), (485.677, 549.742, 8.7, 12.352, 1.0, 1.0, 1.0), (346.48, 537.847, 8.7, 11.895, 1.0, 1.0, 1.0), (416.079, 537.847, 8.7, 11.895, 1.0, 1.0, 1.0), (485.677, 537.847, 8.7, 11.895, 1.0, 1.0, 1.0), (346.48, 525.952, 8.7, 11.895, 1.0, 1.0, 1.0), (416.079, 525.952, 8.7, 11.895, 1.0, 1.0, 1.0), (485.677, 525.952, 8.7, 11.895, 1.0, 1.0, 1.0), (40.0, 503.077, 1.024, 10.98, 0.753, 0.753, 0.753), (49.724, 503.077, 8.7, 10.98, 0.753, 0.753, 0.753), (40.0, 492.189, 1.024, 10.889, 1.0, 1.0, 1.0), (40.0, 481.3, 1.024, 10.889, 1.0, 1.0, 1.0), (40.0, 470.412, 1.024, 10.889, 1.0, 1.0, 1.0), (40.0, 459.523, 1.024, 10.889, 1.0, 1.0, 1.0), (40.0, 448.635, 1.024, 10.889, 1.0, 1.0, 1.0), (40.0, 437.746, 1.024, 10.889, 1.0, 1.0, 1.0), (40.0, 426.858, 1.024, 10.889, 1.0, 1.0, 1.0), (40.0, 415.969, 1.024, 10.889, 1.0, 1.0, 1.0), (40.0, 405.081, 1.024, 10.889, 1.0, 1.0, 1.0), (40.0, 394.192, 1.024, 10.889, 1.0, 1.0, 1.0), (40.0, 383.304, 1.024, 10.889, 1.0, 1.0, 1.0), (40.0, 372.415, 1.024, 10.889, 1.0, 1.0, 1.0), (40.0, 361.527, 1.024, 10.889, 1.0, 1.0, 1.0), (40.0, 350.638, 1.024, 10.889, 1.0, 1.0, 1.0), (40.0, 339.658, 1.024, 10.98, 1.0, 1.0, 1.0), (41.024, 339.658, 8.7, 10.98, 1.0, 1.0, 1.0), (49.724, 339.658, 8.7, 10.98, 1.0, 1.0, 1.0), (58.423, 339.658, 8.7, 10.98, 1.0, 1.0, 1.0), (67.123, 339.658, 8.7, 10.98, 1.0, 1.0, 1.0), (75.823, 339.658, 8.7, 10.98, 1.0, 1.0, 1.0), (84.523, 339.658, 8.7, 10.98, 1.0, 1.0, 1.0), (93.223, 339.658, 8.7, 10.98, 1.0, 1.0, 1.0), (101.922, 339.658, 8.7, 10.98, 1.0, 1.0, 1.0), (110.622, 339.658, 8.7, 10.98, 1.0, 1.0, 1.0), (119.322, 339.658, 8.7, 10.98, 1.0, 1.0, 1.0), (128.022, 339.658, 8.7, 10.98, 1.0, 1.0, 1.0), (136.722, 339.658, 8.7, 10.98, 1.0, 1.0, 1.0), (145.421, 339.658, 8.7, 10.98, 1.0, 1.0, 1.0), (154.121, 339.658, 8.7, 10.98, 1.0, 1.0, 1.0), (162.821, 339.658, 8.7, 10.98, 1.0, 1.0, 1.0), (171.521, 339.658, 8.7, 10.98, 1.0, 1.0, 1.0), (180.221, 339.658, 8.7, 10.98, 1.0, 1.0, 1.0), (188.92, 339.658, 8.7, 10.98, 1.0, 1.0, 1.0), (197.62, 339.658, 8.7, 10.98, 1.0, 1.0, 1.0), (206.32, 339.658, 8.7, 10.98, 1.0, 1.0, 1.0), (215.02, 339.658, 8.7, 10.98, 1.0, 1.0, 1.0), (223.72, 339.658, 8.7, 10.98, 1.0, 1.0, 1.0), (232.419, 339.658, 8.7, 10.98, 1.0, 1.0, 1.0), (241.119, 339.658, 8.7, 10.98, 1.0, 1.0, 1.0), (249.819, 339.658, 8.7, 10.98, 1.0, 1.0, 1.0), (258.519, 339.658, 8.7, 10.98, 1.0, 1.0, 1.0), (267.219, 339.658, 8.7, 10.98, 1.0, 1.0, 1.0), (275.918, 339.658, 8.7, 10.98, 1.0, 1.0, 1.0), (284.618, 339.658, 8.7, 10.98, 1.0, 1.0, 1.0), (293.318, 339.658, 8.7, 10.98, 1.0, 1.0, 1.0), (302.018, 339.658, 0.964, 10.98, 1.0, 1.0, 1.0), (302.981, 339.658, 8.7, 10.98, 1.0, 1.0, 1.0), (311.681, 339.658, 8.7, 10.98, 1.0, 1.0, 1.0), (320.381, 339.658, 8.7, 10.98, 1.0, 1.0, 1.0), (329.081, 339.658, 8.7, 10.98, 1.0, 1.0, 1.0), (337.781, 339.658, 8.7, 10.98, 1.0, 1.0, 1.0), (346.48, 339.658, 8.7, 10.98, 1.0, 1.0, 1.0), (355.18, 339.658, 8.7, 10.98, 1.0, 1.0, 1.0), (363.88, 339.658, 8.7, 10.98, 1.0, 1.0, 1.0), (372.58, 339.658, 8.7, 10.98, 1.0, 1.0, 1.0), (381.28, 339.658, 8.7, 10.98, 1.0, 1.0, 1.0), (389.979, 339.658, 8.7, 10.98, 1.0, 1.0, 1.0), (398.679, 339.658, 8.7, 10.98, 1.0, 1.0, 1.0), (407.379, 339.658, 8.7, 10.98, 1.0, 1.0, 1.0), (416.079, 339.658, 8.7, 10.98, 1.0, 1.0, 1.0), (424.779, 339.658, 8.7, 10.98, 1.0, 1.0, 1.0), (433.478, 339.658, 8.7, 10.98, 1.0, 1.0, 1.0), (442.178, 339.658, 8.7, 10.98, 1.0, 1.0, 1.0), (450.878, 339.658, 8.7, 10.98, 1.0, 1.0, 1.0), (459.578, 339.658, 8.7, 10.98, 1.0, 1.0, 1.0), (468.278, 339.658, 8.7, 10.98, 1.0, 1.0, 1.0), (476.977, 339.658, 8.7, 10.98, 1.0, 1.0, 1.0), (485.677, 339.658, 8.7, 10.98, 1.0, 1.0, 1.0), (494.377, 339.658, 8.7, 10.98, 1.0, 1.0, 1.0), (503.077, 339.658, 8.7, 10.98, 1.0, 1.0, 1.0), (511.777, 339.658, 8.7, 10.98, 1.0, 1.0, 1.0), (520.476, 339.658, 8.7, 10.98, 1.0, 1.0, 1.0), (529.176, 339.658, 8.7, 10.98, 1.0, 1.0, 1.0), (537.876, 339.658, 8.7, 10.98, 1.0, 1.0, 1.0), (546.576, 339.658, 8.7, 10.98, 1.0, 1.0, 1.0), (40.0, 327.763, 1.024, 11.895, 0.753, 0.753, 0.753), (49.724, 327.763, 8.7, 11.895, 0.753, 0.753, 0.753), (40.0, 234.937, 1.024, 11.895, 0.753, 0.753, 0.753), (49.724, 234.937, 8.7, 11.895, 0.753, 0.753, 0.753)]
LINES_63=[(40.0, 811.89, 555.276, 811.89), (40.0, 799.995, 555.276, 799.995), (40.0, 796.564, 555.276, 796.564), (40.0, 784.669, 555.276, 784.669), (84.523, 772.316, 136.722, 772.316), (293.318, 772.316, 337.781, 772.316), (503.077, 772.316, 555.276, 772.316), (275.918, 753.101, 302.018, 753.101), (302.981, 753.101, 329.081, 753.101), (337.781, 753.101, 389.979, 753.101), (84.523, 733.886, 136.722, 733.886), (197.62, 733.886, 249.819, 733.886), (363.88, 733.886, 416.079, 733.886), (503.077, 733.886, 555.276, 733.886), (40.0, 721.534, 555.276, 721.534), (40.0, 709.639, 555.276, 709.639), (40.0, 697.972, 555.276, 697.972), (40.0, 685.62, 555.276, 685.62), (40.0, 673.267, 555.276, 673.267), (40.0, 660.915, 555.276, 660.915), (40.0, 648.562, 555.276, 648.562), (40.0, 636.21, 555.276, 636.21), (40.0, 623.857, 555.276, 623.857), (40.0, 611.505, 555.276, 611.505), (40.0, 599.152, 555.276, 599.152), (40.0, 586.8, 555.276, 586.8), (40.0, 574.447, 555.276, 574.447), (40.0, 562.095, 555.276, 562.095), (40.0, 549.742, 555.276, 549.742), (40.0, 537.847, 555.276, 537.847), (40.0, 525.952, 555.276, 525.952), (40.0, 514.057, 555.276, 514.057), (40.0, 503.077, 555.276, 503.077), (40.0, 492.189, 555.276, 492.189), (40.0, 481.3, 555.276, 481.3), (40.0, 470.412, 555.276, 470.412), (40.0, 459.523, 555.276, 459.523), (40.0, 448.635, 555.276, 448.635), (40.0, 437.746, 555.276, 437.746), (40.0, 426.858, 555.276, 426.858), (40.0, 415.969, 555.276, 415.969), (40.0, 405.081, 555.276, 405.081), (40.0, 394.192, 555.276, 394.192), (40.0, 383.304, 555.276, 383.304), (40.0, 372.415, 555.276, 372.415), (40.0, 361.527, 555.276, 361.527), (40.0, 350.638, 555.276, 350.638), (40.0, 339.658, 555.276, 339.658), (40.0, 327.763, 555.276, 327.763), (162.821, 307.267, 555.276, 307.267), (311.681, 286.771, 555.276, 286.771), (58.423, 266.047, 206.32, 266.047), (468.278, 266.047, 546.576, 266.047), (40.0, 254.38, 555.276, 254.38), (40.0, 246.832, 555.276, 246.832), (40.0, 234.937, 555.276, 234.937), (84.523, 211.604, 188.92, 211.604), (206.32, 211.604, 372.58, 211.604), (381.28, 211.604, 555.276, 211.604), (40.0, 177.841, 555.276, 177.841), (40.0, 177.841, 40.0, 246.832), (40.0, 254.38, 40.0, 339.658), (40.0, 350.638, 40.0, 514.057), (40.0, 525.952, 40.0, 611.505), (40.0, 623.857, 40.0, 721.534), (40.0, 784.669, 40.0, 796.564), (40.0, 799.995, 40.0, 811.89), (49.724, 234.937, 49.724, 246.832), (49.724, 327.763, 49.724, 339.658), (49.724, 503.077, 49.724, 514.057), (49.724, 709.639, 49.724, 721.534), (49.724, 784.669, 49.724, 796.564), (49.724, 799.995, 49.724, 811.89), (555.276, 177.841, 555.276, 246.832), (555.276, 254.38, 555.276, 339.658), (555.276, 350.638, 555.276, 503.077), (555.276, 525.952, 555.276, 611.505), (555.276, 623.857, 555.276, 721.534), (555.276, 784.669, 555.276, 796.564), (555.276, 799.995, 555.276, 811.89), (346.48, 525.952, 346.48, 599.152), (346.48, 623.857, 346.48, 721.534), (416.079, 525.952, 416.079, 599.152), (416.079, 623.857, 416.079, 721.534), (485.677, 525.952, 485.677, 599.152), (485.677, 623.857, 485.677, 721.534)]
TEXTS_63=[('8', 40.0, 799.995, 9.724, 11.895, 8.235, 0, 1, 0, 4.7), ('TRANSFERÊNCIA  DURANTE O ANO LETIVO', 49.724, 799.995, 505.552, 11.895, 9.15, 1, 1, 0, 4.7), ('8.1', 40.0, 784.669, 9.724, 11.895, 8.235, 0, 1, 0, 4.7), ('Ensino Fundamental', 49.724, 784.669, 505.552, 11.895, 9.15, 1, 1, 0, 4.7), ('Ano:', 40.0, 772.316, 44.523, 12.352, 9.15, 0, 1, 0, 4.7), ('Turma:', 258.519, 772.316, 166.26, 12.352, 9.15, 0, 0, 0, 4.7), ('Nº de chamada:', 424.779, 772.316, 69.598, 12.352, 9.15, 0, 1, 0, 4.7), ('TRANSFERIDO EM: ', 171.521, 753.101, 95.698, 12.352, 9.15, 0, 1, 0, 4.7), ('/', 302.018, 753.101, 27.063, 12.352, 10.98, 0, 0, 0, 4.7), ('/', 329.081, 753.101, 226.195, 12.352, 10.98, 0, 0, 0, 4.7), ('Dias Letivos:', 40.0, 733.886, 44.523, 12.352, 9.15, 0, 1, 0, 4.7), ('Ausências:', 145.421, 733.886, 52.199, 12.352, 9.15, 0, 1, 0, 4.7), ('Ausências Compensadas:', 258.519, 733.886, 105.361, 12.352, 9.15, 0, 1, 0, 4.7), ('Frequência (%):', 424.779, 733.886, 69.598, 12.352, 9.15, 0, 1, 0, 4.7), ('8.2', 40.0, 709.639, 9.724, 11.895, 8.235, 0, 1, 0, 4.7), ('CURRICULO', 49.724, 709.639, 296.757, 11.895, 9.15, 1, 1, 0, 4.7), ('1º TRIMESTRE', 346.48, 709.639, 69.598, 11.895, 7.32, 1, 1, 0, 4.7), ('2º TRIMESTRE', 416.079, 709.639, 69.598, 11.895, 7.32, 1, 1, 0, 4.7), ('3º TRIMESTRE', 485.677, 709.639, 69.598, 11.895, 7.32, 1, 1, 0, 4.7), ('LÍNGUA PORTUGUESA', 40.0, 697.972, 306.48, 11.666, 9.15, 0, 0, 0, 4.7), ('GEOGRAFIA', 40.0, 685.62, 306.48, 12.352, 9.15, 0, 0, 0, 4.7), ('MATEMÁTICA', 40.0, 673.267, 306.48, 12.352, 9.15, 0, 0, 0, 4.7), ('CIÊNCIAS', 40.0, 660.915, 306.48, 12.352, 9.15, 0, 0, 0, 4.7), ('HISTÓRIA', 40.0, 648.562, 306.48, 12.352, 9.15, 0, 0, 0, 4.7), ('ED. FÍSICA', 40.0, 636.21, 306.48, 12.352, 9.15, 0, 0, 0, 4.7), ('ARTE', 40.0, 623.857, 306.48, 12.352, 9.15, 0, 0, 0, 4.7), ('PARTE DIVERSIFICADA ', 40.0, 599.152, 515.276, 12.352, 9.15, 1, 0, 1, 4.7), ('LINGUAGENS E TECNOLOGIAS', 40.0, 586.8, 306.48, 12.352, 9.15, 0, 0, 0, 4.7), ('ACOMPANHAMENTO PEDAGÓGICO', 40.0, 574.447, 306.48, 12.352, 9.15, 0, 0, 0, 4.7), ('PRÁTICAS EXPERIMENTAIS E DE TUTORIA DE ESTUDO', 40.0, 562.095, 306.48, 12.352, 9.15, 0, 0, 0, 4.7), ('PRÁTICAS DE ESTUDO', 40.0, 549.742, 306.48, 12.352, 9.15, 0, 0, 0, 4.7), ('LINGUAGENS ', 40.0, 537.847, 306.48, 11.895, 9.15, 0, 0, 0, 4.7), ('ESPORTE E EDUCAÇÃO DO MOVIMENTO', 40.0, 525.952, 306.48, 11.895, 9.15, 0, 0, 0, 4.7), ('9', 40.0, 503.077, 9.724, 10.98, 8.235, 0, 1, 0, 4.7), ('OBSERVAÇÕES', 49.724, 503.077, 505.552, 10.98, 8.235, 1, 1, 0, 4.7), ('10', 40.0, 327.763, 9.724, 11.895, 8.235, 0, 1, 0, 4.7), ('CERTIFICADO', 49.724, 327.763, 505.552, 11.895, 9.15, 1, 1, 0, 4.7), ('            O diretor da', 40.0, 307.267, 114.121, 11.666, 9.15, 0, 1, 0, 4.7), ('de acordo com o Art.24, inciso VII, da Lei Federal 9394/96, certifica que', 40.0, 286.771, 271.681, 11.666, 8.693, 0, 0, 0, 4.7), ('R.A.', 40.0, 266.047, 18.423, 11.895, 8.235, 0, 1, 0, 4.7), ('11', 40.0, 234.937, 9.724, 11.895, 8.235, 0, 1, 0, 4.7), ('ASSINATURAS', 49.724, 234.937, 505.552, 11.895, 9.15, 1, 1, 0, 4.7), ('Limeira,', 41.024, 211.604, 43.499, 11.666, 9.15, 0, 1, 0, 4.7), ('  ', 180.221, 198.337, 375.055, 13.267, 9.15, 0, 0, 0, 4.7), ('SECRETÁRIO (A) DE ESCOLA', 206.32, 186.67, 166.26, 11.666, 9.15, 0, 1, 0, 4.7), ('DIRETOR DE ESCOLA', 381.28, 186.67, 173.996, 11.666, 9.15, 0, 1, 0, 4.7)]

_LOGO_ARQUIVO = 'logo_prefeitura.png'

def _caminho_logo_prefeitura():
    """Localiza o logo já existente no projeto, sem incorporar bytes ao módulo."""
    candidatos = []
    try:
        candidatos.append(Path(__file__).resolve().with_name(_LOGO_ARQUIVO))
    except NameError:
        pass
    candidatos.append(Path.cwd() / _LOGO_ARQUIVO)
    vistos = set()
    for caminho in candidatos:
        chave = str(caminho)
        if chave not in vistos and caminho.is_file():
            return caminho
        vistos.add(chave)
    return None

_FORM_FONT = 'Helvetica'
_FORM_BOLD = 'Helvetica-Bold'

class Formulario:
    def __init__(self, c):
        self.c = c
        self.x = X_EDGES
        self.y = Y_EDGES
        self.left = 40.0
        self.top = 30.0
        self.width = A4[0] - 80
        self.start = 0

    def rect(self, r, col, r1=None, c1=None):
        if r1 is None:
            r1, c1 = r + 1, col + 1
        return (
            self.x[col],
            A4[1] - self.top - (self.y[r1] - self.y[self.start]),
            self.x[c1] - self.x[col],
            self.y[r1] - self.y[r],
        )

    def _desenhar_texto(self, texto, x, y, w, h, size=8, bold=False, align=0, wrap=False, minsize=4.2):
        if not str(texto).strip():
            return
        font = _FORM_BOLD if bold else _FORM_FONT
        texto = str(texto)
        if wrap:
            sz = float(size)
            while True:
                p = Paragraph(
                    escape(texto).replace('\n', '<br/>'),
                    ParagraphStyle('celula', fontName=font, fontSize=sz, leading=sz * 1.04, alignment=align),
                )
                _, ph = p.wrap(max(w - 3, 1), max(h - 1, 1))
                if ph <= h - 1:
                    break
                sz -= .1
                if sz < minsize:
                    # No formulário oficial há textos legais muito densos.
                    # Em vez de falhar, usa o menor corpo permitido.
                    sz = minsize
                    p = Paragraph(
                        escape(texto).replace('\n', '<br/>'),
                        ParagraphStyle('celula_min', fontName=font, fontSize=sz, leading=sz * 1.02, alignment=align),
                    )
                    _, ph = p.wrap(max(w - 3, 1), max(h - 1, 1))
                    break
            p.drawOn(self.c, x + 1.5, y + max((h - ph) / 2, 0))
            return
        max_width = max(w - 3, 1)
        measured = max(pdfmetrics.stringWidth(texto, font, 1), .001)
        size = min(float(size), max_width / measured)
        size = max(size, minsize) if measured * minsize <= max_width else size
        self.c.setFont(font, max(size, 3.2))
        self.c.setFillColorRGB(0, 0, 0)
        yy = y + (h - max(size, 3.2)) / 2 + max(size, 3.2) * .18
        if align == 1:
            self.c.drawCentredString(x + w / 2, yy, texto)
        elif align == 2:
            self.c.drawRightString(x + w - 1.5, yy, texto)
        else:
            self.c.drawString(x + 1.5, yy, texto)

    def texto(self, texto, r, col, r1=None, c1=None, size=8, bold=False, align=0, wrap=False, minsize=4.2):
        x, y, w, h = self.rect(r, col, r1, c1)
        self._desenhar_texto(texto, x, y, w, h, size, bold, align, wrap, minsize)

    def pagina(self, start, end):
        self.start = start
        fills = FILLS_0 if start == 0 else FILLS_63
        lines = LINES_0 if start == 0 else LINES_63
        texts = TEXTS_0 if start == 0 else TEXTS_63
        c = self.c
        for x, y, w, h, rr, gg, bb in fills:
            c.setFillColorRGB(rr, gg, bb)
            c.rect(x, y, w, h, stroke=0, fill=1)
        c.setStrokeColorRGB(0, 0, 0)
        c.setLineWidth(.4)
        for x1, y1, x2, y2 in lines:
            c.line(x1, y1, x2, y2)
        for texto, x, y, w, h, size, bold, align, mode, minsize in texts:
            if mode == 2:
                c.setFillColorRGB(0, 0, 0)
                c.setFont(_FORM_BOLD if bold else _FORM_FONT, size)
                c.drawString(x + 1.5, y + 1, texto)
            else:
                self._desenhar_texto(texto, x, y, w, h, size, bool(bold), align, bool(mode), minsize)
        if start == 0:
            x, y, w, h = self.rect(43, 0, 45, 61)
            c.rect(x, y, w, h, stroke=1, fill=0)
            logo = _caminho_logo_prefeitura()
            if logo is not None:
                try:
                    imagem = ImageReader(str(logo))
                    x, y, w, h = self.rect(0, 0, 6, 12)
                    c.drawImage(imagem, x + 4, y + 1, w - 8, h - 2, preserveAspectRatio=True, anchor='c', mask='auto')
                except Exception:
                    # O restante do histórico continua emitível caso a imagem esteja
                    # corrompida ou o decodificador da instalação esteja indisponível.
                    pass

def gerar_pdf(dados, rascunho=False):
    erros, _ = validar(dados, exigir_conferencia=not rascunho)
    if erros and not rascunho:
        raise ValueError('\n'.join(erros))
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4, pageCompression=1)
    c.setTitle('Histórico Escolar - ' + dados['aluno']['nome'])
    c.setAuthor(dados['escola']['nome'])
    f = Formulario(c)
    a = dados['aluno']
    e = dados['escola']
    def t(v, r, col, r1, c1, **kw):
        f.texto(v, r, col, r1, c1, **kw)
    def marca():
        if dados['demonstracao'] or rascunho:
            c.saveState()
            c.setFillColorRGB(.70, .14, .14)
            c.setFont('Helvetica-Bold', 8)
            c.drawCentredString(A4[0] / 2, 15, 'DEMONSTRAÇÃO - SEM VALIDADE' if dados['demonstracao'] else 'RASCUNHO - NÃO EMITIDO')
            c.restoreState()

    # FRENTE: campos 1 a 7. O campo 8 não é desenhado nesta página.
    f.pagina(0, 63)
    for k, r, col, end_col in [('nome',0,21,52),('ato',1,21,52),('endereco',2,21,52),('bairro',3,18,36),('municipio',3,44,61),('cep',4,15,23),('telefone',4,33,52),('email',5,17,52)]:
        t(e[k], r, col, r + 1, end_col, size=7.4)
    t(a['ra'], 9, 52, 10, 61, size=7.6, align=1)
    t(a['nome'], 10, 9, 11, 40, size=8, bold=True)
    t(a['ra_escolar'], 10, 48, 11, 61, size=8)
    for k, col, end_col in [('localidade',12,33),('uf',33,40),('nacionalidade',40,51)]:
        t(a[k], 12, col, 13, end_col, size=8, align=1)
    if a['nascimento']:
        try:
            dt = date.fromisoformat(a['nascimento'])
            for v, col, end_col in [(str(dt.day).zfill(2),51,54),(str(dt.month).zfill(2),54,57),(dt.year,57,61)]:
                t(v, 12, col, 13, end_col, align=1)
        except ValueError:
            pass
    for k, r, col, end_col in [('livro',13,44,61),('distrito',14,8,23),('cidade_certidao',14,28,45),('uf_certidao',14,50,61),('matricula_certidao',15,20,61),('documento_estrangeiro',16,20,61)]:
        t(a[k], r, col, r + 1, end_col, size=7.5)
    for i, ano in enumerate(dados['anos']):
        col = 31 + 6 * i
        if ano['situacao'] != 'Concluído':
            continue
        for j, disc in enumerate(BASE):
            t(ano['conceitos'][disc], 23 + j, col, 24 + j, col + 6, align=1)
        for j, disc in enumerate(DIV):
            t(ano['participacao'][disc], 33 + j, col, 34 + j, col + 6, align=1)
        try:
            t(carga(ano, 'base'), 30, col, 31, col + 6, size=7.8, align=1)
            t(carga(ano, 'div'), 42, col, 43, col + 6, size=7.8, align=1)
            t(total(ano), 52, col, 53, col + 6, size=7.8, align=1)
        except ValueError:
            if not rascunho:
                raise
        t(ano['ch_religioso'], 46, col, 47, col + 6, size=7.8, align=1)
        t('AEE' if ano['aee'] else '-', 50, col, 51, col + 6, align=1)
    estudos = [x for x in dados['anos'] if x['situacao'] != 'Não cursado']
    for i, ano in enumerate(estudos):
        for v, col, end_col in [(ano['ano_letivo'],0,6),(str(ano['serie'])+'º ANO',6,12),(ano['estabelecimento'],12,39),(ano['municipio'],39,52),(ano['uf'],52,61)]:
            t(v, 56 + i, col, 57 + i, end_col, size=7.5, align=1)
    marca()
    c.showPage()

    # VERSO: inicia obrigatoriamente pelo campo 8 (Transferência).
    f.pagina(63, 120)
    tr = dados['transferencia']
    if tr['ativa']:
        for v, r, col, end_col in [(str(tr['serie'])+'º',66,6,12),(tr['turma'],66,30,36),(tr['chamada'],66,55,61),(tr['dias'],70,6,12),(tr['ausencias'],70,19,25),(tr['compensadas'],70,39,45),(tr['frequencia'],70,55,61)]:
            t(v, r, col, r + 1, end_col, size=8, align=1)
        if tr['data']:
            try:
                dt = date.fromisoformat(tr['data'])
                for v, col, end_col in [(dt.day,28,31),(dt.month,32,35),(dt.year,36,42)]:
                    t(v, 68, col, 69, end_col, align=1)
            except ValueError:
                pass
        for disc, row in list(zip(BASE, range(73,80))) + list(zip(DIV[3:], range(82,88))):
            for i, v in enumerate(tr['conceitos'][disc]):
                t(v, row, 37 + i * 8, row + 1, 45 + i * 8, align=1)

    linhas = []
    for par in dados['observacoes'].split('\n'):
        linhas.extend(simpleSplit(par, _FORM_FONT, 8, f.width - 4) if par else [''])
    if len(linhas) > 14:
        raise ValueError('Observações excedem as 14 linhas disponíveis. Reduza o texto ou use documento anexo.')
    for i, linha in enumerate(linhas):
        t(linha, 90 + i, 0, 91 + i, 61, size=8)
    t('concluiu o ______ do Ensino Fundamental, no ano letivo de', 111, 20, 112, 51, size=8)
    if dados['certificar']:
        t(e['nome'], 107, 15, 108, 61, size=8)
        t(a['nome'], 109, 33, 110, 61, size=8)
        t(a['ra'], 111, 3, 112, 20, size=8)
        xx, yy, ww, hh = f.rect(111, 20, 112, 51)
        c.setFillColorRGB(1, 1, 1)
        c.rect(xx + .5, yy + .5, ww - 1, hh - 1, stroke=0, fill=1)
        t('concluiu o ' + str(dados['serie_certificada']) + 'º ano do Ensino Fundamental, no ano letivo de', 111, 20, 112, 51, size=8)
        t(dados['ano_certificado'], 111, 51, 112, 60, size=8, align=1)
    try:
        dt = date.fromisoformat(dados['data_emissao'])
        t(dt.strftime('%d/%m/%Y'), 116, 6, 117, 18, size=8, align=1)
    except ValueError:
        pass
    t(e['secretario'], 116, 20, 117, 40, size=7.5, align=1)
    t(e['diretor'], 116, 41, 117, 61, size=7.5, align=1)
    marca()
    c.save()
    buffer.seek(0)
    return buffer

"""Persistência local e arquivo imutável de cada emissão, separado da edição."""
import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from contextlib import contextmanager

@contextmanager
def _repo_conectar(caminho):
    db=sqlite3.connect(caminho)
    db.execute('CREATE TABLE IF NOT EXISTS registros (id TEXT PRIMARY KEY, ra TEXT NOT NULL UNIQUE, nome TEXT NOT NULL, dados TEXT NOT NULL, atualizado TEXT NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS _repo_emissoes (id TEXT PRIMARY KEY, registro_id TEXT NOT NULL, emitido TEXT NOT NULL, dados TEXT NOT NULL, sha256 TEXT NOT NULL, pdf BLOB NOT NULL)')
    db.commit()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:db.close()

def _repo_salvar(caminho,dados,registro_id=None):
    ident=registro_id or str(uuid.uuid4());agora=datetime.now(timezone.utc).isoformat()
    with _repo_conectar(caminho) as db:
        db.execute('INSERT INTO registros VALUES (?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET ra=excluded.ra,nome=excluded.nome,dados=excluded.dados,atualizado=excluded.atualizado',(ident,dados['aluno']['ra'],dados['aluno']['nome'],json.dumps(dados,ensure_ascii=False),agora))
    return ident

def _repo_listar(caminho):
    with _repo_conectar(caminho) as db:return db.execute('SELECT id,ra,nome,atualizado FROM registros ORDER BY nome').fetchall()

def _repo_carregar(caminho,ident):
    with _repo_conectar(caminho) as db:
        row=db.execute('SELECT dados FROM registros WHERE id=?',(ident,)).fetchone()
    if not row:raise ValueError('Registro não encontrado.')
    return json.loads(row[0])

def _repo_arquivar(caminho,registro_id,dados,pdf):
    ident=str(uuid.uuid4());digest=hashlib.sha256(pdf).hexdigest()
    with _repo_conectar(caminho) as db:
        db.execute('INSERT INTO _repo_emissoes VALUES (?,?,?,?,?,?)',(ident,registro_id,datetime.now(timezone.utc).isoformat(),json.dumps(dados,ensure_ascii=False),digest,pdf))
    return ident,digest

def _repo_emissoes(caminho,ident):
    with _repo_conectar(caminho) as db:return db.execute('SELECT id,emitido,sha256,pdf FROM _repo_emissoes WHERE registro_id=? ORDER BY emitido DESC',(ident,)).fetchall()

repo=SimpleNamespace(conectar=_repo_conectar,salvar=_repo_salvar,listar=_repo_listar,carregar=_repo_carregar,arquivar=_repo_arquivar,emissoes=_repo_emissoes)

"""Execute: streamlit run app.py (uso local, um operador)."""
import hashlib
import json
import re
import sqlite3
from copy import deepcopy
from pathlib import Path
import pandas as pd
import streamlit as st

DB=Path(os.environ.get('HISTORICO_DB_PATH', str(Path(tempfile.gettempdir())/'historicos_escolares.sqlite3')))

class _EstadoHistorico:
    """Isola o estado do módulo e preserva login/menu do aplicativo principal."""
    prefixo = 'modulo_historico__'
    def __contains__(self, key): return self.prefixo+key in st.session_state
    def __getattr__(self, key): return st.session_state[self.prefixo+key]
    def __setattr__(self, key, value): st.session_state[self.prefixo+key]=value
    def get(self, key, default=None): return st.session_state.get(self.prefixo+key,default)
    def clear(self):
        for key in list(st.session_state):
            if str(key).startswith(self.prefixo): del st.session_state[key]

estado_historico=_EstadoHistorico()


def _widget_key(label):
    return 'modulo_historico__widget_'+str(label)

class _StreamlitModulo:
    _controles={'text_input','text_area','checkbox','selectbox','button','download_button','file_uploader','data_editor'}
    def __getattr__(self,nome):
        original=getattr(_streamlit_original,nome)
        if nome not in self._controles:return original
        def controle(*args,**kwargs):
            rotulo=kwargs.get('key', kwargs.get('label',args[0] if args else nome))
            kwargs['key']=_widget_key(rotulo)
            return original(*args,**kwargs)
        return controle

_streamlit_original=st
st=_StreamlitModulo()

def texto(obj,key,label,**kw):
    obj[key]=st.text_input(label,value=str(obj.get(key,'')),key=kw.pop('id',label),**kw)

def tabela(obj,chave,nomes,cols,key,opcoes=None):
    rows=[{'Componente':n,**{label:str(obj[chave][n][i]) for i,label in enumerate(cols)}} for n in nomes]
    config={'Componente':st.column_config.TextColumn(disabled=True,width='large')}
    for label in cols:
        config[label]=st.column_config.SelectboxColumn(options=opcoes,required=False) if opcoes else st.column_config.TextColumn(max_chars=8)
    edit=st.data_editor(pd.DataFrame(rows),hide_index=True,num_rows='fixed',column_config=config,key=key,width='stretch')
    for _,row in edit.iterrows():obj[chave][row['Componente']]=['' if pd.isna(row[x]) else str(row[x]).strip() for x in cols]

def importar(raw):
    if len(raw)>2_000_000:raise ValueError('Arquivo muito grande.')
    d=json.loads(raw)
    def estrutura(ref,valor,path=''):
        if isinstance(ref,dict):
            if not isinstance(valor,dict) or set(ref)!=set(valor):raise ValueError('Campos incompatíveis em '+path)
            for k in ref:estrutura(ref[k],valor[k],path+'/'+k)
        elif isinstance(ref,list):
            if not isinstance(valor,list) or len(ref)!=len(valor):raise ValueError('Quantidade de itens inválida em '+path)
            for i,x in enumerate(ref):estrutura(x,valor[i],path+'/'+str(i))
        elif type(ref)!=type(valor):raise ValueError('Tipo inválido em '+path)
    estrutura(novo(),d)
    if d['versao']!=1:raise ValueError('Versão não suportada.')
    return d

def trocar(d,ident=None):
    estado_historico.clear()
    estado_historico.dados=d;estado_historico.ident=ident
    st.rerun()

def renderizar_modulo(banco_path=None):
    """Renderiza o módulo; banco_path opcional aponta para SQLite persistente."""
    global DB
    if banco_path is not None: DB=Path(banco_path)
    DB.parent.mkdir(parents=True,exist_ok=True)
    if 'dados' not in estado_historico:estado_historico.dados=novo()
    d=estado_historico.dados
    st.title('Emissão de histórico escolar')
    st.caption('Ensino Fundamental • Anos iniciais • Modelo municipal 2026')
    with st.sidebar:
        st.header('Registros locais')
        if st.button('Novo estudante',width='stretch'):trocar(novo())
        registros=repo.listar(DB)
        selecao=st.selectbox('Estudantes salvos',[None]+[x[0] for x in registros],format_func=lambda v:'Selecione' if v is None else next(x[2]+' · RA '+x[1] for x in registros if x[0]==v))
        if st.button('Abrir registro',disabled=selecao is None,width='stretch'):trocar(repo.carregar(DB,selecao),selecao)
        with st.expander('Importar / testar'):
            arquivo=st.file_uploader('Registro JSON',type=['json'])
            if st.button('Importar registro',disabled=arquivo is None):
                try:novo_d=importar(arquivo.getvalue())
                except (ValueError,TypeError,KeyError) as exc:st.error(str(exc))
                else:trocar(novo_d)
            if st.button('Carregar exemplo fictício'):trocar(exemplo())
        st.caption('Registros salvos no disco da instância que executa o sistema. Em hospedagem, esse disco pode ser temporário. Exporte JSON/PDF ou configure armazenamento persistente.')
    if d['demonstracao']:st.warning('Demonstração: todos os PDFs deste registro terão a marca SEM VALIDADE. Crie um novo estudante para uso real.')
    tabs=st.tabs(['1 · Escola e estudante','2 · Vida escolar','3 · Transferência','4 · Fechamento','5 · Conferir e emitir'])
    with tabs[0]:
        with st.expander('Identificação da escola e responsáveis',expanded=True):
            labels={'nome':'Nome da escola','ato':'Ato de criação','endereco':'Endereço','bairro':'Bairro','municipio':'Município','cep':'CEP','telefone':'Telefone','email':'E-mail','secretario':'Secretário(a) de escola','diretor':'Diretor(a) de escola'}
            cs=st.columns(2)
            for i,(k,label) in enumerate(labels.items()):
                with cs[i%2]:texto(d['escola'],k,label,id='escola_'+k)
        st.subheader('Estudante')
        labels={'nome':'Nome completo','ra':'RA','ra_escolar':'RA escolar (se houver)','nascimento':'Nascimento (AAAA-MM-DD)','localidade':'Localidade de nascimento','uf':'UF de nascimento','nacionalidade':'Nacionalidade','distrito':'(Sub)distrito da certidão antiga','livro':'Livro da certidão antiga','cidade_certidao':'Cidade da certidão antiga','uf_certidao':'UF da certidão antiga','matricula_certidao':'Matrícula da certidão nova','documento_estrangeiro':'Documento estrangeiro (quando aplicável)'}
        cs=st.columns(2)
        for i,(k,label) in enumerate(labels.items()):
            with cs[i%2]:texto(d['aluno'],k,label,id='aluno_'+k)
    with tabs[1]:
        st.info('Cada coluna corresponde ao ano de escolaridade. O ano letivo determina a matriz de referência. Transcreva resultados e cargas dos registros escolares; o sistema não atribui conceitos nem participação automaticamente.')
        for ano in d['anos']:
            n=ano['serie'];prefix=f'a{n}_'
            with st.expander(f'{n}º ano · {ano["situacao"]}',expanded=n==1):
                cs=st.columns(3)
                with cs[0]:ano['situacao']=st.selectbox('Situação',SITUACOES,index=SITUACOES.index(ano['situacao']),key=prefix+'situacao')
                with cs[1]:texto(ano,'ano_letivo','Ano letivo',id=prefix+'letivo')
                with cs[2]:ano['modalidade']=st.selectbox('Atendimento / matriz',MODOS,index=MODOS.index(ano['modalidade']),key=prefix+'modalidade')
                if ano['situacao']=='Não cursado':
                    st.caption('Deixe os resultados deste ano vazios. Se havia dados, limpe-os antes de alterar a situação.')
                cs=st.columns([3,2,1])
                for col,k,label in zip(cs,['estabelecimento','municipio','uf'],['Estabelecimento','Município dos estudos','UF dos estudos']):
                    with col:texto(ano,k,label,id=prefix+k)
                texto(ano,'fonte','Registro de origem das notas e cargas (livro, ata, ficha ou histórico anterior)',id=prefix+'fonte')
                if ano['situacao']=='Concluído':
                    cs=st.columns(2)
                    with cs[0]:
                        frame=pd.DataFrame([{'Componente':k,'Resultado':ano['conceitos'][k]} for k in BASE])
                        ed=st.data_editor(frame,hide_index=True,disabled=['Componente'],column_config={'Resultado':st.column_config.TextColumn(max_chars=8)},key=prefix+'base',width='stretch')
                        ano['conceitos']={r['Componente']:('' if pd.isna(r['Resultado']) else str(r['Resultado']).strip()) for _,r in ed.iterrows()}
                    with cs[1]:
                        frame=pd.DataFrame([{'Componente':k,'Registro':ano['participacao'][k]} for k in DIV])
                        ed=st.data_editor(frame,hide_index=True,disabled=['Componente'],column_config={'Registro':st.column_config.SelectboxColumn(options=['','P','-'])},key=prefix+'div',width='stretch')
                        ano['participacao']={r['Componente']:('' if pd.isna(r['Registro']) else str(r['Registro'])) for _,r in ed.iterrows()}
                    try:comp=esperados(ano);st.caption('Componentes previstos no anexo: '+(', '.join(k for k in DIV if k in comp) if comp else 'Consultar matriz documentada.'))
                    except (ValueError,TypeError):pass
                    st.caption('P = participação comprovada. Traço = componente não correspondente / sem participação, conforme registro. Anos não cursados ficam em branco.')
                    cs=st.columns(4)
                    for i,campo in enumerate(['base','div']):
                        with cs[i*2]:texto(ano,'ch_'+campo,'Carga anual '+('base comum' if campo=='base' else 'diversificada'),id=prefix+'ch_'+campo)
                        with cs[i*2+1]:ano['unidade_'+campo]=st.selectbox('Unidade '+campo,['H/A','H'],index=['H/A','H'].index(ano['unidade_'+campo]),key=prefix+'unidade_'+campo)
                    texto(ano,'minutos_aula','Duração da hora-aula em minutos (necessária ao combinar H e H/A)',id=prefix+'minutos')
                    try:st.caption('Total calculado, campo 6: '+total(ano))
                    except ValueError:st.caption('Total disponível após preencher as cargas e unidades.')
                    texto(ano,'ch_religioso','Carga de Ensino Religioso (transcrição, com unidade; se houver)',id=prefix+'religioso')
                    ano['aee']=st.checkbox('Frequentou AEE neste ano',value=ano['aee'],key=prefix+'aee')
                    ano['relatorio_fc']=st.checkbox('Relatório pedagógico anual de FC disponível para anexar',value=ano['relatorio_fc'],key=prefix+'fc')
                    if ano['relatorio_fc']:st.caption('Anexe o relatório à documentação entregue. O sistema não gera nem incorpora esse relatório automaticamente.')
                    ano['justificativa_matriz']=st.text_area('Orientação documentada para divergência de matriz (quando houver)',value=ano['justificativa_matriz'],key=prefix+'justificativa')
                elif ano['situacao']=='Em curso':st.caption('Preencha os resultados trimestrais na aba Transferência; não lance resultados anuais ainda.')
    with tabs[2]:
        tr=d['transferencia'];tr['ativa']=st.checkbox('Emitir transferência durante o ano letivo',value=tr['ativa'])
        if tr['ativa']:
            tr['serie']=st.selectbox('Ano de escolaridade da transferência',[1,2,3,4,5],index=tr['serie']-1,format_func=lambda x:f'{x}º ano')
            cs=st.columns(3)
            for i,(k,label) in enumerate({'turma':'Turma','chamada':'Número de chamada','data':'Data da transferência (AAAA-MM-DD)','dias':'Dias letivos','ausencias':'Ausências registradas','compensadas':'Ausências compensadas','frequencia':'Frequência (%) conforme registro'}.items()):
                with cs[i%3]:texto(tr,k,label,id='tr_'+k)
            st.caption('A frequência deve ser transcrita do registro escolar. Dias letivos e ausências podem ter unidades diferentes, portanto não se presume uma fórmula.')
            tabela(tr,'conceitos',BASE+DIV[3:],['1º trimestre','2º trimestre','3º trimestre'],'tr_notas')
    with tabs[3]:
        d['observacoes']=st.text_area('Observações (até 14 linhas no formulário)',value=d['observacoes'],height=180)
        d['certificar']=st.checkbox('Preencher certificado de conclusão do ano',value=d['certificar'])
        if d['certificar']:
            d['serie_certificada']=st.selectbox('Ano concluído a certificar',[1,2,3,4,5],index=d['serie_certificada']-1,format_func=lambda x:f'{x}º ano')
            texto(d,'ano_certificado','Ano letivo da conclusão')
            st.caption('O texto certifica o ano de escolaridade indicado; não declara conclusão de todo o Ensino Fundamental ao concluir o 5º ano.')
        texto(d,'data_emissao','Data da emissão (AAAA-MM-DD)')
    with tabs[4]:
        erros,avisos=validar(d,exigir_conferencia=False)
        for aviso in avisos:st.warning(aviso)
        if erros:
            st.error(f'{len(erros)} pendência(s) para emissão')
            for erro in erros:st.write('• '+erro)
        else:st.success('Campos obrigatórios e consistência dos registros conferidos pelo sistema.')
        conteudo={k:v for k,v in d.items() if k!='conferido'}
        chave_conferencia='confirmacao_'+hashlib.sha256(json.dumps(conteudo,sort_keys=True).encode()).hexdigest()
        d['conferido']=st.checkbox('Conferi os dados com os documentos escolares e a matriz aplicável. Os responsáveis assinarão o histórico.',value=False,key=chave_conferencia)
        assinatura=hashlib.sha256(json.dumps(d,sort_keys=True).encode()).hexdigest()
        cs=st.columns(3)
        with cs[0]:
            if st.button('Salvar registro',width='stretch'):
                if not d['aluno']['ra'].strip() or not d['aluno']['nome'].strip():st.error('Informe nome e RA para salvar.')
                else:
                    try:estado_historico.ident=repo.salvar(DB,d,estado_historico.get('ident'));st.success('Registro salvo.')
                    except sqlite3.IntegrityError:st.error('Já existe um registro com este RA. Abra o registro salvo para atualizá-lo.')
        with cs[1]:
            if st.button('Gerar prévia',width='stretch'):
                try:estado_historico.pdf=(assinatura,gerar_pdf(d,rascunho=True).getvalue(),'Previa')
                except ValueError as exc:st.error(str(exc))
        with cs[2]:
            if st.button('Emitir histórico em PDF',type='primary',disabled=bool(erros) or not d['conferido'],width='stretch'):
                try:
                    pdf=gerar_pdf(d).getvalue()
                    ident=repo.salvar(DB,d,estado_historico.get('ident'));estado_historico.ident=ident
                    repo.arquivar(DB,ident,d,pdf)
                    estado_historico.pdf=(assinatura,pdf,'Historico');st.success('PDF emitido e cópia arquivada nesta instância.')
                except (ValueError,sqlite3.IntegrityError) as exc:st.error(str(exc))
        st.download_button('Exportar registro editável (JSON)',json.dumps(d,ensure_ascii=False,indent=2),file_name='registro_historico.json',mime='application/json')
        result=estado_historico.get('pdf')
        if result and result[0]==assinatura:
            _,pdf,tipo=result;ra=re.sub(r'[^\w-]','',d['aluno']['ra'])[:40] or 'rascunho'
            st.download_button('Baixar PDF',pdf,file_name=f'{tipo}_{ra}.pdf',mime='application/pdf',type='primary')
            try:
                visualizador = getattr(st, 'pdf')
            except AttributeError:
                visualizador = None
            if visualizador is not None:
                try:
                    visualizador(pdf, height=820)
                except TypeError:
                    visualizador(pdf)
            else:
                st.caption('A prévia inline requer uma versão do Streamlit com st.pdf. O botão “Baixar PDF” continua disponível.')
        elif result:st.info('Os dados mudaram. Gere uma nova prévia ou emissão.')
        if estado_historico.get('ident'):
            with st.expander('Emissões anteriores deste registro'):
                for ident,dt,digest,pdf in repo.emissoes(DB,estado_historico.ident):
                    st.download_button(dt+' · baixar cópia',pdf,file_name='Historico_'+ident+'.pdf',mime='application/pdf',key=ident)
                    st.caption('SHA-256: '+digest)

if __name__=='__main__':
    st.set_page_config(page_title='Histórico Escolar | Limeira',page_icon='📄',layout='wide')
    renderizar_modulo()
