import streamlit as st
import io
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from datetime import date
import os

# Configuração da Página
st.set_page_config(page_title="Sistema Integra AEE - Limeira", layout="wide")

# Estilos CSS Customizados
st.markdown("""
<style>
    .main { background-color: #f8fafc; }
    .header-box {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #1e40af;
        margin-bottom: 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .header-title { color: #1e3a8a; font-size: 24px; font-weight: bold; }
    div[data-testid="stExpander"] { background-color: white; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# Estado da Sessão
if 'data_avaliacao' not in st.session_state:
    st.session_state.data_avaliacao = {
        'nome': '',
        'ano_esc': '',
        'defic_chk': [],
        'defic_outra': '',
        'aspectos_gerais': '',
        'alim_nivel': 'É independente.',
        'alim_obs': '',
        'hig_nivel': 'É independente.',
        'hig_obs': '',
        'loc_nivel': [],
        'loc_obs': '',
        'comportamento': 'Demonstra comportamento adequado em relação às situações escolares cotidianas.',
        'comp_obs': '',
        'part_grupo': 'participa de atividades em grupo integrando-se.',
        'part_obs': '',
        'interacao': 'Adequada com as crianças e adultos.',
        'interacao_outros': '',
        'rotina': 'Atende orientações de forma autônoma.',
        'rotina_obs': '',
        'ativ_pedag': 'Não há necessidade de flexibilização.',
        'atencao_sust': 'Mantém atenção por longo período.',
        'atencao_div': 'Mantém atenção em dois estímulos.',
        'atencao_sel': 'Ignora estímulos externos.',
        'linguagem': [],
        'ling_obs': '',
        'conclusao_nivel': 'Não necessita de apoio',
        'apoio_existente': '',
        'resp_sala': '',
        'resp_ee': '',
        'resp_dir': '',
        'resp_coord': '',
        'data_emissao': date.today()
    }

data_aval = st.session_state.data_avaliacao

# Listas de Opções
defs_opts = ["Deficiência auditiva/surdez", "Deficiência física", "Deficiência intelectual", "Deficiência múltipla", "Deficiência visual", "Transtorno do Espectro Autista", "Síndrome de Down"]
opts_alim = ["É independente.", "Necessita de apoio parcial.", "Necessita de apoio total."]
opts_hig = ["É independente.", "Usa fralda.", "Necessita de apoio parcial.", "Necessita de apoio total."]
opts_loc = ["é independente.", "cai ou tropeça com frequência.", "faz uso de cadeira de rodas de forma independente", "faz uso de cadeira de rodas, necessitando ser conduzido.", "possui prótese/órtese.", "faz uso de andador.", "faz uso de bengala."]
opts_comp = [
    "Demonstra comportamento adequado em relação às situações escolares cotidianas (sala de aula, refeitório, quadra etc).",
    "Apresenta alguns comportamentos inadequados (choro, recusa verbal, se jogar no chão) em momentos específicos , mas a recuperação é rápida.",
    "diariamente apresenta comportamentos inadequados que envolvem choro, recusa verbal, birras, saídas sem autorização, correr incontido não atendimento às solicitações dos docentes e funcionários.",
    "Frequentemente a criança emite comportamento inadequado severo que é perigoso a si própria ou outras pessoas (ex: agressões, autolesivos)."
]
opts_part = [
    "participa de atividades em grupo da rotina escolar, interagindo com os estudantes",
    "é capaz de participar de atividades em grupo somente em momentos de curta duração",
    "não é capaz de participar de atividades em grupo de forma autônoma, dependendo de apoio para essa interação",
    "Mesmo com apoio, não é capaz de participar de atividades em grupo."
]
opts_int = ["Adequada com as crianças e adultos.", "Satisfatória.", "Inadequada.", "Outros"]
opts_rot = [
    "Compreende e atende as orientações oferecidas pelo docente de forma autônoma",
    "Precisa de intervenções pontuais do docente para compreender e atender as orientações.",
    "Mesmo com apoio apresenta severas dificuldades quanto à compreensão para atendimento de solicitações."
]
opts_ativ = [
    "não há necessidade de flexibilização curricular",
    "precisa de flexibilização curricular em relação à metodologia de ensino, mantendo-se os conteúdos previstos para o ano de escolaridade",
    "precisa de flexibilização curricular em relação à metodologia de ensino e ao conteúdo curricular, adequando às potencialidades do estudantes",
    "há a necessidade de um currículo funcional, envolvendo as atividades de vida prática e diária."
]
opts_at_sust = ["Mantém atenção por longo período de tempo.", "Mantém atenção por longo período de tempo com apoio.", "Não mantém atenção por longo período de tempo."]
opts_at_div = ["Mantém atenção em dois estímulos diferentes.", "Mantém atenção em dois estímulos diferentes em algumas situações.", "Não mantém atenção em dois estímulos differentes."]
opts_at_sel = ["Mantém atenção na tarefa ignorando estímulos externos.", "Mantém atenção na tarefa ignorando estímulos externos com apoio.", "Não mantém atenção na tarefa com a presença de outros"]
opts_ling = [
    "Faz uso de palavras para se comunicar, expressando seus pensamentos e desejos.",
    "Faz uso de palavras para se comunicar, apresentando trocas fonéticas orais.",
    "Utiliza palavras e frases desconexas, não conseguindo se expressar.",
    "Não faz uso de palavras para se comunicar, expressando seus desejos por meio de gestos e comportamentos",
    "Não faz uso de palavras e de gestos para se comunicar."
]

# Interface Principal
st.markdown("""<div class="header-box"><div class="header-title">Avaliação Pedagógica: Apoio Escolar</div></div>""", unsafe_allow_html=True)

with st.form("form_avaliacao"):
    st.markdown("### 1. Identificação")
    c1, c2 = st.columns([3, 1])
    data_aval['nome'] = c1.text_input("Nome do Estudante", value=data_aval.get('nome'))
    data_aval['ano_esc'] = c2.text_input("Ano Escolar", value=data_aval.get('ano_esc'))
    
    st.markdown("**Deficiências:**")
    data_aval['defic_chk'] = st.multiselect("Selecione as opções aplicáveis", defs_opts, default=data_aval.get('defic_chk'))
    data_aval['defic_outra'] = st.text_input("Outras deficiências ou diagnósticos:", value=data_aval.get('defic_outra'))
    
    st.markdown("---")
    st.markdown("### 2. Aspectos Gerais da Vida Escolar")
    data_aval['aspectos_gerais'] = st.text_area("Relatar matrícula, plano de atendimento, histórico, etc.", value=data_aval.get('aspectos_gerais'), height=100)

    st.markdown("---")
    st.markdown("### 3. Itens de Avaliação (1 a 12)")
    
    with st.expander("Parte I - Habilidades de Vida Diária (Itens 1 a 3)", expanded=True):
        data_aval['alim_nivel'] = st.radio("1. ALIMENTAÇÃO:", opts_alim, index=opts_alim.index(data_aval['alim_nivel']) if data_aval['alim_nivel'] in opts_alim else 0)
        data_aval['alim_obs'] = st.text_input("Observações Alimentação", value=data_aval['alim_obs'])
        
        st.divider()
        data_aval['hig_nivel'] = st.radio("2. HIGIENE:", opts_hig, index=opts_hig.index(data_aval['hig_nivel']) if data_aval['hig_nivel'] in opts_hig else 0)
        data_aval['hig_obs'] = st.text_input("Observações Higiene", value=data_aval['hig_obs'])
        
        st.divider()
        data_aval['loc_nivel'] = st.multiselect("3. LOCOMOÇÃO:", opts_loc, default=data_aval['loc_nivel'])
        data_aval['loc_obs'] = st.text_input("Observações Locomoção", value=data_aval['loc_obs'])

    with st.expander("Parte II - Habilidades Sociais e Interação (Itens 4 a 6)"):
        data_aval['comportamento'] = st.radio("4. COMPORTAMENTO:", opts_comp, index=opts_comp.index(data_aval['comportamento']) if data_aval['comportamento'] in opts_comp else 0)
        data_aval['comp_obs'] = st.text_input("Observações Comportamento", value=data_aval['comp_obs'])
        
        st.divider()
        data_aval['part_grupo'] = st.radio("5. PARTICIPAÇÃO EM GRUPO:", opts_part, index=opts_part.index(data_aval['part_grupo']) if data_aval['part_grupo'] in opts_part else 0)
        data_aval['part_obs'] = st.text_input("Observações Participação", value=data_aval['part_obs'])
        
        st.divider()
        data_aval['interacao'] = st.radio("6. INTERAÇÃO:", opts_int, index=opts_int.index(data_aval['interacao']) if data_aval['interacao'] in opts_int else 0)
        if data_aval['interacao'] == "Outros":
            data_aval['interacao_outros'] = st.text_input("Especifique a interação", value=data_aval['interacao_outros'])

    with st.expander("Parte III - Habilidades Pedagógicas (Itens 7 a 8)"):
        data_aval['rotina'] = st.radio("7. ROTINA EM SALA DE AULA:", opts_rot, index=opts_rot.index(data_aval['rotina']) if data_aval['rotina'] in opts_rot else 0)
        data_aval['rotina_obs'] = st.text_input("Observações Rotina", value=data_aval['rotina_obs'])
        
        st.divider()
        data_aval['ativ_pedag'] = st.radio("8. ATIVIDADES PEDAGÓGICAS:", opts_ativ, index=opts_ativ.index(data_aval['ativ_pedag']) if data_aval['ativ_pedag'] in opts_ativ else 0)

    with st.expander("Parte IV - Comunicação e Atenção (Itens 9 a 12)"):
        data_aval['atencao_sust'] = st.radio("9. ATENÇÃO SUSTENTADA:", opts_at_sust, index=opts_at_sust.index(data_aval['atencao_sust']) if data_aval['atencao_sust'] in opts_at_sust else 0)
        data_aval['atencao_div'] = st.radio("10. ATENÇÃO DIVIDIDA:", opts_at_div, index=opts_at_div.index(data_aval['atencao_div']) if data_aval['atencao_div'] in opts_at_div else 0)
        data_aval['atencao_sel'] = st.radio("11. ATENÇÃO SELETIVA:", opts_at_sel, index=opts_at_sel.index(data_aval['atencao_sel']) if data_aval['atencao_sel'] in opts_at_sel else 0)
        
        st.divider()
        data_aval['linguagem'] = st.multiselect("12. LINGUAGEM:", opts_ling, default=data_aval['linguagem'])
        data_aval['ling_obs'] = st.text_input("Observações Linguagem", value=data_aval['ling_obs'])

    st.markdown("### 4. Conclusão e Responsáveis")
    data_aval['conclusao_nivel'] = st.selectbox("Nível de Apoio:", ["Não necessita de apoio", "Nível 1", "Nível 2", "Nível 3"], index=0)
    data_aval['apoio_existente'] = st.text_input("Caso já receba apoio, especifique:", value=data_aval['apoio_existente'])
    
    col_r1, col_r2 = st.columns(2)
    data_aval['resp_sala'] = col_r1.text_input("Prof. Sala Regular", value=data_aval['resp_sala'])
    data_aval['resp_ee'] = col_r2.text_input("Prof. Ed. Especial", value=data_aval['resp_ee'])
    data_aval['resp_dir'] = col_r1.text_input("Direção Escolar", value=data_aval['resp_dir'])
    data_aval['resp_coord'] = col_r2.text_input("Coordenação", value=data_aval['resp_coord'])
    
    data_aval['data_emissao'] = st.date_input("Data de Emissão", value=data_aval['data_emissao'])

    submit = st.form_submit_button("📄 GERAR ARQUIVO WORD (.DOCX) PARA EDIÇÃO")

if submit:
    # Geração do DOCX
    doc = Document()
    
    # Estilo padrão
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Arial'
    font.size = Pt(11)

    # Cabeçalho
    def add_centered(text, size, bold=True):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(text)
        run.bold = bold
        run.font.size = Pt(size)
        return p

    add_centered("PREFEITURA MUNICIPAL DE LIMEIRA", 12)
    add_centered("CEIEF RAFAEL AFFONSO LEITE", 14)
    doc.add_paragraph("_" * 70).alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph()
    
    p_title = add_centered("AVALIAÇÃO PEDAGÓGICA: APOIO ESCOLAR PARA ESTUDANTE COM DEFICIÊNCIA", 12)
    doc.add_paragraph()

    # Identificação
    p_id = doc.add_paragraph()
    p_id.add_run("Estudante: ").bold = True
    p_id.add_run(f"{data_aval['nome']}")
    
    p_id2 = doc.add_paragraph()
    p_id2.add_run("Ano escolaridade: ").bold = True
    p_id2.add_run(f"{data_aval['ano_esc']}")
    
    # Deficiências
    doc.add_paragraph().add_run("Deficiências:").bold = True
    for d in defs_opts:
        mark = " [X] " if d in data_aval['defic_chk'] else " [  ] "
        doc.add_paragraph(mark + d)
    if data_aval['defic_outra']:
        doc.add_paragraph(f" [X] Outra: {data_aval['defic_outra']}")
    
    doc.add_paragraph()

    # Legislação Integral
    p_leg_header = doc.add_paragraph()
    p_leg_header.add_run("PRESSUPOSTOS LEGAIS:").bold = True
    
    doc.add_paragraph("1- Lei nº 12.764/2012, em seu artigo 3º que trata dos direitos da pessoa com transtorno do espectro autista indica:")
    p_leg1 = doc.add_paragraph()
    p_leg1.paragraph_format.left_indent = Pt(36)
    p_leg1.add_run("Parágrafo único. Em casos de comprovada necessidade, a pessoa com transtorno do espectro autista incluída nas classes comuns de ensino regular, nos termos do inciso IV do art. 2º, terá direito a acompanhante especializado.").italic = True
    
    doc.add_paragraph("2- Lei Brasileira de Inclusão da Pessoa com Deficiência (LBI) no art. 3º, inciso XIII, descreve as ações referentes ao apoio:")
    p_leg2 = doc.add_paragraph()
    p_leg2.paragraph_format.left_indent = Pt(36)
    p_leg2.add_run("XIII - profissional de apoio escolar: pessoa que exerce atividades de alimentação, higiene e locomoção do estudante com deficiência e atua em todas as atividades escolares nas quais se fizer necessária, em todos os níveis e modalidades de ensino, em instituições públicas e privadas, excluídas as técnicas ou os procedimentos identificados com profissões legalmente estabelecidas;").italic = True
    
    doc.add_paragraph("3- CNE/CEB nº 02/01, do Conselho Nacional de Educação, que Instituiu as Diretrizes Nacionais para a Educação Especial na Educação Básica, cujo artigo 6º assim dispõe:")
    p_leg3 = doc.add_paragraph()
    p_leg3.paragraph_format.left_indent = Pt(36)
    p_leg3.add_run("Art. 6º Para a identificação das necessidades educacionais especiais dos alunos e a tomada de decisões quanto ao atendimento necessário, a escola deve realizar, com assessoramento técnico, avaliação do aluno no processo de ensino e aprendizagem, contando, para tal, com:").italic = True
    
    p_leg3_list = doc.add_paragraph()
    p_leg3_list.paragraph_format.left_indent = Pt(72)
    p_leg3_list.add_run("I – a experiência de seu corpo docente, seus diretores, coordenadores, orientadores e supervisores educacionais;\nII – o setor responsável pela educação especial do respectivo sistema;\nIII – a colaboração da família e a cooperação dos serviços de Saúde, Assistência Social, Trabalho, Justiça e Esporte, bem como do Ministério Público, quando necessário.").italic = True

    doc.add_page_break()

    # Aspectos Gerais
    p_asp = doc.add_paragraph()
    p_asp.add_run("ASPECTOS GERAIS DA VIDA ESCOLAR DO ESTUDANTE:").bold = True
    doc.add_paragraph(data_aval['aspectos_gerais'])
    doc.add_paragraph()

    # Itens de Avaliação 1 a 12
    def add_docx_item(title, opts, selected, obs=""):
        p = doc.add_paragraph()
        p.add_run(title).bold = True
        for o in opts:
            checked = " [X] " if (o == selected or (isinstance(selected, list) and o in selected)) else " [  ] "
            doc.add_paragraph(checked + o)
        if obs:
            doc.add_paragraph(f"Obs: {obs}")
        doc.add_paragraph()

    add_docx_item("1. ALIMENTAÇÃO:", opts_alim, data_aval['alim_nivel'], data_aval['alim_obs'])
    add_docx_item("2. HIGIENE:", opts_hig, data_aval['hig_nivel'], data_aval['hig_obs'])
    add_docx_item("3. LOCOMOÇÃO:", opts_loc, data_aval['loc_nivel'], data_aval['loc_obs'])
    add_docx_item("4. COMPORTAMENTO:", opts_comp, data_aval['comportamento'], data_aval['comp_obs'])
    add_docx_item("5. PARTICIPAÇÃO EM GRUPO:", opts_part, data_aval['part_grupo'], data_aval['part_obs'])
    
    interac_val = data_aval['interacao']
    if interac_val == "Outros": interac_val = f"Outros: {data_aval['interacao_outros']}"
    add_docx_item("6. INTERAÇÃO:", opts_int, interac_val)
    
    add_docx_item("7. ROTINA EM SALA DE AULA:", opts_rot, data_aval['rotina'], data_aval['rotina_obs'])
    add_docx_item("8. ATIVIDADES PEDAGÓGICAS:", opts_ativ, data_aval['ativ_pedag'])
    add_docx_item("9. ATENÇÃO SUSTENTADA:", opts_at_sust, data_aval['atencao_sust'])
    add_docx_item("10. ATENÇÃO DIVIDIDA:", opts_at_div, data_aval['atencao_div'])
    add_docx_item("11. ATENÇÃO SELETIVA:", opts_at_sel, data_aval['atencao_sel'])
    add_docx_item("12. LINGUAGEM:", opts_ling, data_aval['linguagem'], data_aval['ling_obs'])

    # Tabela de Níveis
    doc.add_page_break()
    doc.add_paragraph().add_run("TABELA DE NÍVEIS DE APOIO:").bold = True
    table = doc.add_table(rows=1, cols=2)
    table.style = 'Table Grid'
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = 'NÍVEIS DE APOIO'
    hdr_cells[1].text = 'CARACTERÍSTICAS'
    
    levels = [
        ("Não há necessidade de apoio", "O estudante apresenta autonomia. As ações disponibilizadas aos demais estudantes são suficientes, acrescidas de ações do AEE."),
        ("Nível 1 - Apoio pouco substancial", "Não há necessidade de apoio constante, apenas em ações pontuais."),
        ("Nível 2 - Apoio substancial", "Há necessidade de apoio constante ao estudante em sala de aula."),
        ("Nível 3 - Apoio muito substancial", "Casos severos com necessidade de monitor e ações específicas: flexibilização de horário e espaços.")
    ]
    for n, c in levels:
        row_cells = table.add_row().cells
        row_cells[0].text = n
        row_cells[1].text = c

    doc.add_paragraph()
    doc.add_paragraph().add_run(f"CONCLUSÃO: O estudante necessita de {data_aval['conclusao_nivel'].upper()}").bold = True
    if data_aval['apoio_existente']:
        doc.add_paragraph(f"Apoio existente: {data_aval['apoio_existente']}")

    doc.add_paragraph()
    doc.add_paragraph(f"Limeira, {data_aval['data_emissao'].strftime('%d de %B de %Y')}")
    doc.add_paragraph("\n\n")

    # Assinaturas
    sigs = [
        f"Prof. Sala Regular: {data_aval['resp_sala']}",
        f"Prof. Ed. Especial: {data_aval['resp_ee']}",
        f"Direção: {data_aval['resp_dir']}",
        f"Coordenação: {data_aval['resp_coord']}"
    ]
    for s in sigs:
        doc.add_paragraph("_" * 50)
        doc.add_paragraph(s)
        doc.add_paragraph()

    # Salvar em buffer
    target_stream = io.BytesIO()
    doc.save(target_stream)
    st.session_state.docx_bytes = target_stream.getvalue()
    st.success("Arquivo Gerado! Clique no botão abaixo para baixar.")

if 'docx_bytes' in st.session_state:
    st.download_button(
        label="📥 BAIXAR ARQUIVO WORD (.DOCX)",
        data=st.session_state.docx_bytes,
        file_name=f"Avaliacao_{data_aval['nome'].replace(' ', '_')}.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        type="primary"
    )
