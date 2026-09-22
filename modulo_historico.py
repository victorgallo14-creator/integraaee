import streamlit as st
import io
from datetime import datetime
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

# ==========================================
# 1. INTEGRAÇÃO SUPABASE (LÓGICA DE DADOS)
# ==========================================
def init_connection():
    # Exemplo de conexão com Supabase (descomente no ambiente real)
    # from supabase import create_client, Client
    # url = st.secrets["SUPABASE_URL"]
    # key = st.secrets["SUPABASE_KEY"]
    # return create_client(url, key)
    pass

def buscar_dados_historico(ra):
    # supabase = init_connection()
    # No Integra real, a lógica seria:
    # aluno = supabase.table("alunos").select("*").eq("ra", ra).execute().data[0]
    # notas = supabase.table("historico_notas").select("*").eq("aluno_id", aluno['id']).execute().data
    
    # Mock de dados simulando o retorno do banco para renderização do histórico
    return {
        "aluno": {
            "nome": "NOME COMPLETO DO ESTUDANTE",
            "ra": ra,
            "cpf": "123.456.789-00",
            "nacionalidade": "Brasileiro nato",
            "nascimento": "14/11/2015",
            "rg": "12.345.678-9",
            "certidao": "Livro 123, Folha 45, Cartório de Registro Civil - Limeira/SP"
        },
        # Representação dos conceitos e carga horária por ano (1º ao 5º)
        # Campos vazios acionarão automaticamente a "Regra do Traço"
        "base_comum": {
            "Língua Portuguesa": ["AD", "AD", "AD", "", ""],
            "Matemática": ["AD", "B", "AD", "", ""],
            "História": ["AD", "AD", "AD", "", ""],
            "Geografia": ["AD", "AD", "AD", "", ""],
            "Ciências": ["AD", "AD", "AD", "", ""],
            "Arte": ["AD", "AD", "B", "", ""],
            "Educação Física": ["AD", "AD", "AD", "", ""]
        },
        "parte_diversificada": {
            "Linguagens e Tecnologias": ["P", "P", "P", "", ""],
            "Acompanhamento Pedagógico": ["P", "P", "P", "", ""]
        },
        "carga_horaria": {
            "1º Ano": {"bc": 1120, "pd": 1000, "total": 2120}, 
            "2º Ano": {"bc": 1120, "pd": 560, "total": 1680},  
            "3º Ano": {"bc": 1120, "pd": 80, "total": 1200},   
            "4º Ano": {"bc": 0, "pd": 0, "total": 0},
            "5º Ano": {"bc": 0, "pd": 0, "total": 0}
        }
    }

# ==========================================
# 2. GERAÇÃO DO PDF (REPORTLAB PLATYPUS)
# ==========================================
def regra_do_traco(valor):
    """Aplica o traço obrigatório em campos nulos ou vazios para evitar adulteração."""
    return valor if valor not in [None, "", 0, "0"] else "-"

