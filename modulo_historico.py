import streamlit as st
import io
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT

# ==========================================
# 1. INTEGRAÇÃO DE DADOS (MOCK PARA TESTE)
# ==========================================
def buscar_dados_historico(ra):
    # Lógica futura de integração com o banco de dados (Supabase/SQLite)
    return {
        "aluno": {
            "nome": "NOME COMPLETO DO ESTUDANTE AQUI",
            "ra": ra,
            "ra_escolar": "12345-6",
            "nascimento_loc": "LIMEIRA",
            "nascimento_est": "SP",
            "nacionalidade": "BRASILEIRA",
            "dia": "14", "mes": "11", "ano": "2015",
            "certidao_distrito": "1º SUBDISTRITO",
            "certidao_livro": "A-123",
            "certidao_cidade": "LIMEIRA",
            "certidao_estado": "SP",
            "certidao_nova": "123456.78.90.1112.34567.8901234-56",
            "estrangeiro_doc": "-"
        },
        "curriculo": {
            "LÍNGUA PORTUGUESA": ["B", "", "", "", ""],
            "GEOGRAFIA": ["B", "", "", "", ""],
            "MATEMÁTICA": ["B", "", "", "", ""],
            "CIÊNCIAS": ["B", "", "", "", ""],
            "HISTÓRIA": ["B", "", "", "", ""],
            "ED. FÍSICA": ["B", "", "", "", ""],
            "ARTE": ["B", "", "", "", ""]
        },
        "ch_curriculo": "1020H/A",
        "parte_diversificada": {
            "EIXO INTELECTUAL": ["", "", "", "", ""],
            "EIXO ESPORTIVO": ["-", "", "", "", ""],
            "EIXO CULTURAL": ["-", "", "", "", ""],
            "LINGUAGENS E TECNOLOGIAS": ["P", "", "", "", ""],
            "ACOMPANHAMENTO PEDAGÓGICO": ["P", "", "", "", ""],
            "PRÁTICAS EXPERIMENTAIS E DE TUTORIA DE ESTUDO": ["P", "", "", "", ""],
            "PRÁTICAS DE ESTUDO": ["P", "", "", "", ""],
            "LINGUAGENS": ["P", "", "", "", ""],
            "ESPORTE E EDUCAÇÃO DO MOVIMENTO": ["P", "", "", "", ""]
        },
        "ch_diversificada": "1000H/A",
        "aee": ["", "", "", "", ""],
        "ch_total": "2020H/A",
        "estudos": [
            ["2022", "1º ANO", "CEIEF RAFAEL AFFONSO LEITE", "LIMEIRA", "SP"],
            ["", "", "", "", ""],
            ["", "", "", "", ""],
            ["", "", "", "", ""],
            ["", "", "", "", ""]
        ],
        "transferencia": {
            "ano": "", "turma": "", "chamada": "", "transferido_em": "",
            "dias_letivos": "", "ausencias": "", "compensadas": "", "frequencia": "",
            "curriculo": {
                "LÍNGUA PORTUGUESA": ["", "", ""],
                "GEOGRAFIA": ["", "", ""],
                "MATEMÁTICA": ["", "", ""],
                "CIÊNCIAS": ["", "", ""],
                "HISTÓRIA": ["", "", ""],
                "ED. FÍSICA": ["", "", ""],
                "ARTE": ["", "", ""]
            },
            "diversificada": {
                "LINGUAGENS E TECNOLOGIAS": ["", "", ""],
                "ACOMPANHAMENTO PEDAGÓGICO": ["", "", ""],
                "PRÁTICAS EXPERIMENTAIS E DE TUTORIA DE ESTUDO": ["", "", ""],
                "PRÁTICAS DE ESTUDO": ["", "", ""],
                "LINGUAGENS": ["", "", ""],
                "ESPORTE E EDUCAÇÃO DO MOVIMENTO": ["", "", ""]
            }
        }
    }

# ==========================================
# 2. GERAÇÃO DO PDF EXATO (REPORTLAB PLATYPUS)
# ==========================================
def regra_do_traco(valor):
    """Aplica o traço em campos nulos ou vazios para evitar adulteração (Regra Oficial)."""
    return valor if valor and str(valor).strip() != "" else "-"

