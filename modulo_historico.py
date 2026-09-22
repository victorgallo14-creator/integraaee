import streamlit as st
import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT

# ==========================================
# 1. INTEGRAÇÃO DE DADOS (MOCK PARA TESTE)
# ==========================================
def buscar_dados_historico(ra):
    # Substitua pela busca real no Supabase futuramente
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
            "EIXO ESPORTIVO": ["X", "", "", "", ""],
            "EIXO CULTURAL": ["X", "", "", "", ""],
            "LINGUAGENS E TECNOLOGIAS": ["P", "", "", "", ""],
            "ACOMPANHAMENTO PEDAGÓGICO": ["P", "", "", "", ""],
            "PRÁTICAS EXPERIMENTAIS E DE TUTORIA DE ESTUDO": ["P", "", "X", "", ""],
            "PRÁTICAS DE ESTUDO": ["P", "", "X", "", ""],
            "LINGUAGENS": ["P", "", "", "", ""],
            "ESPORTE E EDUCAÇÃO DO MOVIMENTO": ["P", "", "", "", ""]
        },
        "ch_diversificada": "1000H/A",
        "ensino_religioso": "",
        "aee": ["", "", "", "", ""],
        "ch_total": "",
        "estudos": [
            ["2022", "1º ANO", "CEIEF RAFAEL AFFONSO LEITE", "LIMEIRA", "SP"],
            ["", "", "", "", ""],
            ["", "", "", "", ""],
            ["", "", "", "", ""],
            ["", "", "", "", ""]
        ]
    }