def gerar_pdf(dados, obs_texto):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, 
        rightMargin=15*mm, leftMargin=15*mm, 
        topMargin=15*mm, bottomMargin=15*mm
    )
    
    elementos = []
    styles = getSampleStyleSheet()
    
    # Estilos customizados
    style_titulo = ParagraphStyle(name="Titulo", parent=styles['Normal'], fontName="Helvetica-Bold", fontSize=12, alignment=TA_CENTER, spaceAfter=10)
    style_sub = ParagraphStyle(name="Sub", parent=styles['Normal'], fontName="Helvetica", fontSize=9, alignment=TA_CENTER)
    style_secao = ParagraphStyle(name="Secao", parent=styles['Normal'], fontName="Helvetica-Bold", fontSize=10, spaceBefore=10, spaceAfter=5)
    
    # --- CABEÇALHO (Chancela Institucional Inviolável) ---
    elementos.append(Paragraph("PREFEITURA MUNICIPAL DE LIMEIRA", style_titulo))
    elementos.append(Paragraph("Ato de Criação: Jornal Oficial do Município (JOM) nº XXXX de DD/MM/AAAA", style_sub))
    elementos.append(Paragraph("CEIEF RAFAEL AFFONSO LEITE", style_sub))
    elementos.append(Paragraph("Rua Exemplo, 123 - Tel: (19) 3400-0000", style_sub))
    elementos.append(Paragraph("E-mail: ceief.rafael.leite@limeira.sp.gov.br", style_sub))
    elementos.append(Spacer(1, 10))
    
    # --- CAMPO 1: DADOS DO ESTUDANTE ---
    elementos.append(Paragraph("CAMPO 1 - DADOS DO ESTUDANTE", style_secao))
    aluno = dados['aluno']
    dados_aluno_tabela = [
        ["Nome Completo:", aluno['nome'], "RA:", aluno['ra']],
        ["Data Nascimento:", aluno['nascimento'], "CPF:", aluno['cpf']],
        ["Nacionalidade:", aluno['nacionalidade'], "RG:", aluno['rg']],
        ["Certidão:", aluno['certidao'], "", ""]
    ]
    tabela_aluno = Table(dados_aluno_tabela, colWidths=[35*mm, 85*mm, 15*mm, 45*mm])
    tabela_aluno.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME', (2,0), (2,-1), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('SPAN', (1,3), (3,3)), # Mescla a célula da certidão
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE')
    ]))
    elementos.append(tabela_aluno)
    
    # --- MATRIZ CURRICULAR (NOTAS / CONCEITOS) ---
    elementos.append(Paragraph("CAMPO - COMPONENTES CURRICULARES (RENDIMENTO)", style_secao))
    
    cabecalho_matriz = ["BASE COMUM", "1º Ano", "2º Ano", "3º Ano", "4º Ano", "5º Ano"]
    tabela_matriz_dados = [cabecalho_matriz]
    
    # Preenchendo Base Comum
    for disc, notas in dados['base_comum'].items():
        linha = [disc] + [regra_do_traco(n) for n in notas]
        tabela_matriz_dados.append(linha)
        
    tabela_matriz_dados.append(["PARTE DIVERSIFICADA", "", "", "", "", ""])
    
    # Preenchendo Parte Diversificada
    for disc, notas in dados['parte_diversificada'].items():
        linha = [disc] + [regra_do_traco(n) for n in notas]
        tabela_matriz_dados.append(linha)
        
    tabela_matriz = Table(tabela_matriz_dados, colWidths=[70*mm] + [22*mm]*5)
    tabela_matriz.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('BACKGROUND', (0,len(dados['base_comum'])+1), (-1,len(dados['base_comum'])+1), colors.lightgrey),
        ('FONTNAME', (0,len(dados['base_comum'])+1), (-1,len(dados['base_comum'])+1), 'Helvetica-Bold'),
        ('ALIGN', (1,0), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black)
    ]))
    elementos.append(tabela_matriz)
    
    # --- CAMPO 6: TOTAL DA CARGA HORÁRIA ---
    elementos.append(Paragraph("CAMPO 6 - TOTAL DA CARGA HORÁRIA (Matemática Exata)", style_secao))
    cabecalho_ch = ["ESPECIFICAÇÃO", "1º Ano", "2º Ano", "3º Ano", "4º Ano", "5º Ano"]
    ch = dados['carga_horaria']
    
    linha_bc = ["Total da Base Comum"] + [regra_do_traco(ch[f"{i}º Ano"]['bc']) for i in range(1,6)]
    linha_pd = ["Total da Parte Diversificada"] + [regra_do_traco(ch[f"{i}º Ano"]['pd']) for i in range(1,6)]
    linha_total = ["TOTAL EXATO (Sem arredondamento)"] + [regra_do_traco(ch[f"{i}º Ano"]['total']) for i in range(1,6)]
    
    tabela_ch = Table([cabecalho_ch, linha_bc, linha_pd, linha_total], colWidths=[70*mm] + [22*mm]*5)
    tabela_ch.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('ALIGN', (1,0), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black)
    ]))
    elementos.append(tabela_ch)

    # --- CAMPO 9: OBSERVAÇÕES JURÍDICAS ---
    elementos.append(Paragraph("CAMPO 9 - OBSERVAÇÕES", style_secao))
    
    texto_obs = Paragraph(regra_do_traco(obs_texto), styles['Normal'])
    tabela_obs = Table([[texto_obs]], colWidths=[180*mm], rowHeights=[20*mm])
    tabela_obs.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'TOP')
    ]))
    elementos.append(tabela_obs)
    
    elementos.append(Spacer(1, 30*mm))
    
    # --- CAMPO 11: ASSINATURAS ---
    elementos.append(Paragraph("11 - ASSINATURAS", style_secao))
    tabela_assinaturas = Table([
        ["_______________________________________", "_______________________________________"],
        ["Secretário de Escola\n(Carimbo e Assinatura)", "Diretor de Escola\n(Carimbo e Assinatura)"]
    ], colWidths=[90*mm, 90*mm])
    tabela_assinaturas.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'TOP')
    ]))
    elementos.append(tabela_assinaturas)

    doc.build(elementos)
    buffer.seek(0)
    return buffer

