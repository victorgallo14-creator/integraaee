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

_LOGO_ARQUIVO = 'logo_prefeitura.png'
def _caminho_logo_prefeitura():
    for p in (Path(__file__).resolve().with_name(_LOGO_ARQUIVO), Path.cwd() / _LOGO_ARQUIVO):
        if p.is_file(): return p
    return None

# Composição vetorial A4. Coordenadas referidas ao topo da página, em pontos.
# Mantém a ordem e os campos do formulário oficial, com campo 8 só no verso.
from reportlab.lib.colors import HexColor
from reportlab.pdfbase.ttfonts import TTFont

INK = HexColor('#1C2935')
BLUE = HexColor('#153B60')
PALE = HexColor('#EAF0F5')
PAPER = HexColor('#F7F9FB')
LINE = HexColor('#B5C2CC')
MUTED = HexColor('#526779')
LEFT, RIGHT = 36, A4[0] - 36
WIDTH = RIGHT - LEFT

# Uma fonte incorporada mantém acentos e símbolos estáveis nos leitores de PDF.
_FONT_PATHS = ['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
               '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf']
if all(Path(p).is_file() for p in _FONT_PATHS):
    pdfmetrics.registerFont(TTFont('HistoricoRegular', _FONT_PATHS[0]))
    pdfmetrics.registerFont(TTFont('HistoricoBold', _FONT_PATHS[1]))
    _REG, _BOLD = 'HistoricoRegular', 'HistoricoBold'
else:
    _REG, _BOLD = 'Helvetica', 'Helvetica-Bold'

class Page:
    def __init__(self, c): self.c = c
    def box(self, x, y, w, h, fill=None, stroke=LINE, lw=.55):
        c=self.c; c.setLineWidth(lw)
        if fill: c.setFillColor(fill)
        if stroke: c.setStrokeColor(stroke)
        c.rect(x, A4[1]-y-h, w, h, stroke=int(bool(stroke)), fill=int(bool(fill)))
    def rule(self, x1,y1,x2,y2,color=LINE,lw=.55):
        c=self.c; c.setStrokeColor(color); c.setLineWidth(lw)
        c.line(x1,A4[1]-y1,x2,A4[1]-y2)
    def text(self, value, x,y,w=None,size=8,bold=False,align='left',color=INK,minsize=6):
        value=str(value or '').strip()
        if not value: return
        font=_BOLD if bold else _REG
        if w is not None:
            maxw=max(w-4,1)
            size=min(size,maxw/max(pdfmetrics.stringWidth(value,font,1),.001))
            if size < minsize:
                raise ValueError('Texto excede o campo do PDF: '+value[:65])
        c=self.c; c.setFillColor(color); c.setFont(font,size)
        baseline=A4[1]-y-size*.82
        if align=='center': c.drawCentredString(x+w/2,baseline,value)
        elif align=='right': c.drawRightString(x+w-2,baseline,value)
        else: c.drawString(x+2,baseline,value)
    def fit_lines(self,value,x,y,w,h,size=7.1,leading=10,color=INK):
        from reportlab.lib.utils import simpleSplit
        rows=[]
        for paragraph in str(value or '').split('\n'):
            rows.extend(simpleSplit(paragraph,_REG,size,w-18) if paragraph else [''])
        if len(rows)*leading>h-3:
            raise ValueError('Texto excede o espaço reservado no PDF: '+str(value)[:65])
        for i,line in enumerate(rows): self.text(line,x+2,y+2+i*leading,w-4,size,color=color,minsize=5.2)
        return len(rows)
    def band(self,num,title,y,h=18):
        self.box(LEFT,y,WIDTH,h,PALE,LINE,.7)
        if num:
            self.box(LEFT,y,26,h,BLUE,BLUE,.7)
            self.text(num,LEFT,y+4,26,8.1,True,'center',HexColor('#FFFFFF'))
        self.text(title,LEFT+(32 if num else 10),y+3,WIDTH-(36 if num else 14),9.0,True,color=BLUE)
    def footer(self,page):
        self.rule(LEFT,823,RIGHT,823,LINE,.5)
        self.text('CEIEF "Rafael Affonso Leite"  |  Histórico escolar',LEFT,827,410,6.6,color=MUTED)
        self.text(f'{page} / 2',RIGHT-40,827,40,6.6,align='right',color=MUTED)
    def matrix(self,y,rows,values,heading=True,row_h=14,col0=282,headers=None):
        cols=[LEFT+col0+i*(WIDTH-col0)/5 for i in range(6)]
        if heading:
            self.box(LEFT,y,WIDTH,17,PAPER,LINE)
            self.text(headers[0] if headers else 'COMPONENTE CURRICULAR',LEFT+5,y+4,col0-8,7.2,True,color=BLUE)
            for j in range(5):
                self.text(headers[j+1] if headers else f'{j+1}º ano',cols[j],y+4,cols[j+1]-cols[j],7.1,True,'center',BLUE)
                self.rule(cols[j],y,cols[j],y+17)
            y+=17
        for i,name in enumerate(rows):
            if i%2: self.box(LEFT,y+i*row_h,WIDTH,row_h,PAPER,None)
            self.rule(LEFT,y+(i+1)*row_h,RIGHT,y+(i+1)*row_h)
            self.text(name,LEFT+5,y+i*row_h+3,col0-8,7.05,minsize=6.2)
            for j in range(5):
                v=values[j].get(name,'') if j<len(values) else ''
                self.text(v,cols[j],y+i*row_h+3,cols[j+1]-cols[j],7.6,True,'center')
        for x in cols[:-1]: self.rule(x,y,x,y+len(rows)*row_h)
        self.rule(LEFT,y,LEFT,y+len(rows)*row_h)
        self.rule(RIGHT,y,RIGHT,y+len(rows)*row_h)
        return y+len(rows)*row_h
    def load_row(self,y,title,values,h=16,col0=282):
        self.box(LEFT,y,WIDTH,h,PAPER,LINE)
        self.text(title,LEFT+5,y+4,col0-8,7.2,True,color=BLUE)
        cw=(WIDTH-col0)/5
        for j,v in enumerate(values):
            x=LEFT+col0+j*cw
            self.rule(x,y,x,y+h)
            self.text(v,x,y+3,cw,7.2,True,'center')


