import streamlit as st
from fpdf import FPDF
from datetime import datetime, date, timedelta, timezone
import io
import os
import base64
import json
import tempfile
from PIL import Image
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import time

# --- CONEXÃO COM GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(
    page_title="Integra | Sistema AEE",
    layout="wide",
    page_icon="🧠",
    initial_sidebar_state="auto"
)

# --- OCULTAR TOOLBAR E MENU E RESPONSIVIDADE ---
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            .stAppDeployButton {display:none;}
            
            /* --- COMPORTAMENTO DESKTOP (Largura > 992px) --- */
            @media (min-width: 992px) {
                /* Esconde o header e trava a sidebar aberta */
                header {visibility: hidden;}
                [data-testid="stSidebarCollapseButton"] {display: none;}
            }
            
            /* --- COMPORTAMENTO MOBILE/TABLET (Largura <= 991px) --- */
            @media (max-width: 991px) {
                /* Header visível para acessar o menu hambúrguer */
                header {visibility: visible;}
                
                /* Ajustes para evitar que o conteúdo suba demais */
                .header-box {
                    margin-top: 0px !important;
                }
            }
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- FUNÇÃO DE LOGIN COMPLETA E ROBUSTA (SME LIMEIRA) ---
def login():
    # Inicializa o estado de autenticação se não existir
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        # --- CSS DA TELA DE LOGIN (NO-SCROLL LAYOUT) ---
        st.markdown("""
            <style>
                /* Remove padding padrão do Streamlit para ocupar a tela toda */
                .block-container {
                    padding-top: 0rem !important;
                    padding-bottom: 0rem !important;
                    max-width: 100%;
                    min-height: 100vh;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                }
                
                /* Fundo da Página */
                [data-testid="stAppViewContainer"] {
                    background: linear-gradient(135deg, #f0f4f8 0%, #d9e2ec 100%);
                }
                
                /* Painel Esquerdo (Arte) */
                .login-art-box {
                    background: linear-gradient(135deg, #2563eb 0%, #1e3a8a 100%);
                    height: 550px; /* Altura ajustada para centralizar melhor */
                    border-radius: 16px 0 0 16px; /* Arredondado apenas na esquerda */
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                    color: white;
                    padding: 40px;
                    text-align: center;
                    box-shadow: -5px 10px 25px rgba(37, 99, 235, 0.2);
                }
                
                /* Painel Direito (Formulário) - Estilizando o próprio stForm */
                div[data-testid="stForm"] {
                    background-color: white;
                    border: none;
                    padding: 2rem 3rem;
                    border-radius: 0 16px 16px 0; /* Arredondado apenas na direita */
                    height: 550px; /* Mesma altura da arte */
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    box-shadow: 5px 10px 25px rgba(0,0,0,0.05);
                }

                /* Tipografia */
                .welcome-title {
                    font-size: 1.8rem;
                    font-weight: 700;
                    color: #1e293b;
                    margin-bottom: 5px;
                }
                .welcome-sub {
                    font-size: 0.95rem;
                    color: #64748b;
                    margin-bottom: 20px;
                }
                
                /* Inputs Customizados */
                .stTextInput label {
                    font-size: 0.85rem;
                    color: #475569;
                    font-weight: 600;
                }
                
                /* Aviso LGPD */
                .lgpd-box {
                    background-color: #fff7ed;
                    border-left: 4px solid #f97316;
                    padding: 10px;
                    margin-top: 15px;
                    margin-bottom: 15px;
                    border-radius: 6px;
                }
                .lgpd-title {
                    color: #9a3412;
                    font-weight: 700;
                    font-size: 0.75rem;
                    display: flex; 
                    align-items: center; 
                    gap: 6px;
                }
                .lgpd-text {
                    color: #9a3412;
                    font-size: 0.7rem;
                    margin-top: 2px;
                    line-height: 1.2;
                    text-align: justify; /* Texto justificado */
                }
            </style>
        """, unsafe_allow_html=True)
        
        # Espaçamento para centralizar verticalmente na tela
        st.write("")
        st.write("")

        # Layout em Colunas: Spacer, Arte, Form, Spacer
        # Ajuste de proporção para ficar elegante
        c_pad1, c_art, c_form, c_pad2 = st.columns([1, 4, 4, 1])
        
        # --- LADO ESQUERDO (ARTE AZUL) ---
        with c_art:
            # Atenção: HTML sem indentação para evitar renderização de bloco de código
            st.markdown("""
<div class="login-art-box">
    <div style="font-size: 6rem; margin-bottom: 1rem; filter: drop-shadow(0px 4px 6px rgba(0,0,0,0.2));">🧠</div>
    <h1 style="color: white; font-weight: 800; font-size: 3.5rem; margin: 0; line-height: 1;">INTEGRA</h1>
    <p style="font-size: 1.2rem; opacity: 0.9; font-weight: 300; margin-top: 10px;">Gestão de Educação<br>Especial Inclusiva</p>
    <div style="margin-top: 40px; width: 100%;">
        <hr style="border-color: rgba(255,255,255,0.3); margin-bottom: 20px;">
        <p style="font-style: italic; font-size: 1rem; opacity: 0.9;">
            "A inclusão acontece quando se aprende com as diferenças e não com as igualdades."
        </p>
    </div>
</div>
""", unsafe_allow_html=True)
            
        # --- LADO DIREITO (FORMULÁRIO BRANCO) ---
        with c_form:
            # Usando st.form como o container do cartão branco
            with st.form("login_form"):
                
                # Layout Header: Texto à esquerda, Logo à direita (menor)
                c_head_txt, c_head_logo = st.columns([3, 1.2])
                
                with c_head_txt:
                    st.markdown('<div class="welcome-title" style="margin-top: 0px;">Bem-vindo(a)</div>', unsafe_allow_html=True)
                    st.markdown('<div class="welcome-sub">Insira suas credenciais para acessar o sistema.</div>', unsafe_allow_html=True)
                
                with c_head_logo:
                    if os.path.exists("logo_escola.png"):
                        # Logo alinhado à direita no layout de colunas
                        st.image("logo_escola.png", use_container_width=True)
                
                st.write("") # Espaço
                
                user_id = st.text_input("Matrícula Funcional", placeholder="Ex: 12345")
                password = st.text_input("Senha", type="password", placeholder="••••••")
                
                st.markdown("""
                    <div class="lgpd-box">
                        <div class="lgpd-title">🔒 CONFIDENCIALIDADE E SIGILO</div>
                        <div class="lgpd-text">
                            Acesso Monitorado. Este sistema contém informações confidenciais e dados sensíveis protegidos pela Lei Geral de Proteção de Dados (LGPD). O uso é estritamente destinado a finalidades pedagógicas e administrativas. 
                            Ao prosseguir, você declara estar ciente de que todas as ações são registradas, podendo haver auditoria para garantia da segurança, integridade e conformidade dos dados. A utilização indevida acarretará responsabilização conforme a legislação vigente.
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                
                submit = st.form_submit_button("ACESSAR SISTEMA", type="primary")
                
                if submit:
                    try:
                        # 1. Busca a senha mestre nos Secrets
                        SENHA_MESTRA = st.secrets.get("credentials", {}).get("password", "admin")
                        
                        # 2. Busca a lista de professores
                        df_professores = conn.read(worksheet="Professores", ttl=0)
                        
                        if not df_professores.empty:
                            df_professores['matricula'] = df_professores['matricula'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
                            user_id_limpo = str(user_id).strip()
                            
                            if password == SENHA_MESTRA and user_id_limpo in df_professores['matricula'].values:
                                registro = df_professores[df_professores['matricula'] == user_id_limpo]
                                nome_prof = registro['nome'].values[0]
                                
                                st.session_state.authenticated = True
                                st.session_state.usuario_nome = nome_prof
                                st.toast(f"Acesso autorizado. Bem-vindo(a), {nome_prof}!", icon="🔓")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("Credenciais inválidas.")
                        else:
                            st.error("Erro de conexão com a base de dados.")
                            
                    except Exception as e:
                        st.error(f"Erro técnico: {e}")
        
        # Interrompe o carregamento do restante do app até que o login seja feito
        st.stop()

# --- ATIVAÇÃO DO LOGIN ---
login()

# --- ESTILO VISUAL DA INTERFACE (CSS MELHORADO E RESPONSIVO) ---
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
        /* Margem negativa apenas para Desktop para 'colar' no topo */
        margin-top: -50px;
    }
    
    .header-title { color: #1e293b; font-weight: 700; font-size: 1.8rem; margin: 0; }
    .header-subtitle { color: #64748b; font-size: 1rem; margin-top: 5px; }
    
    /* Dashboard Cards */
    .metric-card {
        background-color: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border: 1px solid #e2e8f0;
        text-align: center;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #1e3a8a;
    }
    .metric-label {
        color: #64748b;
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    /* Botões */
    .stButton button { width: 100%; border-radius: 8px; }
    
    /* --- MEDIA QUERIES PARA MOBILE --- */
    @media (max-width: 991px) {
        .header-box {
            margin-top: 10px !important; /* Reseta a margem no mobile */
            padding: 1.5rem !important;
        }
        .header-title {
            font-size: 1.5rem !important;
        }
        
        /* Ajustes gerais de espaçamento */
        .stBlock {
            padding-top: 1rem;
        }
    }
</style>
""", unsafe_allow_html=True)

# --- FUNÇÕES DE BANCO DE DADOS ---

def load_db():
    """Lê os dados da planilha do Google"""
    try:
        df = conn.read(worksheet="Alunos", ttl=0)
        df = df.dropna(how="all")
        return df
    except Exception as e:
        return pd.DataFrame(columns=["nome", "tipo_doc", "dados_json", "id"])

def safe_read(worksheet_name, columns):
    """Lê uma aba com segurança, retornando vazio se falhar"""
    try:
        df = conn.read(worksheet=worksheet_name, ttl=0)
        # Se vier vazio, retornamos o DF com as colunas certas
        if df.empty:
             return pd.DataFrame(columns=columns)
        return df
    except:
        return pd.DataFrame(columns=columns)

def safe_update(worksheet_name, data):
    """Atualiza uma aba com segurança"""
    try:
        conn.update(worksheet=worksheet_name, data=data)
        return True
    except Exception as e:
        st.error(f"Erro ao atualizar {worksheet_name}: {e}")
        return False

def log_action(student_name, action, details=""):
    """Registra uma ação no histórico do aluno."""
    try:
        user = st.session_state.get('usuario_nome', 'Desconhecido')
        df_hist = safe_read("Historico", ["Data_Hora", "Aluno", "Usuario", "Acao", "Detalhes"])
        
        new_entry = {
            "Data_Hora": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "Aluno": student_name,
            "Usuario": user,
            "Acao": action,
            "Detalhes": details
        }
        
        df_hist = pd.concat([pd.DataFrame([new_entry]), df_hist], ignore_index=True)
        safe_update("Historico", df_hist)
    except Exception as e:
        print(f"Erro no log: {e}")

def save_student(doc_type, name, data, section="Geral"):
    """Salva ou atualiza garantindo que não duplique linhas"""
    try:
        df_atual = load_db()
        id_registro = f"{name} ({doc_type})"
        
        def serializar_datas(obj):
            if isinstance(obj, (date, datetime)): return obj.strftime("%Y-%m-%d")
            if isinstance(obj, dict): return {k: serializar_datas(v) for k, v in obj.items()}
            if isinstance(obj, list): return [serializar_datas(i) for i in obj]
            return obj
            
        data_limpa = serializar_datas(data)
        novo_json = json.dumps(data_limpa, ensure_ascii=False)

        if not df_atual.empty and "id" in df_atual.columns and id_registro in df_atual["id"].values:
            df_atual.loc[df_atual["id"] == id_registro, "dados_json"] = novo_json
            df_final = df_atual
        else:
            novo_registro = {
                "id": id_registro,
                "nome": name,
                "tipo_doc": doc_type,
                "dados_json": novo_json
            }
            df_final = pd.concat([df_atual, pd.DataFrame([novo_registro])], ignore_index=True)

        conn.update(worksheet="Alunos", data=df_final)
        
        # Registra no histórico
        log_action(name, f"Salvou {doc_type}", f"Seção: {section}")
        
        st.toast(f"✅ Alterações em {name} salvas na nuvem!", icon="💾")
        
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")

def delete_student(student_name):
    """Exclui um aluno do DataFrame e atualiza a planilha"""
    try:
        df = load_db()
        if "nome" in df.columns:
            df_new = df[df["nome"] != student_name]
            if len(df_new) < len(df):
                conn.update(worksheet="Alunos", data=df_new)
                log_action(student_name, "Exclusão", "Registro do aluno excluído")
                st.toast(f"🗑️ Registro de {student_name} excluído com sucesso!", icon="🔥")
                return True
    except Exception as e:
        st.error(f"Erro ao excluir: {e}")
    return False

# --- HELPERS PARA PDF ---
def clean_pdf_text(text):
    if text is None or text is False: return ""
    if text is True: return "Sim"
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

# --- INICIALIZAÇÃO DE ESTADO ---
if 'data_pei' not in st.session_state: 
    st.session_state.data_pei = {
        'terapias': {}, 'avaliacao': {}, 'flex': {}, 'plano_ensino': {},
        'comunicacao_tipo': [], 'permanece': []
    }
if 'data_conduta' not in st.session_state:
    st.session_state.data_conduta = {}
if 'data_avaliacao' not in st.session_state:
    st.session_state.data_avaliacao = {}
if 'data_diario' not in st.session_state:
    st.session_state.data_diario = {}

def carregar_dados_aluno():
    selecao = st.session_state.get('aluno_selecionado')
    
    # Init empty
    st.session_state.data_pei = {'terapias': {}, 'avaliacao': {}, 'flex': {}, 'plano_ensino': {}, 'comunicacao_tipo': [], 'permanece': []}
    st.session_state.data_case = {'irmaos': [{'nome': '', 'idade': '', 'esc': ''} for _ in range(4)], 'checklist': {}, 'clinicas': []}
    st.session_state.data_conduta = {}
    st.session_state.data_avaliacao = {}
    st.session_state.data_diario = {}
    st.session_state.nome_original_salvamento = None

    if not selecao or selecao == "-- Novo Registro --":
        return

    try:
        df_db = load_db()
        # Filter by name
        if "nome" in df_db.columns:
            rows = df_db[df_db["nome"] == selecao]
            if rows.empty: return
            
            st.session_state.nome_original_salvamento = selecao
            st.session_state.data_pei['nome'] = selecao
            st.session_state.data_case['nome'] = selecao
            st.session_state.data_conduta['nome'] = selecao
            st.session_state.data_avaliacao['nome'] = selecao
            st.session_state.data_diario['nome'] = selecao

            for _, row in rows.iterrows():
                try:
                    dados = json.loads(row["dados_json"])
                    # Date conversion
                    for k, v in dados.items():
                        if isinstance(v, str) and len(v) == 10 and v.count('-') == 2:
                            try: dados[k] = datetime.strptime(v, '%Y-%m-%d').date()
                            except: pass
                    
                    dtype = row["tipo_doc"]
                    if dtype == "PEI":
                        st.session_state.data_pei.update(dados)
                    elif dtype == "CASO":
                        st.session_state.data_case.update(dados)
                    elif dtype == "CONDUTA":
                        st.session_state.data_conduta.update(dados)
                    elif dtype == "AVALIACAO":
                        st.session_state.data_avaliacao.update(dados)
                    elif dtype == "DIARIO":
                        st.session_state.data_diario.update(dados)
                except: pass
            
            st.toast(f"✅ {selecao} carregado.")
            
    except Exception as e:
        st.info("Pronto para novo preenchimento.")

