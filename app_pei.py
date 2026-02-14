import streamlit as st
from fpdf import FPDF
from datetime import datetime, date
import io
import os
import base64
import json

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(
    page_title="SME Limeira | Sistema AEE",
    layout="wide",
    page_icon="🎓",
    initial_sidebar_state="expanded"
)

# --- ESTILO VISUAL DA INTERFACE (CSS MELHORADO) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #f8fafc; }
    .stButton button { width: 100%; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# --- BANCO DE DADOS ---
DB_FILE = "banco_dados_aee_final.json"

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except:
                return {}
    return {}

def save_student(doc_type, name, data):
    db = load_db()
    key = f"{name} ({doc_type})"

    def serialize(obj):
        if isinstance(obj, (datetime, date)):
            return obj.strftime("%Y-%m-%d")
        elif isinstance(obj, dict):
            return {k: serialize(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [serialize(i) for i in obj]
        return obj

    clean_data = serialize(data)
    db[key] = clean_data
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=4, ensure_ascii=False)

    st.toast(f"✅ Documento de {name} salvo com sucesso!", icon="💾")

def delete_student(student_key):
    db = load_db()
    if student_key in db:
        del db[student_key]
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=4, ensure_ascii=False)
        st.toast(f"🗑️ Registro excluído com sucesso!", icon="🔥")
        return True
    return False

# --- INICIALIZAÇÃO ---
if 'data_pei' not in st.session_state: 
    st.session_state.data_pei = {
        'terapias': {}, 'avaliacao': {}, 'flex': {}, 'plano_ensino': {},
        'comunicacao_tipo': [], 'permanece': []
    }

if 'data_case' not in st.session_state: 
    st.session_state.data_case = {'irmaos': [{'nome': '', 'idade': '', 'esc': ''} for _ in range(4)], 'checklist': {}}

# --- BARRA LATERAL ---
with st.sidebar:
    st.markdown('<div class="sidebar-header">', unsafe_allow_html=True)
    st.markdown("""
        <div class="sidebar-title">SISTEMA INTEGRA RAFAEL</div>
        <div class="sidebar-subtitle">Gestão de Educação Especial</div>
        </div>
    """, unsafe_allow_html=True)
    
    st.divider()

    # Seleção de estudante
    st.markdown("### 👤 Selecionar Estudante")
    db = load_db()
    all_students = list(db.keys())
    
    selected_student = st.selectbox(
        "Selecione para abrir ou criar novo:", 
        ["-- Novo Registro --"] + all_students,
        label_visibility="collapsed"
    )

    # Tipo de documento
    st.markdown("### 📂 Tipo de Documento")
    default_doc_idx = 0
    if selected_student != "-- Novo Registro --":
        if "(CASO)" in selected_student: default_doc_idx = 1
    
    doc_mode = st.radio(
        "Documento:", 
        ["PEI (Plano Educacional)", "Estudo de Caso"],
        index=default_doc_idx,
        label_visibility="collapsed"
    )
# ==============================================================================
# PEI
# ==============================================================================
if "PEI" in doc_mode:
    st.markdown(f"""<div class="header-box"><div class="header-title">Plano Educacional Individualizado - PEI</div></div>""", unsafe_allow_html=True)
    tabs = st.tabs(["1. Identificação", "2. Saúde", "3. Conduta", "4. Escolar", "5. Acadêmico", "6. Metas/Flex", "7. Emissão"])
    data = st.session_state.data_pei

    # --- Aba 1: Identificação ---
    with tabs[0]:
        c1, c2 = st.columns([3, 1])
        data['nome'] = c1.text_input("Nome", value=data.get('nome', ''))
        d_val = data.get('nasc')
        if isinstance(d_val, str):
            try: d_val = datetime.strptime(d_val, '%Y-%m-%d').date()
            except: d_val = date.today()
        data['nasc'] = c2.date_input("Nascimento", value=d_val if d_val else date.today())
        c3, c4 = st.columns(2)
        data['idade'] = c3.text_input("Idade", value=data.get('idade', ''))
        data['ano_esc'] = c4.text_input("Ano Escolar", value=data.get('ano_esc', ''))
        data['mae'] = st.text_input("Nome da Mãe", value=data.get('mae', ''))
        data['pai'] = st.text_input("Nome do Pai", value=data.get('pai', ''))
        data['tel'] = st.text_input("Telefone", value=data.get('tel', ''))
        st.markdown("**Docentes Responsáveis**")
        d1, d2, d3 = st.columns(3)
        data['prof_poli'] = d1.text_input("Polivalente/Regente", value=data.get('prof_poli', ''))
        data['prof_aee'] = d2.text_input("Prof. AEE", value=data.get('prof_aee', ''))
        data['prof_arte'] = d3.text_input("Arte", value=data.get('prof_arte', ''))
        d4, d5, d6 = st.columns(3)
        data['prof_ef'] = d4.text_input("Ed. Física", value=data.get('prof_ef', ''))
        data['prof_tec'] = d5.text_input("Tecnologia", value=data.get('prof_tec', ''))
        data['gestor'] = d6.text_input("Gestor Escolar", value=data.get('gestor', ''))
        dg1, dg2 = st.columns(2)
        data['coord'] = dg1.text_input("Coordenação", value=data.get('coord', ''))
        data['revisoes'] = st.text_input("Revisões", value=data.get('revisoes', ''))
        elab_opts = ["1º Trimestre", "2º Trimestre", "3º Trimestre", "Anual"]
        elab_idx = elab_opts.index(data['elab_per']) if data.get('elab_per') in elab_opts else 0
        data['elab_per'] = st.selectbox("Período", elab_opts, index=elab_idx)

    # --- Aba 2: Saúde ---
    with tabs[1]:
        st.subheader("Informações de Saúde")
        diag_idx = 0 if data.get('diag_status') == "Sim" else 1
        data['diag_status'] = st.radio("Diagnóstico conclusivo?", ["Sim", "Não"], horizontal=True, index=diag_idx)
        c_l1, c_l2 = st.columns(2)
        ld_val = data.get('laudo_data')
        if isinstance(ld_val, str):
            try: ld_val = datetime.strptime(ld_val, '%Y-%m-%d').date()
            except: ld_val = date.today()
        data['laudo_data'] = c_l1.date_input("Data do Laudo Médico", value=ld_val if ld_val else date.today())
        data['laudo_medico'] = c_l2.text_input("Médico Responsável pelo Laudo", value=data.get('laudo_medico', ''))
        
        st.markdown("Categorias de Diagnóstico:")
        cats = ["Deficiência", "Transtorno do Neurodesenvolvimento", "Transtornos Aprendizagem", "AH/SD", "Outros"]
        data['diag_tipo'] = data.get('diag_tipo', [])
        c_c1, c_c2 = st.columns(2)
        for i, cat in enumerate(cats):
            col = c_c1 if i % 2 == 0 else c_c2
            if col.checkbox(cat, value=cat in data['diag_tipo'], key=f"ui_cat_{cat}"):
                if cat not in data['diag_tipo']: data['diag_tipo'].append(cat)
            else:
                if cat in data['diag_tipo']: data['diag_tipo'].remove(cat)
        
        data['defic_txt'] = st.text_input("Descrição da Deficiência", value=data.get('defic_txt', ''))
        data['neuro_txt'] = st.text_input("Descrição do Transtorno Neuro", value=data.get('neuro_txt', ''))
        data['aprend_txt'] = st.text_input("Descrição do Transtorno de Aprendizagem", value=data.get('aprend_txt', ''))

        st.divider(); st.markdown("**Terapias que realiza**")
        especs = ["Psicologia", "Fonoaudiologia", "Terapia Ocupacional", "Psicopedagogia", "Fisioterapia", "Outros"]
        if 'terapias' not in data: data['terapias'] = {}
        for esp in especs:
            with st.expander(esp):
                if esp not in data['terapias']: data['terapias'][esp] = {'realiza': False, 'dias': [], 'horario': ''}
                data['terapias'][esp]['realiza'] = st.checkbox("Realiza?", value=data['terapias'][esp].get('realiza', False), key=f"ui_check_{esp}")
                if data['terapias'][esp]['realiza']:
                    if esp == "Outros": data['terapias'][esp]['nome_custom'] = st.text_input("Especifique a terapia:", value=data['terapias'][esp].get('nome_custom', ''), key="ui_custom_name")
                    data['terapias'][esp]['dias'] = st.multiselect("Dias", ["2ª", "3ª", "4ª", "5ª", "6ª", "Sábado", "Domingo"], default=data['terapias'][esp].get('dias', []), key=f"ui_dias_{esp}")
                    data['terapias'][esp]['horario'] = st.text_input("Horário", value=data['terapias'][esp].get('horario', ''), key=f"ui_hor_{esp}")
        
        st.divider(); data['med_nome'] = st.text_area("Nome da(s) Medicação(ões)", value=data.get('med_nome', ''))
        m1, m2 = st.columns(2); data['med_hor'] = m1.text_input("Horário(s)", value=data.get('med_hor', '')); data['med_doc'] = m2.text_input("Médico Responsável", value=data.get('med_doc', ''))
        data['med_obj'] = st.text_area("Objetivo da medicação", value=data.get('med_obj', ''))
        data['saude_extra'] = st.text_area("Outras informações de saúde consideradas relevantes:", value=data.get('saude_extra', ''))

    # --- Aba 3: Conduta ---
    with tabs[2]:
        st.subheader("3. Protocolo de Conduta")
        st.markdown("### 🗣️ COMUNICAÇÃO")
        com_opts = ["Oralmente", "Não comunica", "Não se aplica", "Comunicação alternativa"]
        com_idx = com_opts.index(data['com_tipo']) if data.get('com_tipo') in com_opts else 0
        data['com_tipo'] = st.selectbox("Como o estudante se comunica?", com_opts, index=com_idx)
        data['com_alt_espec'] = st.text_input("Especifique (Comunicação alternativa):", value=data.get('com_alt_espec', ''))
        
        nec_idx = 0 if data.get('com_necessidades') == 'Sim' else 1
        data['com_necessidades'] = st.radio("É capaz de expressar necessidades, desejos e interesses?", ["Sim", "Não"], horizontal=True, index=nec_idx)
        data['com_necessidades_espec'] = st.text_input("Especifique necessidades:", value=data.get('com_necessidades_espec', ''))
        
        cha_idx = 0 if data.get('com_chamado') == 'Sim' else 1
        data['com_chamado'] = st.radio("Atende quando é chamado?", ["Sim",
        data['com_chamado'] = st.radio("Atende quando é chamado?", ["Sim", "Não"], horizontal=True, index=cha_idx)
        data['com_chamado_espec'] = st.text_input("Especifique chamado:", value=data.get('com_chamado_espec', ''))
        
        cmd_idx = 0 if data.get('com_comandos') == 'Sim' else 1
        data['com_comandos'] = st.radio("Responde a comandos simples?", ["Sim", "Não"], horizontal=True, index=cmd_idx)
        data['com_comandos_espec'] = st.text_input("Especifique comandos:", value=data.get('com_comandos_espec', ''))

        st.divider(); st.markdown("### 🚶 LOCOMOÇÃO")
        loc_r_idx = 1 if data.get('loc_reduzida') == 'Sim' else 0
        data['loc_reduzida'] = st.radio("Possui mobilidade reduzida?", ["Não", "Sim"], horizontal=True, index=loc_r_idx)
        data['loc_reduzida_espec'] = st.text_input("Especifique mobilidade:", value=data.get('loc_reduzida_espec', ''))
        c_l1, c_l2 = st.columns(2)
        amb_idx = 0 if data.get('loc_ambiente') == 'Sim' else 1
        data['loc_ambiente'] = c_l1.radio("Locomove-se pela casa e em outros ambientes?", ["Sim", "Não"], horizontal=True, index=amb_idx)
        helper_idx = 0 if data.get('loc_ambiente_ajuda') == 'Com autonomia' else 1
        data['loc_ambiente_ajuda'] = c_l2.selectbox("Grau:", ["Com autonomia", "Com ajuda"], index=helper_idx, key="loc_degree_ui")
        data['loc_ambiente_espec'] = st.text_input("Especifique locomoção:", value=data.get('loc_ambiente_espec', ''))

        st.divider(); st.markdown("### 🧼 AUTOCUIDADO E HIGIENE")
        c_h1, c_h2 = st.columns(2)
        wc_idx = 0 if data.get('hig_banheiro') == 'Sim' else 1
        data['hig_banheiro'] = c_h1.radio("Utiliza o banheiro?", ["Sim", "Não"], horizontal=True, index=wc_idx)
        wc_help_idx = 0 if data.get('hig_banheiro_ajuda') == 'Com autonomia' else 1
        data['hig_banheiro_ajuda'] = c_h2.selectbox("Ajuda banheiro:", ["Com autonomia", "Com ajuda"], index=wc_help_idx, key="hig_wc_degree_ui")
        data['hig_banheiro_espec'] = st.text_input("Especifique banheiro:", value=data.get('hig_banheiro_espec', ''))
        
        c_h3, c_h4 = st.columns(2)
        tooth_idx = 0 if data.get('hig_dentes') == 'Sim' else 1
        data['hig_dentes'] = c_h3.radio("Escova os dentes?", ["Sim", "Não"], horizontal=True, index=tooth_idx)
        tooth_help_idx = 0 if data.get('hig_dentes_ajuda') == 'Com autonomia' else 1
        data['hig_dentes_ajuda'] = c_h4.selectbox("Ajuda dentes:", ["Com autonomia", "Com ajuda"], index=tooth_help_idx, key="hig_tooth_degree_ui")
        data['hig_dentes_espec'] = st.text_input("Especifique dentes:", value=data.get('hig_dentes_espec', ''))

        st.divider(); st.markdown("### 🧩 COMPORTAMENTO E INTERESSES")
        data['beh_interesses'] = st.text_area("Quais são os interesses do estudante?", value=data.get('beh_interesses', ''))
        data['beh_objetos_gosta'] = st.text_area("Quais objetos que gosta? Tem um objeto de apego?", value=data.get('beh_objetos_gosta', ''))
        data['beh_objetos_odeia'] = st.text_area("Quais objetos o estudante não gosta e/ou causam aversão?", value=data.get('beh_objetos_odeia', ''))
        data['beh_toque'] = st.text_area("Gosta de toque, abraço, beijo?", value=data.get('beh_toque', ''))
        data['beh_calmo'] = st.text_area("O que o deixa calmo e relaxado?", value=data.get('beh_calmo', ''))
        data['beh_atividades'] = st.text_area("Quais atividades são mais prazerosas?", value=data.get('beh_atividades', ''))
        data['beh_gatilhos'] = st.text_area("Quais são os gatilhos já identificados para episódios de crise?", value=data.get('beh_gatilhos', ''))
        data['beh_crise_regula'] = st.text_area("Quando o estudante está em crise como normalmente se regula?", value=data.get('beh_crise_regula', ''))
        data['beh_desafios'] = st.text_area("O estudante costuma apresentar comportamentos desafiadores? Neste caso o que fazer? Qual a melhor forma de agir para que a criança se autorregule?", value=data.get('beh_desafios', ''))
        
        c_b1, c_b2 = st.columns([1, 2])
        food_idx = 1 if data.get('beh_restricoes') == 'Sim' else 0
        data['beh_restricoes'] = c_b1.radio("Tem restrições alimentares? Alergias ou seletividade alimentar?", ["Não", "Sim"], horizontal=True, index=food_idx)
        data['beh_restricoes_espec'] = c_b2.text_input("Especifique alimentação:", value=data.get('beh_restricoes_espec', ''), key="food_espec_ui")
        
        c_b3, c_b4 = st.columns([1, 2])
        water_idx = 0 if data.get('beh_autonomia_agua') == 'Sim' else 1
        data['beh_autonomia_agua'] = c_b3.radio("Tem autonomia para tomar água e se alimentar?", ["Sim", "Não"], horizontal=True, index=water_idx)
        data['beh_autonomia_agua_espec'] = c_b4.text_input("Especifique autonomia:", value=data.get('beh_autonomia_agua_espec', ''), key="water_espec_ui")
        data['beh_pertinentes'] = st.text_area("Outras informações julgadas pertinentes:", value=data.get('beh_pertinentes', ''))

    # --- Aba 4: Escolar ---
    with tabs[3]:
        st.subheader("4. Desenvolvimento Escolar")
        
        c_p1, c_p2 = st.columns([1, 2])
        perm_options = ["Sim - Por longo período", "Sim - Por curto período", "Não"]
        perm_idx = perm_options.index(data.get('dev_permanece', "Sim - Por longo período")) if data.get('dev_permanece') in perm_options else 0
        data['dev_permanece'] = c_p1.selectbox("Permanece em sala e aula?", perm_options, index=perm_idx)
        data['dev_permanece_espec'] = c_p2.text_input("Especifique (Permanência):", value=data.get('dev_permanece_espec', ''))

        c_i1, c_i2 = st.columns([1, 2])
        int_idx = 0 if data.get('dev_integrado') == 'Sim' else 1
        data['dev_integrado'] = c_i1.radio("Está integrado ao ambiente escolar?", ["Sim", "Não"], horizontal=True, index=int_idx)
        data['dev_integrado_espec'] = c_i2.text_input("Especifique (Integração):", value=data.get('dev_integrado_espec', ''))

        c_l1, c_l2, c_l3 = st.columns([1, 1, 2])
        loc_options = ["Sim - Com autonomia", "Sim - Com ajuda", "Não"]
        loc_idx = loc_options.index(data.get('dev_loc_escola', "Sim - Com autonomia")) if data.get('dev_loc_escola') in loc_options else 0
        data['dev_loc_escola'] = c_l1.selectbox("Locomove-se pela escola?", loc_options, index=loc_idx)
        data['dev_loc_escola_espec'] = c_l3.text_input("Especifique (Locomoção escola):", value=data.get('dev_loc_escola_espec', ''))

        c_t1, c_t2, c_t3 = st.columns([1, 1, 2])
        tar_options = ["Sim - Com autonomia", "Sim - Com ajuda", "Não"]
        tar_idx = tar_options.index(data.get('dev_tarefas', "Sim - Com autonomia")) if data.get('dev_tarefas') in tar_options else 0
        data['dev_tarefas'] = c_t1.selectbox("Realiza tarefas escolares?", tar_options, index=tar_idx)
        data['dev_tarefas_espec'] = c_t3.text_input("Especifique (Tarefas):", value=data.get('dev_tarefas_espec', ''))

        c_a1, c_a2 = st.columns([1, 2])
        amg_idx = 0 if data.get('dev_amigos') == 'Sim' else 1
        data['dev_amigos'] = c_a1.radio("Tem amigos?", ["Sim", "Não"], horizontal=True, index=amg_idx)
        data['dev_amigos_espec'] = c_a2.text_input("Especifique (Amigos):", value=data.get('dev_amigos_espec', ''))

        data['dev_colega_pref'] = st.radio("Tem um colega predileto?", ["Sim", "Não"], horizontal=True, index=0 if data.get('dev_colega_pref') == 'Sim' else 1)

        c_ia1, c_ia2 = st.columns([1, 2])
        ia_idx = 0 if data.get('dev_participa') == 'Sim' else 1
        data['dev_participa'] = c_ia1.radio("Participa das atividades e interage?", ["Sim", "Não"], horizontal=True, index=ia_idx)
        data['dev_participa_espec'] = c_ia2.text_input("Especifique (Interação):", value=data.get('dev_participa_espec', ''))

        data['dev_afetivo'] = st.text_area("Como é o envolvimento afetivo e social da turma com o estudante?", value=data.get('dev_afetivo', ''))

    # --- Aba 5: Avaliação Acadêmica ---
    with tabs[4]:
        st.subheader("5. Avaliação Acadêmica do Estudante")
        st.info("Descreva o desenvolvimento do estudante em cada área.")

        if pei_level == "Fundamental":
            # --- LAYOUT FUNDAMENTAL ---
            c_f1, c_f2 = st.columns(2)
            data['aval_port'] = c_f1.text_area("Língua Portuguesa", value=data.get('aval_port', ''))
            data['aval_mat'] = c_f2.text_area("Matemática", value=data.get('aval_mat', ''))
            data['aval_con_gerais'] = st.text_area("Conhecimentos Gerais", value=data.get('aval_con_gerais', ''))

            st.divider()
            st.markdown("### 🎨 ARTE")
            data['aval_arte_visuais'] = st.text_area("Artes Visuais: Produções artísticas", value=data.get('aval_arte_visuais', ''))
            data['aval_arte_musica'] = st.text_area("Música: Estudos dos sons", value=data.get('aval_arte_musica', ''))
            c_a1, c_a2 = st.columns(2)
            data['aval_arte_teatro'] = c_a1.text_area("Teatro: Formas teatrais", value=data.get('aval_arte_teatro', ''))
            data['aval_arte_danca'] = c_a2.text_area("Dança: Gêneros e modalidades", value=data.get('aval_arte_danca', ''))

            st.divider()
            st.markdown("### ⚽ EDUCAÇÃO FÍSICA")
            c_ef1, c_ef2 = st.columns(2)
            data['aval_ef_motoras'] = c_ef1.text_area("Habilidades Motoras", value=data.get('aval_ef_motoras', ''))
            data['aval_ef_corp_conhec'] = c_ef2.text_area("Conhecimento Corporal", value=data.get('aval_ef_corp_conhec', ''))
            data['aval_ef_exp'] = st.text_area("Experiências Corporais e Expressividade", value=data.get('aval_ef_exp', ''))

            st.divider()
            st.markdown("### 💻 LINGUAGENS E TECNOLOGIAS")
            data['aval_ling_tec'] = st.text_area("Avaliação da disciplina:", value=data.get('aval_ling_tec', ''))

        else:
            # --- LAYOUT INFANTIL ---
            data['aval_ling_verbal'] = st.text_area("Linguagem Verbal", value=data.get('aval_ling_verbal', ''))
            data['aval_ling_mat'] = st.text_area("Linguagem Matemática", value=data.get('aval_ling_mat', ''))
            data['aval_ind_soc'] = st.text_area("Indivíduo e Sociedade", value=data.get('aval_ind_soc', ''))

            st.divider()
            st.markdown("### 🎨 ARTE")
            data['aval_arte_visuais'] = st.text_area("Artes Visuais", value=data.get('aval_arte_visuais', ''))
            data['aval_arte_musica'] = st.text_area("Música", value=data.get('aval_arte_musica', ''))
            data['aval_arte_teatro'] = st.text_area("Teatro", value=data.get('aval_arte_teatro', ''))

            st.divider()
            st.markdown("### ⚽ EDUCAÇÃO FÍSICA")
            c_ef1, c_ef2, c_ef3 = st.columns(3)
            data['aval_ef_motoras'] = c_ef1.text_area("Habilidades Motoras", value=data.get('aval_ef_motoras', ''))
            data['aval_ef_corp_conhec'] = c_ef2.text_area("Conhecimento Corporal", value=data.get('aval_ef_corp_conhec', ''))
            data['aval_ef_exp'] = c_ef3.text_area("Experiências Corporais", value=data.get('aval_ef_exp', ''))