def gerar_pdf(dados):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, 
        rightMargin=10*mm, leftMargin=10*mm, 
        topMargin=10*mm, bottomMargin=10*mm
    )
    
    elementos = []
    styles = getSampleStyleSheet()
    
    # Estilos de texto
    s_normal = ParagraphStyle('normal', fontName='Helvetica', fontSize=7, leading=8)
    s_bold = ParagraphStyle('bold', fontName='Helvetica-Bold', fontSize=7, leading=8)
    s_legal = ParagraphStyle('legal', fontName='Helvetica', fontSize=5.5, leading=6, alignment=TA_JUSTIFY)
    s_center = ParagraphStyle('center', fontName='Helvetica-Bold', fontSize=8, alignment=TA_CENTER)
    s_title = ParagraphStyle('title', fontName='Helvetica-Bold', fontSize=10, alignment=TA_CENTER)
    s_header = ParagraphStyle('header', fontName='Helvetica', fontSize=8, leading=10)
    
    def celula(texto, estilo=s_normal):
        return Paragraph(texto, estilo)

    # ---------------------------------------------------------
    # CABEÇALHO OFICIAL (Logo local + Linhas Sublinhadas)
    # ---------------------------------------------------------
    img_logo = ""
    if os.path.exists("brasao.png"):
        img_logo = Image("brasao.png", width=35*mm, height=35*mm)
    elif os.path.exists("logo_prefeitura.png"):
        img_logo = Image("logo_prefeitura.png", width=35*mm, height=35*mm)
    else:
        img_logo = celula("PREFEITURA MUNICIPAL<br/>DE LIMEIRA<br/>ESTADO DE SÃO PAULO", s_center)

    header_text_data = [
        [celula("ESCOLA:", s_header), celula("CEIEF RAFAEL AFFONSO LEITE", s_center), "", "", ""],
        [celula("ATO DE CRIAÇÃO:", s_header), celula("JOM nº XXXX", s_center), "", "", ""],
        [celula("ENDEREÇO:", s_header), celula("RUA EXEMPLO, 123", s_center), "", "", ""],
        [celula("BAIRRO:", s_header), celula("CENTRO", s_center), celula("MUNICÍPIO:", s_header), celula("LIMEIRA", s_center), ""],
        [celula("CEP:", s_header), celula("13480-000", s_center), celula("TELEFONES:", s_header), celula("(19) 3400-0000", s_center), ""],
        [celula("E-MAIL:", s_header), celula("<font color='blue'>ceief.rafael.leite@limeira.sp.gov.br</font>", s_center), "", "", ""]
    ]
    t_info = Table(header_text_data, colWidths=[28*mm, 55*mm, 20*mm, 40*mm, 7*mm])
    t_info.setStyle([
        ('SPAN', (1,0), (4,0)),
        ('SPAN', (1,1), (4,1)),
        ('SPAN', (1,2), (4,2)),
        ('SPAN', (1,5), (4,5)),
        ('LINEBELOW', (1,0), (4,0), 0.5, colors.black),
        ('LINEBELOW', (1,1), (4,1), 0.5, colors.black),
        ('LINEBELOW', (1,2), (4,2), 0.5, colors.black),
        ('LINEBELOW', (1,3), (1,3), 0.5, colors.black),
        ('LINEBELOW', (3,3), (3,3), 0.5, colors.black),
        ('LINEBELOW', (1,4), (1,4), 0.5, colors.black),
        ('LINEBELOW', (3,4), (3,4), 0.5, colors.black),
        ('LINEBELOW', (1,5), (4,5), 0.5, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'BOTTOM'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1)
    ])

    t_header = Table([[img_logo, t_info]], colWidths=[40*mm, 150*mm])
    t_header.setStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE')])
    elementos.append(t_header)
    
    elementos.append(Table([[celula("SECRETARIA MUNICIPAL DE EDUCAÇÃO DE LIMEIRA/SP", s_title)]], colWidths=[190*mm]))
    t_hist = Table([[celula("HISTÓRICO ESCOLAR", s_title)]], colWidths=[190*mm])
    t_hist.setStyle([('BACKGROUND', (0,0), (-1,-1), colors.lightgrey), ('GRID', (0,0), (-1,-1), 0.5, colors.black)])
    elementos.append(t_hist)
    elementos.append(Spacer(1, 2*mm))

    # ---------------------------------------------------------
    # 1.1 DADOS DO ESTUDANTE & 1.2 CERTIDÃO DE NASCIMENTO
    # ---------------------------------------------------------
    a = dados['aluno']
    dados_1 = [
        [celula("1.1", s_center), celula("DADOS DO ESTUDANTE", s_bold), "", "", "", "", celula("RA", s_center), ""],
        [celula(f"NOME DO ALUNO: <b>{a['nome']}</b>", s_normal), "", "", "", "", celula(f"RA ESCOLAR: <b>{a['ra_escolar']}</b>", s_normal), "", ""],
        [celula("NASCIMENTO:", s_center), "", celula("LOCALIDADE", s_center), celula("ESTADO", s_center), celula("NACIONALIDADE", s_center), celula("DIA", s_center), celula("MÊS", s_center), celula("ANO", s_center)],
        ["", "", celula(a['nascimento_loc'], s_center), celula(a['nascimento_est'], s_center), celula(a['nacionalidade'], s_center), celula(a['dia'], s_center), celula(a['mes'], s_center), celula(a['ano'], s_center)],
        [celula("1.2", s_center), celula("CERTIDÃO DE NASCIMENTO", s_bold), "", "", "", celula(f"LIVRO: <b>{a['certidao_livro']}</b>", s_normal), "", ""],
        [celula(f"(SUB) DISTRITO: <b>{a['certidao_distrito']}</b>", s_normal), "", "", celula(f"CIDADE: <b>{a['certidao_cidade']}</b>", s_normal), "", celula(f"ESTADO: <b>{a['certidao_estado']}</b>", s_normal), "", ""],
        [celula(f"CERTIDÃO NOVA - MATRÍCULA: <b>{a['certidao_nova']}</b>", s_normal), "", "", "", "", "", "", ""],
        [celula(f"ESTRANGEIRO - DOCUMENTO: <b>{a['estrangeiro_doc']}</b>", s_normal), "", "", "", "", "", "", ""]
    ]
    t_sec1 = Table(dados_1, colWidths=[10*mm, 30*mm, 40*mm, 20*mm, 40*mm, 15*mm, 15*mm, 20*mm])
    t_sec1.setStyle([
        ('SPAN', (1,0), (5,0)), ('SPAN', (6,0), (7,0)),
        ('SPAN', (0,1), (4,1)), ('SPAN', (5,1), (7,1)),
        ('SPAN', (0,2), (1,3)), 
        ('SPAN', (1,4), (4,4)), ('SPAN', (5,4), (7,4)),
        ('SPAN', (0,5), (2,5)), ('SPAN', (3,5), (4,5)), ('SPAN', (5,5), (7,5)),
        ('SPAN', (0,6), (7,6)),
        ('SPAN', (0,7), (7,7)),
        ('BACKGROUND', (0,0), (7,0), colors.lightgrey),
        ('BACKGROUND', (0,4), (4,4), colors.lightgrey),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE')
    ])
    elementos.append(t_sec1)
    elementos.append(Spacer(1, 2*mm))

    # ---------------------------------------------------------
    # 2 RESULTADO DOS ESTUDOS REALIZADOS
    # ---------------------------------------------------------
    texto_legal = "Lei Federal nº 9394/96, art. 26; Deliberação CME nº 02/2016; Resolução SME nº 11/2016; Resolução CNE/CP nº 02/2017; Resolução SME nº 06/2020; Resolução CNE/CEB nº 01/2022; Lei nº 14.640/2023; Resolução CNE/CEB nº 02/2025; Resolução CNE/CEB nº 07/25; Decreto Municipal nº 405/2022; Resolução SME nº 03/2026"
    
    dados_2 = [
        [celula("2", s_center), celula("RESULTADO DOS ESTUDOS REALIZADOS NO ENSINO FUNDAMENTAL", s_bold), "", "", "", "", ""],
        [celula("2.1", s_center), "", celula("2.2", s_center), celula("ESCOLARIDADE", s_bold), "", "", ""],
        [[celula("CURRÍCULO", s_bold), celula(texto_legal, s_legal)], "", celula("Anos Iniciais", s_bold), "", "", "", ""],
        ["", "", celula("1º Ano", s_bold), celula("2º Ano", s_bold), celula("3º Ano", s_bold), celula("4º Ano", s_bold), celula("5º Ano", s_bold)]
    ]
    
    for disc, notas in dados['curriculo'].items():
        dados_2.append([celula(disc, s_normal), ""] + [celula(regra_do_traco(n), s_center) for n in notas])
        
    dados_2.append([celula("2.3", s_center), celula("CARGA HORÁRIA", s_bold), celula(dados['ch_curriculo'], s_center), "", "", "", ""])
    
    texto_fc = "<b>2.4</b> Flexibilização Curricular (FC): nomenclatura que deve ser utilizada para o estudante da educação especial cuja avaliação pedagógica identificou necessidade significativa de adequação curricular e diante disso o conteúdo trabalhado foi compatível aos seus processos de aprendizagem e desenvolvimento e não ao previsto"
    dados_2.append([celula(texto_fc, s_legal), "", "", "", "", "", ""])

    t_sec2 = Table(dados_2, colWidths=[10*mm, 80*mm, 20*mm, 20*mm, 20*mm, 20*mm, 20*mm])
    styles_2 = [
        ('SPAN', (1,0), (6,0)),
        ('SPAN', (0,1), (1,1)), ('SPAN', (3,1), (6,1)),
        ('SPAN', (0,2), (1,3)), ('SPAN', (2,2), (6,2)),
    ]
    styles_2 += [('SPAN', (0,r), (1,r)) for r in range(4, 11)]
    styles_2 += [
        ('SPAN', (2,11), (6,11)), 
        ('SPAN', (0,12), (6,12)), 
        ('BACKGROUND', (0,0), (6,0), colors.lightgrey),
        ('BACKGROUND', (0,1), (6,1), colors.lightgrey),
        ('BACKGROUND', (2,3), (6,3), colors.lightgrey),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE')
    ]
    t_sec2.setStyle(TableStyle(styles_2))
    elementos.append(t_sec2)

    # ---------------------------------------------------------
    # 3 PARTE DIVERSIFICADA
    # ---------------------------------------------------------
    dados_3 = [
        [celula("3", s_center), celula("PARTE DIVERSIFICADA", s_bold), celula("1º Ano", s_center), celula("2º Ano", s_center), celula("3º Ano", s_center), celula("4º Ano", s_center), celula("5º Ano", s_center)]
    ]
    for disc, notas in dados['parte_diversificada'].items():
        dados_3.append([celula(disc, s_normal), ""] + [celula(regra_do_traco(n), s_center) for n in notas])
        
    dados_3.append([celula("3.1", s_center), celula("CARGA HORÁRIA", s_bold), celula(dados['ch_diversificada'], s_center), "", "", "", ""])
    
    texto_obs = "OBS: As escolas de atendimento integral deverão considerar os eixos intelectual, esportivo e cultural até o ano de 2025. A partir do ano de 2026, para preenchimento deste campo da Parte Diversificada, considerar os anexos da Resolução SME nº 03/26 que trata da Matriz Curricular. Os campos de disciplinas que não correspondem ao modelo de atendimento adotado pela escola deverão ser preenchido com traço. Para o estudante que frequentou a parte diversificada, indicar P de participação."
    dados_3.append([celula(texto_obs, s_legal), "", "", "", "", "", ""])

    t_sec3 = Table(dados_3, colWidths=[10*mm, 80*mm, 20*mm, 20*mm, 20*mm, 20*mm, 20*mm])
    styles_3 = [('SPAN', (0, r), (1, r)) for r in range(1, 10)]
    styles_3 += [
        ('SPAN', (2, 10), (6, 10)),
        ('SPAN', (0, 11), (6, 11)),
        ('BACKGROUND', (0,0), (6,0), colors.lightgrey),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE')
    ]
    t_sec3.setStyle(TableStyle(styles_3))
    elementos.append(t_sec3)

    # ---------------------------------------------------------
    # 4, 5 e 6
    # ---------------------------------------------------------
    matriz_456 = [
        [celula("4 ENSINO RELIGIOSO (art.33-LDB e Deliberação CME nº 02/2016)", s_bold), celula("CARGA HORÁRIA", s_center), "", "", "", ""],
        [celula("<b>5 EDUCAÇÃO ESPECIAL - ATENDIMENTO EDUCACIONAL ESPECIALIZADO</b><br/>Decreto Nº 12.686/2025 - Indicação Cme Nº02/2023 - Decreto Municipal Nº 23/2026<br/>Indicar a sigla AEE (Atendimento Educacional Especializado) para o estudante que frequentou esse tipo de atendimento no respectivo ano.", s_legal), celula("1º ano", s_center), celula("2º ano", s_center), celula("3º ano", s_center), celula("4º ano", s_center), celula("5º ano", s_center)],
        [celula("", s_normal)] + [celula(n, s_center) for n in dados['aee']],
        [celula("6 TOTAL DA CARGA HORÁRIA (CAMPO 2 + CAMPO 3)", s_bold), celula(dados['ch_total'], s_center), "", "", "", ""]
    ]
    t_456 = Table(matriz_456, colWidths=[100*mm, 18*mm, 18*mm, 18*mm, 18*mm, 18*mm])
    t_456.setStyle(TableStyle([
        ('SPAN', (1, 0), (-1, 0)),
        ('SPAN', (1, 3), (-1, 3)),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (0, 0), colors.lightgrey),
        ('BACKGROUND', (0, 1), (-1, 1), colors.lightgrey),
        ('BACKGROUND', (0, 3), (0, 3), colors.lightgrey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
    ]))
    elementos.append(t_456)
    elementos.append(Spacer(1, 2*mm))

    # ---------------------------------------------------------
    # 7 ESTUDOS REALIZADOS
    # ---------------------------------------------------------
    matriz_7 = [
        [celula("7 ESTUDOS REALIZADOS", s_bold), "", "", "", ""],
        [celula("ANO", s_center), celula("CICLO/ANO", s_center), celula("ESTABELECIMENTO", s_center), celula("MUNICÍPIO", s_center), celula("ESTADO", s_center)]
    ]
    for est in dados['estudos']:
        matriz_7.append([celula(c, s_center) for c in est])
        
    t_7 = Table(matriz_7, colWidths=[20*mm, 30*mm, 80*mm, 40*mm, 20*mm])
    t_7.setStyle(TableStyle([
        ('SPAN', (0, 0), (-1, 0)),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (-1, 1), colors.lightgrey),
    ]))
    elementos.append(t_7)

    # =========================================================
    # QUEBRA DE PÁGINA (VERSO: CAMPOS 8 AO 11 - OBRIGATÓRIO)
    # =========================================================
    elementos.append(PageBreak())

    # ---------------------------------------------------------
    # 8 TRANSFERÊNCIA DURANTE O ANO LETIVO
    # ---------------------------------------------------------
    t = dados['transferencia']
    dados_8 = [
        [celula("8", s_center), celula("TRANSFERÊNCIA DURANTE O ANO LETIVO", s_bold), "", "", ""],
        [celula("8.1", s_center), celula(f"Ano: {t['ano']} Ensino Fundamental   Turma: {t['turma']}   Nº de chamada: {t['chamada']}   TRANSFERIDO EM: {t['transferido_em']}<br/>Dias Letivos: {t['dias_letivos']}   Ausências: {t['ausencias']}   Ausências Compensadas: {t['compensadas']}   Frequência (%): {t['frequencia']}", s_normal), "", "", ""],
        [celula("8.2", s_center), celula("CURRÍCULO", s_bold), celula("1º TRIMESTRE", s_center), celula("2º TRIMESTRE", s_center), celula("3º TRIMESTRE", s_center)]
    ]
    
    for disc, notas in t['curriculo'].items():
        dados_8.append([celula(disc, s_normal), ""] + [celula(regra_do_traco(n), s_center) for n in notas])
        
    dados_8.append([celula("PARTE DIVERSIFICADA", s_bold), "", "", "", ""])
    
    for disc, notas in t['diversificada'].items():
        dados_8.append([celula(disc, s_normal), ""] + [celula(regra_do_traco(n), s_center) for n in notas])

    t_sec8 = Table(dados_8, colWidths=[10*mm, 90*mm, 30*mm, 30*mm, 30*mm])
    styles_8 = [
        ('SPAN', (1,0), (4,0)),
        ('SPAN', (1,1), (4,1)),
        ('SPAN', (0,2), (1,2)),
        ('SPAN', (0,10), (4,10)), 
        ('BACKGROUND', (0,0), (4,0), colors.lightgrey),
        ('BACKGROUND', (0,2), (4,2), colors.lightgrey),
        ('BACKGROUND', (0,10), (4,10), colors.lightgrey),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE')
    ]
    for r in range(3, 10):
        styles_8.append(('SPAN', (0,r), (1,r)))
    for r in range(11, 17):
        styles_8.append(('SPAN', (0,r), (1,r)))

    t_sec8.setStyle(TableStyle(styles_8))
    elementos.append(t_sec8)
    elementos.append(Spacer(1, 2*mm))

    # ---------------------------------------------------------
    # 9, 10 e 11
    # ---------------------------------------------------------
    elementos.append(Table([[celula("9 OBSERVAÇÕES", s_bold)]], colWidths=[190*mm], style=[('GRID', (0,0), (-1,-1), 0.5, colors.black), ('BACKGROUND', (0,0), (-1,-1), colors.lightgrey)]))
    elementos.append(Table([["\n\n\n"]], colWidths=[190*mm], style=[('GRID', (0,0), (-1,-1), 0.5, colors.black)]))
    
    matriz_10 = [
        [celula("10 CERTIFICADO", s_bold)],
        [celula("O diretor da __________________________________________________________________________________________<br/>de acordo com o Art.24, inciso VII, da Lei Federal 9394/96, certifica que ___________________________________<br/>R.A. ____________________________ concluiu o ______________________________________________________<br/>do Ensino Fundamental, no ano letivo de ______________", s_normal)]
    ]
    elementos.append(Table(matriz_10, colWidths=[190*mm], style=[('GRID', (0,0), (-1,-1), 0.5, colors.black), ('BACKGROUND', (0,0), (-1,0), colors.lightgrey)]))

    elementos.append(Spacer(1, 4*mm))
    
    matriz_11 = [
        [celula("11 ASSINATURAS", s_bold), "", ""],
        [celula(f"Limeira, {datetime.now().strftime('%d/%m/%Y')}", s_center), celula("\n\n________________________________\nSECRETÁRIO (A) DE ESCOLA", s_center), celula("\n\n________________________________\nDIRETOR DE ESCOLA", s_center)]
    ]
    elementos.append(Table(matriz_11, colWidths=[60*mm, 65*mm, 65*mm], style=[('SPAN', (0,0), (-1,0)), ('GRID', (0,0), (-1,-1), 0.5, colors.black), ('BACKGROUND', (0,0), (-1,0), colors.lightgrey), ('VALIGN', (0,1), (-1,1), 'BOTTOM')]))

    doc.build(elementos)
    buffer.seek(0)
    return buffer