# --- BARRA LATERAL ULTRA-COMPACTA ---
with st.sidebar:
    # CSS PARA "ESPREMER" O LAYOUT
    st.markdown("""
    <style>
        section[data-testid="stSidebar"] > div {
            padding-top: 1rem !important;
            padding-bottom: 2rem !important;
        }
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
            gap: 1.2rem !important;
        }
        .sidebar-title {
            font-size: 1.1rem;
            font-weight: 800;
            color: #1e3a8a;
            margin: 0;
            text-align: center;
            line-height: 1.2;
        }
        .sidebar-sub {
            font-size: 0.7rem;
            color: #64748b;
            text-align: center;
            margin-bottom: 8px;
        }
        .section-label {
            font-size: 0.8rem;
            font-weight: 700;
            color: #475569;
            margin-top: 8px;
            margin-bottom: 0px;
        }
        .user-slim {
            background-color: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 4px;
            padding: 4px;
            font-size: 0.8rem;
            color: #334155;
            text-align: center;
        }
        .stRadio { margin-top: -5px; }
        div[data-baseweb="select"] { min-height: 32px; }
        hr { margin: 0.5em 0 !important; }
    </style>
    """, unsafe_allow_html=True)

    # 1. TÍTULO
    st.markdown('<div class="sidebar-title">SISTEMA INTEGRA</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-sub">Gestão de Ed. Especial</div>', unsafe_allow_html=True)

    # 2. USUÁRIO
    nome_prof = st.session_state.get('usuario_nome', 'Docente')
    nomes = nome_prof.split()
    nome_curto = f"{nomes[0]} {nomes[-1]}" if len(nomes) > 1 else nomes[0]
    st.markdown(f'<div class="user-slim">👤 <b>{nome_curto}</b></div>', unsafe_allow_html=True)
    
    st.divider()

    # 3. NAVEGAÇÃO PRINCIPAL
    app_mode = st.radio("Navegação", ["📊 Painel de Gestão", "👥 Gestão de Alunos"], label_visibility="collapsed")

    selected_student = "-- Novo Registro --"
    pei_level = "Fundamental" # Default
    doc_mode = "Dashboard"

    # --- SEÇÃO GESTÃO DE ALUNOS ---
    if app_mode == "👥 Gestão de Alunos":
        st.divider()
        df_db = load_db()
        # Fix duplicates in dropdown
        lista_nomes = df_db["nome"].dropna().unique().tolist() if not df_db.empty else []
        
        st.markdown('<p class="section-label">🎓 Selecionar Estudante</p>', unsafe_allow_html=True)
        selected_student = st.selectbox(
            "Estudante", 
            ["-- Novo Registro --"] + lista_nomes,
            key="aluno_selecionado",
            on_change=carregar_dados_aluno,
            label_visibility="collapsed"
        )

        # Foto na Sidebar
        current_photo_sb = None
        if selected_student != "-- Novo Registro --":
            if st.session_state.get('data_pei', {}).get('nome') == selected_student:
                 current_photo_sb = st.session_state.data_pei.get('foto_base64')
            elif st.session_state.get('data_case', {}).get('nome') == selected_student:
                 current_photo_sb = st.session_state.data_case.get('foto_base64')
                 
        if current_photo_sb:
            try:
                img_bytes_sb = base64.b64decode(current_photo_sb)
                st.image(img_bytes_sb, use_container_width=True)
            except: pass
        
        # Auto-seleção de documento
        default_doc_idx = 0
        if selected_student != "-- Novo Registro --":
            # Just simple heuristic
            pass

        st.markdown('<p class="section-label">📂 Tipo de Documento</p>', unsafe_allow_html=True)
        doc_sub_mode = st.radio(
            "Modo Doc", 
            ["PEI", "Estudo de Caso", "Protocolo de Conduta", "Avaliação Pedagógica", "Relatório Diário"], 
            index=default_doc_idx, 
            key="doc_option",
            label_visibility="collapsed"
        )
        
        doc_mode = doc_sub_mode # Variavel de controle principal

        if doc_mode == "PEI":
            st.markdown('<p class="section-label">🏫 Nível de Ensino</p>', unsafe_allow_html=True)
            pei_level = st.selectbox(
                "Nível", 
                ["Fundamental", "Infantil"], 
                key="pei_level_choice",
                label_visibility="collapsed"
            )
        
        st.markdown('<div style="flex-grow: 1;"></div>', unsafe_allow_html=True)
        st.divider()
        
        c_del1, c_del2 = st.columns(2)
        if selected_student != "-- Novo Registro --":
            if c_del2.button("🗑️", type="secondary", help="Excluir Aluno"):
                st.session_state.confirm_delete = True

    # 4. RODAPÉ FIXO
    if st.sidebar.button("🚪 Sair", use_container_width=True):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

    # Confirmação de exclusão
    if st.session_state.get("confirm_delete"):
        st.warning(f"Excluir {selected_student}?")
        col_d1, col_d2 = st.columns(2)
        if col_d1.button("✅ Sim"):
            delete_student(selected_student)
            st.session_state.confirm_delete = False
            st.rerun()
        if col_d2.button("❌ Não"):
            st.session_state.confirm_delete = False
            st.rerun()

# ==============================================================================
# VIEW: DASHBOARD
# ==============================================================================
if app_mode == "📊 Painel de Gestão":
    # Data e Hora (Fuso BR)
    fuso_br = timezone(timedelta(hours=-3))
    agora = datetime.now(fuso_br)
    
    dias_semana = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]
    meses = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
    
    dia_str = dias_semana[agora.weekday()]
    mes_str = meses[agora.month - 1]
    data_formatada = f"{dia_str}, {agora.day} de {mes_str} de {agora.year}"
    
    st.markdown(f"""
    <div class="header-box" style="margin-top:-50px;">
        <div class="header-title">Painel de Gestão</div>
        <div class="header-subtitle">{data_formatada} | {agora.strftime('%H:%M')}</div>
    </div>
    """, unsafe_allow_html=True)
    
    df_dash = load_db()
    
    # --- CÁLCULO DE MÉTRICAS ---
    # Contagem de alunos únicos
    if not df_dash.empty and "nome" in df_dash.columns:
        total_alunos = df_dash["nome"].nunique()
    else:
        total_alunos = 0
        
    total_pei = len(df_dash[df_dash["tipo_doc"] == "PEI"])
    total_caso = len(df_dash[df_dash["tipo_doc"] == "CASO"])
    
    # Função Auxiliar de Progresso
    def calc_progress(row_json, keys_check):
        try:
            data = json.loads(row_json)
            filled = 0
            for k in keys_check:
                val = data.get(k)
                if val:
                    if isinstance(val, list) and len(val) > 0: filled += 1
                    elif isinstance(val, dict) and len(val) > 0: filled += 1
                    elif isinstance(val, str) and val.strip() != "": filled += 1
                    elif isinstance(val, (int, float)): filled += 1
                    elif val is True: filled += 1
            return int((filled / len(keys_check)) * 100)
        except: return 0

    # Chaves para checagem (focadas em conteúdo preenchido para evitar falsos positivos)
    keys_pei = [
        'prof_poli', 'prof_aee',       # 1. Identificação
        'defic_txt', 'saude_extra',    # 2. Saúde
        'beh_interesses', 'beh_desafios', # 3. Conduta
        'dev_afetivo',                 # 4. Escolar
        'aval_port', 'aval_ling_verbal', # 5. Acadêmico (um dos dois)
        'meta_social_obj', 'meta_acad_obj', # 6. Metas
        'plano_obs_geral'              # Final
    ]
    
    concluidos = 0
    deficiencies_count = {}
    pei_progress_list = []

    for idx, row in df_dash.iterrows():
        try:
            d = json.loads(row['dados_json'])
            # Deficiências
            for dtype in d.get('diag_tipo', []):
                deficiencies_count[dtype] = deficiencies_count.get(dtype, 0) + 1
            if "Deficiência" in d.get('diag_tipo', []) and d.get('defic_txt'):
                d_txt = d.get('defic_txt').upper().strip()
                deficiencies_count[d_txt] = deficiencies_count.get(d_txt, 0) + 1
            
            # Progresso PEI
            if row['tipo_doc'] == "PEI":
                prog = calc_progress(row['dados_json'], keys_pei)
                pei_progress_list.append({"Aluno": row['nome'], "Progresso": prog})
                if prog >= 90: concluidos += 1
        except: pass

    # --- CARDS DE MÉTRICAS ---
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    col_m1.markdown(f'<div class="metric-card"><div class="metric-value">{total_alunos}</div><div class="metric-label">Total Alunos</div></div>', unsafe_allow_html=True)
    col_m2.markdown(f'<div class="metric-card"><div class="metric-value">{total_pei}</div><div class="metric-label">PEIs Criados</div></div>', unsafe_allow_html=True)
    col_m3.markdown(f'<div class="metric-card"><div class="metric-value">{concluidos}</div><div class="metric-label">PEIs Concluídos</div></div>', unsafe_allow_html=True)
    col_m4.markdown(f'<div class="metric-card"><div class="metric-value">{total_caso}</div><div class="metric-label">Estudos de Caso</div></div>', unsafe_allow_html=True)
    
    st.divider()

    # --- ABAS DO DASHBOARD ---
    tab_graf, tab_com = st.tabs(["📊 Estatísticas & Progresso", "📢 Comunicação & Agenda"])
    
    with tab_graf:
        c_chart, c_prog = st.columns([1, 1])
        with c_chart:
            st.subheader("Tipos de Deficiência")
            if deficiencies_count:
                df_def = pd.DataFrame(list(deficiencies_count.items()), columns=["Tipo", "Qtd"])
                st.bar_chart(df_def.set_index("Tipo"), color="#1e3a8a")
            else:
                st.info("Sem dados suficientes.")
        
        with c_prog:
            st.subheader("Progresso dos PEIs")
            if pei_progress_list:
                df_prog = pd.DataFrame(pei_progress_list).sort_values("Progresso")
                with st.container(height=300):
                    for _, row in df_prog.iterrows():
                        st.caption(f"{row['Aluno']} ({row['Progresso']}%)")
                        st.progress(row['Progresso'] / 100)
            else:
                st.info("Nenhum PEI cadastrado.")

    with tab_com:
        c_aviso, c_agenda = st.columns([1, 1])
        
        # --- MURAL DE AVISOS ---
        with c_aviso:
            st.markdown("### 📌 Mural de Avisos")
            with st.form("form_recado"):
                txt_recado = st.text_area("Novo Recado", height=80)
                if st.form_submit_button("Publicar"):
                    df_recados = safe_read("Recados", ["Data", "Autor", "Mensagem"])
                    novo_recado = {
                        "Data": datetime.now().strftime("%d/%m %H:%M"),
                        "Autor": st.session_state.get('usuario_nome', 'Admin'),
                        "Mensagem": txt_recado
                    }
                    df_recados = pd.concat([pd.DataFrame([novo_recado]), df_recados], ignore_index=True)
                    safe_update("Recados", df_recados)
                    st.cache_data.clear() # Limpa cache para atualizar
                    time.sleep(1) # Aguarda propagação
                    st.rerun()
            
            # Listar Recados
            df_recados = safe_read("Recados", ["Data", "Autor", "Mensagem"])
            if not df_recados.empty:
                with st.container(height=300):
                    for index, row in df_recados.iterrows():
                        c_msg, c_del = st.columns([0.85, 0.15])
                        with c_msg:
                            st.info(f"**{row['Autor']}** ({row['Data']}):\n\n{row['Mensagem']}")
                        with c_del:
                            if st.button("🗑️", key=f"del_rec_{index}", help="Excluir recado"):
                                df_recados = df_recados.drop(index)
                                safe_update("Recados", df_recados)
                                st.cache_data.clear()
                                time.sleep(0.5)
                                st.rerun()
            else:
                st.write("Nenhum recado.")

        # --- AGENDA DA EQUIPE ---
        with c_agenda:
            st.markdown("### 📅 Agenda da Equipe")
            with st.form("form_agenda"):
                c_d, c_e = st.columns([1, 2])
                data_evento = c_d.date_input("Data", format="DD/MM/YYYY")
                desc_evento = c_e.text_input("Evento")
                if st.form_submit_button("Agendar"):
                    df_agenda = safe_read("Agenda", ["Data", "Evento", "Autor"])
                    novo_evento = {
                        "Data": data_evento.strftime("%Y-%m-%d"),
                        "Evento": desc_evento,
                        "Autor": st.session_state.get('usuario_nome', 'Admin')
                    }
                    df_agenda = pd.concat([df_agenda, pd.DataFrame([novo_evento])], ignore_index=True)
                    # Ordenar por data
                    df_agenda = df_agenda.sort_values(by="Data", ascending=False)
                    safe_update("Agenda", df_agenda)
                    st.cache_data.clear() # Limpa cache para atualizar
                    time.sleep(1) # Aguarda propagação
                    st.rerun()
            
            # Listar Agenda
            df_agenda = safe_read("Agenda", ["Data", "Evento", "Autor"])
            if not df_agenda.empty:
                with st.container(height=300):
                    for index, row in df_agenda.iterrows():
                        try:
                            d_fmt = datetime.strptime(str(row['Data']), "%Y-%m-%d").strftime("%d/%m")
                        except:
                            d_fmt = str(row['Data'])
                        
                        c_evt, c_del_evt = st.columns([0.85, 0.15])
                        with c_evt:
                            st.write(f"🗓️ **{d_fmt}** - {row['Evento']} _({row['Autor']})_")
                        with c_del_evt:
                            if st.button("🗑️", key=f"del_agd_{index}", help="Excluir evento"):
                                df_agenda = df_agenda.drop(index)
                                safe_update("Agenda", df_agenda)
                                st.cache_data.clear()
                                time.sleep(0.5)
                                st.rerun()
            else:
                st.write("Agenda vazia.")

