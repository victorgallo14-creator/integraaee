"""PDF vetorial de duas páginas, sem XLS ou fontes externas. Usa logo_prefeitura.png se disponível."""
from io import BytesIO
from datetime import date
from xml.sax.saxutils import escape
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.pagesizes import A4
from reportlab.platypus import Paragraph
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.lib.colors import HexColor
from reportlab.pdfbase.ttfonts import TTFont
from pathlib import Path

_LOGO_ARQUIVO = 'logo_prefeitura.png'
def _caminho_logo_prefeitura():
    for p in (Path(__file__).resolve().with_name(_LOGO_ARQUIVO), Path.cwd() / _LOGO_ARQUIVO):
        if p.is_file(): return p
    return None

# Cores monocromáticas para o layout oficial tabular
INK = HexColor('#000000')
BLUE = HexColor('#000000') 
PALE = HexColor('#D9D9D9') # Fundo cinza das faixas
PAPER = HexColor('#FFFFFF')
LINE = HexColor('#000000')
MUTED = HexColor('#000000')

LEFT, RIGHT = 36, A4[0] - 36
WIDTH = RIGHT - LEFT

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
    def box(self, x, y, w, h, fill=None, stroke=LINE, lw=0.8):
        c=self.c; c.setLineWidth(lw)
        if fill: c.setFillColor(fill)
        if stroke: c.setStrokeColor(stroke)
        c.rect(x, A4[1]-y-h, w, h, stroke=int(bool(stroke)), fill=int(bool(fill)))
    def rule(self, x1,y1,x2,y2,color=LINE,lw=0.8):
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
    def fit_lines(self,value,x,y,w,h,size=7.1,leading=9,color=INK):
        rows=[]
        for paragraph in str(value or '').split('\n'):
            rows.extend(simpleSplit(paragraph,_REG,size,w-6) if paragraph else [''])
        if len(rows)*leading>h-2:
            raise ValueError('Texto excede o espaço reservado no PDF: '+str(value)[:65])
        for i,line in enumerate(rows): self.text(line,x+2,y+2+i*leading,w-4,size,color=color,minsize=5.2)
        return len(rows)
    def band(self,num,title,y,h=14):
        self.box(LEFT,y,WIDTH,h,PALE,LINE)
        if num:
            self.box(LEFT,y,20,h,None,LINE)
            self.text(num,LEFT,y+3,20,8.5,True,'center')
            self.text(title,LEFT+24,y+3,WIDTH-24,8.5,True)
        else:
            self.text(title,LEFT,y+3,WIDTH,8.5,True,'center')
    def footer(self,page):
        pass # Sem rodapé no padrão visual fornecido
    def matrix(self,y,rows,values,heading=True,row_h=12,col0=282,headers=None):
        cols=[LEFT+col0+i*(WIDTH-col0)/5 for i in range(6)]
        for i,name in enumerate(rows):
            self.box(LEFT,y+i*row_h,WIDTH,row_h,PAPER,LINE)
            self.text(name,LEFT+2,y+i*row_h+2,col0-4,7.5,minsize=6.2)
            for j in range(5):
                v=values[j].get(name,'') if j<len(values) else ''
                self.text(v,cols[j],y+i*row_h+2,cols[j+1]-cols[j],8,True,'center')
        for x in cols[:-1]: self.rule(x,y,x,y+len(rows)*row_h)
        return y+len(rows)*row_h
    def load_row(self,y,title,values,h=14,col0=282,num=None, align_title='left'):
        self.box(LEFT,y,WIDTH,h,PAPER,LINE)
        if num:
            self.box(LEFT,y,20,h,None,LINE)
            self.text(num,LEFT,y+2,20,8.5,True,'center')
            self.text(title,LEFT+24,y+2,col0-26,8.5,True,align_title)
        else:
            self.text(title,LEFT+2,y+2,col0-4,8.5,True,align_title)
        cw=(WIDTH-col0)/5
        for j,v in enumerate(values):
            x=LEFT+col0+j*cw
            self.rule(x,y,x,y+h)
            self.text(v,x,y+2,cw,8,True,'center')