# ==========================================
# 3. INTERFACE STREAMLIT
# ==========================================
def renderizar_modulo():
    st.markdown('<div class="header-box"><div class="header-title">📜 Emissão de Histórico Escolar</div></div>', unsafe_allow_html=True)
    st.warning("⚠️ **Regra de Ouro:** Documento gerado seguindo estritamente as resoluções vigentes (Frente: Campos 1 ao 7 | Verso: Campos 8 ao 11).")
    
    with st.container():
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.subheader("Busca de Estudante")
            ra_busca = st.text_input("Número do RA (Ex: 123456)")
            btn_gerar = st.button("Processar Documento Oficial", type="primary")
            
        with col2:
            if btn_gerar and ra_busca:
                with st.spinner("Estruturando matriz oficial com quebra de página (frente e verso)..."):
                    try:
                        dados = buscar_dados_historico(ra_busca)
                        pdf_buffer = gerar_pdf(dados)
                        
                        st.success(f"Histórico escolar processado com sucesso para: **{dados['aluno']['nome']}**")
                        
                        st.download_button(
                            label="📥 Fazer Download do Histórico (PDF)",
                            data=pdf_buffer,
                            file_name=f"Historico_Oficial_{dados['aluno']['ra']}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                    except Exception as e:
                        st.error(f"Erro ao processar: {e}")
            elif btn_gerar and not ra_busca:
                st.error("Preencha o campo de RA.")

if __name__ == "__main__":
    renderizar_modulo()