def _date(value):
    try:return date.fromisoformat(str(value)).strftime('%d/%m/%Y')
    except (ValueError,TypeError):return ''

def _mark(c,d,rascunho):
    if d.get('demonstracao') or rascunho:
        c.setFont(_BOLD,7.3);c.setFillColor(HexColor('#A52B2B'))
        c.drawCentredString(A4[0]/2,12,'DEMONSTRAÇÃO - SEM VALIDADE' if d.get('demonstracao') else 'RASCUNHO - NÃO EMITIDO')

def _header(p,e):
    c=p.c
    logo=_caminho_logo_prefeitura()
    if logo:
        try:
            c.drawImage(ImageReader(str(logo)),LEFT+1,A4[1]-24-44,75,44,preserveAspectRatio=True,anchor='c',mask='auto')
        except Exception: pass
    else:
        p.text('PREFEITURA DE',LEFT+4,42,78,6.8,True,'center',BLUE)
        p.text('LIMEIRA',LEFT+4,53,78,12,True,'center',BLUE)
    p.rule(LEFT+88,25,LEFT+88,68,LINE,.7)
    p.text('PREFEITURA MUNICIPAL DE LIMEIRA',LEFT+98,24,420,8.2,True,color=BLUE)
    p.text('SECRETARIA MUNICIPAL DE EDUCAÇÃO',LEFT+98,35,420,8.0,color=MUTED)
    p.text('HISTÓRICO ESCOLAR',LEFT+98,47,420,15.0,True,color=BLUE)
    p.rule(LEFT,69,RIGHT,69,BLUE,1.4)
    # Dados institucionais em duas linhas, sem grade ornamental.
    p.text(e['nome'],LEFT,75,300,8.1,True)
    p.text('Ato: '+e['ato'],LEFT+304,76,WIDTH-304,6.8,minsize=6.0)
    addr=f"{e['endereco']}  ·  {e['bairro']}  ·  {e['municipio']}/SP  ·  CEP {e['cep']}"
    p.text(addr,LEFT,86,WIDTH,7.0,minsize=6.2)
    p.text(f"Telefone: {e['telefone']}  ·  {e['email']}",LEFT,97,WIDTH,7.0,minsize=6.1)

