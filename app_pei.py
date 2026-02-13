import streamlit as st
from fpdf import FPDF
from datetime import datetime, date
import io
import os
import base64
import json
import pandas as pd  # <--- ESTA LINHA É A QUE ESTÁ FALTANDO
import json
from streamlit_gsheets import GSheetsConnection

conn = st.connection("gsheets", type=GSheetsConnection)

# --- OCULTAR TOOLBAR E MENU ---
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            header {visibility: hidden;}
            footer {visibility: hidden;}
            .stAppDeployButton {display:none;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- FUNÇÃO DE LOGIN COMPLETA E ROBUSTA (SME LIMEIRA) ---
def login():
    # Inicializa o estado de autenticação se não existir
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        # Layout centralizado e limpo
        st.markdown("""
            <div style="text-align: center; padding: 20px;">
                <h2 style="color: #1e3a8a;">SISTEMA INTEGRA AEE</h2>
                <p style="color: #64748b;">Acesso restrito aos docentes do CEIEF Rafael Affonso Leite</p>
            </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 1.5, 1])
        with col2:
            with st.form("login_form"):
                user_id = st.text_input("Matrícula (Funcional)")
                # A senha agora é buscada direto do painel 'Secrets' do Streamlit
                password = st.text_input("Senha do Sistema", type="password")
                submit = st.form_submit_button("Entrar")
                
                if submit:
                    try:
                        # 1. Busca a senha mestre nos Secrets (Segurança)
                        # No painel do Streamlit Cloud, em Secrets, adicione:
                        # [credentials]
                        # password = "sua_senha_aqui"
                        SENHA_MESTRA = st.secrets["credentials"]["password"]
                        
                        # 2. Busca a lista de professores na aba 'Professores'
                        df_professores = conn.read(worksheet="Professores", ttl=0)
                        
                        # --- TRATAMENTO DE DADOS (PARA NÃO DAR ERRO DE RECONHECIMENTO) ---
                        # Converte para texto, remove o ".0" do final e tira espaços vazios
                        df_professores['matricula'] = df_professores['matricula'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
                        user_id_limpo = str(user_id).strip()
                        
                        # 3. Validação dupla (Senha + Matrícula na lista)
                        if password == SENHA_MESTRA and user_id_limpo in df_professores['matricula'].values:
                            # Busca o nome do professor para personalizar a saudação
                            registro = df_professores[df_professores['matricula'] == user_id_limpo]
                            nome_prof = registro['nome'].values[0]
                            
                            st.session_state.authenticated = True
                            st.session_state.usuario_nome = nome_prof
                            st.success(f"Acesso liberado! Bem-vindo(a), {nome_prof}.")
                            st.rerun()
                        else:
                            st.error("Matrícula não cadastrada ou senha incorreta.")
                            
                    except Exception as e:
                        st.error("Erro técnico: Verifique se a aba 'Professores' existe e se a senha está nos Secrets.")
        
        # Interrompe o carregamento do restante do app até que o login seja feito
        st.stop()

# --- ATIVAÇÃO DO LOGIN ---
login()

# Se o código continuar daqui, o usuário está logado.
# Exibimos o nome do professor na barra lateral para confirmação
st.sidebar.markdown(f"👤 **Docente:** {st.session_state.get('usuario_nome', 'Professor')}")


def registrar_log(acao, aluno="N/A", detalhes=""):
    """Registra a atividade do professor na aba Log"""
    try:
        # Pega os dados do professor logado no st.session_state
        prof_nome = st.session_state.get('usuario_nome', 'Desconhecido')
        # Precisamos garantir que a matrícula foi salva no login
        prof_mat = st.session_state.get('usuario_matricula', '000') 
        
        novo_log = {
            "data_hora": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "professor": prof_nome,
            "matricula": prof_mat,
            "aluno": aluno,
            "acao": acao,
            "detalhes": detalhes
        }
        
        df_log_atual = conn.read(worksheet="Log", ttl=0)
        df_novo_log = pd.concat([df_log_atual, pd.DataFrame([novo_log])], ignore_index=True)
        conn.update(worksheet="Log", data=df_novo_log)
    except Exception as e:
        print(f"Erro ao registrar log: {e}")

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(
    page_title="Integra | Sistema AEE",
    layout="wide",
    page_icon="🎓",
    initial_sidebar_state="expanded"
    
)

    # --- OCULTAR TOOLBAR E MENU ---
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            header {visibility: hidden;}
            footer {visibility: hidden;}
            .stAppDeployButton {display:none;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- ESTILO VISUAL DA INTERFACE (CSS MELHORADO) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #f8fafc; }
    
    /* Melhoria da Sidebar */
    [data-testid="stSidebar"] [data-testid="stImage"] {
        display: flex;
        justify-content: center;
        margin-left: auto;
        margin-right: auto;
    }
    
    /* Centralizar o container de texto da sidebar */
    .sidebar-header {
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
        width: 100%;
        padding-bottom: 20px;
    }
    }
    .sidebar-title {
        color: #1e3a8a; /* Azul Institucional */
        font-weight: 800;
        font-size: 1.4rem;
        margin-top: 10px;
        line-height: 1.2;
    }
    .sidebar-subtitle {
        color: #64748b;
        font-size: 0.85rem;
        font-weight: 400;
    }

    /* Estilo dos Cards Principais */
    .header-box {
        background: white; padding: 2rem; border-radius: 12px;
        border-left: 6px solid #2563eb; /* Borda lateral azul */
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        margin-bottom: 2rem;
        margin-top: -120px !important;
    }
    .header-title { color: #1e293b; font-weight: 700; font-size: 1.8rem; margin: 0; }
    
    /* Botões */
    .stButton button { width: 100%; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# --- MEMÓRIA (JSON) ---
DB_FILE = "banco_dados_aee_final.json"

def load_db():
    """Lê os dados da planilha do Google"""
    try:
        # Tenta ler a aba chamada 'Alunos'
        df = conn.read(worksheet="Alunos", ttl=0)
        # Remove linhas completamente vazias
        df = df.dropna(how="all")
        return df
    except Exception as e:
        # Se a planilha estiver vazia ou der erro, retorna um DataFrame com as colunas certas
        return pd.DataFrame(columns=["nome", "tipo_doc", "dados_json"])

def save_student(doc_type, name, data):
    """Salva ou atualiza garantindo que não duplique linhas"""
    try:
        df_atual = load_db()
        
        # 1. Geramos o ID único exatamente como ele aparece na lista
        # Se o seu sistema usa "Nome (PEI)", mantenha esse padrão
        id_registro = f"{name} ({doc_type})"
        
        # 2. Limpamos os dados para salvar
        def serializar_datas(obj):
            if isinstance(obj, (date, datetime)): return obj.strftime("%Y-%m-%d")
            if isinstance(obj, dict): return {k: serializar_datas(v) for k, v in obj.items()}
            if isinstance(obj, list): return [serializar_datas(i) for i in obj]
            return obj
            
        data_limpa = serializar_datas(data)
        novo_json = json.dumps(data_limpa, ensure_ascii=False)

        # 3. VERIFICAÇÃO DE DUPLICIDADE
        # Se o ID já existe, atualizamos a linha existente
        if not df_atual.empty and "id" in df_atual.columns and id_registro in df_atual["id"].values:
            df_atual.loc[df_atual["id"] == id_registro, "dados_json"] = novo_json
            df_final = df_atual
        else:
            # Se não existe, aí sim cria uma linha nova
            novo_registro = {
                "id": id_registro,
                "nome": name,
                "tipo_doc": doc_type,
                "dados_json": novo_json
            }
            df_final = pd.concat([df_atual, pd.DataFrame([novo_registro])], ignore_index=True)

        # 4. Envia para a planilha
        conn.update(worksheet="Alunos", data=df_final)
        st.toast(f"✅ Alterações em {name} salvas na mesma linha!", icon="💾")
        
    except Exception as e:
        st.error(f"Erro ao salvar sem duplicar: {e}")

def delete_student(student_key):
    db = load_db()
    if student_key in db:
        del db[student_key]
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=4, ensure_ascii=False)
        st.toast(f"🗑️ Registro excluído com sucesso!", icon="🔥")
        return True
    return False
    
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

from streamlit_autorefresh import st_autorefresh

# --- CONFIGURAÇÃO DO SALVAMENTO AUTOMÁTICO ---
# O intervalo é em milissegundos (60000ms = 1 minuto)
count = st_autorefresh(interval=60000, key="autosave_counter")

def auto_save():
    # 1. Verifica se o usuário está logado
    if st.session_state.get('authenticated'):
        
        # 2. Busca o modo de documento do session_state (onde ele fica guardado com segurança)
        # Substituímos o 'doc_mode' direto por uma busca segura no estado da sessão
        modo_atual = st.session_state.get('doc_option', '') 

        # 3. Lógica para PEI
        if "PEI" in modo_atual:
            # Só salva se houver um nome de aluno preenchido
            if st.session_state.get('data_pei') and st.session_state.data_pei.get('nome'):
                save_student("PEI", st.session_state.data_pei['nome'], st.session_state.data_pei)
                # Opcional: registrar_log("AUTO-SAVE", st.session_state.data_pei['nome'], "Automático")
            
        # 4. Lógica para Estudo de Caso
        elif "Estudo de Caso" in modo_atual:
            if st.session_state.get('data_case') and st.session_state.data_case.get('nome'):
                save_student("CASO", st.session_state.data_case['nome'], st.session_state.data_case)

# Se o contador do autorefresh subir, ele executa a função
if count > 0:
    auto_save()

# --- ESTILO VISUAL DA INTERFACE ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #f8fafc; }
    .header-box {
        background: white; padding: 2rem; border-radius: 12px;
        border-bottom: 4px solid #2563eb; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        margin-bottom: 2rem;
    }
    .header-title { color: #1e293b; font-weight: 700; font-size: 1.8rem; margin: 0; }
    .header-subtitle { color: #64748b; font-size: 1rem; margin-top: 5px; }
</style>
""", unsafe_allow_html=True)

# --- HELPERS ---
def clean_pdf_text(text):
    if text is None or text is False: return ""
    if text is True: return "Sim"
    # Isso garante que o Python converta símbolos estranhos para algo que o PDF aceite
    return str(text).encode('latin-1', 'replace').decode('latin-1')

def get_pdf_bytes(pdf_instance):
    try: return bytes(pdf_instance.output(dest='S').encode('latin-1'))
    except: return bytes(pdf_instance.output(dest='S'))


# --- CLASSE PDF CUSTOMIZADA ---
class OfficialPDF(FPDF):
    def footer(self):
        self.set_y(-20); self.set_font('Arial', '', 9); self.set_text_color(80, 80, 80)
        addr = "Secretaria Municipal de Educação | Centro de Formação do Professor - Limeira-SP"
        self.cell(0, 5, clean_pdf_text(addr), 0, 1, 'C')
        self.set_font('Arial', 'I', 8); self.cell(0, 5, clean_pdf_text(f'Página {self.page_no()}'), 0, 0, 'R')

    def section_title(self, title, width=0):
        self.set_font('Arial', 'B', 12); self.set_fill_color(240, 240, 240)
        self.cell(width, 8, clean_pdf_text(title), 1, 1, 'L', 1)

# --- INICIALIZAÇÃO ---
if 'data_pei' not in st.session_state: 
    st.session_state.data_pei = {
        'terapias': {}, 'avaliacao': {}, 'flex': {}, 'plano_ensino': {},
        'comunicacao_tipo': [], 'permanece': []
    }
    # REMOVA A LINHA: st.session_state.data_pei.update(demo_pei)
def carregar_dados_aluno():
    selecao = st.session_state.get('aluno_selecionado')
    
    if not selecao or selecao == "-- Novo Registro --":
        st.session_state.data_pei = {'terapias': {}, 'avaliacao': {}, 'flex': {}, 'plano_ensino': {}, 'comunicacao_tipo': [], 'permanece': []}
        st.session_state.data_case = {'irmaos': [{'nome': '', 'idade': '', 'esc': ''} for _ in range(4)], 'checklist': {}, 'clinicas': []}
        st.session_state.nome_original_salvamento = None
        return

    try:
        df_db = load_db()
        # Busca o registro exato
        if "nome" in df_db.columns and selecao in df_db["nome"].values:
            registro = df_db[df_db["nome"] == selecao].iloc[0]
            dados = json.loads(registro["dados_json"])
            
            # TRAVA O NOME: Força o nome da planilha para dentro do formulário
            dados['nome'] = registro["nome"] 
            st.session_state.nome_original_salvamento = registro["nome"]

            # Reidratação de datas
            for k, v in dados.items():
                if isinstance(v, str) and len(v) == 10 and v.count('-') == 2:
                    try: dados[k] = datetime.strptime(v, '%Y-%m-%d').date()
                    except: pass
            
            if registro["tipo_doc"] == "PEI":
                st.session_state.data_pei = dados
            else:
                st.session_state.data_case = dados
                
            st.toast(f"✅ {selecao} carregado com sucesso.")
    except Exception as e:
        st.info("Pronto para novo preenchimento.")

# --- BARRA LATERAL ---
with st.sidebar:
    st.markdown('<div class="sidebar-header">', unsafe_allow_html=True)
    st.markdown("""<div class="sidebar-title">SISTEMA INTEGRA RAFAEL</div>
        <div class="sidebar-subtitle">Gestão de Educação Especial</div></div>""", unsafe_allow_html=True)
    st.divider()

    default_doc_idx = 0
    st.markdown("### 👤 Selecionar Estudante")
    df_db = load_db()
    lista_nomes = df_db["nome"].dropna().tolist() if not df_db.empty else []

    # SELECTBOX ÚNICA (on_change faz carregar automático)
    selected_student = st.selectbox(
        "Selecione o Estudante:", 
        options=["-- Novo Registro --"] + lista_nomes,
        key="aluno_selecionado",
        on_change=carregar_dados_aluno,
        label_visibility="collapsed"
    )

    if selected_student != "-- Novo Registro --":
        # Se na lista o nome contiver (CASO), muda o rádio automaticamente
        df_aluno = df_db[df_db["nome"] == selected_student]
        if not df_aluno.empty and df_aluno.iloc[0]["tipo_doc"] == "CASO":
            default_doc_idx = 1

    st.markdown("### 📂 Tipo de Documento")
    doc_mode = st.radio(
        "Documento:", ["PEI (Plano Educacional)", "Estudo de Caso"],
        index=default_doc_idx, key="doc_option", label_visibility="collapsed"
    )

    if "PEI" in doc_mode:
        st.markdown("### 🏫 Nível de Ensino")
        pei_level = st.selectbox("Nível:", ["Fundamental", "Infantil"], key="pei_level_choice")
    else:
        pei_level = None

    st.divider()
    
    # Botões de ação secundários
    if selected_student != "-- Novo Registro --":
        if st.button("🗑️ Excluir Registro", type="secondary", use_container_width=True):
            st.session_state.confirm_delete = True

    if st.button("🚪 SAIR DO SISTEMA", use_container_width=True):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

# ==============================================================================
# PEI
# ==============================================================================
if "PEI" in doc_mode:
    st.markdown(f"""<div class="header-box"><div class="header-title">Plano Educacional Individualizado - PEI</div></div>""", unsafe_allow_html=True)
    tabs = st.tabs(["1. Identificação", "2. Saúde", "3. Conduta", "4. Escolar", "5. Acadêmico", "6. Metas/Flex", "7. Emissão"])
    data = st.session_state.data_pei

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

# --- 5. AVALIAÇÃO ACADÊMICA (ADAPTADO: INFANTIL vs FUNDAMENTAL) ---
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
            # Arte no fundamental inclui Dança
            data['aval_arte_visuais'] = st.text_area("Artes Visuais: Produções artísticas (Gêneros, elementos formais, etc)", value=data.get('aval_arte_visuais', ''))
            data['aval_arte_musica'] = st.text_area("Música: Estudos dos sons (Elementos, gênero, instrumentos)", value=data.get('aval_arte_musica', ''))
            c_a1, c_a2 = st.columns(2)
            data['aval_arte_teatro'] = c_a1.text_area("Teatro: Formas teatrais (Gêneros, elementos, ação)", value=data.get('aval_arte_teatro', ''))
            data['aval_arte_danca'] = c_a2.text_area("Dança: Gêneros, modalidades e elementos da dança", value=data.get('aval_arte_danca', ''))

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
            # --- LAYOUT INFANTIL (MANTIDO) ---
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
            data['aval_ef_jogos'] = c_ef1.text_area("Jogos e Brincadeiras", value=data.get('aval_ef_jogos', ''))
            data['aval_ef_ritmo'] = c_ef2.text_area("Ritmo e Expressividade", value=data.get('aval_ef_ritmo', ''))
            data['aval_ef_corp'] = c_ef3.text_area("Conhecimento Corporal", value=data.get('aval_ef_corp', ''))
            
            st.divider()
            st.markdown("### 💻 LINGUAGEM E TECNOLOGIAS")
            data['aval_ling_tec'] = st.text_area("Avaliação da disciplina:", value=data.get('aval_ling_tec', ''))

# --- 6. METAS E FLEXIBILIZAÇÃO (ADAPTADO) ---
    with tabs[5]:
        st.header("6. Metas Específicas para o Ano em Curso")
        st.info("Defina as metas e estratégias.")

        # Metas são iguais para ambos (campos de texto livre)
        c_m1, c_m2 = st.columns(2)
        st.subheader("Habilidades Sociais")
        data['meta_social_obj'] = st.text_area("Metas (Sociais):", value=data.get('meta_social_obj', ''), height=100)
        data['meta_social_est'] = st.text_area("Estratégias (Sociais):", value=data.get('meta_social_est', ''), height=100)

        st.divider(); st.subheader("Habilidades de Autocuidado e Vida Prática")
        data['meta_auto_obj'] = st.text_area("Metas (Autocuidado):", value=data.get('meta_auto_obj', ''), height=100)
        data['meta_auto_est'] = st.text_area("Estratégias (Autocuidado):", value=data.get('meta_auto_est', ''), height=100)

        st.divider(); st.subheader("Habilidades Acadêmicas")
        data['meta_acad_obj'] = st.text_area("Metas (Acadêmicas):", value=data.get('meta_acad_obj', ''), height=100)
        data['meta_acad_est'] = st.text_area("Estratégias (Acadêmicas):", value=data.get('meta_acad_est', ''), height=100)

        # --- SEÇÃO 7: FLEXIBILIZAÇÃO ---
        st.markdown("---")
        st.header("7. Flexibilização Curricular")
        st.subheader("7.1 Disciplinas que necessitam de adaptação")
        
        # --- DEFINIÇÃO DAS DISCIPLINAS POR NÍVEL ---
        if pei_level == "Fundamental":
            disciplinas_flex = [
                "Língua Portuguesa", "Matemática", "História", "Geografia", "Ciências",
                "Arte", "Educação Física", "Linguagens e Tecnologia"
            ]
        else: # Infantil
            disciplinas_flex = [
                "Linguagem Verbal", "Linguagem Matemática", "Indivíduo e Sociedade", 
                "Arte", "Educação Física", "Linguagens e Tecnologia"
            ]

        if 'flex_matrix' not in data: data['flex_matrix'] = {}

        # Tabela Visual 7.1
        c_h1, c_h2, c_h3 = st.columns([2, 1, 1])
        c_h1.markdown("**Disciplina**"); c_h2.markdown("**Conteúdo**"); c_h3.markdown("**Metodologia**")

        for disc in disciplinas_flex:
            if disc not in data['flex_matrix']: data['flex_matrix'][disc] = {'conteudo': False, 'metodologia': False}
            c1, c2, c3 = st.columns([2, 1, 1])
            c1.write(disc)
            data['flex_matrix'][disc]['conteudo'] = c2.checkbox("Sim", key=f"flex_cont_{disc}", value=data['flex_matrix'][disc]['conteudo'])
            data['flex_matrix'][disc]['metodologia'] = c3.checkbox("Sim", key=f"flex_met_{disc}", value=data['flex_matrix'][disc]['metodologia'])

        # --- SEÇÃO 7.2: PLANO DE ENSINO ---
        st.divider()
        st.subheader("7.2 Plano de Ensino Anual")
        
        trimestres = ["1º Trimestre", "2º Trimestre", "3º Trimestre"]
        if 'plano_ensino_tri' not in data: data['plano_ensino_tri'] = {}

        tab_t1, tab_t2, tab_t3 = st.tabs(trimestres)
        tabs_tri = [tab_t1, tab_t2, tab_t3]

        for i, tri in enumerate(trimestres):
            with tabs_tri[i]:
                st.markdown(f"**Planejamento: {tri}**")
                if tri not in data['plano_ensino_tri']: data['plano_ensino_tri'][tri] = {}
                
                for disc in disciplinas_flex:
                    with st.expander(f"Disciplina: {disc}", expanded=False):
                        if disc not in data['plano_ensino_tri'][tri]:
                            data['plano_ensino_tri'][tri][disc] = {'obj': '', 'cont': '', 'met': ''}
                        
                        p_ref = data['plano_ensino_tri'][tri][disc]
                        c_p1, c_p2, c_p3 = st.columns(3)
                        p_ref['obj'] = c_p1.text_area("Objetivos", value=p_ref['obj'], key=f"pe_obj_{tri}_{disc}", height=100)
                        p_ref['cont'] = c_p2.text_area("Conteúdos", value=p_ref['cont'], key=f"pe_cont_{tri}_{disc}", height=100)
                        p_ref['met'] = c_p3.text_area("Metodologia", value=p_ref['met'], key=f"pe_met_{tri}_{disc}", height=100)

                st.markdown("Observações do Trimestre:")
                data['plano_ensino_tri'][tri]['obs'] = st.text_area("Obs/Recomendações:", value=data['plano_ensino_tri'][tri].get('obs', ''), key=f"pe_obs_{tri}")
        
        st.markdown("**Considerações e/ou recomendações finais:**")
        data['plano_obs_geral'] = st.text_area("", value=data.get('plano_obs_geral', ''))


    with tabs[6]:
        if st.button("💾 SALVAR PEI COMPLETO", type="primary"): save_student("PEI", data['nome'], data)
        if st.button("👁️ GERAR PDF COMPLETO"):
            pdf = OfficialPDF('L', 'mm', 'A4'); pdf.add_page(); pdf.set_margins(10, 10, 10)
            
            # --- PÁGINA 1 (CONGELADA) ---
            if os.path.exists("logo_prefeitura.png"): pdf.image("logo_prefeitura.png", 10, 8, 25)
            if os.path.exists("logo_escola.png"): pdf.image("logo_escola.png", 252, 4, 37) 
            pdf.set_xy(0, 12); pdf.set_font("Arial", "", 14)
            pdf.cell(305, 6, clean_pdf_text("      PREFEITURA MUNICIPAL DE LIMEIRA"), 0, 1, 'C')
            pdf.ln(6); pdf.set_font("Arial", "B", 12)
            pdf.cell(297, 6, clean_pdf_text("CEIEF RAFAEL AFFONSO LEITE"), 0, 1, 'C')
            pdf.ln(8); pdf.set_font("Arial", "B", 14)
            pdf.cell(297, 8, clean_pdf_text("PLANO EDUCACIONAL ESPECIALIZADO - PEI"), 0, 1, 'C')
            
            pdf.rect(256, 53, 30, 40)
            pdf.set_xy(255.5, 70); pdf.set_font("Arial", "", 9); pdf.cell(30, 5, "FOTO", 0, 0, 'C')
            
            pdf.set_xy(10, 48); table_w = 240; h = 9 
            pdf.section_title("1. IDENTIFICAÇÃO DO ESTUDANTE", width=table_w) 
            pdf.set_font("Arial", "B", 12); pdf.cell(40, h, "Estudante:", 1); pdf.set_font("Arial", "", 12); pdf.cell(table_w-40, h, clean_pdf_text(data.get('nome', '')), 1, 1)
            pdf.set_font("Arial", "B", 12); pdf.cell(40, h, "Nascimento:", 1); pdf.set_font("Arial", "", 12); pdf.cell(40, h, clean_pdf_text(str(data.get('nasc', ''))), 1)
            pdf.set_font("Arial", "B", 12); pdf.cell(20, h, "Idade:", 1); pdf.set_font("Arial", "", 12); pdf.cell(20, h, clean_pdf_text(data.get('idade', '')), 1)
            pdf.set_font("Arial", "B", 12); pdf.cell(30, h, "Ano:", 1); pdf.set_font("Arial", "", 12); pdf.cell(table_w - 150, h, clean_pdf_text(data.get('ano_esc', '')), 1, 1)
            pdf.set_font("Arial", "B", 12); pdf.cell(40, h, "Mãe:", 1); pdf.set_font("Arial", "", 12); pdf.cell(table_w - 40, h, clean_pdf_text(data.get('mae', '')), 1, 1)
            pdf.set_font("Arial", "B", 12); pdf.cell(40, h, "Pai:", 1); pdf.set_font("Arial", "", 12); pdf.cell(table_w - 40, h, clean_pdf_text(data.get('pai', '')), 1, 1)
            pdf.set_font("Arial", "B", 12); pdf.cell(40, h, "Telefone:", 1); pdf.set_font("Arial", "", 12); pdf.cell(table_w - 40, h, clean_pdf_text(data.get('tel', '')), 1, 1)
            
            pdf.ln(5); full_w = 277 
            pdf.set_font("Arial", "B", 12); pdf.cell(full_w, h, "Docentes Responsáveis", 1, 1, 'L', 1)
            docs = [("Polivalente:", data.get('prof_poli')), ("Arte:", data.get('prof_arte')), ("Ed. Física:", data.get('prof_ef')), ("Tecnologia:", data.get('prof_tec')), ("AEE:", data.get('prof_aee')), ("Gestor:", data.get('gestor')), ("Coordenação:", data.get('coord')), ("Revisões:", data.get('revisoes'))]
            for l, v in docs:
                pdf.set_font("Arial", "B", 12); pdf.cell(60, h, clean_pdf_text(l), 1); pdf.set_font("Arial", "", 12); pdf.cell(full_w-60, h, clean_pdf_text(v), 1, 1)

            # --- PÁGINA 2 (CONGELADA - SAÚDE) ---
            pdf.add_page(); pdf.section_title("2. INFORMAÇÕES DE SAÚDE", width=0); h = 10
            pdf.set_font("Arial", "B", 12); pdf.cell(100, h, clean_pdf_text("O estudante tem diagnóstico conclusivo:"), 1, 0, 'L')
            status_sim = "[ X ]" if data.get('diag_status') == "Sim" else "[   ]"
            status_nao = "[ X ]" if data.get('diag_status') == "Não" else "[   ]"
            pdf.set_font("Arial", "", 12); pdf.cell(0, h, f"  {status_sim} Sim      {status_nao} Não", 1, 1, 'L')
            pdf.set_font("Arial", "B", 12); pdf.cell(40, h, "Data do Laudo:", 1, 0, 'L')
            pdf.set_font("Arial", "", 12); pdf.cell(60, h, clean_pdf_text(str(data.get('laudo_data', ''))), 1, 0, 'L')
            pdf.set_font("Arial", "B", 12); pdf.cell(40, h, "Médico Respons.:", 1, 0, 'L')
            pdf.set_font("Arial", "", 12); pdf.cell(0, h, clean_pdf_text(data.get('laudo_medico', '---')), 1, 1, 'L')

            pdf.ln(2); diag_list = data.get('diag_tipo', []); diag_ativos = []
            if "Deficiência" in diag_list and data.get('defic_txt'): diag_ativos.append(("Deficiência:", data.get('defic_txt')))
            if "Transtorno do Neurodesenvolvimento" in diag_list and data.get('neuro_txt'): diag_ativos.append(("Transtorno Neuro:", data.get('neuro_txt')))
            if "Transtornos Aprendizagem" in diag_list and data.get('aprend_txt'): diag_ativos.append(("Transt. Aprendizagem:", data.get('aprend_txt')))
            if "AH/SD" in diag_list: diag_ativos.append(("Destaque:", "Altas Habilidades / Superdotação"))
            if "Outros" in diag_list: diag_ativos.append(("Outros Diagnósticos:", "Conforme prontuário"))

            if diag_ativos:
                for l_diag, t_diag in diag_ativos:
                    pdf.set_font("Arial", "B", 11); pdf.cell(60, h, clean_pdf_text(l_diag), "LTB", 0, 'L')
                    pdf.set_font("Arial", "", 11); pdf.cell(0, h, clean_pdf_text(t_diag), "RTB", 1, 'L')
            else: pdf.set_font("Arial", "I", 11); pdf.cell(0, h, "Nenhum diagnóstico selecionado.", 1, 1, 'C')

            pdf.ln(6); pdf.set_font("Arial", "B", 12); pdf.set_fill_color(245, 245, 245); pdf.cell(277, 10, "Terapias que realiza", 1, 1, 'C', 1)
            pdf.set_font("Arial", "B", 11); pdf.cell(80, 10, "Especialidades", 1, 0, 'L', 1); pdf.cell(0, 10, clean_pdf_text("Frequência e Horário de Atendimento"), 1, 1, 'L', 1)
            for esp in ["Psicologia", "Fonoaudiologia", "Terapia Ocupacional", "Psicopedagogia", "Fisioterapia", "Outros"]:
                info = data.get('terapias', {}).get(esp, {'realiza': False, 'dias': [], 'horario': ''})
                chk = "[ X ]" if info['realiza'] else "[   ]"
                label_esp = f"  {chk} {esp}"
                if esp == "Outros" and info.get('nome_custom'): label_esp = f"  {chk} Outros ({info['nome_custom']})"
                pdf.set_font("Arial", "B", 11); pdf.cell(80, 12, clean_pdf_text(label_esp), 1, 0, 'L')
                x_start = pdf.get_x(); y_start = pdf.get_y(); pdf.set_font("Arial", "", 10)
                if info['realiza']:
                    pdf.set_xy(x_start + 5, y_start + 2); pdf.cell(0, 4, clean_pdf_text("Dias: " + ", ".join(info['dias'])), 0, 1)
                    pdf.set_x(x_start + 5); pdf.set_font("Arial", "B", 10); pdf.cell(16, 4, "Horário:", 0); pdf.set_font("Arial", "", 10); pdf.cell(0, 4, clean_pdf_text(info['horario']), 0, 1)
                else:
                    pdf.set_xy(x_start + 5, y_start + 4); pdf.set_font("Arial", "I", 10); pdf.set_text_color(150, 0, 0)
                    pdf.cell(0, 4, "NÃO REALIZA ATENDIMENTO NESTA ESPECIALIDADE.", 0, 1); pdf.set_text_color(0, 0, 0)
                pdf.set_xy(x_start, y_start); pdf.cell(0, 12, "", 1, 1)

            pdf.ln(5); pdf.set_font("Arial", "B", 12); pdf.cell(0, 10, "Medicação e Horários:", "LTR", 1, 'L', 1)
            pdf.set_font("Arial", "", 12); pdf.multi_cell(0, 8, clean_pdf_text(f"{data.get('med_nome', 'Não utiliza')}\nHorários: {data.get('med_hor', 'N/A')}"), "LRB")
            pdf.set_font("Arial", "B", 12); pdf.cell(60, 10, "Médico Responsável:", 1); pdf.set_font("Arial", "", 12); pdf.cell(0, 10, clean_pdf_text(data.get('med_doc', 'N/A')), 1, 1)
            pdf.set_font("Arial", "B", 12); pdf.cell(0, 8, "Objetivo da medicação:", "LTR", 1, 'L', 1); pdf.set_font("Arial", "", 12); pdf.multi_cell(0, 8, clean_pdf_text(data.get('med_obj', 'Não informado.')), "LRB")
            pdf.ln(3); pdf.set_font("Arial", "B", 12); pdf.cell(0, 8, clean_pdf_text("Outras informações de saúde consideradas relevantes:"), "LTR", 1, 'L', 1)
            pdf.set_font("Arial", "", 12); pdf.multi_cell(0, 8, clean_pdf_text(data.get('saude_extra', 'Nenhuma informação adicional.')), "LRB")

            # --- 3. PROTOCOLO DE CONDUTA (CONGELADO - CONTINUADO) ---
            pdf.ln(5); pdf.section_title("3. PROTOCOLO DE CONDUTA", width=0); h = 8
            pdf.set_font("Arial", "B", 11); pdf.set_fill_color(245, 245, 245); pdf.cell(0, 8, "COMUNICAÇÃO, LOCOMOÇÃO E HIGIENE", 1, 1, 'C', 1)
            rows_cond = [
                ("Como o estudante se comunica?", f"{data.get('com_tipo')} {data.get('com_alt_espec')}"),
                ("Capaz de expressar necessidades, desejos e interesses?", f"{data.get('com_necessidades')} - {data.get('com_necessidades_espec')}"),
                ("Atende quando é chamado?", f"{data.get('com_chamado')} - {data.get('com_chamado_espec')}"),
                ("Responde a comandos simples?", f"{data.get('com_comandos')} - {data.get('com_comandos_espec')}"),
                ("Possui mobilidade reduzida?", f"{data.get('loc_reduzida')} - {data.get('loc_reduzida_espec')}"),
                ("Locomove-se pela casa e ambientes?", f"{data.get('loc_ambiente')} ({data.get('loc_ambiente_ajuda')}) - {data.get('loc_ambiente_espec')}"),
                ("Utiliza o banheiro?", f"{data.get('hig_banheiro')} ({data.get('hig_banheiro_ajuda')}) - {data.get('hig_banheiro_espec')}"),
                ("Escova os dentes?", f"{data.get('hig_dentes')} ({data.get('hig_dentes_ajuda')}) - {data.get('hig_dentes_espec')}")
            ]
            for l, v in rows_cond:
                pdf.set_font("Arial", "B", 10); pdf.cell(95, h, clean_pdf_text(l), 1, 0, 'L'); pdf.set_font("Arial", "", 10); pdf.cell(0, h, clean_pdf_text(v), 1, 1, 'L')
            
            pdf.ln(4); pdf.set_font("Arial", "B", 11); pdf.set_fill_color(245, 245, 245); pdf.cell(0, 8, "COMPORTAMENTO E INTERESSES", 1, 1, 'C', 1)
            verbatims = [
                ("Quais são os interesses do estudante?", data.get('beh_interesses')),
                ("Quais objetos que gosta? Tem um objeto de apego?", data.get('beh_objetos_gosta')),
                ("Quais objetos o estudante não gosta e/ou causam aversão?", data.get('beh_objetos_odeia')),
                ("Gosta de toque, abraço, beijo?", data.get('beh_toque')),
                ("O que o deixa calmo e relaxado?", data.get('beh_calmo')),
                ("Quais atividades são mais prazerosas?", data.get('beh_atividades')),
                ("Quais são os gatilhos já identificados para episódios de crise?", data.get('beh_gatilhos')),
                ("Quando o estudante está em crise como normalmente se regula?", data.get('beh_crise_regula')),
                ("O estudante costuma apresentar comportamentos desafiadores? Manejo?", data.get('beh_desafios')),
                ("Tem restrições alimentares / Seletividade?", f"{data.get('beh_restricoes')} - {data.get('beh_restricoes_espec')}"),
                ("Tem autonomia para tomar água e se alimentar?", f"{data.get('beh_autonomia_agua')} - {data.get('beh_autonomia_agua_espec')}"),
                ("Outras informações julgadas pertinentes:", data.get('beh_pertinentes'))
            ]
            for l, v in verbatims:
                pdf.set_font("Arial", "B", 10); pdf.cell(0, 7, clean_pdf_text(l), "LTR", 1, 'L', 1)
                pdf.set_font("Arial", "", 10); pdf.multi_cell(0, 6, clean_pdf_text(v if v else "---"), "LRB")

            # --- 4. DESENVOLVIMENTO ESCOLAR (NOVA SEÇÃO) ---
            pdf.ln(5); pdf.section_title("4. DESENVOLVIMENTO ESCOLAR", width=0); h = 8
            dev_rows = [
                ("Permanece em sala e aula?", f"{data.get('dev_permanece')} - {data.get('dev_permanece_espec')}"),
                ("Está integrado ao ambiente escolar?", f"{data.get('dev_integrado')} - {data.get('dev_integrado_espec')}"),
                ("Locomove-se pela escola?", f"{data.get('dev_loc_escola')} - {data.get('dev_loc_escola_espec')}"),
                ("Realiza tarefas escolares?", f"{data.get('dev_tarefas')} - {data.get('dev_tarefas_espec')}"),
                ("Tem amigos?", f"{data.get('dev_amigos')} - {data.get('dev_amigos_espec')}"),
                ("Tem um colega predileto?", f"{data.get('dev_colega_pref')}"),
                ("Participa das atividades e interage em diferentes espaços?", f"{data.get('dev_participa')} - {data.get('dev_participa_espec')}")
            ]
            for l, v in dev_rows:
                pdf.set_font("Arial", "B", 10); pdf.cell(100, h, clean_pdf_text(l), 1, 0, 'L'); pdf.set_font("Arial", "", 10); pdf.cell(0, h, clean_pdf_text(v), 1, 1, 'L')
            
            pdf.ln(2); pdf.set_font("Arial", "B", 10); pdf.cell(0, 7, clean_pdf_text("Envolvimento afetivo e social da turma com o estudante:"), "LTR", 1, 'L', 1)
            pdf.set_font("Arial", "", 10); pdf.multi_cell(0, 6, clean_pdf_text(data.get('dev_afetivo', '---')), "LRB")

# --- 5. AVALIAÇÃO ACADÊMICA (PDF ADAPTADO) ---
            pdf.ln(5)
            # Verifica espaço
            if pdf.get_y() > 220: pdf.add_page()

            pdf.section_title("5. AVALIAÇÃO ACADÊMICA DO ESTUDANTE", width=0)
            pdf.ln(2)
            
            areas_aval = []
            
            if pei_level == "Fundamental":
                areas_aval = [
                    ("LÍNGUA PORTUGUESA", data.get('aval_port')),
                    ("MATEMÁTICA", data.get('aval_mat')),
                    ("CONHECIMENTOS GERAIS", data.get('aval_con_gerais')),
                    ("ARTE - Artes Visuais", data.get('aval_arte_visuais')),
                    ("ARTE - Música", data.get('aval_arte_musica')),
                    ("ARTE - Teatro", data.get('aval_arte_teatro')),
                    ("ARTE - Dança", data.get('aval_arte_danca')),
                    ("EDUCAÇÃO FÍSICA - Habilidades Motoras", data.get('aval_ef_motoras')),
                    ("EDUCAÇÃO FÍSICA - Conhecimento Corporal", data.get('aval_ef_corp_conhec')),
                    ("EDUCAÇÃO FÍSICA - Exp. Corporais e Expressividade", data.get('aval_ef_exp')),
                    ("LINGUAGENS E TECNOLOGIA", data.get('aval_ling_tec'))
                ]
            else: # Infantil
                areas_aval = [
                    ("LINGUAGEM VERBAL", data.get('aval_ling_verbal')),
                    ("LINGUAGEM MATEMÁTICA", data.get('aval_ling_mat')),
                    ("INDÍVIDUO E SOCIEDADE", data.get('aval_ind_soc')),
                    ("ARTE - Artes Visuais", data.get('aval_arte_visuais')),
                    ("ARTE - Música", data.get('aval_arte_musica')),
                    ("ARTE - Teatro", data.get('aval_arte_teatro')),
                    ("EDUCAÇÃO FÍSICA - Jogos e Brincadeiras", data.get('aval_ef_jogos')),
                    ("EDUCAÇÃO FÍSICA - Ritmo e Expressividade", data.get('aval_ef_ritmo')),
                    ("EDUCAÇÃO FÍSICA - Conhecimento Corporal", data.get('aval_ef_corp')),
                    ("LINGUAGEM E TECNOLOGIAS", data.get('aval_ling_tec'))
                ]
            
            for titulo, texto in areas_aval:
                # Verifica quebra
                if pdf.get_y() > 230: pdf.add_page()
                
                pdf.set_font("Arial", "B", 10); pdf.set_fill_color(240, 240, 240)
                pdf.cell(0, 7, clean_pdf_text(titulo), "LTR", 1, 'L', 1)
                pdf.set_font("Arial", "", 10)
                pdf.multi_cell(0, 6, clean_pdf_text(texto if texto else "---"), "LRB")
                pdf.ln(2)

            # --- 6. METAS (PDF - IGUAL PARA AMBOS) ---
            pdf.ln(5)
            if pdf.get_y() > 230: pdf.add_page()
            
            pdf.section_title("6. METAS ESPECÍFICAS PARA O ANO EM CURSO", width=0)
            pdf.ln(2)
            
            def print_meta_row(titulo, meta, estrategia):
                if pdf.get_y() > 220: pdf.add_page()
                pdf.set_font("Arial", "B", 11); pdf.set_fill_color(230, 230, 230)
                pdf.cell(0, 8, clean_pdf_text(titulo), 1, 1, 'L', 1)
                pdf.set_font("Arial", "B", 10); pdf.cell(0, 6, "Metas / Habilidades:", "LTR", 1)
                pdf.set_font("Arial", "", 10); pdf.multi_cell(0, 5, clean_pdf_text(meta if meta else "---"), "LRB")
                pdf.set_font("Arial", "B", 10); pdf.cell(0, 6, clean_pdf_text("Estratégias:"), "LTR", 1)
                pdf.set_font("Arial", "", 10); pdf.multi_cell(0, 5, clean_pdf_text(estrategia if estrategia else "---"), "LRB")
                pdf.ln(2)

            print_meta_row("Habilidades Sociais", data.get('meta_social_obj'), data.get('meta_social_est'))
            print_meta_row("Habilidades de Autocuidado e Vida Prática", data.get('meta_auto_obj'), data.get('meta_auto_est'))
            print_meta_row("Habilidades Acadêmicas", data.get('meta_acad_obj'), data.get('meta_acad_est'))

            # --- 7. FLEXIBILIZAÇÃO (PDF ADAPTADO) ---
            pdf.ln(5)
            if pdf.get_y() > 230: pdf.add_page()
            
            pdf.section_title("7. FLEXIBILIZAÇÃO CURRICULAR", width=0)
            pdf.ln(4)
            
            pdf.set_font("Arial", "B", 10)
            pdf.cell(0, 6, clean_pdf_text("7.1 DISCIPLINAS QUE NECESSITAM DE ADAPTAÇÃO"), 0, 1)
            pdf.ln(2)

            pdf.set_fill_color(240, 240, 240); pdf.set_font("Arial", "B", 9)
            pdf.cell(90, 8, "DISCIPLINA", 1, 0, 'C', 1)
            pdf.cell(90, 8, clean_pdf_text("CONTEÚDO"), 1, 0, 'C', 1)
            pdf.cell(0, 8, "METODOLOGIA", 1, 1, 'C', 1)

            # LISTA DINÂMICA PARA O PDF
            if pei_level == "Fundamental":
                disciplinas_flex = ["Língua Portuguesa", "Matemática", "História", "Geografia", "Ciências", "Arte", "Educação Física", "Linguagens e Tecnologia"]
            else:
                disciplinas_flex = ["Linguagem Verbal", "Linguagem Matemática", "Indivíduo e Sociedade", "Arte", "Educação Física", "Linguagens e Tecnologia"]
            
            pdf.set_font("Arial", "", 10)
            for disc in disciplinas_flex:
                vals = data.get('flex_matrix', {}).get(disc, {'conteudo': False, 'metodologia': False})
                chk_c_sim = "[X] Sim  [  ] Não" if vals['conteudo'] else "[  ] Sim  [X] Não"
                chk_m_sim = "[X] Sim  [  ] Não" if vals['metodologia'] else "[  ] Sim  [X] Não"
                pdf.cell(90, 8, clean_pdf_text(f" {disc}"), 1, 0, 'L')
                pdf.cell(90, 8, chk_c_sim, 1, 0, 'C')
                pdf.cell(0, 8, chk_m_sim, 1, 1, 'C')

            # --- 7.2 PLANO DE ENSINO (TRIMESTRES) ---
            trimestres = ["1º Trimestre", "2º Trimestre", "3º Trimestre"]
            
            for tri in trimestres:
                dados_tri = data.get('plano_ensino_tri', {}).get(tri, {})
                has_content = False
                if dados_tri.get('obs', '').strip(): has_content = True
                for disc in disciplinas_flex:
                    d_dados = dados_tri.get(disc, {'obj': '', 'cont': '', 'met': ''})
                    if d_dados['obj'].strip() or d_dados['cont'].strip() or d_dados['met'].strip():
                        has_content = True; break
                
                if has_content:
                    pdf.ln(8)
                    if pdf.get_y() > 230: pdf.add_page()
                    pdf.set_font("Arial", "B", 12)
                    pdf.cell(0, 8, clean_pdf_text(f"7.2 PLANO DE ENSINO - {tri.upper()}"), 0, 1, 'L')
                    pdf.ln(2)

                    for disc in disciplinas_flex:
                        plan = dados_tri.get(disc, {'obj': '', 'cont': '', 'met': ''})
                        
                        # Se vazio, pula no PDF? Vamos manter para o professor ver que existe a disciplina.
                        # Ou se preferir ocultar disciplinas vazias, descomente:
                        # if not (plan['obj'] or plan['cont'] or plan['met']): continue

                        if pdf.get_y() > 220: pdf.add_page()
                        
                        pdf.set_font("Arial", "B", 10); pdf.set_fill_color(230, 230, 230)
                        pdf.cell(0, 7, clean_pdf_text(disc), 1, 1, 'L', 1)
                        
                        pdf.set_font("Arial", "B", 9); pdf.set_fill_color(250, 250, 250)
                        pdf.cell(0, 6, "Objetivos:", "LTR", 1, 'L', 1); pdf.set_font("Arial", "", 9)
                        pdf.multi_cell(0, 5, clean_pdf_text(plan['obj'] if plan['obj'] else "---"), "LRB")
                        
                        pdf.set_font("Arial", "B", 9)
                        pdf.cell(0, 6, clean_pdf_text("Conteúdos Específicos:"), "LTR", 1, 'L', 1); pdf.set_font("Arial", "", 9)
                        pdf.multi_cell(0, 5, clean_pdf_text(plan['cont'] if plan['cont'] else "---"), "LRB")
                        
                        pdf.set_font("Arial", "B", 9)
                        pdf.cell(0, 6, "Metodologia:", "LTR", 1, 'L', 1); pdf.set_font("Arial", "", 9)
                        pdf.multi_cell(0, 5, clean_pdf_text(plan['met'] if plan['met'] else "---"), "LRB")
                        pdf.ln(2)

                    if dados_tri.get('obs'):
                        if pdf.get_y() > 240: pdf.add_page()
                        pdf.ln(2)
                        pdf.set_font("Arial", "B", 10)
                        pdf.cell(0, 6, clean_pdf_text(f"Observações do {tri}:"), "LTR", 1, 'L')
                        pdf.set_font("Arial", "", 10)
                        pdf.multi_cell(0, 6, clean_pdf_text(dados_tri.get('obs')), "LRB")

            # --- OBSERVAÇÕES FINAIS ---
            if data.get('plano_obs_geral'):
                pdf.ln(5)
                if pdf.get_y() > 230: pdf.add_page()
                pdf.set_font("Arial", "B", 10)
                pdf.cell(0, 6, clean_pdf_text("Considerações e/ou recomendações finais:"), "LTR", 1, 'L')
                pdf.set_font("Arial", "", 10)
                pdf.multi_cell(0, 6, clean_pdf_text(data.get('plano_obs_geral')), "LRB")

            # --- ASSINATURAS (MANTIDO DO ANTERIOR - SERVE PARA AMBOS) ---
            pdf.ln(15)
            if pdf.get_y() > 230: pdf.add_page(); pdf.ln(15)
            pdf.set_font("Arial", "", 8)
            
            def draw_signature(x_pos, y_pos, nome, cargo):
                pdf.line(x_pos, y_pos, x_pos + 70, y_pos)
                pdf.set_xy(x_pos, y_pos + 2)
                pdf.cell(70, 4, clean_pdf_text(nome if nome else "____________________"), 0, 2, 'C')
                pdf.set_font("Arial", "B", 7)
                pdf.cell(70, 3, clean_pdf_text(cargo), 0, 0, 'C')
                pdf.set_font("Arial", "", 8)

            y = pdf.get_y()
            draw_signature(15, y, data.get('prof_poli', ''), "Prof. Polivalente / Regente")
            draw_signature(113, y, data.get('prof_arte', ''), "Prof. Arte")
            draw_signature(211, y, data.get('prof_ef', ''), "Prof. Ed. Física")
            
            pdf.ln(18)
            y = pdf.get_y()
            draw_signature(65, y, data.get('prof_aee', ''), "Prof. Ed. Especial (AEE)")
            draw_signature(162, y, data.get('prof_tec', ''), "Prof. Linguagens e Tec.")
            
            pdf.ln(18)
            y = pdf.get_y()
            draw_signature(65, y, data.get('coord', ''), "Coordenador Pedagógico")
            draw_signature(162, y, data.get('gestor', ''), "Gestor Escolar")



            st.session_state.pdf_bytes = get_pdf_bytes(pdf)
            st.rerun()

        if 'pdf_bytes' in st.session_state:
            st.download_button("📥 BAIXAR PEI COMPLETO", st.session_state.pdf_bytes, f"PEI_{data.get('nome','aluno')}.pdf", "application/pdf", type="primary")

# ==============================================================================
# ESTUDO DE CASO
# ==============================================================================
# ==============================================================================
# ESTUDO DE CASO (NOVO MÓDULO COMPLETO)
# ==============================================================================
else:
    st.markdown("""<div class="header-box"><div class="header-title">Estudo de Caso</div></div>""", unsafe_allow_html=True)
    
    # Inicializa dados se vazio
    if 'data_case' not in st.session_state: 
        st.session_state.data_case = {
            'irmaos': [{'nome': '', 'idade': '', 'esc': ''} for _ in range(4)], 
            'checklist': {},
            'clinicas': []
        }
    
    data = st.session_state.data_case
    
    tabs = st.tabs(["1. Identificação", "2. Família", "3. Histórico", "4. Saúde", "5. Comportamento", "6. Gerar PDF"])

    # --- ABA 1: IDENTIFICAÇÃO ---
    with tabs[0]:
        st.subheader("1.1 Dados Gerais do Estudante")
        data['nome'] = st.text_input("Nome Completo", value=data.get('nome', ''))
        
        c1, c2, c3 = st.columns([1, 1, 2])
        data['ano_esc'] = c1.text_input("Ano Escolaridade", value=data.get('ano_esc', ''))
        data['periodo'] = c2.selectbox("Período", ["Manhã", "Tarde", "Integral"], index=0 if not data.get('periodo') else ["Manhã", "Tarde", "Integral"].index(data.get('periodo')))
        data['unidade'] = c3.text_input("Unidade Escolar", value=data.get('unidade', ''))

        c4, c5 = st.columns([1, 1])
        data['sexo'] = c4.radio("Sexo", ["Feminino", "Masculino"], horizontal=True, index=0 if data.get('sexo') == 'Feminino' else 1)
        d_nasc = data.get('d_nasc')
        if isinstance(d_nasc, str):
            try: d_nasc = datetime.strptime(d_nasc, '%Y-%m-%d').date()
            except: d_nasc = date.today()
        data['d_nasc'] = c5.date_input("Data de Nascimento", value=d_nasc if d_nasc else date.today())

        data['endereco'] = st.text_input("Endereço", value=data.get('endereco', ''))
        c6, c7, c8 = st.columns([2, 2, 2])
        data['bairro'] = c6.text_input("Bairro", value=data.get('bairro', ''))
        data['cidade'] = c7.text_input("Cidade", value=data.get('cidade', 'Limeira'))
        data['telefones'] = c8.text_input("Telefones", value=data.get('telefones', ''))

    # --- ABA 2: DADOS FAMILIARES ---
    with tabs[1]:
        st.subheader("1.1.2 Dados Familiares")
        
        st.markdown("**Pai**")
        c_p1, c_p2, c_p3, c_p4 = st.columns([3, 2, 2, 2])
        data['pai_nome'] = c_p1.text_input("Nome do Pai", value=data.get('pai_nome', ''))
        data['pai_prof'] = c_p2.text_input("Profissão Pai", value=data.get('pai_prof', ''))
        data['pai_esc'] = c_p3.text_input("Escolaridade Pai", value=data.get('pai_esc', ''))
        data['pai_dn'] = c_p4.text_input("D.N. Pai", value=data.get('pai_dn', '')) # Texto livre para simplificar ou date_input

        st.markdown("**Mãe**")
        c_m1, c_m2, c_m3, c_m4 = st.columns([3, 2, 2, 2])
        data['mae_nome'] = c_m1.text_input("Nome da Mãe", value=data.get('mae_nome', ''))
        data['mae_prof'] = c_m2.text_input("Profissão Mãe", value=data.get('mae_prof', ''))
        data['mae_esc'] = c_m3.text_input("Escolaridade Mãe", value=data.get('mae_esc', ''))
        data['mae_dn'] = c_m4.text_input("D.N. Mãe", value=data.get('mae_dn', ''))

        st.divider()
        st.markdown("**Irmãos**")
        if 'irmaos' not in data: data['irmaos'] = [{'nome': '', 'idade': '', 'esc': ''} for _ in range(4)]
        
        for i in range(4):
            c_i1, c_i2, c_i3 = st.columns([3, 1, 2])
            data['irmaos'][i]['nome'] = c_i1.text_input(f"Nome Irmão {i+1}", value=data['irmaos'][i]['nome'])
            data['irmaos'][i]['idade'] = c_i2.text_input(f"Idade {i+1}", value=data['irmaos'][i]['idade'])
            data['irmaos'][i]['esc'] = c_i3.text_input(f"Escolaridade {i+1}", value=data['irmaos'][i]['esc'])

        data['outros_familia'] = st.text_area("Outros (Moradores da casa):", value=data.get('outros_familia', ''))
        data['quem_mora'] = st.text_input("Com quem mora?", value=data.get('quem_mora', ''))
        
        c_conv1, c_conv2 = st.columns([1, 3])
        data['convenio'] = c_conv1.radio("Possui convênio?", ["Sim", "Não"], horizontal=True, index=1 if data.get('convenio') == "Não" else 0)
        data['convenio_qual'] = c_conv2.text_input("Qual convênio?", value=data.get('convenio_qual', ''))
        
        c_soc1, c_soc2 = st.columns([1, 3])
        data['social'] = c_soc1.radio("Recebe benefício social?", ["Sim", "Não"], horizontal=True, index=1 if data.get('social') == "Não" else 0)
        data['social_qual'] = c_soc2.text_input("Qual benefício?", value=data.get('social_qual', ''))

    # --- ABA 3: HISTÓRICO ESCOLAR E GESTAÇÃO ---
    with tabs[2]:
        st.subheader("1.1.3 História Escolar")
        data['hist_idade_entrou'] = st.text_input("Idade que entrou na escola:", value=data.get('hist_idade_entrou', ''))
        data['hist_outra_escola'] = st.text_input("Já estudou em outra escola? Quais?", value=data.get('hist_outra_escola', ''))
        data['hist_motivo_transf'] = st.text_input("Motivo da transferência:", value=data.get('hist_motivo_transf', ''))
        data['hist_obs'] = st.text_area("Outras observações escolares:", value=data.get('hist_obs', ''))

        st.divider()
        st.subheader("1.2 Informações sobre Gestação, Parto e Desenvolvimento")
        
        c_g1, c_g2 = st.columns(2)
        data['gest_parentesco'] = c_g1.radio("Parentesco entre pais?", ["Sim", "Não"], horizontal=True, index=1 if data.get('gest_parentesco') == "Não" else 0)
        data['gest_doenca'] = c_g2.text_input("Doença/trauma na gestação? Quais?", value=data.get('gest_doenca', ''))
        
        c_g3, c_g4 = st.columns(2)
        data['gest_substancias'] = c_g3.radio("Uso de álcool/fumo/drogas?", ["Sim", "Não"], horizontal=True, index=1 if data.get('gest_substancias') == "Não" else 0)
        data['gest_medicamentos'] = c_g4.text_input("Uso de medicamentos? Quais?", value=data.get('gest_medicamentos', ''))

        data['parto_ocorrencia'] = st.text_input("Ocorrência no parto? Quais?", value=data.get('parto_ocorrencia', ''))
        data['parto_incubadora'] = st.text_input("Incubadora? Motivo?", value=data.get('parto_incubadora', ''))
        
        c_p1, c_p2 = st.columns(2)
        data['parto_prematuro'] = c_p1.radio("Prematuro?", ["Sim", "Não"], horizontal=True, index=1 if data.get('parto_prematuro') == "Não" else 0)
        data['parto_uti'] = c_p2.radio("Ficou em UTI?", ["Sim", "Não"], horizontal=True, index=1 if data.get('parto_uti') == "Não" else 0)

        c_d1, c_d2, c_d3 = st.columns(3)
        data['dev_tempo_gest'] = c_d1.text_input("Tempo Gestação", value=data.get('dev_tempo_gest', ''))
        data['dev_peso'] = c_d2.text_input("Peso", value=data.get('dev_peso', ''))
        data['dev_normal_1ano'] = c_d3.radio("Desenv. normal 1º ano?", ["Sim", "Não"], horizontal=True, index=0 if data.get('dev_normal_1ano') == "Sim" else 1)
        
        data['dev_atraso'] = st.text_input("Atraso importante? Quais?", value=data.get('dev_atraso', ''))
        c_m1, c_m2 = st.columns(2)
        data['dev_idade_andar'] = c_m1.text_input("Idade começou a andar?", value=data.get('dev_idade_andar', ''))
        data['dev_idade_falar'] = c_m2.text_input("Idade começou a falar?", value=data.get('dev_idade_falar', ''))

        st.markdown("---")
        data['diag_possui'] = st.text_input("Possui diagnóstico? Qual?", value=data.get('diag_possui', ''))
        data['diag_reacao'] = st.text_input("Reação da família:", value=data.get('diag_reacao', ''))
        c_dx1, c_dx2 = st.columns(2)
        data['diag_data'] = c_dx1.text_input("Data do diagnóstico:", value=data.get('diag_data', ''))
        data['diag_origem'] = c_dx2.text_input("Origem da informação:", value=data.get('diag_origem', ''))
        
        c_fam1, c_fam2 = st.columns(2)
        data['fam_deficiencia'] = c_fam1.text_input("Pessoa com deficiência na família? Parentesco?", value=data.get('fam_deficiencia', ''))
        data['fam_altas_hab'] = c_fam2.radio("Pessoa com AH/SD na família?", ["Sim", "Não"], horizontal=True, index=1 if data.get('fam_altas_hab') == "Não" else 0)

    # --- ABA 4: SAÚDE (CONTINUAÇÃO) ---
    with tabs[3]:
        st.subheader("1.3 Informações sobre Saúde")
        data['saude_prob'] = st.text_input("Problema de saúde? Quais?", value=data.get('saude_prob', ''))
        data['saude_internacao'] = st.text_input("Internação? Motivos?", value=data.get('saude_internacao', ''))
        data['saude_restricao'] = st.text_input("Restrição/Seletividade alimentar? Quais?", value=data.get('saude_restricao', ''))
        
        st.markdown("**Medicamentos Controlados**")
        data['med_uso'] = st.radio("Faz uso?", ["Sim", "Não"], horizontal=True, index=1 if data.get('med_uso') == "Não" else 0)
        data['med_quais'] = st.text_input("Quais medicamentos?", value=data.get('med_quais', ''))
        c_med1, c_med2, c_med3 = st.columns(3)
        data['med_hor'] = c_med1.text_input("Horário", value=data.get('med_hor', ''))
        data['med_dos'] = c_med2.text_input("Dosagem", value=data.get('med_dos', ''))
        data['med_ini'] = c_med3.text_input("Início", value=data.get('med_ini', ''))

        st.divider()
        st.markdown("**Outros aspectos**")
        c_esf1, c_esf2 = st.columns(2)
        data['esf_urina'] = c_esf1.checkbox("Controla Urina", value=data.get('esf_urina', False))
        data['esf_fezes'] = c_esf2.checkbox("Controla Fezes", value=data.get('esf_fezes', False))
        data['esf_idade'] = st.text_input("Com qual idade controlou?", value=data.get('esf_idade', ''))
        data['sono'] = st.text_input("Dorme bem? Obs:", value=data.get('sono', ''))
        data['medico_ultimo'] = st.text_input("Última visita ao médico:", value=data.get('medico_ultimo', ''))

        st.markdown("**Atendimento Clínico Extraescolar**")
        clinicas_opts = ["APAE", "ARIL", "CEMA", "Família Azul", "CAPS", "Amb. Saúde Mental", "João Fischer D.A.", "João Fischer D.V."]
        prof_opts = ["Fonoaudiólogo", "Terapeuta Ocupacional", "Psicólogo", "Psicopedagogo", "Fisioterapeuta"]
        
        if 'clinicas' not in data: data['clinicas'] = []
        
        # Multiselect para simplificar
        data['clinicas'] = st.multiselect("Selecione os atendimentos:", clinicas_opts + prof_opts, default=data.get('clinicas', []))
        data['clinicas_med_esp'] = st.text_input("Área médica (Especialidade):", value=data.get('clinicas_med_esp', ''))
        data['clinicas_nome'] = st.text_input("Nome da Clínica/Profissional:", value=data.get('clinicas_nome', ''))
        
        data['saude_obs_geral'] = st.text_area("Outras observações de saúde:", value=data.get('saude_obs_geral', ''))

    # --- ABA 5: COMPORTAMENTO E ENTREVISTA ---
   # --- ABA 5: COMPORTAMENTO E ENTREVISTA (CORRIGIDO) ---
    with tabs[4]:
        st.subheader("1.4 Compreensão da Família (Checklist)")
        
        checklist_items = [
            "Relata fatos do dia a dia? Apresentando boa memória?",
            "É organizado com seus pertences?",
            "Aceita regras de forma tranquila?",
            "Busca e aceita ajuda quando não sabe ou não consegue algo?",
            "Aceita alterações no ambiente?",
            "Tem algum medo?",
            "Tem alguma mania?",
            "Tem alguma área/assunto, brinquedo ou hiperfoco?",
            "Prefere brincar sozinho ou com outras crianças? Tem amigos?",
            "Qual a expectativa da família em relação à escolaridade da criança?"
        ]
        
        if 'checklist' not in data: data['checklist'] = {}
        
        # ADICIONAMOS 'i' (índice) PARA GARANTIR CHAVES ÚNICAS
        for i, item in enumerate(checklist_items):
            st.markdown(f"**{item}**")
            col_a, col_b = st.columns([1, 3])
            
            # Cria uma base para o nome do campo
            key_base = item[:10].replace(" ", "").replace("?", "")
            
            # Opção Sim/Não (Adicionamos _{i} na key para não dar erro de duplicidade)
            opt = data['checklist'].get(f"{key_base}_opt", "Não")
            data['checklist'][f"{key_base}_opt"] = col_a.radio(
                "Opção", 
                ["Sim", "Não"], 
                key=f"rad_{key_base}_{i}",  # <--- AQUI ESTAVA O ERRO, AGORA TEM O _{i}
                horizontal=True, 
                label_visibility="collapsed", 
                index=0 if opt == "Sim" else 1
            )
            
            # Observação (Também ajustamos a key aqui por segurança)
            data['checklist'][f"{key_base}_obs"] = col_b.text_input(
                "Observações:", 
                value=data['checklist'].get(f"{key_base}_obs", ""), 
                key=f"obs_{key_base}_{i}"
            )
            st.divider()

        st.subheader("Dados da Entrevista")
        c_e1, c_e2, c_e3 = st.columns(3)
        data['entrevista_prof'] = c_e1.text_input("Prof. Responsável", value=data.get('entrevista_prof', ''))
        data['entrevista_resp'] = c_e2.text_input("Responsável info", value=data.get('entrevista_resp', ''))
        
        d_ent = data.get('entrevista_data')
        if isinstance(d_ent, str): 
             try: d_ent = datetime.strptime(d_ent, '%Y-%m-%d').date()
             except: d_ent = date.today()
        data['entrevista_data'] = c_e3.date_input("Data", value=d_ent if d_ent else date.today())
        
        data['entrevista_extra'] = st.text_area("Outras informações relevantes:", value=data.get('entrevista_extra', ''))

# --- ABA 6: GERAR PDF (ESTUDO DE CASO - ESTILO PEI) ---
    with tabs[5]:
        if st.button("💾 SALVAR ESTUDO DE CASO", type="primary"): 
            save_student("CASO", data.get('nome', 'aluno'), data)


        
        if st.button("👁️ GERAR PDF"):
            # Cria PDF em Retrato ('P')
            pdf = OfficialPDF('P', 'mm', 'A4')
            pdf.add_page(); pdf.set_margins(15, 15, 15)
            
            # --- CABEÇALHO ---
            if os.path.exists("logo_prefeitura.png"): pdf.image("logo_prefeitura.png", 15, 10, 25)
            if os.path.exists("logo_escola.png"): pdf.image("logo_escola.png", 170, 6, 25)

            # Títulos Centralizados
            pdf.set_xy(0, 15); pdf.set_font("Arial", "B", 12)
            pdf.cell(210, 6, clean_pdf_text("PREFEITURA MUNICIPAL DE LIMEIRA"), 0, 1, 'C')
            pdf.cell(180, 6, clean_pdf_text("CEIEF RAFAEL AFFONSO LEITE"), 0, 1, 'C')
            pdf.ln(8)
            pdf.set_font("Arial", "B", 16); pdf.cell(0, 10, "ESTUDO DE CASO", 0, 1, 'C')
            pdf.ln(5)
            
            # --- 1.1 DADOS GERAIS ---
            pdf.section_title("1.1 DADOS GERAIS DO ESTUDANTE", width=0)
            pdf.ln(4)
            
            # 1.1.1 IDENTIFICAÇÃO
            pdf.set_fill_color(240, 240, 240)
            pdf.set_font("Arial", "B", 10); pdf.cell(0, 8, "1.1.1 - IDENTIFICAÇÃO", 1, 1, 'L', 1)
            
            pdf.set_font("Arial", "B", 10); pdf.cell(30, 8, "Nome:", 1, 0, 'L', 1)
            pdf.set_font("Arial", "", 10); pdf.cell(110, 8, clean_pdf_text(data.get('nome', '')), 1, 0)
            pdf.set_font("Arial", "B", 10); pdf.cell(15, 8, "D.N.:", 1, 0, 'C', 1)
            pdf.set_font("Arial", "", 10); pdf.cell(0, 8, clean_pdf_text(str(data.get('d_nasc', ''))), 1, 1, 'C')
            
            pdf.set_font("Arial", "B", 10); pdf.cell(30, 8, "Escolaridade:", 1, 0, 'L', 1)
            pdf.set_font("Arial", "", 10); pdf.cell(40, 8, clean_pdf_text(data.get('ano_esc', '')), 1, 0)
            pdf.set_font("Arial", "B", 10); pdf.cell(20, 8, clean_pdf_text("Período:"), 1, 0, 'C', 1)
            pdf.set_font("Arial", "", 10); pdf.cell(30, 8, clean_pdf_text(data.get('periodo', '')), 1, 0, 'C')
            pdf.set_font("Arial", "B", 10); pdf.cell(20, 8, "Unidade:", 1, 0, 'C', 1)
            pdf.set_font("Arial", "", 10); pdf.cell(0, 8, clean_pdf_text(data.get('unidade', '')), 1, 1)
            
            pdf.set_font("Arial", "B", 10); pdf.cell(30, 8, clean_pdf_text("Endereço:"), 1, 0, 'L', 1)
            pdf.set_font("Arial", "", 10); pdf.cell(0, 8, clean_pdf_text(data.get('endereco', '')), 1, 1)
            
            pdf.set_font("Arial", "B", 10); pdf.cell(20, 8, "Bairro:", 1, 0, 'L', 1)
            pdf.set_font("Arial", "", 10); pdf.cell(60, 8, clean_pdf_text(data.get('bairro', '')), 1, 0)
            pdf.set_font("Arial", "B", 10); pdf.cell(20, 8, "Cidade:", 1, 0, 'C', 1)
            pdf.set_font("Arial", "", 10); pdf.cell(40, 8, clean_pdf_text(data.get('cidade', '')), 1, 0)
            pdf.set_font("Arial", "B", 10); pdf.cell(20, 8, "Telefone:", 1, 0, 'C', 1)
            pdf.set_font("Arial", "", 10); pdf.cell(0, 8, clean_pdf_text(data.get('telefones', '')), 1, 1)
            
            # 1.1.2 DADOS FAMILIARES
            pdf.ln(4)
            pdf.set_font("Arial", "B", 10); pdf.cell(0, 8, "1.1.2 - DADOS FAMILIARES", 1, 1, 'L', 1)
            
            # Pai
            pdf.set_font("Arial", "B", 10); pdf.cell(20, 8, "Pai:", 1, 0, 'L', 1)
            pdf.set_font("Arial", "", 10); pdf.cell(80, 8, clean_pdf_text(data.get('pai_nome', '')), 1, 0)
            pdf.set_font("Arial", "B", 10); pdf.cell(25, 8, clean_pdf_text("Profissão:"), 1, 0, 'C', 1)
            pdf.set_font("Arial", "", 10); pdf.cell(0, 8, clean_pdf_text(data.get('pai_prof', '')), 1, 1)
            
            # Mãe
            pdf.set_font("Arial", "B", 10); pdf.cell(20, 8, clean_pdf_text("Mãe:"), 1, 0, 'L', 1)
            pdf.set_font("Arial", "", 10); pdf.cell(80, 8, clean_pdf_text(data.get('mae_nome', '')), 1, 0)
            pdf.set_font("Arial", "B", 10); pdf.cell(25, 8, clean_pdf_text("Profissão:"), 1, 0, 'C', 1)
            pdf.set_font("Arial", "", 10); pdf.cell(0, 8, clean_pdf_text(data.get('mae_prof', '')), 1, 1)
            
            # Irmãos
            pdf.ln(2)
            pdf.set_font("Arial", "B", 10); pdf.cell(0, 8, clean_pdf_text("Irmãos (Nome | Idade | Escolaridade)"), 1, 1, 'L', 1)
            pdf.set_font("Arial", "", 9)
            for i, irmao in enumerate(data.get('irmaos', [])):
                if irmao['nome']:
                    txt = f"{irmao['nome']}  |  {irmao['idade']}  |  {irmao['esc']}"
                    pdf.cell(0, 6, clean_pdf_text(txt), 1, 1)
            
            pdf.ln(2)
            pdf.set_font("Arial", "B", 10); pdf.cell(40, 8, "Com quem mora:", 1, 0, 'L', 1)
            pdf.set_font("Arial", "", 10); pdf.cell(0, 8, clean_pdf_text(data.get('quem_mora', '')), 1, 1)
            
            pdf.set_font("Arial", "B", 10); pdf.cell(40, 8, clean_pdf_text("Convênio Médico:"), 1, 0, 'L', 1)
            pdf.set_font("Arial", "", 10); pdf.cell(50, 8, clean_pdf_text(data.get('convenio')), 1, 0)
            pdf.set_font("Arial", "B", 10); pdf.cell(20, 8, clean_pdf_text("Qual:"), 1, 0, 'C', 1)
            pdf.set_font("Arial", "", 10); pdf.cell(0, 8, clean_pdf_text(data.get('convenio_qual')), 1, 1)
            
            pdf.set_font("Arial", "B", 10); pdf.cell(40, 8, clean_pdf_text("Benefício Social:"), 1, 0, 'L', 1)
            pdf.set_font("Arial", "", 10); pdf.cell(50, 8, clean_pdf_text(data.get('social')), 1, 0)
            pdf.set_font("Arial", "B", 10); pdf.cell(20, 8, clean_pdf_text("Qual:"), 1, 0, 'C', 1)
            pdf.set_font("Arial", "", 10); pdf.cell(0, 8, clean_pdf_text(data.get('social_qual')), 1, 1)

            # 1.1.3 HISTÓRIA ESCOLAR
            pdf.ln(4)
            pdf.set_font("Arial", "B", 10); pdf.cell(0, 8, clean_pdf_text("1.1.3 - HISTÓRIA ESCOLAR"), 1, 1, 'L', 1)
            
            pdf.set_font("Arial", "B", 10); pdf.cell(50, 8, "Idade entrou na escola:", 1, 0, 'L', 1)
            pdf.set_font("Arial", "", 10); pdf.cell(0, 8, clean_pdf_text(data.get('hist_idade_entrou')), 1, 1)
            
            pdf.set_font("Arial", "B", 10); pdf.cell(50, 8, "Outras escolas:", 1, 0, 'L', 1)
            pdf.set_font("Arial", "", 10); pdf.cell(0, 8, clean_pdf_text(data.get('hist_outra_escola')), 1, 1)
            
            pdf.set_font("Arial", "B", 10); pdf.cell(50, 8, clean_pdf_text("Motivo transferência:"), 1, 0, 'L', 1)
            pdf.set_font("Arial", "", 10); pdf.cell(0, 8, clean_pdf_text(data.get('hist_motivo_transf')), 1, 1)
            
            if data.get('hist_obs'):
                pdf.ln(2)
                pdf.set_font("Arial", "B", 10); pdf.cell(0, 6, "Observações Escolares:", 0, 1)
                pdf.set_font("Arial", "", 9); pdf.multi_cell(0, 5, clean_pdf_text(data.get('hist_obs')), 1)

            # --- 1.2 GESTAÇÃO, PARTO E DESENVOLVIMENTO ---
            pdf.add_page() # Nova página para não quebrar o bloco
            pdf.section_title("1.2 GESTAÇÃO, PARTO E DESENVOLVIMENTO", width=0)
            pdf.ln(4)
            
            # Função auxiliar para linhas de dados (Rótulo | Valor)
            def print_data_row(label, value):
                pdf.set_font("Arial", "B", 9); pdf.set_fill_color(240, 240, 240)
                pdf.cell(80, 7, clean_pdf_text(label), 1, 0, 'L', 1)
                pdf.set_font("Arial", "", 9); pdf.set_fill_color(255, 255, 255)
                pdf.cell(0, 7, clean_pdf_text(value), 1, 1, 'L')

            rows_gest = [
                ("Parentesco entre pais:", data.get('gest_parentesco')),
                ("Doença/Trauma na gestação:", data.get('gest_doenca')),
                ("Uso de substâncias (mãe):", data.get('gest_substancias')),
                ("Uso de medicamentos (mãe):", data.get('gest_medicamentos')),
                ("Ocorrência no parto:", data.get('parto_ocorrencia')),
                ("Necessitou de incubadora:", data.get('parto_incubadora')),
                ("Prematuro?", f"{data.get('parto_prematuro')}  |  UTI: {data.get('parto_uti')}"),
                ("Tempo de gestação / Peso:", f"{data.get('dev_tempo_gest')}  /  {data.get('dev_peso')}"),
                ("Desenvolvimento normal no 1º ano:", data.get('dev_normal_1ano')),
                ("Apresentou atraso importante?", data.get('dev_atraso')),
                ("Idade que andou / falou:", f"{data.get('dev_idade_andar')}  /  {data.get('dev_idade_falar')}"),
                ("Possui diagnóstico?", data.get('diag_possui')),
                ("Reação da família ao diagnóstico:", data.get('diag_reacao')),
                ("Data / Origem do diagnóstico:", f"{data.get('diag_data')}  |  {data.get('diag_origem')}"),
                ("Pessoa com deficiência na família:", data.get('fam_deficiencia')),
                ("Pessoa com AH/SD na família:", data.get('fam_altas_hab'))
            ]
            
            for label, value in rows_gest:
                print_data_row(label, value)

            # --- 1.3 INFORMAÇÕES SOBRE SAÚDE ---
            pdf.add_page()
            pdf.section_title("1.3 INFORMAÇÕES SOBRE SAÚDE", width=0)
            pdf.ln(4)
            
            saude_rows = [
                ("Problemas de saúde:", data.get('saude_prob')),
                ("Já necessitou de internação:", data.get('saude_internacao')),
                ("Restrição/Seletividade alimentar:", data.get('saude_restricao')),
                ("Uso de medicamentos controlados:", f"{data.get('med_uso')} - Quais: {data.get('med_quais')}"),
                ("Horário / Dosagem / Início:", f"{data.get('med_hor')}  |  {data.get('med_dos')}  |  {data.get('med_ini')}"),
                ("Qualidade do sono:", data.get('sono')),
                ("Última visita ao médico:", data.get('medico_ultimo'))
            ]
            for label, value in saude_rows:
                print_data_row(label, value)
            
            # Controle de Esfíncter
            esf = []
            if data.get('esf_urina'): esf.append("Urina")
            if data.get('esf_fezes'): esf.append("Fezes")
            print_data_row("Controle de Esfíncter:", f"{', '.join(esf) if esf else 'Não'}  (Idade: {data.get('esf_idade')})")
            
            # Clínicas
            pdf.ln(4)
            pdf.set_font("Arial", "B", 10); pdf.set_fill_color(240, 240, 240)
            pdf.cell(0, 8, "Atendimentos Clínicos Extraescolares", 1, 1, 'L', 1)
            
            clins = data.get('clinicas', [])
            print_data_row("Realiza atendimento em:", ", ".join(clins) if clins else "Não realiza")
            print_data_row("Especialidade médica:", data.get('clinicas_med_esp'))
            print_data_row("Nome da Clínica/Profissional:", data.get('clinicas_nome'))
            
            if data.get('saude_obs_geral'):
                pdf.ln(2)
                pdf.set_font("Arial", "B", 9); pdf.cell(0, 6, "Outras observações de saúde:", 0, 1)
                pdf.set_font("Arial", "", 9); pdf.multi_cell(0, 5, clean_pdf_text(data.get('saude_obs_geral')), 1)

            # --- 1.4 COMPREENSÃO DA FAMÍLIA (CHECKLIST) ---
            pdf.add_page()
            pdf.section_title("1.4 COMPREENSÃO DA FAMÍLIA (CHECKLIST)", width=0)
            pdf.ln(4)
            
            # Tabela
            pdf.set_fill_color(220, 220, 220); pdf.set_font("Arial", "B", 9)
            pdf.cell(110, 8, "PERGUNTA / ASPECTO OBSERVADO", 1, 0, 'C', 1)
            pdf.cell(25, 8, "SIM/NÃO", 1, 0, 'C', 1)
            pdf.cell(0, 8, clean_pdf_text("OBSERVAÇÕES DA FAMÍLIA"), 1, 1, 'C', 1)
            
            checklist_items = [
                "Relata fatos do dia a dia? Apresentando boa memória?",
                "É organizado com seus pertences?",
                "Aceita regras de forma tranquila?",
                "Busca e aceita ajuda quando não sabe/consegue?",
                "Aceita alterações no ambiente?",
                "Tem algum medo?",
                "Tem alguma mania?",
                "Tem algum hiperfoco ou interesse específico?",
                "Prefere brincar com outras crianças? Tem amigos?",
                "Expectativa da família quanto à escolaridade?"
            ]
            
            pdf.set_font("Arial", "", 9)
            for item in checklist_items:
                key_base = item[:10].replace(" ", "").replace("?", "")
                opt = data.get('checklist', {}).get(f"{key_base}_opt", "Não")
                obs = data.get('checklist', {}).get(f"{key_base}_obs", "")
                
                # Ajusta altura da célula baseada no tamanho da observação
                line_height = 6
                num_lines = pdf.get_string_width(obs) / 50  # Estimativa simples
                cell_height = max(line_height, (int(num_lines) + 1) * line_height)
                
                x_start = pdf.get_x(); y_start = pdf.get_y()
                
                # Pergunta (com quebra de linha se necessário)
                pdf.multi_cell(110, line_height, clean_pdf_text(item), 1, 'L')
                
                # Opção (Sim/Não)
                pdf.set_xy(x_start + 110, y_start)
                pdf.cell(25, cell_height, clean_pdf_text(opt), 1, 0, 'C')
                
                # Observação (Multi-cell)
                pdf.set_xy(x_start + 135, y_start)
                pdf.multi_cell(0, line_height, clean_pdf_text(obs), 1, 'L')
                
                # Garante que o cursor desça para a próxima linha da tabela corretamente
                pdf.set_xy(x_start, y_start + cell_height)

            # --- FINALIZAÇÃO ---
            pdf.ln(5)
            pdf.set_font("Arial", "B", 10); pdf.set_fill_color(240, 240, 240)
            pdf.cell(0, 8, clean_pdf_text("OUTRAS INFORMAÇÕES RELEVANTES"), 1, 1, 'L', 1)
            pdf.set_font("Arial", "", 9)
            pdf.multi_cell(0, 6, clean_pdf_text(data.get('entrevista_extra', '---')), 1)
            
            # --- ASSINATURAS ---
            pdf.ln(10)
            if pdf.get_y() > 240: pdf.add_page()
            
            pdf.set_fill_color(240, 240, 240); pdf.set_font("Arial", "B", 10)
            pdf.cell(0, 8, "DADOS DA ENTREVISTA", 1, 1, 'L', 1)
            
            print_data_row("Responsável pelas informações:", data.get('entrevista_resp'))
            print_data_row("Profissional Entrevistador:", data.get('entrevista_prof'))
            print_data_row("Data da Entrevista:", str(data.get('entrevista_data', '')))
            
            pdf.ln(25) # Espaço para assinar
            
            y = pdf.get_y()
            pdf.line(20, y, 90, y); pdf.line(110, y, 190, y)
            pdf.set_font("Arial", "", 9)
            pdf.set_xy(20, y+2); pdf.cell(70, 5, "Assinatura do Responsável Legal", 0, 0, 'C')
            pdf.set_xy(110, y+2); pdf.cell(80, 5, "Assinatura do Docente/Gestor", 0, 1, 'C')

            # Salva na sessão e recarrega
            st.session_state.pdf_bytes_caso = get_pdf_bytes(pdf)
            st.rerun()

        # Botão de Download (Fora do if do botão Gerar, mas dentro da tab)
        if 'pdf_bytes_caso' in st.session_state:
            st.download_button("📥 BAIXAR PDF ESTUDO DE CASO", st.session_state.pdf_bytes_caso, f"Caso_{data.get('nome','estudante')}.pdf", "application/pdf", type="primary")

# Apenas um exemplo de como exibir os logs para você
if st.sidebar.checkbox("👁️ Ver Histórico (Diretor)"):
    st.markdown("### 📜 Histórico de Alterações")
    df_logs = conn.read(worksheet="Log", ttl=0)
    # Mostra os mais recentes primeiro
    st.dataframe(df_logs.sort_values(by="data_hora", ascending=False), use_container_width=True)



































































