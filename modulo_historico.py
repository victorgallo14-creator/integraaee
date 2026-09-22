"""Módulo de histórico escolar para integração em aplicação Streamlit.

Uso no aplicativo principal:
    from modulo_historico import renderizar_modulo
    renderizar_modulo()

Não chama set_page_config quando importado. Modelo XLS, brasão, fontes e licença
ficam na pasta modulo_historico_assets ao lado deste arquivo; não usa recursos embutidos em Base64.
Use HISTORICO_DB_PATH ou renderizar_modulo(banco_path=...) para definir o SQLite.
Em hospedagens com disco efêmero, exporte JSON/PDF; o SQLite não substitui um
banco persistente. Não há conexão automática com Supabase ou cadastro externo.
"""
import base64
import tempfile
from pathlib import Path
from types import SimpleNamespace

ASSETS = Path(__file__).resolve().parent / "modulo_historico_assets"

_ARQUIVOS_OBRIGATORIOS = (
    "brasao.png",
    "modelo_oficial.xls",
    "fonts/NimbusSansNarrow-Regular.afm",
    "fonts/NimbusSansNarrow-Regular.pfb",
    "fonts/NimbusSansNarrow-Bold.afm",
    "fonts/NimbusSansNarrow-Bold.pfb",
)

def _validar_assets():
    ausentes = [nome for nome in _ARQUIVOS_OBRIGATORIOS if not (ASSETS / nome).is_file()]
    if ausentes:
        lista = ", ".join(ausentes)
        raise FileNotFoundError(
            f"Recursos do módulo de histórico não encontrados em {ASSETS}: {lista}. "
            "Mantenha a pasta modulo_historico_assets ao lado de modulo_historico.py."
        )

_validar_assets()


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