# ==========================================
# 3. INTERFACE STREAMLIT (INTEGRA)
# ==========================================
def renderizar_modulo():
    # st.set_page_config removido para evitar conflito ao ser chamado no app.py
    
    st.markdown('<div class="header-box"><div class="header-title">📜 Emissão de Histórico Escolar</div></div>', unsafe_allow_html=True)
    st.markdown("Módulo administrativo de expedição em conformidade com as Diretrizes Normativas de Limeira/SP (2026).")
    st.warning("⚠️ **Regra de Ouro:** Fidelidade absoluta. Transcrição exata de dados, aplicação da regra do traço e matemática exata na carga horária.")
    
    with st.container():
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.subheader("Busca de Estudante")
            ra_busca = st.text_input("Número do RA (Ex: 123456)")
            
            st.subheader("Fórmulas de Observação")
            st.markdown("É **expressamente proibida** a criação de textos livres (Campo 9).")
            opcao_obs = st.selectbox(
                "Selecione a finalidade:",
                [
                    "",
                    "[Controle de Desempenho] Expedição regular para transferência.",
                    "[Regularização de Vida Escolar] Adequação sistêmica de percurso.",
                    "[Reclassificação] Estudante reclassificado mediante avaliação."
                ]
            )
            
            btn_gerar = st.button("Processar Documento Oficial", type="primary")
            
        with col2:
            if btn_gerar and ra_busca:
                with st.spinner("Buscando informações sistêmicas e estruturando matriz..."):
                    try:
                        # 1. Recupera os dados
                        dados = buscar_dados_historico(ra_busca)
                        
                        # 2. Renderiza o PDF
                        pdf_buffer = gerar_pdf(dados, opcao_obs)
                        
                        st.success(f"Histórico escolar processado com sucesso para o estudante: **{dados['aluno']['nome']}**")
                        
                        # 3. Disponibiliza para Download
                        st.download_button(
                            label="📥 Fazer Download do Histórico (PDF)",
                            data=pdf_buffer,
                            file_name=f"Historico_{dados['aluno']['ra']}_{datetime.now().strftime('%Y%m%d')}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                        
                        st.info("Lembrete: A documentação exige protocolo de dupla assinatura. Providencie o carimbo funcional para os campos de Secretário e Diretor.")
                        
                    except Exception as e:
                        st.error(f"Ocorreu um erro ao processar o documento: {e}")
            elif btn_gerar and not ra_busca:
                st.error("Por favor, preencha o campo de RA.")

if __name__ == "__main__":
    renderizar_modulo()