def _date(value):
    try:return date.fromisoformat(str(value)).strftime('%d/%m/%Y')
    except (ValueError,TypeError):return ''
def _date_parts(value):
    try:
        d = date.fromisoformat(str(value))
        return f"{d.day:02d}", f"{d.month:02d}", str(d.year)
    except: return '', '', ''

def _mark(c,d,rascunho):
    if d.get('demonstracao') or rascunho:
        c.setFont(_BOLD,7.3);c.setFillColor(HexColor('#A52B2B'))
        c.drawCentredString(A4[0]/2,12,'DEMONSTRAÇÃO - SEM VALIDADE' if d.get('demonstracao') else 'RASCUNHO - NÃO EMITIDO')

def _header(p,e):
    c=p.c
    logo=_caminho_logo_prefeitura()
    if logo:
        try:
            c.drawImage(ImageReader(str(logo)),LEFT+5,A4[1]-75,70,60,preserveAspectRatio=True,anchor='c',mask='auto')
        except Exception: pass
    
    # Textos do cabeçalho alinhados à direita do brasão
    ox = LEFT + 90
    lh = 10 # line height
    cy = 20
    
    p.text('ESCOLA:', ox, cy, 60, 7.5, True); p.text(e['nome'], ox+60, cy, 330, 8.5, True)
    p.rule(ox+60, cy+9, RIGHT, cy+9, LINE, 0.5)
    
    cy+=lh
    p.text('ATO DE CRIAÇÃO:', ox, cy, 80, 7.5, True); p.text(e['ato'], ox+80, cy, 310, 8.5)
    p.rule(ox+80, cy+9, RIGHT, cy+9, LINE, 0.5)
    
    cy+=lh
    p.text('ENDEREÇO:', ox, cy, 60, 7.5, True); p.text(e['endereco'], ox+60, cy, 330, 8.5)
    p.rule(ox+60, cy+9, RIGHT, cy+9, LINE, 0.5)
    
    cy+=lh
    p.text('BAIRRO:', ox, cy, 45, 7.5, True); p.text(e['bairro'], ox+45, cy, 180, 8.5)
    p.rule(ox+45, cy+9, ox+225, cy+9, LINE, 0.5)
    p.text('MUNICÍPIO:', ox+230, cy, 55, 7.5, True); p.text(e['municipio'], ox+285, cy, 105, 8.5)
    p.rule(ox+285, cy+9, RIGHT, cy+9, LINE, 0.5)
    
    cy+=lh
    p.text('CEP:', ox, cy, 30, 7.5, True); p.text(e['cep'], ox+30, cy, 80, 8.5)
    p.rule(ox+30, cy+9, ox+110, cy+9, LINE, 0.5)
    p.text('TELEFONES:', ox+115, cy, 65, 7.5, True); p.text(e['telefone'], ox+180, cy, 210, 8.5)
    p.rule(ox+180, cy+9, RIGHT, cy+9, LINE, 0.5)
    
    cy+=lh
    p.text('E-MAIL:', ox, cy, 40, 7.5, True); p.text(e['email'], ox+40, cy, 350, 8.5, color=HexColor('#0000EE'))
    p.rule(ox+40, cy+9, RIGHT, cy+9, LINE, 0.5)
    
    p.text('SECRETARIA MUNICIPAL DE EDUCAÇÃO DE LIMEIRA/SP', ox, cy+14, WIDTH-90, 9.5, True, 'center')
    p.rule(ox, cy+25, RIGHT, cy+25, LINE, 1.2)
    
    p.band(None, 'HISTÓRICO ESCOLAR', cy+27, 14)

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

    # FRENTE:
    _header(p,e)
    y = 104
    p.box(LEFT, y, WIDTH, 14, PALE, LINE)
    p.box(LEFT, y, 20, 14, None, LINE)
    p.text('1.1', LEFT, y+3, 20, 8.5, True, 'center')
    p.text('DADOS DO ESTUDANTE', LEFT+24, y+3, 200, 8.5, True)
    p.box(RIGHT-150, y, 150, 14, None, LINE)
    p.text('RA', RIGHT-150, y+3, 150, 8.5, True, 'center')
    
    y += 14
    p.box(LEFT, y, WIDTH, 14, PAPER, LINE)
    p.text('NOME DO ALUNO:', LEFT+2, y+3, 100, 8, True)
    p.text(a['nome'], LEFT+90, y+3, 250, 9)
    p.box(RIGHT-150, y, 150, 14, None, LINE)
    p.text('RA ESCOLAR:', RIGHT-148, y+3, 140, 8, True)
    
    y += 14
    p.box(LEFT, y, WIDTH, 18, PAPER, LINE)
    p.text('NASCIMENTO:', LEFT+2, y+5, 90, 8, True)
    
    col_w = (WIDTH - 90 - 75) / 3 
    c1 = LEFT + 90
    p.box(c1, y, col_w, 9, None, LINE); p.text('LOCALIDADE', c1, y+1, col_w, 6, True, 'center')
    p.box(c1, y+9, col_w, 9, None, LINE); p.text(a['localidade'], c1, y+10, col_w, 8, align='center')
    
    c2 = c1 + col_w
    p.box(c2, y, col_w, 9, None, LINE); p.text('ESTADO', c2, y+1, col_w, 6, True, 'center')
    p.box(c2, y+9, col_w, 9, None, LINE); p.text(a['uf'], c2, y+10, col_w, 8, align='center')
    
    c3 = c2 + col_w
    p.box(c3, y, col_w, 9, None, LINE); p.text('NACIONALIDADE', c3, y+1, col_w, 6, True, 'center')
    p.box(c3, y+9, col_w, 9, None, LINE); p.text(a['nacionalidade'], c3, y+10, col_w, 8, align='center')
    
    c_date = c3 + col_w
    d_day, d_month, d_year = _date_parts(a['nascimento'])
    p.box(c_date, y, 25, 9, None, LINE); p.text('DIA', c_date, y+1, 25, 6, True, 'center')
    p.box(c_date, y+9, 25, 9, None, LINE); p.text(d_day, c_date, y+10, 25, 8, align='center')
    p.box(c_date+25, y, 25, 9, None, LINE); p.text('MÊS', c_date+25, y+1, 25, 6, True, 'center')
    p.box(c_date+25, y+9, 25, 9, None, LINE); p.text(d_month, c_date+25, y+10, 25, 8, align='center')
    p.box(c_date+50, y, 25, 9, None, LINE); p.text('ANO', c_date+50, y+1, 25, 6, True, 'center')
    p.box(c_date+50, y+9, 25, 9, None, LINE); p.text(d_year, c_date+50, y+10, 25, 8, align='center')
    
    y += 18
    p.box(LEFT, y, WIDTH, 14, PAPER, LINE)
    p.box(LEFT, y, 20, 14, None, LINE)
    p.text('1.2', LEFT, y+3, 20, 8.5, True, 'center')
    p.text('CERTIDÃO DE NASCIMENTO', LEFT+24, y+3, 300, 8.5, True)
    p.box(LEFT+350, y, WIDTH-350, 14, None, LINE)
    p.text('LIVRO:', LEFT+352, y+3, 40, 8, True); p.text(a['livro'], LEFT+390, y+3, 100, 8.5)
    
    y += 14
    p.box(LEFT, y, WIDTH, 14, PAPER, LINE)
    p.text('(SUB) DISTRITO:', LEFT+2, y+3, 80, 8, True); p.text(a['distrito'], LEFT+85, y+3, 120, 8.5)
    p.box(LEFT+220, y, 160, 14, None, LINE)
    p.text('CIDADE:', LEFT+222, y+3, 45, 8, True); p.text(a['cidade_certidao'], LEFT+265, y+3, 110, 8.5)
    p.text('ESTADO:', LEFT+385, y+3, 45, 8, True); p.text(a['uf_certidao'], LEFT+430, y+3, 80, 8.5)
    p.rule(LEFT+380, y, LEFT+380, y+14, LINE)
    
    y += 14
    p.box(LEFT, y, WIDTH, 14, PAPER, LINE)
    p.text('CERTIDÃO NOVA - MATRÍCULA:', LEFT+2, y+3, 160, 8, True); p.text(a['matricula_certidao'], LEFT+165, y+3, 300, 8.5)
    
    y += 14
    p.box(LEFT, y, WIDTH, 14, PAPER, LINE)
    p.text('ESTRANGEIRO - DOCUMENTO:', LEFT+2, y+3, 160, 8, True); p.text(a['documento_estrangeiro'], LEFT+165, y+3, 300, 8.5)
    
    y += 18
    p.band('2', 'RESULTADO DOS ESTUDOS REALIZADOS NO ENSINO FUNDAMENTAL', y, 14)
    y += 14
    p.box(LEFT, y, WIDTH, 14, PAPER, LINE)
    p.box(LEFT, y, 20, 14, None, LINE); p.text('2.1', LEFT, y+3, 20, 8.5, True, 'center')
    p.box(LEFT+300, y, 20, 14, None, LINE); p.text('2.2', LEFT+300, y+3, 20, 8.5, True, 'center')
    p.text('ESCOLARIDADE', LEFT+320, y+3, WIDTH-320, 8.5, True, 'center')
    
    y += 14
    p.box(LEFT, y, WIDTH, 35, PAPER, LINE)
    p.text('CURRÍCULO', LEFT+2, y+3, 280, 8.5, True)
    legal=('Lei Federal nº 9.394/1996, art. 26; Deliberação CME nº 02/2016; Resolução SME nº 11/2016; Resolução CNE/CP nº 02/2017; Resolução SME nº 06/2020; Resolução CNE/CEB nº 01/2022; Lei nº 14.640/2023; Resolução CNE/CEB nº 02/2025; Resolução CNE/CEB nº 07/2025; Decreto Municipal nº 405/2022; Resolução SME nº 03/2026')
    p.fit_lines(legal, LEFT+2, y+14, 290, 20, 4.5, 5.5)
    
    p.rule(LEFT+300, y, LEFT+300, y+35)
    p.text('Anos Iniciais', LEFT+300, y+15, WIDTH-300, 9, True, 'center')
    
    # Cabeçalho da Tabela
    y += 35
    p.box(LEFT, y, WIDTH, 14, PALE, LINE)
    cols=[LEFT+300+i*(WIDTH-300)/5 for i in range(6)]
    for j in range(5):
        p.text(f'{j+1}º Ano', cols[j], y+3, cols[j+1]-cols[j], 8.5, True, 'center')
        p.rule(cols[j], y, cols[j], y+14)
    p.rule(cols[5], y, cols[5], y+14)
    
    # Matriz Base Comum
    y += 14
    y = p.matrix(y, BASE, [x['conceitos'] if x['situacao']=='Concluído' else {} for x in anos], heading=False, row_h=12, col0=300)
    
    p.load_row(y, 'CARGA HORÁRIA', [v(x, lambda z: carga(z,'base')) for x in anos], h=14, col0=300, num='2.3', align_title='left')
    y += 14
    
    p.box(LEFT, y, WIDTH, 24, PAPER, LINE)
    p.box(LEFT, y, 20, 24, None, LINE); p.text('2.4', LEFT, y+8, 20, 8.5, True, 'center')
    fc=('Flexibilização Curricular (FC): nomenclatura que deve ser utilizada para o estudante da educação especial cuja avaliação pedagógica identificou necessidade significativa de adequação curricular e diante disso o conteúdo trabalhado foi compatível aos seus processos de aprendizagem e desenvolvimento e não ao previsto para o seu ano de escolaridade. Deverá ser anexado relatório pedagógico anual.')
    p.fit_lines(fc, LEFT+22, y+2, WIDTH-24, 20, 5.5, 7)
    
    y += 24
    p.band('3', 'PARTE DIVERSIFICADA', y, 14)
    y += 14
    p.box(LEFT, y, WIDTH, 14, PALE, LINE)
    for j in range(5):
        p.text(f'{j+1}º Ano', cols[j], y+3, cols[j+1]-cols[j], 8.5, True, 'center')
        p.rule(cols[j], y, cols[j], y+14)
    
    y += 14
    y = p.matrix(y, DIV, [x['participacao'] if x['situacao']=='Concluído' else {} for x in anos], heading=False, row_h=12, col0=300)
    
    p.load_row(y, 'CARGA HORÁRIA', [v(x, lambda z: carga(z,'div')) for x in anos], h=14, col0=300, num='3.1')
    y += 14
    
    p.box(LEFT, y, WIDTH, 24, PAPER, LINE)
    obs_txt = ('OBS: As escolas de atendimento integral deverão considerar os eixos intelectual, esportivo e cultural até o ano de 2025. A partir do ano de 2026, para preenchimento deste campo da Parte Diversificada, considerar os anexos da Resolução SME nº 03/26 que trata da Matriz Curricular. Os campos de disciplinas que não correspondem ao modelo de atendimento adotado pela escola deverão ser preenchido com traço. Para o estudante que frequentou a parte diversificada, indicar P de participação.')
    p.fit_lines(obs_txt, LEFT+2, y+2, WIDTH-4, 20, 5.5, 7)
    
    y += 24
    p.band('4', 'ENSINO RELIGIOSO (art. 33-LDB e Deliberação CME nº 02/2016)', y, 14)
    y += 14
    p.load_row(y, 'CARGA HORÁRIA', [v(x, lambda z: z['ch_religioso']) for x in anos], h=14, col0=300)
    
    y += 16
    p.box(LEFT, y, WIDTH, 24, PALE, LINE)
    p.box(LEFT, y, 20, 24, None, LINE); p.text('5', LEFT, y+8, 20, 8.5, True, 'center')
    p.text('EDUCAÇÃO ESPECIAL - ATENDIMENTO EDUCACIONAL ESPECIALIZADO', LEFT+24, y+4, WIDTH-24, 8.5, True)
    p.text('Decreto Nº 12.686/2025- Indicação Cme Nº02/2023 -Decreto Municipal Nº 23/2026', LEFT+24, y+14, WIDTH-24, 6, True)
    
    y += 24
    p.box(LEFT, y, WIDTH, 16, PAPER, LINE)
    p.fit_lines('Indicar a sigla AEE (Atendimento Educacional Especializado) para o estudante que frequentou esse tipo de atendimento no respectivo ano.', LEFT+2, y+2, 296, 14, 5.5, 6.5)
    for j in range(5):
        p.rule(cols[j], y, cols[j], y+16)
        p.box(cols[j], y, cols[j+1]-cols[j], 16, PALE, None)
        p.text(f'{j+1}º ano', cols[j], y+4, cols[j+1]-cols[j], 8.5, True, 'center')
    
    y += 16
    p.load_row(y, '', [v(x, lambda z: 'AEE' if z['aee'] else '-') for x in anos], h=14, col0=300)
    
    y += 16
    p.band('6', 'TOTAL DA CARGA HORÁRIA (CAMPO 2 + CAMPO 3)', y, 14)
    y += 14
    p.load_row(y, '', [v(x, total) for x in anos], h=14, col0=300)
    
    y += 16
    p.band('7', 'ESTUDOS REALIZADOS', y, 14)
    y += 14
    
    cw=[45, 60, 215, 115, 89]; labels=['ANO', 'CICLO/ANO', 'ESTABELECIMENTO', 'MUNICÍPIO', 'ESTADO']
    p.box(LEFT, y, WIDTH, 14, PAPER, LINE)
    off=0
    for w, label in zip(cw, labels):
        p.text(label, LEFT+off, y+3, w, 8, True, 'center')
        off+=w
        if off<WIDTH: p.rule(LEFT+off, y, LEFT+off, y+14+5*14)
    
    y += 14
    estudos=[x for x in anos if x['situacao']!='Não cursado']
    for i in range(5):
        row=estudos[i] if i<len(estudos) else None
        p.box(LEFT, y+i*14, WIDTH, 14, PAPER, LINE)
        if row:
            vals=[row['ano_letivo'], str(row['serie'])+'º ano', row['estabelecimento'], row['municipio'], row['uf']]
            off=0
            for w, val in zip(cw, vals):
                p.text(val, LEFT+off, y+i*14+3, w, 8, align='center')
                off+=w
                
    y += 5*14
    p.footer(1); _mark(c, dados, rascunho); c.showPage()
    
    # VERSO: Permanece inalterado, iniciando pelo campo 8.