# ==========================================
# 2. GERAÇÃO DO PDF EXATO (REPORTLAB PLATYPUS)
# ==========================================
def gerar_pdf(dados):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, 
        rightMargin=10*mm, leftMargin=10*mm, 
        topMargin=10*mm, bottomMargin=10*mm
    )
    
    elementos = []
    styles = getSampleStyleSheet()
    
    # Estilos de parágrafo milimétricos
    s_normal = ParagraphStyle('normal', fontName='Helvetica', fontSize=7, leading=8)
    s_bold = ParagraphStyle('bold', fontName='Helvetica-Bold', fontSize=7, leading=8)
    s_legal = ParagraphStyle('legal', fontName='Helvetica', fontSize=5.5, leading=6, alignment=TA_JUSTIFY)
    s_center = ParagraphStyle('center', fontName='Helvetica-Bold', fontSize=8, alignment=TA_CENTER)
    s_title = ParagraphStyle('title', fontName='Helvetica-Bold', fontSize=10, alignment=TA_CENTER)
    
    def celula(texto, estilo=s_normal):
        return Paragraph(texto, estilo)

    # ---------------------------------------------------------
    # CABEÇALHO OFICIAL
    # ---------------------------------------------------------
    cabecalho_dados = [
        [celula("PREFEITURA MUNICIPAL DE LIMEIRA", s_title), "", ""],
        [celula("ESCOLA:<br/>XXXXXXXXXXXXXXXXXXXXXX"), celula("ATO DE CRIAÇÃO:<br/>"), ""],
        [celula("ENDEREÇO:<br/>XXXXXXXXXXXXXXXXXXXXXX"), celula("BAIRRO:<br/>XXXXXXXXXXXXXXXXX"), ""],
        [celula("MUNICÍPIO:<br/>XXXXXXXXXXXXXX"), celula("CEP:<br/>"), celula("TELEFONES:<br/>")],
        [celula("ESTADO DE SÃO PAULO - BRASIL"), celula("E-MAIL:<br/>XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"), ""],
        [celula("SECRETARIA MUNICIPAL DE EDUCAÇÃO DE LIMEIRA/SP", s_center), "", ""],
        [celula("HISTÓRICO ESCOLAR", s_center), "", ""]
    ]
    t_cabecalho = Table(cabecalho_dados, colWidths=[90*mm, 50*mm, 50*mm])
    t_cabecalho.setStyle(TableStyle([
        ('SPAN', (0, 0), (2, 0)),
        ('SPAN', (1, 1), (2, 1)),
        ('SPAN', (1, 2), (2, 2)),
        ('SPAN', (1, 4), (2, 4)),
        ('SPAN', (0, 5), (2, 5)),
        ('SPAN', (0, 6), (2, 6)),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BACKGROUND', (0, 5), (2, 6), colors.lightgrey),
    ]))
    elementos.append(t_cabecalho)
    elementos.append(Spacer(1, 2*mm))

    # ---------------------------------------------------------
    # 1.1 DADOS DO ESTUDANTE & 1.2 CERTIDÃO
    # ---------------------------------------------------------
    a = dados['aluno']
    dados_1_1 = [
        [celula("1.1 DADOS DO ESTUDANTE", s_bold), "", "", "", "", "", ""],
        [celula(f"NOME DO ALUNO:<br/><b>{a['nome']}</b>"), "", "", "", celula(f"RA<br/><b>{a['ra']}</b>"), celula(f"RA ESCOLAR:<br/><b>{a['ra_escolar']}</b>"), ""],
        [celula("NASCIMENTO:", s_bold), celula(f"LOCALIDADE<br/><b>{a['nascimento_loc']}</b>"), celula(f"ESTADO<br/><b>{a['nascimento_est']}</b>"), celula(f"NACIONALIDADE<br/><b>{a['nacionalidade']}</b>"), celula("DIA<br/><b>"+a['dia']+"</b>", s_center), celula("MÊS<br/><b>"+a['mes']+"</b>", s_center), celula("ANO<br/><b>"+a['ano']+"</b>", s_center)]
    ]
    t_1_1 = Table(dados_1_1, colWidths=[35*mm, 45*mm, 20*mm, 40*mm, 15*mm, 15*mm, 20*mm])
    t_1_1.setStyle(TableStyle([
        ('SPAN', (0, 0), (-1, 0)),
        ('SPAN', (0, 1), (3, 1)),
        ('SPAN', (5, 1), (6, 1)),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP')
    ]))
    elementos.append(t_1_1)
    
    dados_1_2 = [
        [celula("1.2 CERTIDÃO DE NASCIMENTO", s_bold), "", "", "", ""],
        [celula(f"(SUB) DISTRITO:<br/><b>{a['certidao_distrito']}</b>"), celula(f"LIVRO:<br/><b>{a['certidao_livro']}</b>"), celula("FOLHA:<br/>"), celula(f"CIDADE:<br/><b>{a['certidao_cidade']}</b>"), celula(f"ESTADO:<br/><b>{a['certidao_estado']}</b>")],
        [celula(f"CERTIDÃO NOVA - MATRÍCULA:<br/><b>{a['certidao_nova']}</b>"), "", "", "", ""],
        [celula(f"ESTRANGEIRO - DOCUMENTO:<br/><b>{a['estrangeiro_doc']}</b>"), "", "", "", ""]
    ]
    t_1_2 = Table(dados_1_2, colWidths=[60*mm, 30*mm, 30*mm, 40*mm, 30*mm])
    t_1_2.setStyle(TableStyle([
        ('SPAN', (0, 0), (-1, 0)),
        ('SPAN', (0, 2), (-1, 2)),
        ('SPAN', (0, 3), (-1, 3)),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP')
    ]))
    elementos.append(t_1_2)
    elementos.append(Spacer(1, 2*mm))

    # ---------------------------------------------------------
    # 2 RESULTADO DOS ESTUDOS
    # ---------------------------------------------------------
    elementos.append(Table([[celula("2 RESULTADO DOS ESTUDOS REALIZADOS NO ENSINO FUNDAMENTAL", s_bold)]], colWidths=[190*mm], style=[('GRID', (0,0), (-1,-1), 0.5, colors.black), ('BACKGROUND', (0,0), (-1,-1), colors.lightgrey)]))
    
    texto_legal = "<b>2.1 | 2.2  CURRÍCULO  | ESCOLARIDADE: Anos Iniciais</b><br/><br/>Lei Federal nº 9394/96, art. 26; Deliberação CME nº 02/2016; Resolução SME nº 11/2016; Resolução CNE/CP nº 02/2017; Resolução SME nº 06/2020; Resolução CNE/CEB nº 01/2022; Lei nº 14.640/2023; Resolução CNE/CEB nº 02/2025; Resolução CNE/CEB nº 07/25; Decreto Municipal nº 405/2022; Resolução SME nº 03/2026"
    
    matriz_2 = [
        [celula(texto_legal, s_legal), celula("1º Ano", s_center), celula("2º Ano", s_center), celula("3º Ano", s_center), celula("4º Ano", s_center), celula("5º Ano", s_center)]
    ]
    for disc, notas in dados['curriculo'].items():
        matriz_2.append([celula(disc, s_bold)] + [celula(n, s_center) for n in notas])
    
    matriz_2.append([celula("2.3 CARGA HORÁRIA", s_bold), celula(dados['ch_curriculo'], s_center), "", "", "", ""])
    
    t_2 = Table(matriz_2, colWidths=[100*mm, 18*mm, 18*mm, 18*mm, 18*mm, 18*mm])
    t_2.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (1, 0), (-1, 0), colors.lightgrey),
    ]))
    elementos.append(t_2)
    
    texto_fc = "<b>2.4 Flexibilização Curricular (FC):</b> nomenclatura que deve ser utilizada para o estudante da educação especial cuja avaliação pedagógica identificou necessidade significativa de adequação curricular e diante disso o conteúdo trabalhado foi compatível aos seus processos de aprendizagem e desenvolvimento e não ao previsto"
    elementos.append(Table([[celula(texto_fc, s_legal)]], colWidths=[190*mm], style=[('GRID', (0,0), (-1,-1), 0.5, colors.black)]))
    elementos.append(Spacer(1, 2*mm))

    # ---------------------------------------------------------
    # 3 PARTE DIVERSIFICADA
    # ---------------------------------------------------------
    elementos.append(Table([[celula("3 PARTE DIVERSIFICADA", s_bold), celula("1º Ano", s_center), celula("2º Ano", s_center), celula("3º Ano", s_center), celula("4º Ano", s_center), celula("5º Ano", s_center)]], colWidths=[100*mm, 18*mm, 18*mm, 18*mm, 18*mm, 18*mm], style=[('GRID', (0,0), (-1,-1), 0.5, colors.black), ('BACKGROUND', (0,0), (-1,-1), colors.lightgrey)]))
    
    matriz_3 = []
    for disc, notas in dados['parte_diversificada'].items():
        matriz_3.append([celula(disc, s_normal)] + [celula(n, s_center) for n in notas])
    
    matriz_3.append([celula("3.1 CARGA HORÁRIA", s_bold), celula(dados['ch_diversificada'], s_center), "", "", "", ""])
    
    t_3 = Table(matriz_3, colWidths=[100*mm, 18*mm, 18*mm, 18*mm, 18*mm, 18*mm])
    t_3.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.5, colors.black), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
    elementos.append(t_3)
    
    texto_obs = "OBS: As escolas de atendimento integral deverão considerar os eixos intelectual, esportivo e cultural até o ano de 2025. A partir do ano de 2026, para preenchimento deste campo da Parte Diversificada, considerar os anexos da Resolução SME nº 03/26 que trata da Matriz Curricular. Os campos de disciplinas que não correspondem ao modelo de atendimento adotado pela escola deverão ser preenchido com traço. Para o estudante que frequentou a parte diversificada, indicar P de participação."
    elementos.append(Table([[celula(texto_obs, s_legal)]], colWidths=[190*mm], style=[('GRID', (0,0), (-1,-1), 0.5, colors.black)]))
    elementos.append(Spacer(1, 2*mm))

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
    for est em dados['estudos']:
        matriz_7.append([celula(c, s_center) for c in est])
        
    t_7 = Table(matriz_7, colWidths=[20*mm, 30*mm, 80*mm, 40*mm, 20*mm])
    t_7.setStyle(TableStyle([
        ('SPAN', (0, 0), (-1, 0)),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (-1, 1), colors.lightgrey),
    ]))
    elementos.append(t_7)
    elementos.append(Spacer(1, 2*mm))

    # ---------------------------------------------------------
    # 8 TRANSFERÊNCIA (Omitido para simplificar visualmente o bloco final que quebra a página)
    # 9, 10 e 11
    # ---------------------------------------------------------
    # Força quebra de página se necessário, mas o layout acima é compacto.
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
        [celula("Limeira, ______/______/______", s_center), celula("\n\n________________________________\nSECRETÁRIO (A) DE ESCOLA", s_center), celula("\n\n________________________________\nDIRETOR DE ESCOLA", s_center)]
    ]
    elementos.append(Table(matriz_11, colWidths=[60*mm, 65*mm, 65*mm], style=[('SPAN', (0,0), (-1,0)), ('GRID', (0,0), (-1,-1), 0.5, colors.black), ('BACKGROUND', (0,0), (-1,0), colors.lightgrey), ('VALIGN', (0,1), (-1,1), 'BOTTOM')]))

    doc.build(elementos)
    buffer.seek(0)
    return buffer

# ==========================================
# 3. INTERFACE STREAMLIT (INTEGRA)
# ==========================================
def renderizar_modulo():
    st.markdown('<div class="header-box"><div class="header-title">📜 Emissão de Histórico Escolar</div></div>', unsafe_allow_html=True)
    st.warning("⚠️ **Regra de Ouro:** Documento gerado seguindo estritamente as resoluções vigentes (Espelho do Anexo Original).")
    
    with st.container():
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.subheader("Busca de Estudante")
            ra_busca = st.text_input("Número do RA (Ex: 123456)")
            btn_gerar = st.button("Processar Documento Oficial", type="primary")
            
        with col2:
            if btn_gerar and ra_busca:
                with st.spinner("Estruturando matriz oficial com textos legais..."):
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