# ==============================================================================
# VIEW: GESTÃO DE ALUNOS (PEI / CASO)
# ==============================================================================
elif app_mode == "👥 Gestão de Alunos":
    
    # PEI COM FORMULÁRIOS
    if doc_mode == "PEI":
        st.markdown(f"""<div class="header-box"><div class="header-title">Plano Educacional Individualizado - PEI</div></div>""", unsafe_allow_html=True)
        
        st.markdown("""<style>div[data-testid="stFormSubmitButton"] > button {width: 100%; background-color: #dcfce7; color: #166534; border: 1px solid #166534;}</style>""", unsafe_allow_html=True)

        tabs = st.tabs(["1. Identificação", "2. Saúde", "3. Conduta", "4. Escolar", "5. Acadêmico", "6. Metas/Flex", "7. Emissão", "8. Histórico"])
        data = st.session_state.data_pei

        # --- ABA 1: IDENTIFICAÇÃO ---
        with tabs[0]:
            with st.form("form_pei_identificacao"):
                st.subheader("1. Identificação")
                
                # --- LAYOUT COM FOTO ---
                col_img, col_data = st.columns([1, 4])
                
                with col_img:
                    st.markdown("📷 **Foto**")
                    # Se ja tiver foto, mostra
                    if data.get('foto_base64'):
                        try:
                            b = base64.b64decode(data['foto_base64'])
                            st.image(b, use_container_width=True)
                            if st.checkbox("Remover", key="rem_foto_pei"):
                                data['foto_base64'] = None
                        except:
                            st.error("Erro foto")
                    
                    # Upload
                    uploaded_photo = st.file_uploader("Carregar", type=["jpg", "jpeg", "png"], label_visibility="collapsed", key="up_foto_pei")
                    if uploaded_photo:
                        try:
                            img = Image.open(uploaded_photo)
                            if img.mode != 'RGB': img = img.convert('RGB')
                            # Resize para não pesar no banco
                            img.thumbnail((300, 400))
                            buf = io.BytesIO()
                            img.save(buf, format="JPEG", quality=85)
                            data['foto_base64'] = base64.b64encode(buf.getvalue()).decode()
                            st.success("OK!")
                        except Exception as e:
                            st.error(f"Erro: {e}")
                
                with col_data:
                    c1, c2 = st.columns([3, 1])
                    data['nome'] = c1.text_input("Nome", value=data.get('nome', ''), disabled=True)
                    
                    d_val = data.get('nasc')
                    if isinstance(d_val, str): 
                        try: d_val = datetime.strptime(d_val, '%Y-%m-%d').date()
                        except: d_val = date.today()
                    data['nasc'] = c2.date_input("Nascimento", value=d_val if d_val else date.today(), format="DD/MM/YYYY")
                    
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
                idx_elab = elab_opts.index(data['elab_per']) if data.get('elab_per') in elab_opts else 0
                data['elab_per'] = st.selectbox("Período", elab_opts, index=idx_elab)

                st.markdown("---")
                if st.form_submit_button("💾 Salvar Identificação"):
                    save_student("PEI", data.get('nome'), data, "Identificação")

        # --- ABA 2: SAÚDE ---
        with tabs[1]:
            with st.form("form_pei_saude"):
                st.subheader("Informações de Saúde")
                diag_idx = 0 if data.get('diag_status') == "Sim" else 1
                data['diag_status'] = st.radio("Diagnóstico conclusivo?", ["Sim", "Não"], horizontal=True, index=diag_idx)
                
                c_l1, c_l2 = st.columns(2)
                ld_val = data.get('laudo_data')
                if isinstance(ld_val, str): 
                    try: ld_val = datetime.strptime(ld_val, '%Y-%m-%d').date()
                    except: ld_val = date.today()
                data['laudo_data'] = c_l1.date_input("Data do Laudo Médico", value=ld_val if ld_val else date.today(), format="DD/MM/YYYY")
                data['laudo_medico'] = c_l2.text_input("Médico Responsável pelo Laudo", value=data.get('laudo_medico', ''))
                
                st.markdown("Categorias de Diagnóstico:")
                cats = ["Deficiência", "Transtorno do Neurodesenvolvimento", "Transtornos Aprendizagem", "AH/SD", "Outros"]
                if 'diag_tipo' not in data: data['diag_tipo'] = []
                
                c_c1, c_c2 = st.columns(2)
                for i, cat in enumerate(cats):
                    col = c_c1 if i % 2 == 0 else c_c2
                    is_checked = cat in data['diag_tipo']
                    if col.checkbox(cat, value=is_checked, key=f"pei_chk_{i}"):
                        if cat not in data['diag_tipo']: data['diag_tipo'].append(cat)
                    else:
                        if cat in data['diag_tipo']: data['diag_tipo'].remove(cat)
                
                data['defic_txt'] = st.text_input("Descrição da Deficiência", value=data.get('defic_txt', ''))
                data['neuro_txt'] = st.text_input("Descrição do Transtorno Neuro", value=data.get('neuro_txt', ''))
                data['aprend_txt'] = st.text_input("Descrição do Transtorno de Aprendizagem", value=data.get('aprend_txt', ''))

                st.divider()
                st.markdown("**Terapias que realiza**")
                especs = ["Psicologia", "Fonoaudiologia", "Terapia Ocupacional", "Psicopedagogia", "Fisioterapia", "Outros"]
                if 'terapias' not in data: data['terapias'] = {}
                
                for esp in especs:
                    st.markdown(f"**{esp}**")
                    if esp not in data['terapias']: data['terapias'][esp] = {'realiza': False, 'dias': [], 'horario': ''}
                    
                    c_t1, c_t2, c_t3 = st.columns([1, 2, 2])
                    data['terapias'][esp]['realiza'] = c_t1.checkbox("Realiza?", value=data['terapias'][esp].get('realiza', False), key=f"pei_terapias_{esp}")
                    
                    data['terapias'][esp]['dias'] = c_t2.multiselect("Dias", ["2ª", "3ª", "4ª", "5ª", "6ª", "Sábado", "Domingo"], default=data['terapias'][esp].get('dias', []), key=f"pei_dias_{esp}")
                    data['terapias'][esp]['horario'] = c_t3.text_input("Horário", value=data['terapias'][esp].get('horario', ''), key=f"pei_hor_{esp}")
                    
                    if esp == "Outros":
                        data['terapias'][esp]['nome_custom'] = st.text_input("Especifique (Outros):", value=data['terapias'][esp].get('nome_custom', ''), key="pei_custom_name")
                    st.divider()

                data['med_nome'] = st.text_area("Nome da(s) Medicação(ões)", value=data.get('med_nome', ''))
                m1, m2 = st.columns(2)
                data['med_hor'] = m1.text_input("Horário(s)", value=data.get('med_hor', ''))
                data['med_doc'] = m2.text_input("Médico Responsável (Medicação)", value=data.get('med_doc', ''))
                data['med_obj'] = st.text_area("Objetivo da medicação", value=data.get('med_obj', ''))
                data['saude_extra'] = st.text_area("Outras informações de saúde:", value=data.get('saude_extra', ''))

                st.markdown("---")
                if st.form_submit_button("💾 Salvar Saúde"):
                    save_student("PEI", data.get('nome'), data, "Saúde")

        # --- ABA 3: CONDUTA ---
        with tabs[2]:
            with st.form("form_pei_conduta"):
                st.subheader("3. Protocolo de Conduta")
                st.markdown("### 🗣️ COMUNICAÇÃO")
                com_opts = ["Oralmente", "Não comunica", "Não se aplica", "Comunicação alternativa"]
                idx_com = com_opts.index(data['com_tipo']) if data.get('com_tipo') in com_opts else 0
                data['com_tipo'] = st.selectbox("Como o estudante se comunica?", com_opts, index=idx_com)
                data['com_alt_espec'] = st.text_input("Especifique (Comunicação alternativa):", value=data.get('com_alt_espec', ''))
                
                nec_idx = 0 if data.get('com_necessidades') == 'Sim' else 1
                data['com_necessidades'] = st.radio("Expressa necessidades/desejos?", ["Sim", "Não"], horizontal=True, index=nec_idx)
                data['com_necessidades_espec'] = st.text_input("Especifique necessidades:", value=data.get('com_necessidades_espec', ''))
                
                cha_idx = 0 if data.get('com_chamado') == 'Sim' else 1
                data['com_chamado'] = st.radio("Atende quando é chamado?", ["Sim", "Não"], horizontal=True, index=cha_idx)
                data['com_chamado_espec'] = st.text_input("Especifique chamado:", value=data.get('com_chamado_espec', ''))
                
                cmd_idx = 0 if data.get('com_comandos') == 'Sim' else 1
                data['com_comandos'] = st.radio("Responde a comandos simples?", ["Sim", "Não"], horizontal=True, index=cmd_idx)
                data['com_comandos_espec'] = st.text_input("Especifique comandos:", value=data.get('com_comandos_espec', ''))

                st.divider()
                st.markdown("### 🚶 LOCOMOÇÃO")
                loc_r_idx = 1 if data.get('loc_reduzida') == 'Sim' else 0
                data['loc_reduzida'] = st.radio("Possui mobilidade reduzida?", ["Não", "Sim"], horizontal=True, index=loc_r_idx)
                data['loc_reduzida_espec'] = st.text_input("Especifique mobilidade:", value=data.get('loc_reduzida_espec', ''))
                
                c_l1, c_l2 = st.columns(2)
                amb_idx = 0 if data.get('loc_ambiente') == 'Sim' else 1
                data['loc_ambiente'] = c_l1.radio("Locomove-se pela casa?", ["Sim", "Não"], horizontal=True, index=amb_idx)
                helper_idx = 0 if data.get('loc_ambiente_ajuda') == 'Com autonomia' else 1
                data['loc_ambiente_ajuda'] = c_l2.selectbox("Grau:", ["Com autonomia", "Com ajuda"], index=helper_idx)
                data['loc_ambiente_espec'] = st.text_input("Especifique locomoção:", value=data.get('loc_ambiente_espec', ''))

                st.divider()
                st.markdown("### 🧼 AUTOCUIDADO E HIGIENE")
                c_h1, c_h2 = st.columns(2)
                wc_idx = 0 if data.get('hig_banheiro') == 'Sim' else 1
                data['hig_banheiro'] = c_h1.radio("Utiliza o banheiro?", ["Sim", "Não"], horizontal=True, index=wc_idx)
                wc_help_idx = 0 if data.get('hig_banheiro_ajuda') == 'Com autonomia' else 1
                data['hig_banheiro_ajuda'] = c_h2.selectbox("Ajuda banheiro:", ["Com autonomia", "Com ajuda"], index=wc_help_idx)
                data['hig_banheiro_espec'] = st.text_input("Especifique banheiro:", value=data.get('hig_banheiro_espec', ''))
                
                c_h3, c_h4 = st.columns(2)
                tooth_idx = 0 if data.get('hig_dentes') == 'Sim' else 1
                data['hig_dentes'] = c_h3.radio("Escova os dentes?", ["Sim", "Não"], horizontal=True, index=tooth_idx)
                tooth_help_idx = 0 if data.get('hig_dentes_ajuda') == 'Com autonomia' else 1
                data['hig_dentes_ajuda'] = c_h4.selectbox("Ajuda dentes:", ["Com autonomia", "Com ajuda"], index=tooth_help_idx)
                data['hig_dentes_espec'] = st.text_input("Especifique dentes:", value=data.get('hig_dentes_espec', ''))

                st.divider()
                st.markdown("### 🧩 COMPORTAMENTO")
                data['beh_interesses'] = st.text_area("Interesses do estudante:", value=data.get('beh_interesses', ''))
                data['beh_objetos_gosta'] = st.text_area("Objetos que gosta / Apego:", value=data.get('beh_objetos_gosta', ''))
                data['beh_objetos_odeia'] = st.text_area("Objetos que não gosta / Aversão:", value=data.get('beh_objetos_odeia', ''))
                data['beh_toque'] = st.text_area("Gosta de toque/abraço?", value=data.get('beh_toque', ''))
                data['beh_calmo'] = st.text_area("O que o acalma?", value=data.get('beh_calmo', ''))
                data['beh_atividades'] = st.text_area("Atividades prazerosas:", value=data.get('beh_atividades', ''))
                data['beh_gatilhos'] = st.text_area("Gatilhos de crise:", value=data.get('beh_gatilhos', ''))
                data['beh_crise_regula'] = st.text_area("Como se regula na crise?", value=data.get('beh_crise_regula', ''))
                data['beh_desafios'] = st.text_area("Comportamentos desafiadores / Manejo:", value=data.get('beh_desafios', ''))
                
                c_b1, c_b2 = st.columns([1, 2])
                food_idx = 1 if data.get('beh_restricoes') == 'Sim' else 0
                data['beh_restricoes'] = c_b1.radio("Restrições alimentares?", ["Não", "Sim"], horizontal=True, index=food_idx)
                data['beh_restricoes_espec'] = c_b2.text_input("Especifique alimentação:", value=data.get('beh_restricoes_espec', ''))
                
                c_b3, c_b4 = st.columns([1, 2])
                water_idx = 0 if data.get('beh_autonomia_agua') == 'Sim' else 1
                data['beh_autonomia_agua'] = c_b3.radio("Autonomia (água/comida)?", ["Sim", "Não"], horizontal=True, index=water_idx)
                data['beh_autonomia_agua_espec'] = c_b4.text_input("Especifique autonomia:", value=data.get('beh_autonomia_agua_espec', ''))
                
                data['beh_pertinentes'] = st.text_area("Outras informações:", value=data.get('beh_pertinentes', ''))

                st.markdown("---")
                if st.form_submit_button("💾 Salvar Conduta"):
                    save_student("PEI", data.get('nome'), data, "Conduta")

        # --- ABA 4: ESCOLAR ---
        with tabs[3]:
            with st.form("form_pei_escolar"):
                st.subheader("4. Desenvolvimento Escolar")
                
                c_p1, c_p2 = st.columns([1, 2])
                perm_opts = ["Sim - Por longo período", "Sim - Por curto período", "Não"]
                idx_perm = perm_opts.index(data.get('dev_permanece')) if data.get('dev_permanece') in perm_opts else 0
                data['dev_permanece'] = c_p1.selectbox("Permanece em sala?", perm_opts, index=idx_perm)
                data['dev_permanece_espec'] = c_p2.text_input("Obs Permanência:", value=data.get('dev_permanece_espec', ''))

                c_i1, c_i2 = st.columns([1, 2])
                int_idx = 0 if data.get('dev_integrado') == 'Sim' else 1
                data['dev_integrado'] = c_i1.radio("Integrado ao ambiente?", ["Sim", "Não"], horizontal=True, index=int_idx)
                data['dev_integrado_espec'] = c_i2.text_input("Obs Integração:", value=data.get('dev_integrado_espec', ''))

                c_l1, c_l2 = st.columns([1, 2])
                loc_opts = ["Sim - Com autonomia", "Sim - Com ajuda", "Não"]
                idx_loc = loc_opts.index(data.get('dev_loc_escola')) if data.get('dev_loc_escola') in loc_opts else 0
                data['dev_loc_escola'] = c_l1.selectbox("Locomove-se pela escola?", loc_opts, index=idx_loc)
                data['dev_loc_escola_espec'] = c_l2.text_input("Obs Locomoção:", value=data.get('dev_loc_escola_espec', ''))

                c_t1, c_t2 = st.columns([1, 2])
                tar_opts = ["Sim - Com autonomia", "Sim - Com ajuda", "Não"]
                idx_tar = tar_opts.index(data.get('dev_tarefas')) if data.get('dev_tarefas') in tar_opts else 0
                data['dev_tarefas'] = c_t1.selectbox("Realiza tarefas?", tar_opts, index=idx_tar)
                data['dev_tarefas_espec'] = c_t2.text_input("Obs Tarefas:", value=data.get('dev_tarefas_espec', ''))

                c_a1, c_a2 = st.columns([1, 2])
                amg_idx = 0 if data.get('dev_amigos') == 'Sim' else 1
                data['dev_amigos'] = c_a1.radio("Tem amigos?", ["Sim", "Não"], horizontal=True, index=amg_idx)
                data['dev_amigos_espec'] = c_a2.text_input("Obs Amigos:", value=data.get('dev_amigos_espec', ''))

                data['dev_colega_pref'] = st.radio("Tem colega predileto?", ["Sim", "Não"], horizontal=True, index=0 if data.get('dev_colega_pref') == 'Sim' else 1)

                c_ia1, c_ia2 = st.columns([1, 2])
                ia_idx = 0 if data.get('dev_participa') == 'Sim' else 1
                data['dev_participa'] = c_ia1.radio("Participa/Interage?", ["Sim", "Não"], horizontal=True, index=ia_idx)
                data['dev_participa_espec'] = c_ia2.text_input("Obs Interação:", value=data.get('dev_participa_espec', ''))

                data['dev_afetivo'] = st.text_area("Envolvimento afetivo/social da turma:", value=data.get('dev_afetivo', ''))

                st.markdown("---")
                if st.form_submit_button("💾 Salvar Escolar"):
                    save_student("PEI", data.get('nome'), data, "Escolar")

        # --- ABA 5: ACADÊMICO ---
        with tabs[4]:
            with st.form("form_pei_academico"):
                st.subheader("5. Avaliação Acadêmica")
                
                if pei_level == "Fundamental":
                    c_f1, c_f2 = st.columns(2)
                    data['aval_port'] = c_f1.text_area("Língua Portuguesa", value=data.get('aval_port', ''))
                    data['aval_mat'] = c_f2.text_area("Matemática", value=data.get('aval_mat', ''))
                    data['aval_con_gerais'] = st.text_area("Conhecimentos Gerais", value=data.get('aval_con_gerais', ''))

                    st.markdown("**ARTE**")
                    data['aval_arte_visuais'] = st.text_area("Artes Visuais", value=data.get('aval_arte_visuais', ''))
                    data['aval_arte_musica'] = st.text_area("Música", value=data.get('aval_arte_musica', ''))
                    c_a1, c_a2 = st.columns(2)
                    data['aval_arte_teatro'] = c_a1.text_area("Teatro", value=data.get('aval_arte_teatro', ''))
                    data['aval_arte_danca'] = c_a2.text_area("Dança", value=data.get('aval_arte_danca', ''))

                    st.markdown("**EDUCAÇÃO FÍSICA**")
                    c_ef1, c_ef2 = st.columns(2)
                    data['aval_ef_motoras'] = c_ef1.text_area("Habilidades Motoras", value=data.get('aval_ef_motoras', ''))
                    data['aval_ef_corp_conhec'] = c_ef2.text_area("Conhecimento Corporal", value=data.get('aval_ef_corp_conhec', ''))
                    data['aval_ef_exp'] = st.text_area("Exp. Corporais e Expressividade", value=data.get('aval_ef_exp', ''))
                    
                    st.markdown("**LINGUAGENS E TECNOLOGIAS**")
                    data['aval_ling_tec'] = st.text_area("Avaliação da disciplina:", value=data.get('aval_ling_tec', ''))
                else:
                    # Infantil
                    data['aval_ling_verbal'] = st.text_area("Linguagem Verbal", value=data.get('aval_ling_verbal', ''))
                    data['aval_ling_mat'] = st.text_area("Linguagem Matemática", value=data.get('aval_ling_mat', ''))
                    data['aval_ind_soc'] = st.text_area("Indivíduo e Sociedade", value=data.get('aval_ind_soc', ''))
                    
                    st.markdown("**ARTE**")
                    data['aval_arte_visuais'] = st.text_area("Artes Visuais", value=data.get('aval_arte_visuais', ''))
                    data['aval_arte_musica'] = st.text_area("Música", value=data.get('aval_arte_musica', ''))
                    data['aval_arte_teatro'] = st.text_area("Teatro", value=data.get('aval_arte_teatro', ''))

                    st.markdown("**EDUCAÇÃO FÍSICA**")
                    c_ef1, c_ef2, c_ef3 = st.columns(3)
                    data['aval_ef_jogos'] = c_ef1.text_area("Jogos/Brincadeiras", value=data.get('aval_ef_jogos', ''))
                    data['aval_ef_ritmo'] = c_ef2.text_area("Ritmo", value=data.get('aval_ef_ritmo', ''))
                    data['aval_ef_corp'] = c_ef3.text_area("Conhecimento Corporal", value=data.get('aval_ef_corp', ''))
                    
                    st.markdown("**LINGUAGEM E TECNOLOGIAS**")
                    data['aval_ling_tec'] = st.text_area("Avaliação da disciplina:", value=data.get('aval_ling_tec', ''))

                st.markdown("---")
                if st.form_submit_button("💾 Salvar Acadêmico"):
                    save_student("PEI", data.get('nome'), data, "Acadêmico")

        # --- ABA 6: METAS E FLEXIBILIZAÇÃO ---
        with tabs[5]:
            with st.form("form_pei_metas"):
                st.header("6. Metas Específicas")
                
                c_m1, c_m2 = st.columns(2)
                st.subheader("Habilidades Sociais")
                data['meta_social_obj'] = st.text_area("Metas (Sociais):", value=data.get('meta_social_obj', ''))
                data['meta_social_est'] = st.text_area("Estratégias (Sociais):", value=data.get('meta_social_est', ''))

                st.divider(); st.subheader("Autocuidado e Vida Prática")
                data['meta_auto_obj'] = st.text_area("Metas (Autocuidado):", value=data.get('meta_auto_obj', ''))
                data['meta_auto_est'] = st.text_area("Estratégias (Autocuidado):", value=data.get('meta_auto_est', ''))

                st.divider(); st.subheader("Habilidades Acadêmicas")
                data['meta_acad_obj'] = st.text_area("Metas (Acadêmicas):", value=data.get('meta_acad_obj', ''))
                data['meta_acad_est'] = st.text_area("Estratégias (Acadêmicas):", value=data.get('meta_acad_est', ''))

                st.header("7. Flexibilização Curricular")
                if pei_level == "Fundamental":
                    disciplinas_flex = ["Língua Portuguesa", "Matemática", "História", "Geografia", "Ciências", "Arte", "Educação Física", "Linguagens e Tecnologia"]
                else:
                    disciplinas_flex = ["Linguagem Verbal", "Linguagem Matemática", "Indivíduo e Sociedade", "Arte", "Educação Física", "Linguagens e Tecnologia"]

                if 'flex_matrix' not in data: data['flex_matrix'] = {}
                
                st.markdown("**7.1 Disciplinas que necessitam de adaptação**")
                c_h1, c_h2, c_h3 = st.columns([2, 1, 1])
                c_h1.write("**Disciplina**")
                c_h2.write("**Conteúdo?**")
                c_h3.write("**Metodologia?**")
                
                for disc in disciplinas_flex:
                    if disc not in data['flex_matrix']: data['flex_matrix'][disc] = {'conteudo': False, 'metodologia': False}
                    
                    c1, c2, c3 = st.columns([2, 1, 1])
                    c1.write(disc)
                    data['flex_matrix'][disc]['conteudo'] = c2.checkbox("Sim", key=f"flex_c_{disc}", value=data['flex_matrix'][disc]['conteudo'])
                    data['flex_matrix'][disc]['metodologia'] = c3.checkbox("Sim", key=f"flex_m_{disc}", value=data['flex_matrix'][disc]['metodologia'])

                st.divider()
                st.subheader("7.2 Plano de Ensino Anual")
                trimestres = ["1º Trimestre", "2º Trimestre", "3º Trimestre"]
                if 'plano_ensino_tri' not in data: data['plano_ensino_tri'] = {}

                for tri in trimestres:
                    st.markdown(f"### 🗓️ {tri}")
                    if tri not in data['plano_ensino_tri']: data['plano_ensino_tri'][tri] = {}
                    
                    for disc in disciplinas_flex:
                        with st.expander(f"{tri} - {disc}", expanded=False):
                            if disc not in data['plano_ensino_tri'][tri]:
                                data['plano_ensino_tri'][tri][disc] = {'obj': '', 'cont': '', 'met': ''}
                            
                            p_ref = data['plano_ensino_tri'][tri][disc]
                            
                            p_ref['obj'] = st.text_area(f"Objetivos ({disc})", value=p_ref['obj'], key=f"obj_{tri}_{disc}")
                            p_ref['cont'] = st.text_area(f"Conteúdos ({disc})", value=p_ref['cont'], key=f"cont_{tri}_{disc}")
                            p_ref['met'] = st.text_area(f"Metodologia ({disc})", value=p_ref['met'], key=f"met_{tri}_{disc}")

                    st.markdown("---")
                    data['plano_ensino_tri'][tri]['obs'] = st.text_area(f"Obs/Recomendações {tri}:", value=data['plano_ensino_tri'][tri].get('obs', ''), key=f"obs_{tri}")

                st.markdown("Considerações finais:")
                data['plano_obs_geral'] = st.text_area("", value=data.get('plano_obs_geral', ''), key="obs_geral_pei")

                st.markdown("---")
                if st.form_submit_button("💾 Salvar Metas e Plano"):
                    save_student("PEI", data.get('nome'), data, "Metas e Plano")

        # --- ABA 7: EMISSÃO ---
        with tabs[6]:
            st.info("Antes de gerar o PDF, certifique-se de ter clicado em 'Salvar' nas abas anteriores.")
            if st.button("💾 SALVAR PEI COMPLETO", type="primary"): save_student("PEI", data['nome'], data, "Completo")
            if st.button("👁️ GERAR PDF COMPLETO"):
                # Registrar ação de gerar PDF
                log_action(data.get('nome'), "Gerou PDF", "PEI Completo")
                
                pdf = OfficialPDF('L', 'mm', 'A4'); pdf.add_page(); pdf.set_margins(10, 10, 10)
                
                # --- PÁGINA 1 ---
                if os.path.exists("logo_prefeitura.png"): pdf.image("logo_prefeitura.png", 10, 8, 25)
                if os.path.exists("logo_escola.png"): pdf.image("logo_escola.png", 252, 4, 37) 
                pdf.set_xy(0, 12); pdf.set_font("Arial", "", 14)
                pdf.cell(305, 6, clean_pdf_text("      PREFEITURA MUNICIPAL DE LIMEIRA"), 0, 1, 'C')
                pdf.ln(6); pdf.set_font("Arial", "B", 12)
                pdf.cell(297, 6, clean_pdf_text("CEIEF RAFAEL AFFONSO LEITE"), 0, 1, 'C')
                pdf.ln(8); pdf.set_font("Arial", "B", 14)
                pdf.cell(297, 8, clean_pdf_text("PLANO EDUCACIONAL ESPECIALIZADO - PEI"), 0, 1, 'C')
                
                # --- FOTO ---
                # Retângulo da foto: x=256, y=53, w=30, h=40
                if data.get('foto_base64'):
                    try:
                        img_data = base64.b64decode(data.get('foto_base64'))
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
                            tmp_file.write(img_data)
                            tmp_path = tmp_file.name
                        pdf.image(tmp_path, 256, 53, 30, 40)
                        os.unlink(tmp_path)
                        pdf.rect(256, 53, 30, 40) # Borda
                    except:
                        pdf.rect(256, 53, 30, 40)
                        pdf.set_xy(255.5, 70); pdf.set_font("Arial", "", 8); pdf.cell(30, 5, "Erro", 0, 0, 'C')
                else:
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

                # --- PÁGINA 2 ---
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
                pdf.ln(5); pdf.set_font("Arial", "B", 12); pdf.cell(50, 8, clean_pdf_text("Médico Responsável:"), 1, 0); pdf.set_font("Arial", "", 12); pdf.cell(0, 8, clean_pdf_text(data.get('med_doc', 'N/A')), 1, 1)
                pdf.set_font("Arial", "B", 12); pdf.cell(0, 8, "Objetivo da medicação:", "LTR", 1, 'L', 1); pdf.set_font("Arial", "", 12); pdf.multi_cell(0, 8, clean_pdf_text(data.get('med_obj', 'Não informado.')), "LRB")
                pdf.ln(3); pdf.set_font("Arial", "B", 12); pdf.cell(0, 8, clean_pdf_text("Outras informações de saúde consideradas relevantes:"), "LTR", 1, 'L', 1)
                pdf.set_font("Arial", "", 12); pdf.multi_cell(0, 8, clean_pdf_text(data.get('saude_extra', 'Nenhuma informação adicional.')), "LRB")

                # --- 3. PROTOCOLO DE CONDUTA ---
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
                    if pdf.get_y() > 250: 
                        pdf.add_page()
                        
                    pdf.set_x(10)
                    pdf.set_font("Arial", "B", 10)
                    pdf.multi_cell(0, 7, clean_pdf_text(l), border="LTR", align='L', fill=True) 
                    
                    pdf.set_x(10)
                    pdf.set_font("Arial", "", 10)
                    pdf.multi_cell(0, 6, clean_pdf_text(v if v else "---"), border="LBR", align='L', fill=False)

                # --- 4. DESENVOLVIMENTO ESCOLAR ---
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

                # --- 5. AVALIAÇÃO ACADÊMICA ---
                pdf.ln(5)
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
                    if pdf.get_y() > 230: pdf.add_page()
                    
                    pdf.set_font("Arial", "B", 10); pdf.set_fill_color(240, 240, 240)
                    pdf.cell(0, 7, clean_pdf_text(titulo), "LTR", 1, 'L', 1)
                    pdf.set_font("Arial", "", 10)
                    pdf.multi_cell(0, 6, clean_pdf_text(texto if texto else "---"), "LRB")
                    pdf.ln(2)

                # --- 6. METAS ---
                pdf.ln(5)
                if pdf.get_y() > 220: pdf.add_page()
                
                pdf.section_title("6. METAS ESPECÍFICAS PARA O ANO EM CURSO", width=0)
                pdf.ln(2)
                
                def print_meta_row(titulo, meta, estrategia):
                    if pdf.get_y() > 220: pdf.add_page()
                    pdf.set_font("Arial", "B", 11); pdf.set_fill_color(230, 230, 230)
                    pdf.cell(0, 8, clean_pdf_text(titulo), 1, 1, 'L', 1)
                    pdf.set_font("Arial", "B", 10); pdf.cell(0, 6, "Metas / Habilidades:", "LTR", 1)
                    pdf.set_font("Arial", "", 10); pdf.multi_cell(0, 5, clean_pdf_text(meta if meta else "---"), "LRB")
                    pdf.set_x(10); pdf.set_font("Arial", "B", 10); pdf.cell(0, 5, clean_pdf_text("Estratégias:"), "LTR", 1)
                    pdf.set_x(10); pdf.set_font("Arial", "", 10); pdf.multi_cell(0, 5, clean_pdf_text(estrategia if estrategia else "---"), "LRB")
                    pdf.ln(2)

                print_meta_row("Habilidades Sociais", data.get('meta_social_obj'), data.get('meta_social_est'))
                print_meta_row("Habilidades de Autocuidado e Vida Prática", data.get('meta_auto_obj'), data.get('meta_auto_est'))
                print_meta_row("Habilidades Acadêmicas", data.get('meta_acad_obj'), data.get('meta_acad_est'))

                # --- 7. FLEXIBILIZAÇÃO ---
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

                # --- ASSINATURAS ---
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

        # --- ABA 8: HISTÓRICO ---
        with tabs[7]:
            st.subheader("Histórico de Atividades")
            st.caption("Registro de alterações, salvamentos e geração de documentos.")
            
            df_hist = safe_read("Historico", ["Data_Hora", "Aluno", "Usuario", "Acao", "Detalhes"])
            
            if not df_hist.empty and data.get('nome'):
                # Filtrar pelo aluno atual
                student_hist = df_hist[df_hist["Aluno"] == data.get('nome')]
                
                if not student_hist.empty:
                    # Ordenar por data (mais recente primeiro)
                    student_hist = student_hist.iloc[::-1]
                    st.dataframe(student_hist, use_container_width=True, hide_index=True)
                else:
                    st.info("Nenhum histórico encontrado para este aluno.")
            else:
                st.info("O histórico está vazio ou aluno não selecionado.")

    # ESTUDO DE CASO COM FORMULÁRIOS
    elif doc_mode == "Estudo de Caso":
        st.markdown("""<div class="header-box"><div class="header-title">Estudo de Caso</div></div>""", unsafe_allow_html=True)
        
        if 'data_case' not in st.session_state: 
            st.session_state.data_case = {
                'irmaos': [{'nome': '', 'idade': '', 'esc': ''} for _ in range(4)], 
                'checklist': {},
                'clinicas': []
            }
        
        data = st.session_state.data_case
        
        st.markdown("""<style>div[data-testid="stFormSubmitButton"] > button {width: 100%; background-color: #dcfce7; color: #166534; border: 1px solid #166534;}</style>""", unsafe_allow_html=True)

        tabs = st.tabs(["1. Identificação", "2. Família", "3. Histórico", "4. Saúde", "5. Comportamento", "6. Gerar PDF", "7. Histórico"])

        # --- ABA 1: IDENTIFICAÇÃO ---
        with tabs[0]:
            with st.form("form_caso_identificacao"):
                st.subheader("1.1 Dados Gerais do Estudante")
                data['nome'] = st.text_input("Nome Completo", value=data.get('nome', ''), disabled=True)
                
                c1, c2, c3 = st.columns([1, 1, 2])
                data['ano_esc'] = c1.text_input("Ano Escolaridade", value=data.get('ano_esc', ''))
                
                p_val = data.get('periodo') if data.get('periodo') in ["Manhã", "Tarde", "Integral"] else "Manhã"
                idx_per = ["Manhã", "Tarde", "Integral"].index(p_val)
                data['periodo'] = c2.selectbox("Período", ["Manhã", "Tarde", "Integral"], index=idx_per)
                data['unidade'] = c3.text_input("Unidade Escolar", value=data.get('unidade', ''))

                c4, c5 = st.columns([1, 1])
                data['sexo'] = c4.radio("Sexo", ["Feminino", "Masculino"], horizontal=True, index=0 if data.get('sexo') == 'Feminino' else 1)
                
                d_nasc = data.get('d_nasc')
                if isinstance(d_nasc, str):
                    try: d_nasc = datetime.strptime(d_nasc, '%Y-%m-%d').date()
                    except: d_nasc = date.today()
                data['d_nasc'] = c5.date_input("Data de Nascimento", value=d_nasc if d_nasc else date.today(), format="DD/MM/YYYY")

                data['endereco'] = st.text_input("Endereço", value=data.get('endereco', ''))
                c6, c7, c8 = st.columns([2, 2, 2])
                data['bairro'] = c6.text_input("Bairro", value=data.get('bairro', ''))
                data['cidade'] = c7.text_input("Cidade", value=data.get('cidade', 'Limeira'))
                data['telefones'] = c8.text_input("Telefones", value=data.get('telefones', ''))
                
                st.markdown("---")
                if st.form_submit_button("💾 Salvar Dados de Identificação"):
                    save_student("CASO", data.get('nome'), data, "Identificação")

        # --- ABA 2: DADOS FAMILIARES ---
        with tabs[1]:
            with st.form("form_caso_familia"):
                st.subheader("1.1.2 Dados Familiares")
                
                st.markdown("**Pai**")
                c_p1, c_p2, c_p3, c_p4 = st.columns([3, 2, 2, 2])
                data['pai_nome'] = c_p1.text_input("Nome do Pai", value=data.get('pai_nome', ''))
                data['pai_prof'] = c_p2.text_input("Profissão Pai", value=data.get('pai_prof', ''))
                data['pai_esc'] = c_p3.text_input("Escolaridade Pai", value=data.get('pai_esc', ''))
                data['pai_dn'] = c_p4.text_input("D.N. Pai", value=data.get('pai_dn', '')) 

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

                st.markdown("---")
                if st.form_submit_button("💾 Salvar Dados Familiares"):
                    save_student("CASO", data.get('nome'), data, "Família")

        # --- ABA 3: HISTÓRICO ---
        with tabs[2]:
            with st.form("form_caso_historico"):
                st.subheader("1.1.3 História Escolar")
                data['hist_idade_entrou'] = st.text_input("Idade que entrou na escola:", value=data.get('hist_idade_entrou', ''))
                data['hist_outra_escola'] = st.text_input("Já estudou em outra escola? Quais?", value=data.get('hist_outra_escola', ''))
                data['hist_motivo_transf'] = st.text_input("Motivo da transferência:", value=data.get('hist_motivo_transf', ''))
                data['hist_obs'] = st.text_area("Outras observações escolares:", value=data.get('hist_obs', ''))

                st.divider()
                st.subheader("1.2 Informações sobre Gestação")
                
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
                data['fam_deficiencia'] = c_fam1.text_input("Pessoa com deficiência na família?", value=data.get('fam_deficiencia', ''))
                data['fam_altas_hab'] = c_fam2.radio("Pessoa com AH/SD na família?", ["Sim", "Não"], horizontal=True, index=1 if data.get('fam_altas_hab') == "Não" else 0)
                
                st.markdown("---")
                if st.form_submit_button("💾 Salvar Dados de Histórico"):
                    save_student("CASO", data.get('nome'), data, "Histórico")

        # --- ABA 4: SAÚDE ---
        with tabs[3]:
            with st.form("form_caso_saude"):
                st.subheader("1.3 Informações sobre Saúde")
                data['saude_prob'] = st.text_input("Problema de saúde? Quais?", value=data.get('saude_prob', ''))
                data['saude_internacao'] = st.text_input("Internação? Motivos?", value=data.get('saude_internacao', ''))
                data['saude_restricao'] = st.text_input("Restrição/Seletividade alimentar?", value=data.get('saude_restricao', ''))
                
                st.markdown("**Medicamentos Controlados**")
                data['med_uso'] = st.radio("Faz uso?", ["Sim", "Não"], horizontal=True, index=1 if data.get('med_uso') == "Não" else 0)
                data['med_quais'] = st.text_input("Quais medicamentos?", value=data.get('med_quais', ''))
                c_med1, c_med2, c_med3 = st.columns(3)
                data['med_hor'] = c_med1.text_input("Horário", value=data.get('med_hor', ''))
                data['med_dos'] = c_med2.text_input("Dosagem", value=data.get('med_dos', ''))
                data['med_ini'] = c_med3.text_input("Início", value=data.get('med_ini', ''))

                st.divider()
                c_esf1, c_esf2 = st.columns(2)
                data['esf_urina'] = c_esf1.checkbox("Controla Urina", value=data.get('esf_urina', False))
                data['esf_fezes'] = c_esf2.checkbox("Controla Fezes", value=data.get('esf_fezes', False))
                data['esf_idade'] = st.text_input("Com qual idade controlou?", value=data.get('esf_idade', ''))
                data['sono'] = st.text_input("Dorme bem? Obs:", value=data.get('sono', ''))
                data['medico_ultimo'] = st.text_input("Última visita ao médico:", value=data.get('medico_ultimo', ''))

                st.markdown("**Atendimento Clínico Extraescolar**")
                clinicas_opts = ["APAE", "ARIL", "CEMA", "Família Azul", "CAPS", "Amb. Saúde Mental", "João Fischer D.A.", "João Fischer D.V."]
                prof_opts = ["Fonoaudiólogo", "Terapeuta Ocupacional", "Psicólogo", "Psicopedagogo", "Fisioterapeuta"]
                
                data['clinicas'] = st.multiselect("Selecione os atendimentos:", clinicas_opts + prof_opts, default=data.get('clinicas', []))
                data['clinicas_med_esp'] = st.text_input("Área médica (Especialidade):", value=data.get('clinicas_med_esp', ''))
                data['clinicas_nome'] = st.text_input("Nome da Clínica/Profissional:", value=data.get('clinicas_nome', ''))
                
                data['saude_obs_geral'] = st.text_area("Outras observações de saúde:", value=data.get('saude_obs_geral', ''))

                st.markdown("---")
                if st.form_submit_button("💾 Salvar Dados de Saúde"):
                    save_student("CASO", data.get('nome'), data, "Saúde")

        # --- ABA 5: COMPORTAMENTO ---
        with tabs[4]:
            with st.form("form_caso_comportamento"):
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
                
                for i, item in enumerate(checklist_items):
                    st.markdown(f"**{item}**")
                    col_a, col_b = st.columns([1, 3])
                    key_base = item[:10].replace(" ", "").replace("?", "")
                    
                    opt = data['checklist'].get(f"{key_base}_opt", "Não")
                    data['checklist'][f"{key_base}_opt"] = col_a.radio("Opção", ["Sim", "Não"], key=f"rad_f_{i}", horizontal=True, label_visibility="collapsed", index=0 if opt == "Sim" else 1)
                    
                    data['checklist'][f"{key_base}_obs"] = col_b.text_input("Obs:", value=data['checklist'].get(f"{key_base}_obs", ""), key=f"obs_f_{i}")
                    st.divider()

                st.subheader("Dados da Entrevista")
                c_e1, c_e2, c_e3 = st.columns(3)
                data['entrevista_prof'] = c_e1.text_input("Prof. Responsável", value=data.get('entrevista_prof', ''))
                data['entrevista_resp'] = c_e2.text_input("Responsável info", value=data.get('entrevista_resp', ''))
                
                d_ent = data.get('entrevista_data')
                if isinstance(d_ent, str): 
                     try: d_ent = datetime.strptime(d_ent, '%Y-%m-%d').date()
                     except: d_ent = date.today()
                data['entrevista_data'] = c_e3.date_input("Data", value=d_ent if d_ent else date.today(), format="DD/MM/YYYY")
                
                data['entrevista_extra'] = st.text_area("Outras informações relevantes:", value=data.get('entrevista_extra', ''))
                
                st.markdown("---")
                if st.form_submit_button("💾 Salvar Comportamento"):
                    save_student("CASO", data.get('nome'), data, "Comportamento")

        # --- ABA 6: GERAR PDF (ESTUDO DE CASO) ---
        with tabs[5]:
            if st.button("💾 SALVAR ESTUDO DE CASO", type="primary"): 
                save_student("CASO", data.get('nome', 'aluno'), data, "Completo")

            if st.button("👁️ GERAR PDF"):
                # Registrar ação de gerar PDF
                log_action(data.get('nome'), "Gerou PDF", "Estudo de Caso")
                
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
                pdf.set_font("Arial", "B", 10); pdf.cell(20, 8, "Período:", 1, 0, 'C', 1)
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
                pdf.add_page()
                pdf.section_title("1.2 GESTAÇÃO, PARTO E DESENVOLVIMENTO", width=0)
                pdf.ln(4)
                
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
                
                esf = []
                if data.get('esf_urina'): esf.append("Urina")
                if data.get('esf_fezes'): esf.append("Fezes")
                print_data_row("Controle de Esfíncter:", f"{', '.join(esf) if esf else 'Não'}  (Idade: {data.get('esf_idade')})")
                
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
                
                pdf.set_fill_color(220, 220, 220); pdf.set_font("Arial", "B", 9)
                pdf.cell(110, 8, "PERGUNTA / ASPECTO OBSERVADO", 1, 0, 'C', 1)
                pdf.cell(25, 8, "SIM/NÃO", 1, 0, 'C', 1)
                pdf.cell(0, 8, clean_pdf_text("OBSERVAÇÕES DA FAMÍLIA"), 1, 1, 'C', 1)
                
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
                
                pdf.set_font("Arial", "", 9)
                for item in checklist_items:
                    key_base = item[:10].replace(" ", "").replace("?", "")
                    opt = data.get('checklist', {}).get(f"{key_base}_opt", "Não")
                    obs = data.get('checklist', {}).get(f"{key_base}_obs", "")
                    
                    line_height = 6
                    num_lines = pdf.get_string_width(obs) / 50 
                    cell_height = max(line_height, (int(num_lines) + 1) * line_height)
                    
                    x_start = pdf.get_x(); y_start = pdf.get_y()
                    
                    pdf.multi_cell(110, line_height, clean_pdf_text(item), 1, 'L')
                    
                    pdf.set_xy(x_start + 110, y_start)
                    pdf.cell(25, cell_height, clean_pdf_text(opt), 1, 0, 'C')
                    
                    pdf.set_xy(x_start + 135, y_start)
                    pdf.multi_cell(0, line_height, clean_pdf_text(obs), 1, 'L')
                    
                    pdf.set_xy(x_start, y_start + cell_height)

                # --- FINALIZAÇÃO ---
                pdf.ln(5)
                pdf.set_font("Arial", "B", 10); pdf.set_fill_color(240, 240, 240)
                pdf.cell(0, 8, clean_pdf_text("OUTRAS INFORMAÇÕES RELEVANTES"), 1, 1, 'L', 1)
                pdf.set_font("Arial", "", 9)
                pdf.multi_cell(0, 6, clean_pdf_text(data.get('entrevista_extra', '---')), 1)
                
                pdf.ln(10)
                if pdf.get_y() > 240: pdf.add_page()
                
                pdf.set_fill_color(240, 240, 240); pdf.set_font("Arial", "B", 10)
                pdf.cell(0, 8, "DADOS DA ENTREVISTA", 1, 1, 'L', 1)
                
                print_data_row("Responsável pelas informações:", data.get('entrevista_resp'))
                print_data_row("Profissional Entrevistador:", data.get('entrevista_prof'))
                print_data_row("Data da Entrevista:", str(data.get('entrevista_data', '')))
                
                pdf.ln(25) 
                
                y = pdf.get_y()
                pdf.line(20, y, 90, y); pdf.line(110, y, 190, y)
                pdf.set_font("Arial", "", 9)
                pdf.set_xy(20, y+2); pdf.cell(70, 5, "Assinatura do Responsável Legal", 0, 0, 'C')
                pdf.set_xy(110, y+2); pdf.cell(80, 5, "Assinatura do Docente/Gestor", 0, 1, 'C')

                st.session_state.pdf_bytes_caso = get_pdf_bytes(pdf)
                st.rerun()

            if 'pdf_bytes_caso' in st.session_state:
                st.download_button("📥 BAIXAR PDF ESTUDO DE CASO", st.session_state.pdf_bytes_caso, f"Caso_{data.get('nome','estudante')}.pdf", "application/pdf", type="primary")

        # --- ABA 7: HISTÓRICO ---
        with tabs[6]:
            st.subheader("Histórico de Atividades")
            st.caption("Registro de alterações, salvamentos e geração de documentos.")
            
            df_hist = safe_read("Historico", ["Data_Hora", "Aluno", "Usuario", "Acao", "Detalhes"])
            
            if not df_hist.empty and data.get('nome'):
                # Filtrar pelo aluno atual
                student_hist = df_hist[df_hist["Aluno"] == data.get('nome')]
                
                if not student_hist.empty:
                    # Ordenar por data (mais recente primeiro)
                    student_hist = student_hist.iloc[::-1]
                    st.dataframe(student_hist, use_container_width=True, hide_index=True)
                else:
                    st.info("Nenhum histórico encontrado para este aluno.")
            else:
                st.info("O histórico está vazio ou aluno não selecionado.")

    # --- PROTOCOLO DE CONDUTA ---
    elif doc_mode == "Protocolo de Conduta":
        st.markdown("""<div class="header-box"><div class="header-title">Protocolo de Conduta</div></div>""", unsafe_allow_html=True)
        st.markdown("""<style>div[data-testid="stFormSubmitButton"] > button {width: 100%; background-color: #dcfce7; color: #166534; border: 1px solid #166534;}</style>""", unsafe_allow_html=True)
        
        tabs = st.tabs(["📝 Preenchimento e Emissão", "🕒 Histórico"])
        
        data_conduta = st.session_state.data_conduta
        data_pei = st.session_state.data_pei
        
        with tabs[0]:
            with st.form("form_conduta"):
                st.subheader("Configuração do Protocolo")
                st.caption("Preencha manualmente ou utilize o botão abaixo para importar informações do PEI do aluno, convertendo-as automaticamente para a 1ª pessoa.")
                
                if st.form_submit_button("🔄 Preencher Automaticamente com dados do PEI"):
                    # Mapeamento e conversão simples para 1ª pessoa
                    if data_pei:
                        # Sobre Mim
                        defic = data_pei.get('defic_txt', '') or data_pei.get('neuro_txt', '')
                        data_conduta['conduta_sobre_mim'] = f"Olá, meu nome é {data_pei.get('nome', '')}. Tenho {data_pei.get('idade', '')} anos. Estou matriculado no {data_pei.get('ano_esc', '')} ano. {defic}"
                        
                        # Coisas que eu gosto
                        gostos = []
                        if data_pei.get('beh_interesses'): gostos.append(data_pei.get('beh_interesses'))
                        if data_pei.get('beh_objetos_gosta'): gostos.append(data_pei.get('beh_objetos_gosta'))
                        if data_pei.get('beh_atividades'): gostos.append(data_pei.get('beh_atividades'))
                        data_conduta['conduta_gosto'] = "\n".join(gostos)
                        
                        # Coisas que não gosto
                        nao_gosto = []
                        if data_pei.get('beh_objetos_odeia'): nao_gosto.append(data_pei.get('beh_objetos_odeia'))
                        if data_pei.get('beh_gatilhos'): nao_gosto.append(f"Fico chateado/nervoso quando: {data_pei.get('beh_gatilhos')}")
                        data_conduta['conduta_nao_gosto'] = "\n".join(nao_gosto)
                        
                        # Como me comunico
                        data_conduta['conduta_comunico'] = f"Eu me comunico: {data_pei.get('com_tipo', '')}. {data_pei.get('com_alt_espec', '')}"
                        
                        # Como me ajudar
                        ajuda = []
                        if data_pei.get('beh_crise_regula'): ajuda.append(f"Para me regular: {data_pei.get('beh_crise_regula')}")
                        if data_pei.get('beh_calmo'): ajuda.append(f"O que me acalma: {data_pei.get('beh_calmo')}")
                        data_conduta['conduta_ajuda'] = "\n".join(ajuda)
                        
                        # Habilidades
                        habs = []
                        if data_pei.get('hig_banheiro'): habs.append(f"Uso do banheiro: {data_pei.get('hig_banheiro')}")
                        if data_pei.get('hig_dentes'): habs.append(f"Escovação: {data_pei.get('hig_dentes')}")
                        if data_pei.get('dev_tarefas'): habs.append(f"Tarefas: {data_pei.get('dev_tarefas')}")
                        data_conduta['conduta_habilidades'] = "\n".join(habs)
                        
                        st.success("Dados importados do PEI com sucesso! Revise abaixo.")
                    else:
                        st.warning("Dados do PEI não encontrados para este aluno.")

                # Campos do Formulário
                c1, c2 = st.columns([3, 1])
                data_conduta['nome'] = c1.text_input("Nome", value=data_pei.get('nome', data_conduta.get('nome','')), disabled=True)
                
                d_val = data_conduta.get('nasc') or data_pei.get('nasc')
                if isinstance(d_val, str): 
                    try: d_val = datetime.strptime(d_val, '%Y-%m-%d').date()
                    except: d_val = date.today()
                data_conduta['nasc'] = c2.date_input("Nascimento", value=d_val if d_val else date.today(), format="DD/MM/YYYY")
                
                data_conduta['ano_esc'] = st.text_input("Ano de Escolaridade", value=data_pei.get('ano_esc', data_conduta.get('ano_esc','')))
                
                st.divider()
                
                c_g, c_s = st.columns(2)
                data_conduta['conduta_gosto'] = c_g.text_area("Coisas que eu gosto (Laranja)", value=data_conduta.get('conduta_gosto', ''), height=150)
                data_conduta['conduta_sobre_mim'] = c_s.text_area("Sobre mim (Verde)", value=data_conduta.get('conduta_sobre_mim', ''), height=150)
                
                c_ng, c_com = st.columns(2)
                data_conduta['conduta_nao_gosto'] = c_ng.text_area("Coisas que eu não gosto (Vermelho)", value=data_conduta.get('conduta_nao_gosto', ''), height=150)
                data_conduta['conduta_comunico'] = c_com.text_area("Como me comunico (Roxo)", value=data_conduta.get('conduta_comunico', ''), height=150)
                
                c_aj, c_hab = st.columns(2)
                data_conduta['conduta_ajuda'] = c_aj.text_area("Como me ajudar (Azul)", value=data_conduta.get('conduta_ajuda', ''), height=150)
                data_conduta['conduta_habilidades'] = c_hab.text_area("Habilidades / Eu posso (Amarelo)", value=data_conduta.get('conduta_habilidades', ''), height=150)

                st.markdown("---")
                c_save, c_pdf = st.columns(2)
                
                if c_save.form_submit_button("💾 Salvar Protocolo"):
                    save_student("CONDUTA", data_conduta.get('nome', 'aluno'), data_conduta, "Protocolo")
                
                if c_pdf.form_submit_button("👁️ Gerar PDF"):
                    log_action(data_conduta.get('nome'), "Gerou PDF", "Protocolo de Conduta")
                    
                    pdf = OfficialPDF('P', 'mm', 'A4')
                    pdf.add_page(); pdf.set_margins(10, 10, 10)
                    
                    # --- CABEÇALHO ---
                    if os.path.exists("logo_prefeitura.png"): pdf.image("logo_prefeitura.png", 10, 8, 20)
                    pdf.set_xy(35, 10); pdf.set_font("Arial", "", 12)
                    pdf.cell(0, 6, clean_pdf_text("Secretaria Municipal de"), 0, 1)
                    pdf.set_x(35); pdf.set_font("Arial", "B", 16)
                    pdf.cell(0, 8, clean_pdf_text("EDUCAÇÃO"), 0, 1)
                    
                    # Box Titulo
                    pdf.set_xy(130, 8)
                    pdf.set_font("Arial", "", 12)
                    pdf.cell(70, 10, "Protocolo de conduta", 1, 1, 'C')
                    
                    # --- IDENTIFICAÇÃO (FOTO E DADOS) ---
                    start_y = 35
                    
                    # FOTO (Placeholder circular visual - quadrado com label por simplicidade do FPDF)
                    pdf.set_xy(10, start_y)
                    # Tenta carregar foto do PEI se não tiver no conduta (usa mesma ref)
                    foto_b64 = data_pei.get('foto_base64')
                    if foto_b64:
                        try:
                            img_data = base64.b64decode(foto_b64)
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
                                tmp_file.write(img_data)
                                tmp_path = tmp_file.name
                            pdf.image(tmp_path, 15, start_y, 40, 50) # Imagem retangular
                            os.unlink(tmp_path)
                        except:
                            pdf.rect(15, start_y, 40, 50)
                            pdf.set_xy(15, start_y+20); pdf.set_font("Arial", "", 8); pdf.cell(40, 5, "ERRO FOTO", 0, 0, 'C')
                    else:
                        pdf.rect(15, start_y, 40, 50) # Moldura
                        pdf.set_xy(15, start_y+20); pdf.set_font("Arial", "", 8); pdf.cell(40, 5, "FOTO DO ESTUDANTE", 0, 0, 'C')
                    
                    # Campos ao lado da foto
                    pdf.set_font("Arial", "", 10)
                    
                    # Nome (Borda Vermelha)
                    pdf.set_draw_color(255, 69, 0) # Red
                    pdf.set_line_width(0.5)
                    pdf.set_xy(70, start_y)
                    pdf.cell(130, 8, clean_pdf_text(f"Meu nome: {data_conduta.get('nome','')}"), 1, 1, 'L')
                    
                    # Data Nasc (Borda Azul)
                    pdf.set_draw_color(0, 191, 255) # Cyan/Blue
                    pdf.set_xy(70, start_y + 12)
                    pdf.multi_cell(40, 6, clean_pdf_text(f"Data de\nNascimento:\n{str(data_conduta.get('nasc',''))}"), 1, 'C')
                    
                    # Ano escolar (Borda Rosa)
                    pdf.set_draw_color(255, 105, 180) # Pink
                    pdf.set_xy(115, start_y + 12)
                    pdf.multi_cell(50, 9, clean_pdf_text(f"Ano de escolaridade:\n{data_conduta.get('ano_esc','')}") , 1, 'C')
                    
                    # --- CAIXAS DE CONTEÚDO ---
                    
                    # Função auxiliar para desenhar caixas coloridas
                    def draw_colored_box(x, y, w, h, r, g, b, title, content):
                        pdf.set_draw_color(r, g, b)
                        pdf.set_line_width(0.8)
                        pdf.rect(x, y, w, h)
                        
                        pdf.set_xy(x, y+2)
                        pdf.set_text_color(0, 0, 0)
                        pdf.set_font("Arial", "B", 10)
                        pdf.cell(w, 5, clean_pdf_text(title), 0, 1, 'C')
                        
                        pdf.set_xy(x+2, y+8)
                        pdf.set_font("Arial", "", 9)
                        pdf.multi_cell(w-4, 5, clean_pdf_text(content), 0, 'L')

                    # Sobre Mim (Verde) - Lado Direito
                    draw_colored_box(100, 70, 100, 35, 154, 205, 50, "Sobre mim", data_conduta.get('conduta_sobre_mim', ''))
                    
                    # Coisas que eu gosto (Laranja) - Lado Esquerdo
                    draw_colored_box(10, 100, 85, 50, 255, 165, 0, "Coisas que eu gosto", data_conduta.get('conduta_gosto', ''))
                    
                    # Coisas que eu não gosto (Vermelho) - Lado Direito
                    draw_colored_box(130, 115, 70, 60, 255, 69, 0, "Coisas que eu não gosto", data_conduta.get('conduta_nao_gosto', ''))
                    
                    # Como me comunico (Roxo) - Lado Esquerdo
                    draw_colored_box(10, 160, 110, 40, 147, 112, 219, "Como me comunico", data_conduta.get('conduta_comunico', ''))
                    
                    # Como me ajudar (Azul) - Lado Esquerdo Inferior
                    draw_colored_box(10, 210, 110, 60, 0, 191, 255, "Como me ajudar", data_conduta.get('conduta_ajuda', ''))
                    
                    # Habilidades (Amarelo) - Lado Direito Inferior
                    draw_colored_box(130, 190, 70, 80, 255, 215, 0, "Habilidades (eu posso...)", data_conduta.get('conduta_habilidades', ''))

                    st.session_state.pdf_bytes_conduta = get_pdf_bytes(pdf)
                    st.rerun()

            if 'pdf_bytes_conduta' in st.session_state:
                st.download_button("📥 BAIXAR PROTOCOLO PDF", st.session_state.pdf_bytes_conduta, f"Conduta_{data_conduta.get('nome','aluno')}.pdf", "application/pdf", type="primary")

        # --- ABA 7: HISTÓRICO ---
        with tabs[1]:
            st.subheader("Histórico de Atividades")
            st.caption("Registro de alterações, salvamentos e geração de documentos.")
            
            df_hist = safe_read("Historico", ["Data_Hora", "Aluno", "Usuario", "Acao", "Detalhes"])
            
            if not df_hist.empty and data.get('nome'):
                # Filtrar pelo aluno atual
                student_hist = df_hist[df_hist["Aluno"] == data.get('nome')]
                
                if not student_hist.empty:
                    # Ordenar por data (mais recente primeiro)
                    student_hist = student_hist.iloc[::-1]
                    st.dataframe(student_hist, use_container_width=True, hide_index=True)
                else:
                    st.info("Nenhum histórico encontrado para este aluno.")
            else:
                st.info("O histórico está vazio ou aluno não selecionado.")


    # --- AVALIAÇÃO PEDAGÓGICA ---
    elif doc_mode == "Avaliação Pedagógica":
        st.markdown("""<div class="header-box"><div class="header-title">Avaliação Pedagógica: Apoio Escolar</div></div>""", unsafe_allow_html=True)
        st.markdown("""<style>div[data-testid="stFormSubmitButton"] > button {width: 100%; background-color: #dcfce7; color: #166534; border: 1px solid #166534;}</style>""", unsafe_allow_html=True)
        
        tabs = st.tabs(["📝 Preenchimento e Emissão", "🕒 Histórico"])
        
        # Inicialização de variáveis de estado se não existirem
        if 'data_avaliacao' not in st.session_state: st.session_state.data_avaliacao = {}
        if 'data_pei' not in st.session_state: st.session_state.data_pei = {}
        if 'data_case' not in st.session_state: st.session_state.data_case = {}
        
        data_aval = st.session_state.data_avaliacao
        data_pei = st.session_state.data_pei
        data_caso = st.session_state.data_case
        
        # --- DEFINIÇÃO DAS LISTAS DE OPÇÕES (GLOBAL PARA O CONTEXTO) ---
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
        
        opts_at_sust = [
            "Mantém atenção por longo período de tempo.",
            "Mantém atenção por longo período de tempo com apoio.",
            "Não mantém atenção por longo período de tempo."
        ]
        
        opts_at_div = [
            "Mantém atenção em dois estímulos diferentes.",
            "Mantém atenção em dois estímulos diferentes em algumas situações.",
            "Não mantém atenção em dois estímulos differentes."
        ]
        
        opts_at_sel = [
            "Mantém atenção na tarefa ignorando estímulos externos.",
            "Mantém atenção na tarefa ignorando estímulos externos com apoio.",
            "Não mantém atenção na tarefa com a presença de outros"
        ]
        
        opts_ling = [
            "Faz uso de palavras para se comunicar, expressando seus pensamentos e desejos.",
            "Faz uso de palavras para se comunicar, apresentando trocas fonéticas orais.",
            "Utiliza palavras e frases desconexas, não conseguindo se expressar.",
            "Não faz uso de palavras para se comunicar, expressando seus desejos por meio de gestos e comportamentos",
            "Não faz uso de palavras e de gestos para se comunicar."
        ]

        with tabs[0]:
            with st.form("form_avaliacao"):
                st.subheader("Configuração da Avaliação")
                st.caption("Utilize o botão abaixo para importar informações já preenchidas no PEI e Estudo de Caso.")
                
                if st.form_submit_button("🔄 Preencher Automaticamente"):
                    if data_pei or data_caso:
                        data_aval['nome'] = data_pei.get('nome') or data_caso.get('nome', '')
                        data_aval['nasc'] = data_pei.get('nasc') or data_caso.get('d_nasc', '')
                        data_aval['ano_esc'] = data_pei.get('ano_esc') or data_caso.get('ano_esc', '')
                        data_aval['defic_chk'] = data_pei.get('diag_tipo', [])
                        
                        aspectos = []
                        if data_pei.get('prof_poli'): aspectos.append(f"Polivalente: {data_pei.get('prof_poli')}")
                        if data_pei.get('prof_aee'): aspectos.append(f"AEE: {data_pei.get('prof_aee')}")
                        if data_pei.get('flex_matrix'): aspectos.append("Possui flexibilização curricular registrada no PEI.")
                        data_aval['aspectos_gerais'] = "\n".join(aspectos)
                        
                        if data_pei.get('beh_autonomia_agua') == 'Sim': data_aval['alim_nivel'] = opts_alim[0]
                        if data_pei.get('hig_banheiro') == 'Sim': data_aval['hig_nivel'] = opts_hig[0]
                        if data_pei.get('loc_reduzida') == 'Não': data_aval['loc_nivel'] = [opts_loc[0]]
                        
                        st.success("Dados importados com sucesso!")
                    else:
                        st.warning("Sem dados prévios para importar.")

                # --- CAMPOS DO FORMULÁRIO ---
                st.markdown("### Identificação")
                c_nom, c_ano = st.columns([3, 1])
                data_aval['nome'] = c_nom.text_input("Estudante", value=data_aval.get('nome', ''), disabled=True)
                data_aval['ano_esc'] = c_ano.text_input("Ano Escolaridade", value=data_aval.get('ano_esc', ''))
                
                st.markdown("**Deficiências (Marque as opções):**")
                data_aval['defic_chk'] = st.multiselect("Selecione:", defs_opts, default=data_aval.get('defic_chk', []))
                data_aval['defic_outra'] = st.text_input("Outra:", value=data_aval.get('defic_outra', ''))
                
                st.markdown("---")
                st.markdown("### Aspectos Gerais da Vida Escolar")
                data_aval['aspectos_gerais'] = st.text_area("Relatar data matrícula, plano atendimento, docentes, AEE, PDI...", value=data_aval.get('aspectos_gerais', ''), height=100)
                
                with st.expander("Parte I - Habilidades de Vida Diária", expanded=True):
                    c_a, c_h = st.columns(2)
                    with c_a:
                        st.markdown("**1. Alimentação**")
                        idx_alim = opts_alim.index(data_aval.get('alim_nivel')) if data_aval.get('alim_nivel') in opts_alim else 0
                        data_aval['alim_nivel'] = st.radio("Nível Alimentação", opts_alim, index=idx_alim, key="rad_alim")
                        data_aval['alim_obs'] = st.text_input("Obs Alimentação:", value=data_aval.get('alim_obs', ''))
                    
                    with c_h:
                        st.markdown("**2. Higiene**")
                        idx_hig = opts_hig.index(data_aval.get('hig_nivel')) if data_aval.get('hig_nivel') in opts_hig else 0
                        data_aval['hig_nivel'] = st.radio("Nível Higiene", opts_hig, index=idx_hig, key="rad_hig")
                        data_aval['hig_obs'] = st.text_input("Obs Higiene:", value=data_aval.get('hig_obs', ''))
                    
                    st.markdown("**3. Locomoção (Selecione todos que se aplicam)**")
                    data_aval['loc_nivel'] = st.multiselect("Itens:", opts_loc, default=data_aval.get('loc_nivel', []))
                    data_aval['loc_obs'] = st.text_input("Obs Locomoção:", value=data_aval.get('loc_obs', ''))

                with st.expander("Parte II - Habilidades Sociais e de Interação"):
                    st.markdown("**4. Comportamento**")
                    idx_comp = opts_comp.index(data_aval.get('comportamento')) if data_aval.get('comportamento') in opts_comp else 0
                    data_aval['comportamento'] = st.radio("Nível Comportamento", opts_comp, index=idx_comp)
                    data_aval['comp_obs'] = st.text_input("Obs Comportamento:", value=data_aval.get('comp_obs', ''))
                    
                    st.divider()
                    st.markdown("**5. Participação em Grupo**")
                    idx_part = opts_part.index(data_aval.get('part_grupo')) if data_aval.get('part_grupo') in opts_part else 0
                    data_aval['part_grupo'] = st.radio("Nível Participação", opts_part, index=idx_part)
                    data_aval['part_obs'] = st.text_input("Obs Participação:", value=data_aval.get('part_obs', ''))
                    
                    st.divider()
                    st.markdown("**6. Interação**")
                    idx_int = opts_int.index(data_aval.get('interacao')) if data_aval.get('interacao') in opts_int else 0
                    data_aval['interacao'] = st.radio("Nível Interação", opts_int, index=idx_int)
                    if data_aval['interacao'] == "Outros":
                        data_aval['interacao_outros'] = st.text_input("Especifique (Interação):", value=data_aval.get('interacao_outros', ''))

                with st.expander("Parte III - Habilidades Pedagógicas"):
                    st.markdown("**7. Rotina Sala de Aula**")
                    idx_rot = opts_rot.index(data_aval.get('rotina')) if data_aval.get('rotina') in opts_rot else 0
                    data_aval['rotina'] = st.radio("Nível Rotina", opts_rot, index=idx_rot)
                    data_aval['rotina_obs'] = st.text_input("Obs Rotina:", value=data_aval.get('rotina_obs', ''))
                    
                    st.divider()
                    st.markdown("**8. Atividades Pedagógicas**")
                    idx_ativ = opts_ativ.index(data_aval.get('ativ_pedag')) if data_aval.get('ativ_pedag') in opts_ativ else 0
                    data_aval['ativ_pedag'] = st.radio("Nível Atividades", opts_ativ, index=idx_ativ)

                with st.expander("Parte IV - Habilidades de Comunicação e Atenção"):
                    c_com1, c_com2 = st.columns(2)
                    with c_com1:
                        st.markdown("**9. Atenção Sustentada**")
                        idx_as = opts_at_sust.index(data_aval.get('atencao_sust')) if data_aval.get('atencao_sust') in opts_at_sust else 0
                        data_aval['atencao_sust'] = st.radio("Sustentada", opts_at_sust, index=idx_as, key="at_sust")
                        
                        st.markdown("**11. Atenção Seletiva**")
                        idx_asel = opts_at_sel.index(data_aval.get('atencao_sel')) if data_aval.get('atencao_sel') in opts_at_sel else 0
                        data_aval['atencao_sel'] = st.radio("Seletiva", opts_at_sel, index=idx_asel, key="at_sel")
                    
                    with c_com2:
                        st.markdown("**10. Atenção Dividida**")
                        idx_ad = opts_at_div.index(data_aval.get('atencao_div')) if data_aval.get('atencao_div') in opts_at_div else 0
                        data_aval['atencao_div'] = st.radio("Dividida", opts_at_div, index=idx_ad, key="at_div")
                    
                    st.divider()
                    st.markdown("**12. Linguagem (Marque todas que se aplicam)**")
                    data_aval['linguagem'] = st.multiselect("Linguagem:", opts_ling, default=data_aval.get('linguagem', []))
                    data_aval['ling_obs'] = st.text_input("Obs Linguagem:", value=data_aval.get('ling_obs', ''))

                st.markdown("### Conclusão e Responsáveis")
                data_aval['conclusao_nivel'] = st.selectbox("Nível de Apoio Concluído", ["Não necessita de apoio", "Nível 1", "Nível 2", "Nível 3"], index=0)
                data_aval['apoio_existente'] = st.text_input("Se este apoio já é oferecido, explicitar aqui:", value=data_aval.get('apoio_existente', ''))
                
                c_resp1, c_resp2 = st.columns(2)
                data_aval['resp_sala'] = c_resp1.text_input("Prof. Sala Regular", value=data_aval.get('resp_sala', ''))
                data_aval['resp_arte'] = c_resp2.text_input("Prof. Arte", value=data_aval.get('resp_arte', ''))
                data_aval['resp_ef'] = c_resp1.text_input("Prof. Ed. Física", value=data_aval.get('resp_ef', ''))
                data_aval['resp_ee'] = c_resp2.text_input("Prof. Ed. Especial", value=data_aval.get('resp_ee', ''))
                data_aval['resp_dir'] = c_resp1.text_input("Direção Escolar", value=data_aval.get('resp_dir', ''))
                data_aval['resp_coord'] = c_resp2.text_input("Coordenação", value=data_aval.get('resp_coord', ''))
                
                data_aval['data_emissao'] = st.date_input("Data Emissão", value=date.today(), format="DD/MM/YYYY")

                st.markdown("---")
                c_sv, c_pd = st.columns(2)
                if c_sv.form_submit_button("💾 Salvar Avaliação"):
                    save_student("AVALIACAO", data_aval.get('nome', 'aluno'), data_aval, "Avaliação")
                
                if c_pd.form_submit_button("👁️ Gerar PDF Avaliação"):
                    # --- PDF GENERATION EXPERT MODE ---
                    pdf = OfficialPDF('P', 'mm', 'A4')
                    pdf.add_page(); pdf.set_margins(15, 15, 15)
                    
                    # 1. HEADER (FIXED CEIEF RAFAEL AFFONSO LEITE)
                    if os.path.exists("logo_prefeitura.png"): pdf.image("logo_prefeitura.png", 15, 10, 25)
                    if os.path.exists("logo_escola.png"): pdf.image("logo_escola.png", 170, 6, 25)

                    pdf.set_xy(0, 15); pdf.set_font("Arial", "B", 12)
                    pdf.cell(210, 6, clean_pdf_text("PREFEITURA MUNICIPAL DE LIMEIRA"), 0, 1, 'C')
                    pdf.cell(180, 6, clean_pdf_text("CEIEF RAFAEL AFFONSO LEITE"), 0, 1, 'C')
                    pdf.ln(8)
                    pdf.set_font("Arial", "B", 12); pdf.cell(0, 10, clean_pdf_text("AVALIAÇÃO PEDAGÓGICA: APOIO ESCOLAR PARA ESTUDANTE COM DEFICIÊNCIA"), 0, 1, 'C')
                    pdf.ln(5)
                    
                    # 2. IDENTIFICATION
                    pdf.set_font("Arial", "B", 10); pdf.cell(20, 6, "Estudante:", 0, 0)
                    pdf.set_font("Arial", "", 10); pdf.cell(100, 6, clean_pdf_text(data_aval.get('nome', '')), "B", 0)
                    pdf.set_font("Arial", "B", 10); pdf.cell(35, 6, "Ano escolaridade:", 0, 0)
                    pdf.set_font("Arial", "", 10); pdf.cell(0, 6, clean_pdf_text(data_aval.get('ano_esc', '')), "B", 1)
                    pdf.ln(4)
                    
                    # 3. DEFICIENCIES
                    pdf.set_font("Arial", "", 9)
                    selected_defs = data_aval.get('defic_chk', [])
                    
                    def draw_check_option_simple(pdf, text, checked):
                        pdf.set_x(15) 
                        x, y = pdf.get_x(), pdf.get_y()
                        pdf.set_draw_color(0,0,0)
                        pdf.rect(x, y + 1, 3, 3)
                        if checked:
                            pdf.line(x, y + 1, x + 3, y + 4)
                            pdf.line(x, y + 4, x + 3, y + 1)
                        pdf.set_xy(x + 5, y)
                        # Width 175 ensures it ends at 15+5+175 = 195 (Right margin boundary)
                        pdf.multi_cell(175, 5, clean_pdf_text(text), 0, 'L')

                    if selected_defs:
                        for d in selected_defs:
                            draw_check_option_simple(pdf, d, True)
                        if data_aval.get('defic_outra'):
                            draw_check_option_simple(pdf, f"Outra: {data_aval.get('defic_outra')}", True)
                    else:
                        pdf.cell(0, 5, clean_pdf_text("Nenhuma deficiência selecionada."), 0, 1)
                    pdf.ln(3)
                    
                    # 4. LEGAL TEXT (INTEGRAL) - Justified
                    pdf.set_font("Arial", "B", 10)
                    pdf.cell(0, 6, clean_pdf_text("PRESSUPOSTOS LEGAIS:"), 0, 1, 'L')
                    pdf.set_font("Arial", "", 8)
                    
                    # Full width (0) uses 180mm. 
                    pdf.multi_cell(0, 4, clean_pdf_text("1- Lei nº 12.764/2012, em seu artigo 3º que trata dos direitos da pessoa com transtorno do espectro autista indica:"), 0, 'J')
                    
                    pdf.set_x(25)
                    # Indent 25 (10 more than margin). Max width to right margin (195): 195 - 25 = 170.
                    pdf.multi_cell(170, 4, clean_pdf_text("Parágrafo único. Em casos de comprovada necessidade, a pessoa com transtorno do espectro autista incluída nas classes comuns de ensino regular, nos termos do inciso IV do art. 2º, terá direito a acompanhante especializado."), 0, 'J')
                    pdf.ln(2)

                    pdf.multi_cell(0, 4, clean_pdf_text("2- Lei Brasileira de Inclusão da Pessoa com Deficiência (LBI) no art. 3º, inciso XIII, descreve as ações referentes ao apoio:"), 0, 'J')
                    
                    pdf.set_x(25)
                    pdf.multi_cell(170, 4, clean_pdf_text("XIII - profissional de apoio escolar: pessoa que exerce atividades de alimentação, higiene e locomoção do estudante com deficiência e atua em todas as atividades escolares nas quais se fizer necessária, em todos os níveis e modalidades de ensino, em instituições públicas e privadas, excluídas as técnicas ou os procedimentos identificados com profissões legalmente estabelecidas;"), 0, 'J')
                    pdf.ln(2)

                    pdf.multi_cell(0, 4, clean_pdf_text("3- CNE/CEB nº 02/01, do Conselho Nacional de Educação, que Instituiu as Diretrizes Nacionais para a Educação Especial na Educação Básica, cujo artigo 6º assim dispõe:"), 0, 'J')
                    
                    pdf.set_x(25)
                    pdf.multi_cell(170, 4, clean_pdf_text("Art. 6º Para a identificação das necessidades educacionais especiais dos alunos e a tomada de decisões quanto ao atendimento necessário, a escola deve realizar, com assessoramento técnico, avaliação do aluno no processo de ensino e aprendizagem, contando, para tal, com:"), 0, 'J')
                    
                    pdf.set_x(35)
                    # Indent 35. Max width to right margin (195): 195 - 35 = 160.
                    pdf.multi_cell(160, 4, clean_pdf_text("I - a experiência de seu corpo docente, seus diretores, coordenadores, orientadores e supervisores educacionais;\nII - o setor responsável pela educação especial do respectivo sistema;\nIII - a colaboração da família e a cooperação dos serviços de Saúde, Assistência Social, Trabalho, Justiça e Esporte, bem como do Ministério Público, quando necessário."), 0, 'J')
                    pdf.ln(4)

                    # 5. GENERAL ASPECTS
                    pdf.set_fill_color(240, 240, 240)
                    pdf.set_font("Arial", "B", 10)
                    pdf.cell(0, 7, clean_pdf_text("ASPECTOS GERAIS DA VIDA ESCOLAR DO ESTUDANTE"), 1, 1, 'L', True)
                    pdf.set_font("Arial", "", 10); pdf.set_fill_color(255, 255, 255)
                    text_general = data_aval.get('aspectos_gerais') if data_aval.get('aspectos_gerais') else " "
                    # Use 0 for auto width (margin to margin), Justified 'J'
                    pdf.multi_cell(0, 5, clean_pdf_text(text_general), 1, 'J')
                    pdf.ln(5)

                    def print_section_header_fix(pdf, title):
                        pdf.set_fill_color(240, 240, 240); pdf.set_font("Arial", "B", 10)
                        pdf.cell(0, 8, clean_pdf_text(title), 1, 1, 'L', True)
                        pdf.ln(1)

                    def print_question_options_fix(pdf, question_title, options, selected_value, obs=None):
                        pdf.set_x(15)
                        pdf.set_font("Arial", "B", 10)
                        pdf.cell(0, 6, clean_pdf_text(question_title), 0, 1)
                        pdf.set_font("Arial", "", 10)
                        for opt in options:
                            is_checked = (selected_value == opt) or (isinstance(selected_value, list) and opt in selected_value)
                            pdf.set_x(15)
                            x, y = pdf.get_x(), pdf.get_y()
                            pdf.rect(x, y+1, 3, 3)
                            if is_checked:
                                pdf.line(x, y+1, x+3, y+4)
                                pdf.line(x, y+4, x+3, y+1)
                            pdf.set_xy(x + 5, y)
                            pdf.multi_cell(175, 5, clean_pdf_text(opt), 0, 'L')
                        if obs:
                            pdf.set_x(15)
                            # Obs uses full width (0) and Justified (J)
                            pdf.multi_cell(0, 5, clean_pdf_text(f"Obs: {obs}"), 0, 'J')
                        pdf.ln(2)

                    # PART I
                    print_section_header_fix(pdf, "PARTE I - HABILIDADES DE VIDA DIÁRIA")
                    print_question_options_fix(pdf, "1. ALIMENTAÇÃO:", opts_alim, data_aval.get('alim_nivel'), data_aval.get('alim_obs'))
                    print_question_options_fix(pdf, "2. HIGIENE:", opts_hig, data_aval.get('hig_nivel'), data_aval.get('hig_obs'))
                    print_question_options_fix(pdf, "3. LOCOMOÇÃO:", opts_loc, data_aval.get('loc_nivel'), data_aval.get('loc_obs'))
                    
                    # PART II
                    if pdf.get_y() > 220: pdf.add_page()
                    print_section_header_fix(pdf, "PARTE II - HABILIDADE SOCIAIS E DE INTERAÇÃO")
                    print_question_options_fix(pdf, "4. COMPORTAMENTO:", opts_comp, data_aval.get('comportamento'), data_aval.get('comp_obs'))
                    if pdf.get_y() > 230: pdf.add_page()
                    print_question_options_fix(pdf, "5. PARTICIPAÇÃO EM GRUPO:", opts_part, data_aval.get('part_grupo'), data_aval.get('part_obs'))
                    
                    pdf.set_font("Arial", "B", 10); pdf.cell(0, 6, "6. INTERAÇÃO:", 0, 1)
                    pdf.set_font("Arial", "", 10)
                    for opt in opts_int[:-1]:
                        draw_check_option_simple(pdf, opt, data_aval.get('interacao') == opt)
                    is_outros = (data_aval.get('interacao') == "Outros")
                    txt_outros = f"Outros: {data_aval.get('interacao_outros') if data_aval.get('interacao_outros') else '____________________'}"
                    draw_check_option_simple(pdf, txt_outros, is_outros)
                    pdf.ln(4)

                    # PART III
                    if pdf.get_y() > 230: pdf.add_page()
                    print_section_header_fix(pdf, "PARTE III - HABILIDADES PEDAGÓGICAS")
                    print_question_options_fix(pdf, "7. ROTINA EM SALA:", opts_rot, data_aval.get('rotina'), data_aval.get('rotina_obs'))
                    print_question_options_fix(pdf, "8. ATIVIDADES PEDAGÓGICAS:", opts_ativ, data_aval.get('ativ_pedag'))

                    # PART IV
                    if pdf.get_y() > 220: pdf.add_page()
                    print_section_header_fix(pdf, "PARTE IV - HABILIDADES DE COMUNICAÇÃO E ATENÇÃO")
                    print_question_options_fix(pdf, "9. ATENÇÃO SUSTENTADA:", opts_at_sust, data_aval.get('atencao_sust'))
                    print_question_options_fix(pdf, "10. ATENÇÃO DIVIDIDA:", opts_at_div, data_aval.get('atencao_div'))
                    if pdf.get_y() > 240: pdf.add_page()
                    print_question_options_fix(pdf, "11. ATENÇÃO SELETIVA:", opts_at_sel, data_aval.get('atencao_sel'))
                    print_question_options_fix(pdf, "12. LINGUAGEM:", opts_ling, data_aval.get('linguagem'), data_aval.get('ling_obs'))

                    # 6. ZEBRA STRIPED TABLE - IMPROVED
                    if pdf.get_y() > 200: pdf.add_page()
                    pdf.ln(2); pdf.set_font("Arial", "B", 10)
                    pdf.set_fill_color(200, 200, 200)
                    # Use width 180 total (60+120)
                    pdf.cell(60, 8, clean_pdf_text("NÍVEIS DE APOIO"), 1, 0, 'C', True)
                    pdf.cell(120, 8, clean_pdf_text("CARACTERÍSTICAS"), 1, 1, 'C', True)
                    
                    def print_zebra_row_fix(pdf, col1, col2, fill):
                        # Approximate line counting for better cell height
                        # Col1 width 60mm. approx 28 chars per line (Arial 9).
                        # Col2 width 120mm. approx 65 chars per line (Arial 9).
                        
                        lines_left = max(1, len(col1) // 28 + (1 if len(col1) % 28 > 0 else 0))
                        lines_right = max(1, len(col2) // 65 + (1 if len(col2) % 65 > 0 else 0))
                        
                        # Adjust for known texts to ensure clean look
                        if "Não há necessidade" in col1: lines_right = 3
                        if "Nível 1" in col1: lines_right = 2
                        if "Nível 2" in col1: lines_left = 2; lines_right = 1
                        if "Nível 3" in col1: lines_right = 2

                        max_lines = max(lines_left, lines_right)
                        row_height = max_lines * 5 + 4 # 5mm per line + 4mm padding
                        
                        x, y = 15, pdf.get_y()
                        # Check page break
                        if y + row_height > 270:
                            pdf.add_page()
                            y = pdf.get_y()
                        
                        pdf.set_fill_color(240, 240, 240) if fill else pdf.set_fill_color(255, 255, 255)
                        
                        # Draw Backgrounds
                        pdf.rect(x, y, 60, row_height, 'F'); pdf.rect(x, y, 60, row_height)
                        pdf.rect(x+60, y, 120, row_height, 'F'); pdf.rect(x+60, y, 120, row_height)
                        
                        # Print Left (Centered Vertically and Horizontally)
                        pdf.set_font("Arial", "B", 9)
                        y_off1 = (row_height - (lines_left * 5)) / 2
                        pdf.set_xy(x, y + y_off1)
                        pdf.multi_cell(60, 5, clean_pdf_text(col1), 0, 'C')
                        
                        # Print Right (Centered Vertically, Justified)
                        pdf.set_font("Arial", "", 9)
                        y_off2 = (row_height - (lines_right * 5)) / 2
                        pdf.set_xy(x+60, y + y_off2)
                        pdf.multi_cell(120, 5, clean_pdf_text(col2), 0, 'J')
                        
                        pdf.set_xy(x, y + row_height)

                    print_zebra_row_fix(pdf, "Não há necessidade de apoio", "O estudante apresenta autonomia. As ações disponibilizadas aos demais estudantes são suficientes, acrescidas de ações do AEE.", False)
                    print_zebra_row_fix(pdf, "Nível 1 - Apoio pouco substancial", "Não há necessidade de apoio constante, apenas em ações pontuais.", True)
                    print_zebra_row_fix(pdf, "Nível 2 - Apoio substancial (sala de aula)", "Há necessidade de apoio constante ao estudante.", False)
                    print_zebra_row_fix(pdf, "Nível 3 - Apoio muito substancial", "Casos severos com necessidade de monitor e ações específicas: flexibilização de horário e espaços.", True)

                    pdf.ln(5)
                    pdf.set_font("Arial", "B", 11); pdf.cell(0, 8, clean_pdf_text("CONCLUSÃO DA EQUIPE PEDAGÓGICA"), 0, 1)
                    pdf.set_font("Arial", "", 10)
                    pdf.multi_cell(0, 5, clean_pdf_text("Diante dos aspectos avaliados, a equipe pedagógica verificou que o estudante corresponde ao Nível:"), 0, 'L')
                    
                    level_result = data_aval.get('conclusao_nivel', 'NÃO NECESSITA DE APOIO').upper()
                    pdf.set_font("Arial", "B", 12); pdf.ln(2); pdf.cell(0, 8, clean_pdf_text(level_result), 1, 1, 'C')
                    
                    pdf.ln(3); pdf.set_font("Arial", "", 10)
                    apoio_txt = data_aval.get('apoio_existente') if data_aval.get('apoio_existente') else "______________________________________________________"
                    pdf.multi_cell(0, 5, clean_pdf_text(f"Profissional de Apoio Escolar (se houver): {apoio_txt}"), 0, 'L')

                    pdf.ln(10)
                    if pdf.get_y() > 240: pdf.add_page()
                    pdf.set_font("Arial", "B", 10); pdf.cell(0, 6, clean_pdf_text("Responsáveis pela avaliação:"), 0, 1); pdf.ln(5)
                    
                    # Signatures formatted with Name on one line, Role below
                    def draw_signature_block(pdf, x, y, width, name, role):
                        pdf.line(x, y, x + width, y)
                        pdf.set_xy(x, y + 2)
                        pdf.set_font("Arial", "", 9)
                        pdf.multi_cell(width, 4, clean_pdf_text(name), 0, 'C')
                        pdf.set_xy(x, pdf.get_y())
                        pdf.set_font("Arial", "I", 8)
                        pdf.multi_cell(width, 4, clean_pdf_text(role), 0, 'C')

                    y_sig_1 = pdf.get_y()
                    draw_signature_block(pdf, 10, y_sig_1, 55, data_aval.get('resp_sala',''), "Prof. Sala Regular")
                    draw_signature_block(pdf, 75, y_sig_1, 55, data_aval.get('resp_ef',''), "Prof. Ed. Física")
                    draw_signature_block(pdf, 140, y_sig_1, 55, data_aval.get('resp_arte',''), "Prof. Arte")
                    
                    # Add space for next row
                    pdf.set_xy(10, y_sig_1 + 25)
                    y_sig_2 = pdf.get_y()
                    
                    draw_signature_block(pdf, 10, y_sig_2, 55, data_aval.get('resp_dir',''), "Equipe Gestora")
                    draw_signature_block(pdf, 75, y_sig_2, 55, data_aval.get('resp_ee',''), "Prof. Ed. Especial")
                    draw_signature_block(pdf, 140, y_sig_2, 55, data_aval.get('resp_coord',''), "Coordenação")
                    
                    pdf.ln(25); pdf.set_font("Arial", "", 10)
                    # Left aligned date ('L')
                    pdf.cell(0, 6, clean_pdf_text(f"Limeira, {data_aval.get('data_emissao', date.today()).strftime('%d/%m/%Y')}."), 0, 1, 'L')

                    st.session_state.pdf_bytes_aval = get_pdf_bytes(pdf)
                    st.rerun()

            if 'pdf_bytes_aval' in st.session_state:
                st.download_button("📥 BAIXAR PDF AVALIAÇÃO", st.session_state.pdf_bytes_aval, f"Avaliacao_{data_aval.get('nome','aluno')}.pdf", "application/pdf", type="primary")

        # --- ABA HISTÓRICO ---
        with tabs[1]:
            st.subheader("Histórico de Atividades")
            df_hist = safe_read("Historico", ["Data_Hora", "Aluno", "Usuario", "Acao", "Detalhes"])
            if not df_hist.empty and data_aval.get('nome'):
                student_hist = df_hist[df_hist["Aluno"] == data_aval.get('nome')]
                if not student_hist.empty:
                    st.dataframe(student_hist.iloc[::-1], use_container_width=True, hide_index=True)
                else: st.info("Sem histórico.")
            else: st.info("Histórico vazio.")
            
     # --- RELATÓRIO DIÁRIO ---
    elif doc_mode == "Relatório Diário":
        st.markdown("""<div class="header-box"><div class="header-title">Relatório Diário de Acompanhamento</div></div>""", unsafe_allow_html=True)
        st.markdown("""<style>div[data-testid="stFormSubmitButton"] > button {width: 100%; background-color: #dcfce7; color: #166534; border: 1px solid #166534;}</style>""", unsafe_allow_html=True)
        
        # Inicializa se não existir
        if 'data_diario' not in st.session_state: st.session_state.data_diario = {}
        data_diario = st.session_state.data_diario
        if 'logs' not in data_diario: data_diario['logs'] = {}
        
        data_pei = st.session_state.data_pei # Para puxar dados automáticos
        
        tab_fill, tab_gen = st.tabs(["📝 Registro de Atividades", "🖨️ Emissão Mensal"])
        
        with tab_fill:
            with st.form("form_diario_registro"):
                st.subheader("1. Dados Gerais (Configuração)")
                st.caption("Estes dados serão usados no cabeçalho do relatório.")
                
                # Importar dados básicos
                if st.form_submit_button("🔄 Importar Dados do Aluno"):
                    if data_pei:
                        data_diario['nome'] = data_pei.get('nome', '')
                        data_diario['ano_esc'] = data_pei.get('ano_esc', '')
                        data_diario['escola'] = "CEIEF Rafael Affonso Leite"
                        st.success("Dados importados!")
                    else:
                        st.warning("Sem dados PEI para importar.")

                c1, c2 = st.columns(2)
                data_diario['escola'] = c1.text_input("Escola", value=data_diario.get('escola', 'CEIEF Rafael Affonso Leite'))
                data_diario['nome'] = c2.text_input("Estudante", value=data_diario.get('nome', data_pei.get('nome','')), disabled=True)
                
                c3, c4 = st.columns(2)
                data_diario['ano_esc'] = c3.text_input("Ano de Escolaridade", value=data_diario.get('ano_esc', data_pei.get('ano_esc','')))
                data_diario['periodo'] = c4.selectbox("Período", ["Manhã", "Tarde", "Integral"], index=0 if data_diario.get('periodo') == "Manhã" else (1 if data_diario.get('periodo') == "Tarde" else 2))
                
                data_diario['acompanhante'] = st.text_input("Acompanhante (Profissional)", value=data_diario.get('acompanhante', st.session_state.get('usuario_nome','')))
                
                st.divider()
                st.subheader("2. Registro do Dia")
                
                # Seleção da Data para Registro
                col_d_sel, col_info = st.columns([1, 2])
                data_selecionada = col_d_sel.date_input("Selecione a Data", value=date.today(), format="DD/MM/YYYY")
                data_str = data_selecionada.strftime("%Y-%m-%d")
                
                # Recuperar dados existentes para esta data
                log_atual = data_diario['logs'].get(data_str, {})
                
                # Checkbox Falta
                falta_val = log_atual.get('falta', False)
                falta = st.checkbox("Estudante Faltou?", value=falta_val)
                
                # Descrição
                desc_val = log_atual.get('descricao', '')
                descricao = st.text_area("Descrição das atividades realizadas:", value=desc_val, height=150, help="Descreva as atividades ou ocorrências deste dia.")
                
                st.markdown("---")
                # Botão de Salvar
                if st.form_submit_button("💾 Salvar Registro do Dia"):
                    # Atualiza o log no dicionário
                    data_diario['logs'][data_str] = {
                        'falta': falta,
                        'descricao': descricao
                    }
                    # Salva no banco de dados (persistência)
                    save_student("DIARIO", data_diario.get('nome', 'aluno'), data_diario, f"Diário {data_selecionada.strftime('%d/%m')}")
                    st.success(f"Registro de {data_selecionada.strftime('%d/%m/%Y')} salvo com sucesso!")
                    time.sleep(1)
                    st.rerun()

            # Visualização rápida dos últimos registros
            if data_diario['logs']:
                st.divider()
                st.markdown("##### 📅 Registros Recentes")
                # Converter para DF para mostrar
                lista_logs = []
                for d, info in data_diario['logs'].items():
                    lista_logs.append({
                        "Data": datetime.strptime(d, "%Y-%m-%d").date(),
                        "Presença": "Faltou" if info.get('falta') else "Presente",
                        "Resumo Atividade": info.get('descricao', '')[:100] + "..."
                    })
                if lista_logs:
                    df_logs = pd.DataFrame(lista_logs).sort_values("Data", ascending=False)
                    st.dataframe(df_logs, use_container_width=True, hide_index=True)

        with tab_gen:
            st.subheader("Emissão de Relatório Mensal")
            
            c_m, c_y = st.columns(2)
            meses = {1:"Janeiro", 2:"Fevereiro", 3:"Março", 4:"Abril", 5:"Maio", 6:"Junho", 7:"Julho", 8:"Agosto", 9:"Setembro", 10:"Outubro", 11:"Novembro", 12:"Dezembro"}
            mes_sel = c_m.selectbox("Mês", list(meses.keys()), format_func=lambda x: meses[x], index=date.today().month - 1)
            ano_sel = c_y.number_input("Ano", min_value=2020, max_value=2030, value=date.today().year)
            
            if st.button("👁️ Gerar PDF Mensal", type="primary"):
                # Filtra logs do mês/ano selecionado
                logs_mensais = {}
                for d_str, info in data_diario['logs'].items():
                    try:
                        d_obj = datetime.strptime(d_str, "%Y-%m-%d").date()
                        if d_obj.month == mes_sel and d_obj.year == ano_sel:
                            logs_mensais[d_str] = info
                    except: pass
                
                if not logs_mensais:
                    st.warning("Não há registros salvos para o período selecionado.")
                else:
                    log_action(data_diario.get('nome'), "Gerou PDF", f"Relatório Mensal {mes_sel}/{ano_sel}")
                    
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
                    pdf.set_font("Arial", "B", 16); pdf.cell(0, 10, clean_pdf_text("RELATÓRIO DIÁRIO DE AÇÕES DE ACOMPANHAMENTO ESCOLAR"), 0, 1, 'C')
                    pdf.ln(5)
                    
                    # Dados do Cabeçalho
                    pdf.set_font("Arial", "B", 10)
                    
                    # Linha 1
                    pdf.cell(15, 6, "Escola:", 0, 0)
                    pdf.set_font("Arial", "", 10)
                    pdf.cell(110, 6, clean_pdf_text(data_diario.get('escola', '')), "B", 0)
                    
                    pdf.set_font("Arial", "B", 10)
                    pdf.cell(25, 6, clean_pdf_text("Data (Ref):"), 0, 0)
                    pdf.set_font("Arial", "", 10)
                    pdf.cell(0, 6, f"{meses[mes_sel]}/{ano_sel}", "B", 1)
                    pdf.ln(2)
                    
                    # Linha 2
                    pdf.set_font("Arial", "B", 10)
                    pdf.cell(20, 6, "Estudante:", 0, 0)
                    pdf.set_font("Arial", "", 10)
                    pdf.cell(0, 6, clean_pdf_text(data_diario.get('nome', '')), "B", 1)
                    pdf.ln(2)
                    
                    # Linha 3
                    pdf.set_font("Arial", "B", 10)
                    pdf.cell(35, 6, "Ano Escolaridade:", 0, 0)
                    pdf.set_font("Arial", "", 10)
                    pdf.cell(60, 6, clean_pdf_text(data_diario.get('ano_esc', '')), "B", 0)
                    
                    pdf.set_font("Arial", "B", 10)
                    pdf.cell(20, 6, clean_pdf_text("Período:"), 0, 0)
                    pdf.set_font("Arial", "", 10)
                    pdf.cell(0, 6, clean_pdf_text(data_diario.get('periodo', '')), "B", 1)
                    pdf.ln(2)
                    
                    # Linha 4
                    pdf.set_font("Arial", "B", 10)
                    pdf.cell(30, 6, "Acompanhante:", 0, 0)
                    pdf.set_font("Arial", "", 10)
                    pdf.cell(0, 6, clean_pdf_text(data_diario.get('acompanhante', '')), "B", 1)
                    
                    pdf.ln(8)
                    
                    # Tabela
                    pdf.set_font("Arial", "B", 11)
                    pdf.set_fill_color(200, 200, 200)
                    pdf.cell(0, 8, clean_pdf_text("Descrição das atividades realizadas com o estudante"), 1, 1, 'C', True)
                    
                    # Cabeçalho da Tabela
                    pdf.set_font("Arial", "B", 10)
                    pdf.set_fill_color(240, 240, 240)
                    pdf.cell(25, 8, "DATA", 1, 0, 'C', True)
                    pdf.cell(0, 8, clean_pdf_text("ATIVIDADES / OCORRÊNCIAS"), 1, 1, 'C', True)
                    
                    # Conteúdo (Loop)
                    pdf.set_font("Arial", "", 10)
                    
                    # Ordenar dias
                    dias_ordenados = sorted(logs_mensais.keys())
                    
                    for d_str in dias_ordenados:
                        info = logs_mensais[d_str]
                        d_obj = datetime.strptime(d_str, "%Y-%m-%d")
                        d_fmt = d_obj.strftime("%d/%m")
                        
                        texto = info.get('descricao', '')
                        if info.get('falta'):
                            texto = "[ESTUDANTE FALTOU] " + texto
                        
                        pdf.set_x(15)
                        x_start = pdf.get_x()
                        y_start = pdf.get_y()
                        
                        # Simula altura
                        # Largura coluna texto = 155
                        line_height = 5
                        txt_width = pdf.get_string_width(clean_pdf_text(texto))
                        num_lines = txt_width / 150 # 155 - padding
                        h_row = max(8, (int(num_lines) + 1) * line_height + 4)

                        # Check page break
                        if y_start + h_row > 270:
                            pdf.add_page()
                            y_start = pdf.get_y()
                            
                        # Draw Cells
                        pdf.rect(x_start, y_start, 25, h_row) # Box Data
                        pdf.rect(x_start + 25, y_start, 155, h_row) # Box Desc
                        
                        # Print Data
                        pdf.set_xy(x_start, y_start)
                        pdf.cell(25, h_row, d_fmt, 0, 0, 'C')
                        
                        # Print Desc
                        pdf.set_xy(x_start + 27, y_start + 2)
                        pdf.multi_cell(151, 5, clean_pdf_text(texto), 0, 'J')
                        
                        # Move cursor
                        pdf.set_xy(x_start, y_start + h_row)

                    # Assinaturas
                    pdf.ln(10)
                    if pdf.get_y() > 250: pdf.add_page()
                    
                    y = pdf.get_y()
                    pdf.line(15, y+10, 105, y+10)
                    pdf.line(115, y+10, 195, y+10)
                    
                    pdf.set_xy(15, y+11)
                    pdf.set_font("Arial", "", 9)
                    pdf.cell(90, 5, "Assinatura do Acompanhante", 0, 0, 'C')
                    pdf.cell(80, 5, clean_pdf_text("                       Visto da Coordenação/Direção"), 0, 1, 'C')
                    
                    st.session_state.pdf_bytes_diario_mes = get_pdf_bytes(pdf)
                    st.rerun()

            if 'pdf_bytes_diario_mes' in st.session_state:
                file_name_clean = data_diario.get('nome','aluno').replace(" ", "_")
                st.download_button(
                    "📥 BAIXAR RELATÓRIO MENSAL (PDF)", 
                    st.session_state.pdf_bytes_diario_mes, 
                    f"Diario_{file_name_clean}_{mes_sel}_{ano_sel}.pdf", 
                    "application/pdf", 
                    type="primary"
                )