def gerar_pdf(dados, rascunho=False):
    erros,_=validar(dados,exigir_conferencia=not rascunho)
    if erros and not rascunho: raise ValueError('\n'.join(erros))
    buf=BytesIO();c=canvas.Canvas(buf,pagesize=A4,pageCompression=1)
    c.setTitle('Histórico Escolar - '+dados['aluno']['nome']);c.setAuthor(dados['escola']['nome'])
    p=Page(c);a=dados['aluno'];e=dados['escola'];anos=dados['anos']
    def v(ano,fn):
        if ano['situacao']!='Concluído':return ''
        try:return fn(ano)
        except ValueError:
            if rascunho:return ''
            raise
    # FRENTE: campos 1 a 7.
    _header(p,e)
    p.band('1.1','DADOS DO ESTUDANTE',105)
    p.text('RA: '+str(a['ra']),RIGHT-151,109,147,7.2,True,'right',BLUE,minsize=6.0)
    p.text('NOME DO ESTUDANTE',LEFT+5,126,150,6.5,True,color=MUTED)
    p.text(a['nome'],LEFT+5,136,381,9.0,True,minsize=7.0)
    p.text('RA ESCOLAR',LEFT+399,126,118,6.5,True,color=MUTED)
    p.text(a['ra_escolar'] or a['ra'],LEFT+399,136,118,8.5,minsize=6.2)
    p.rule(LEFT,150,RIGHT,150)
    for label,val,x,w in [('NASCIMENTO',_date(a['nascimento']),0,112),('LOCALIDADE',a['localidade'],112,195),('UF',a['uf'],307,40),('NACIONALIDADE',a['nacionalidade'],347,176)]:
        p.text(label,LEFT+x+3,154,w-5,6.3,True,color=MUTED)
        p.text(val,LEFT+x+3,164,w-5,8.1,minsize=6.1)
    p.band('1.2','CERTIDÃO DE NASCIMENTO / DOCUMENTO',179,16)
    p.text('LIVRO',LEFT+5,198,70,6.1,True,color=MUTED);p.text(a['livro'],LEFT+45,198,90,7.2)
    p.text('DISTRITO',LEFT+143,198,70,6.1,True,color=MUTED);p.text(a['distrito'],LEFT+193,198,120,7.2)
    p.text('CIDADE / UF',LEFT+324,198,75,6.1,True,color=MUTED)
    p.text((a['cidade_certidao']+' / '+a['uf_certidao']).strip(' /'),LEFT+394,198,124,7.2)
    p.text('MATRÍCULA DA CERTIDÃO',LEFT+5,211,157,6.1,True,color=MUTED)
    p.text(a['matricula_certidao'],LEFT+151,211,365,7.2)
    p.text('DOCUMENTO ESTRANGEIRO',LEFT+5,223,157,6.1,True,color=MUTED)
    p.text(a['documento_estrangeiro'],LEFT+151,223,365,7.2)
    p.band('2','RESULTADO DOS ESTUDOS REALIZADOS NO ENSINO FUNDAMENTAL',232)
    p.text('2.1  CURRÍCULO / 2.2  ESCOLARIDADE - ANOS INICIAIS',LEFT+4,253,WIDTH-8,7.8,True,color=BLUE)
    legal=('Lei Federal nº 9.394/1996, art. 26; Deliberação CME nº 02/2016; Resoluções SME nº 11/2016, '
           '06/2020 e 03/2026; Resoluções CNE/CP nº 02/2017; CNE/CEB nº 01/2022, 02/2025 e 07/2025; '
           'Lei nº 14.640/2023; Decreto Municipal nº 405/2022.')
    p.fit_lines(legal,LEFT+3,265,WIDTH-6,22,6.0,8)
    y=p.matrix(289,BASE,[x['conceitos'] if x['situacao']=='Concluído' else {} for x in anos],row_h=12.4)
    p.load_row(y,'2.3  CARGA HORÁRIA - BASE COMUM',[v(x,lambda z:carga(z,'base')) for x in anos])
    p.box(LEFT,y+16,WIDTH,40,PAPER,LINE)
    p.text('2.4  FLEXIBILIZAÇÃO CURRICULAR (FC)',LEFT+5,y+19,WIDTH-10,7.2,True,color=BLUE)
    fc=('Flexibilização Curricular (FC): nomenclatura utilizada para estudante da educação especial cuja avaliação pedagógica identificou necessidade significativa de adequação curricular. O conteúdo trabalhado deve ser compatível aos seus processos de aprendizagem e desenvolvimento, e não ao previsto para seu ano no currículo da rede municipal de ensino. Deverá ser anexado relatório pedagógico anual.')
    p.fit_lines(fc,LEFT+5,y+28,WIDTH-10,27,5.9,8)
    y+=62
    p.band('3','PARTE DIVERSIFICADA',y)
    y=p.matrix(y+18,DIV,[x['participacao'] if x['situacao']=='Concluído' else {} for x in anos],row_h=9.6)
    p.load_row(y,'3.1  CARGA HORÁRIA - PARTE DIVERSIFICADA',[v(x,lambda z:carga(z,'div')) for x in anos])
    p.fit_lines('As escolas de atendimento integral deverão considerar os eixos intelectual, esportivo e cultural até 2025. A partir de 2026, considerar os anexos da Resolução SME nº 03/2026 sobre a Matriz Curricular. Os componentes que não correspondem ao modelo de atendimento adotado pela escola devem ser preenchidos com traço. Para o estudante que frequentou a parte diversificada, indicar P de participação.',LEFT+3,y+17,WIDTH-6,31,5.5,7.2)
    y+=51
    p.band('4','ENSINO RELIGIOSO - art. 33 da LDB e Deliberação CME nº 02/2016',y)
    p.load_row(y+18,'CARGA HORÁRIA',[v(x,lambda z:z['ch_religioso']) for x in anos])
    y+=35
    p.band('5','EDUCAÇÃO ESPECIAL - ATENDIMENTO EDUCACIONAL ESPECIALIZADO',y)
    p.text('Decreto nº 12.686/2025; Indicação CME nº 02/2023; Decreto Municipal nº 23/2026.',LEFT+4,y+19,WIDTH-8,5.9,minsize=5.4)
    p.text('Indicar AEE no respectivo ano quando houver frequência neste atendimento.',LEFT+4,y+26,WIDTH-8,6.8)
    p.load_row(y+34,'REGISTRO AEE',[v(x,lambda z:'AEE' if z['aee'] else '-') for x in anos])
    y+=50
    p.band('6','TOTAL DA CARGA HORÁRIA (CAMPOS 2 + 3)',y)
    p.load_row(y+18,'TOTAL ANUAL',[v(x,total) for x in anos])
    y+=37
    p.band('7','ESTUDOS REALIZADOS',y)
    y+=18
    cw=[62,73,219,115,54];labels=['ANO','CICLO / ANO','ESTABELECIMENTO','MUNICÍPIO','ESTADO']
    p.box(LEFT,y,WIDTH,14,PAPER,LINE)
    off=0
    for w,label in zip(cw,labels):
        p.text(label,LEFT+off,y+3,w,6.7,True,'center',BLUE);off+=w
        if off<WIDTH:p.rule(LEFT+off,y,LEFT+off,y+14+5*8.2)
    y+=14
    estudos=[x for x in anos if x['situacao']!='Não cursado']
    for i in range(5):
        row=estudos[i] if i<len(estudos) else None
        if i%2:p.box(LEFT,y+i*8.2,WIDTH,9.2,PAPER,None)
        p.rule(LEFT,y+(i+1)*8.2,RIGHT,y+(i+1)*8.2)
        if row:
            vals=[row['ano_letivo'],str(row['serie'])+'º ano',row['estabelecimento'],row['municipio'],row['uf']]
            off=0
            for w,val in zip(cw,vals):p.text(val,LEFT+off,y+i*8.2+1.5,w,6.5,align='center',minsize=5.5);off+=w
    p.rule(LEFT,y,LEFT,y+5*8.2);p.rule(RIGHT,y,RIGHT,y+5*8.2)
    p.footer(1);_mark(c,dados,rascunho);c.showPage()
    # VERSO: inicia pelo campo 8.
    p.band('8','TRANSFERÊNCIA DURANTE O ANO LETIVO',35)
    tr=dados['transferencia'];on=tr['ativa']
    p.text('8.1  ENSINO FUNDAMENTAL',LEFT+4,57,WIDTH-8,8.0,True,color=BLUE)
    for label,val,x,w in [('ANO',str(tr['serie'])+'º' if on else '',0,95),('TURMA',tr['turma'] if on else '',105,160),('Nº DE CHAMADA',tr['chamada'] if on else '',280,139),('DATA',_date(tr['data']) if on else '',429,94)]:
        p.text(label,LEFT+x+3,74,w-5,6.4,True,color=MUTED);p.text(val,LEFT+x+3,86,w-5,9,True)
        p.rule(LEFT+x+2,99,LEFT+x+w-5,99)
    for label,key,x,w in [('DIAS LETIVOS','dias',0,110),('AUSÊNCIAS','ausencias',120,115),('AUSÊNCIAS COMPENSADAS','compensadas',245,168),('FREQUÊNCIA (%)','frequencia',423,100)]:
        p.text(label,LEFT+x+3,106,w-5,6.3,True,color=MUTED)
        p.text(tr[key] if on else '',LEFT+x+3,118,w-5,8.3)
        p.rule(LEFT+x+2,131,LEFT+x+w-5,131)
    p.text('8.2  CURRÍCULO - RESULTADOS TRIMESTRAIS',LEFT+4,140,WIDTH-8,8.0,True,color=BLUE)
    def trimvals(keys):
        result=[]
        for i in range(3): result.append({k:(tr['conceitos'][k][i] if on else '') for k in keys})
        return result
    def trimester(y,keys,values):
        labw=WIDTH-3*83
        p.box(LEFT,y,WIDTH,18,PALE,LINE)
        p.text('COMPONENTE CURRICULAR',LEFT+5,y+4,labw-6,7.3,True,color=BLUE)
        for i in range(3):
            x=LEFT+labw+i*83;p.rule(x,y,x,y+18+len(keys)*18)
            p.text(f'{i+1}º TRIMESTRE',x,y+5,83,6.5,True,'center',BLUE)
        y+=18
        for j,k in enumerate(keys):
            if j%2:p.box(LEFT,y+j*18,WIDTH,18,PAPER,None)
            p.text(k,LEFT+5,y+j*18+5,labw-8,7.6,minsize=6.4)
            for i in range(3):p.text(values[i].get(k,''),LEFT+labw+i*83,y+j*18+4,83,8,True,'center')
            p.rule(LEFT,y+(j+1)*18,RIGHT,y+(j+1)*18)
        p.rule(LEFT,y,LEFT,y+len(keys)*18);p.rule(RIGHT,y,RIGHT,y+len(keys)*18)
        return y+len(keys)*18
    y=trimester(154,BASE,trimvals(BASE))
    p.band('','PARTE DIVERSIFICADA',y+12)
    y=trimester(y+30,DIV[3:],trimvals(DIV[3:]))
    p.band('9','OBSERVAÇÕES',y+15)
    top=y+33;height=150
    p.box(LEFT,top,WIDTH,height,None,LINE)
    for j in range(1,15):p.rule(LEFT,top+j*10,RIGHT,top+j*10,HexColor('#D8E0E7'),.35)
    p.fit_lines(dados['observacoes'],LEFT+5,top,WIDTH-10,height-4,7.1,10)
    y=top+height+12
    p.band('10','CERTIFICADO',y)
    p.box(LEFT,y+18,WIDTH,56,None,LINE)
    p.text('O diretor da',LEFT+12,y+27,91,8.0)
    p.text(e['nome'] if dados['certificar'] else '',LEFT+103,y+27,WIDTH-118,8.2,True)
    p.text('de acordo com o art. 24, inciso VII, da Lei Federal nº 9.394/1996, certifica que',LEFT+12,y+39,WIDTH-24,7.6)
    p.text(a['nome'] if dados['certificar'] else '',LEFT+12,y+50,WIDTH-24,8.3,True)
    cert=(f"RA {a['ra']}  ·  concluiu o {dados['serie_certificada']}º ano do Ensino Fundamental em {dados['ano_certificado']}." if dados['certificar'] else 'RA:                                      Conclusão:                                              Ano letivo:')
    p.text(cert,LEFT+12,y+63,WIDTH-24,7.7,minsize=6.4)
    y+=76
    p.band('11','ASSINATURAS',y)
    p.box(LEFT,y+18,WIDTH,70,None,LINE)
    p.text('Limeira, '+_date(dados['data_emissao']),LEFT+12,y+26,WIDTH-24,8.3)
    p.rule(LEFT+26,y+55,LEFT+244,y+55,INK,.6)
    p.rule(LEFT+279,y+55,RIGHT-24,y+55,INK,.6)
    p.text(e['secretario'],LEFT+22,y+58,226,7.1,True,'center',minsize=6.1)
    p.text(e['diretor'],LEFT+274,y+58,WIDTH-292,7.1,True,'center',minsize=6.1)
    p.text('SECRETÁRIO(A) DE ESCOLA',LEFT+22,y+70,226,6.3,align='center',color=MUTED)
    p.text('DIRETOR(A) DE ESCOLA',LEFT+274,y+70,WIDTH-292,6.3,align='center',color=MUTED)
    p.footer(2);_mark(c,dados,rascunho)
    c.save();buf.seek(0);return buf

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