def novo():
    return {'versao': 1, 'demonstracao': False,
        'escola': {k: '' for k in ['nome','ato','endereco','bairro','municipio','cep','telefone','email','secretario','diretor']},
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

"""PDF vetorial de duas páginas, com geometria e estilos lidos do XLS oficial."""
from pathlib import Path
from io import BytesIO
from datetime import date
from xml.sax.saxutils import escape
import os
import xlrd
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph



def fontes():
    if 'Formulario' in pdfmetrics.getRegisteredFontNames(): return
    windir=Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts'
    if (windir/'ARIALN.TTF').exists() and (windir/'ARIALNB.TTF').exists():
        pdfmetrics.registerFont(TTFont('Formulario',str(windir/'ARIALN.TTF')))
        pdfmetrics.registerFont(TTFont('FormularioBold',str(windir/'ARIALNB.TTF')))
    else:
        for estilo,sufixo in [('Regular',''),('Bold','Bold')]:
            raiz=ASSETS/'fonts'/('NimbusSansNarrow-'+estilo)
            face=pdfmetrics.EmbeddedType1Face(str(raiz)+'.afm',str(raiz)+'.pfb')
            pdfmetrics.registerTypeFace(face)
            pdfmetrics.registerFont(pdfmetrics.Font('Formulario'+sufixo,face.name,'WinAnsiEncoding'))
    pdfmetrics.registerFontFamily('Formulario',normal='Formulario',bold='FormularioBold',italic='Formulario',boldItalic='FormularioBold')

class Formulario:
    def __init__(self,c):
        self.c=c;self.book=xlrd.open_workbook(str(ASSETS/'modelo_oficial.xls'),formatting_info=True)
        self.sheet=self.book.sheet_by_index(0)
        self.left=40.0;self.top=30.0;self.width=A4[0]-80
        widths=[self.sheet.colinfo_map[i].width for i in range(61)]
        self.x=[self.left]
        for w in widths:self.x.append(self.x[-1]+self.width*w/sum(widths))
        self.scale=.915
        self.y=[0.0]
        for r in range(120):self.y.append(self.y[-1]+self.sheet.rowinfo_map[r].height/20*self.scale)
        self.merge={};self.children=set();self.bounds={}
        for r0,r1,c0,c1 in self.sheet.merged_cells:
            self.merge[(r0,c0)]=(r1,c1)
            self.children.update((r,c) for r in range(r0,r1) for c in range(c0,c1) if (r,c)!=(r0,c0))
            self.bounds.update({(r,c):(r0,r1,c0,c1) for r in range(r0,r1) for c in range(c0,c1)})

    def rect(self,r,c,r1=None,c1=None):
        if r1 is None:r1,c1=self.merge.get((r,c),(r+1,c+1))
        return self.x[c],A4[1]-self.top-(self.y[r1]-self.y[self.start]),self.x[c1]-self.x[c],self.y[r1]-self.y[r]

    def texto(self,texto,r,c,r1=None,c1=None,size=8,bold=False,align=0,wrap=False,minsize=5.5):
        if not str(texto).strip():return
        x,y,w,h=self.rect(r,c,r1,c1)
        font='FormularioBold' if bold else 'Formulario'
        texto=str(texto)
        if wrap:
            sz=size
            while True:
                p=Paragraph(escape(texto).replace('\n','<br/>'),ParagraphStyle('celula',fontName=font,fontSize=sz,leading=sz*1.04,alignment=align))
                pw,ph=p.wrap(w-3,h-1)
                if ph<=h-1:break
                sz-=.1
                if sz<minsize:raise ValueError('Texto não cabe no formulário: '+texto[:70])
            p.drawOn(self.c,x+1.5,y+(h-ph)/2)
        else:
            size=min(size,(w-3)/max(pdfmetrics.stringWidth(texto,font,1),.001))
            if size<minsize:raise ValueError('Texto excede a largura do campo: '+texto[:70])
            self.c.setFont(font,size);self.c.setFillColorRGB(0,0,0)
            yy=y+(h-size)/2+size*.18
            if align==1:self.c.drawCentredString(x+w/2,yy,texto)
            elif align==2:self.c.drawRightString(x+w-1.5,yy,texto)
            else:self.c.drawString(x+1.5,yy,texto)

    def pagina(self,start,end):
        self.start=start
        s,b,c=self.sheet,self.book,self.c
        # Bordas por célula preservam exatamente as mesclagens do XLS.
        for r in range(start,end):
            for col in range(61):
                xf=b.xf_list[s.cell_xf_index(r,col)];x,y,w,h=self.rect(r,col,r+1,col+1)
                bg=xf.background
                if bg.fill_pattern==1:
                    rgb=b.colour_map.get(bg.pattern_colour_index)
                    if rgb:
                        c.setFillColorRGB(*[v/255 for v in rgb]);c.rect(x,y,w,h,stroke=0,fill=1)
        c.setStrokeColorRGB(0,0,0);c.setLineWidth(.4)
        for r in range(start,end):
            for col in range(61):
                bo=b.xf_list[s.cell_xf_index(r,col)].border;x,y,w,h=self.rect(r,col,r+1,col+1)
                r0,r1,c0,c1=self.bounds.get((r,col),(r,r+1,col,col+1))
                for sty,coords in [(bo.left_line_style if col==c0 else 0,(x,y,x,y+h)),(bo.right_line_style if col==c1-1 else 0,(x+w,y,x+w,y+h)),(bo.top_line_style if r==r0 else 0,(x,y+h,x+w,y+h)),(bo.bottom_line_style if r==r1-1 else 0,(x,y,x+w,y))]:
                    if sty:c.line(*coords)
        for r in range(start,end):
            for col in range(61):
                value=s.cell_value(r,col)
                if value=='' or (r,col) in self.children:continue
                if str(value).startswith('XXX') or ((23<=r<=30 or 33<=r<=42) and col>=31):continue
                if isinstance(value,float) and value.is_integer():value=str(int(value))
                if r==111 and col==20:continue
                xf=b.xf_list[s.cell_xf_index(r,col)];f=b.font_list[xf.font_index]
                r1,c1=self.merge.get((r,col),(r+1,col+1))
                if (r,col) not in self.merge:
                    c1=next((j for j in range(col+1,61) if s.cell_value(r,j)!=''),61)
                size=f.height/20*self.scale
                # Células do modelo com trechos de tamanhos diferentes.
                if (r,col)==(20,0):
                    self.texto('CURRÍCULO',r,col,r+1,31,size=8,bold=True)
                    legal=str(value).split('Lei Federal',1)[1]
                    self.texto('Lei Federal'+legal,r+1,col,23,31,size=5.3,wrap=True,minsize=4.7)
                elif (r,col)==(48,2):
                    partes=str(value).split('Decreto',1)
                    self.texto(partes[0].strip(),48,2,49,61,size=8,bold=True)
                    # Linha legal no rodapé da mesma célula (22,5 pt no XLS).
                    xx,yy,ww,hh=self.rect(48,2,49,61)
                    c.setFont('Formulario',5.4);c.drawString(xx+1.5,yy+1,'Decreto'+partes[1])
                else:
                    self.texto(value,r,col,r1,c1,size=size,bold=bool(f.bold),align={2:1,3:2}.get(xf.alignment.hor_align,0),wrap=bool(xf.alignment.text_wrapped),minsize=4.7)
        if start==0:
            x,y,w,h=self.rect(43,0,45,61);c.rect(x,y,w,h,stroke=1,fill=0)
            x,y,w,h=self.rect(0,0,6,12)
            c.drawImage(str(ASSETS/'brasao.png'),x+4,y+1,w-8,h-2,preserveAspectRatio=True,anchor='c',mask='auto')

def gerar_pdf(dados,rascunho=False):
    erros,_=validar(dados,exigir_conferencia=not rascunho)
    if erros and not rascunho:raise ValueError('\n'.join(erros))
    fontes();buffer=BytesIO();c=canvas.Canvas(buffer,pagesize=A4,pageCompression=1)
    c.setTitle('Histórico Escolar - '+dados['aluno']['nome']);c.setAuthor(dados['escola']['nome'])
    f=Formulario(c);a=dados['aluno'];e=dados['escola']
    def t(v,r,col,r1,c1,**kw):f.texto(v,r,col,r1,c1,**kw)
    def marca():
        if dados['demonstracao'] or rascunho:
            c.saveState();c.setFillColorRGB(.70,.14,.14);c.setFont('Helvetica-Bold',8)
            c.drawCentredString(A4[0]/2,15,'DEMONSTRAÇÃO - SEM VALIDADE' if dados['demonstracao'] else 'RASCUNHO - NÃO EMITIDO');c.restoreState()
    f.pagina(0,64)
    for k,r,col,end in [('nome',0,21,52),('ato',1,21,52),('endereco',2,21,52),('bairro',3,18,36),('municipio',3,44,61),('cep',4,15,23),('telefone',4,33,52),('email',5,17,52)]:
        t(e[k],r,col,r+1,end,size=7.4)
    t(a['ra'],9,52,10,61,size=7.6,align=1)
    t(a['nome'],10,9,11,40,size=8,bold=True)
    t(a['ra_escolar'],10,48,11,61,size=8)
    for k,col,end in [('localidade',12,33),('uf',33,40),('nacionalidade',40,51)]:t(a[k],12,col,13,end,size=8,align=1)
    if a['nascimento']:
        try:
            dt=date.fromisoformat(a['nascimento'])
            for v,col,end in [(str(dt.day).zfill(2),51,54),(str(dt.month).zfill(2),54,57),(dt.year,57,61)]:t(v,12,col,13,end,align=1)
        except ValueError:pass
    for k,r,col,end in [('livro',13,44,61),('distrito',14,8,23),('cidade_certidao',14,28,45),('uf_certidao',14,50,61),('matricula_certidao',15,20,61),('documento_estrangeiro',16,20,61)]:t(a[k],r,col,r+1,end,size=7.5)
    for i,ano in enumerate(dados['anos']):
        col=31+6*i
        if ano['situacao']!='Concluído':continue
        for j,disc in enumerate(BASE):t(ano['conceitos'][disc],23+j,col,24+j,col+6,align=1)
        for j,disc in enumerate(DIV):t(ano['participacao'][disc],33+j,col,34+j,col+6,align=1)
        try:
            t(carga(ano,'base'),30,col,31,col+6,size=7.8,align=1)
            t(carga(ano,'div'),42,col,43,col+6,size=7.8,align=1)
            t(total(ano),52,col,53,col+6,size=7.8,align=1)
        except ValueError:
            if not rascunho:raise
        t(ano['ch_religioso'],46,col,47,col+6,size=7.8,align=1)
        t('AEE' if ano['aee'] else '-',50,col,51,col+6,align=1)
    estudos=[x for x in dados['anos'] if x['situacao']!='Não cursado']
    for i,ano in enumerate(estudos):
        for v,col,end in [(ano['ano_letivo'],0,6),(str(ano['serie'])+'º ANO',6,12),(ano['estabelecimento'],12,39),(ano['municipio'],39,52),(ano['uf'],52,61)]:
            t(v,56+i,col,57+i,end,size=7.5,align=1)
    marca();c.showPage();f.pagina(65,120)
    tr=dados['transferencia']
    if tr['ativa']:
        for v,r,col,end in [(str(tr['serie'])+'º',66,6,12),(tr['turma'],66,30,36),(tr['chamada'],66,55,61),(tr['dias'],70,6,12),(tr['ausencias'],70,19,25),(tr['compensadas'],70,39,45),(tr['frequencia'],70,55,61)]:t(v,r,col,r+1,end,size=8,align=1)
        if tr['data']:
            try:
                dt=date.fromisoformat(tr['data'])
                for v,col,end in [(dt.day,28,31),(dt.month,32,35),(dt.year,36,42)]:t(v,68,col,69,end,align=1)
            except ValueError:pass
        for disc,row in list(zip(BASE,range(73,80)))+list(zip(DIV[3:],range(82,88))):
            for i,v in enumerate(tr['conceitos'][disc]):t(v,row,37+i*8,row+1,45+i*8,align=1)
    # Observações respeitam as linhas do impresso e rejeitam excedentes.
    from reportlab.lib.utils import simpleSplit
    linhas=[]
    for par in dados['observacoes'].split('\n'):
        linhas.extend(simpleSplit(par,'Formulario',8,f.width-4) if par else [''])
    if len(linhas)>14:raise ValueError('Observações excedem as 14 linhas disponíveis. Reduza o texto ou use documento anexo.')
    for i,linha in enumerate(linhas):t(linha,90+i,0,91+i,61,size=8)
    t('concluiu o ______ do Ensino Fundamental, no ano letivo de',111,20,112,51,size=8)
    if dados['certificar']:
        t(e['nome'],107,15,108,61,size=8)
        t(a['nome'],109,33,110,61,size=8)
        t(a['ra'],111,3,112,20,size=8)
        # Substitui somente a linha variável da declaração.
        xx,yy,ww,hh=f.rect(111,20,112,51);c.setFillColorRGB(1,1,1);c.rect(xx+.5,yy+.5,ww-1,hh-1,stroke=0,fill=1)
        t('concluiu o '+str(dados['serie_certificada'])+'º ano do Ensino Fundamental, no ano letivo de',111,20,112,51,size=8)
        t(dados['ano_certificado'],111,51,112,60,size=8,align=1)
    try:dt=date.fromisoformat(dados['data_emissao']);t(dt.strftime('%d/%m/%Y'),116,6,117,18,size=8,align=1)
    except ValueError:pass
    t(e['secretario'],116,20,117,40,size=7.5,align=1)
    t(e['diretor'],116,41,117,61,size=7.5,align=1)
    marca();c.save();buffer.seek(0);return buffer

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
import base64
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
            encoded=base64.b64encode(pdf).decode()
            st.components.v1.html(f'<iframe title="Prévia do histórico" src="data:application/pdf;base64,{encoded}" width="100%" height="820"></iframe>',height=830)
        elif result:st.info('Os dados mudaram. Gere uma nova prévia ou emissão.')
        if estado_historico.get('ident'):
            with st.expander('Emissões anteriores deste registro'):
                for ident,dt,digest,pdf in repo.emissoes(DB,estado_historico.ident):
                    st.download_button(dt+' · baixar cópia',pdf,file_name='Historico_'+ident+'.pdf',mime='application/pdf',key=ident)
                    st.caption('SHA-256: '+digest)

if __name__=='__main__':
    st.set_page_config(page_title='Histórico Escolar | Limeira',page_icon='📄',layout='wide')
    renderizar_modulo()
