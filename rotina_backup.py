import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
from gspread_dataframe import set_with_dataframe
from supabase import create_client
import os

print("🤖 A iniciar rotina: Criação de NOVO arquivo de backup no Google Drive...")

try:
    # 1. Puxa as senhas do Supabase e do Google que estão no GitHub
    supa_url = os.environ.get("SUPABASE_URL")
    supa_key = os.environ.get("SUPABASE_KEY")
    supabase = create_client(supa_url, supa_key)

    gcp_credentials_json = json.loads(os.environ.get("GCP_SERVICE_ACCOUNT_JSON"))
    
    # 2. Conecta no Google Drive
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    credentials = Credentials.from_service_account_info(gcp_credentials_json, scopes=scopes)
    gc = gspread.authorize(credentials)

    # 3. Cria a planilha nova DENTRO da sua pasta usando o ID que você me mandou
    PASTA_ID = "1HF0A797fZQYc5YCFncfcHfC6iLkr6AAn"
    agora_str = pd.Timestamp.now(tz="America/Sao_Paulo").strftime("%d-%m-%Y_%H-%M")
    nome_arquivo = f"Backup_Escola_{agora_str}"

    print(f"📄 Criando o arquivo '{nome_arquivo}' na pasta do Drive...")
    sh = gc.create(nome_arquivo, folder_id=PASTA_ID)

    # 4. Lista de todas as suas tabelas
    tabelas = [
        "Agenda", "Agendamentos", "Almoxarifado_Estoque", "Almoxarifado_Pedidos",
        "Alunos", "Atas_Conselho", "Backup_Alunos", "Biblioteca_Acervo",
        "Biblioteca_Emprestimos", "Biblioteca_Exemplares", "Biblioteca_Reservas",
        "Carometro", "Config_Ata", "Historico", "Monitores", 
        "Planejamento", "Professores", "Recados"
    ]

    # 5. Salva cada tabela em uma aba diferente
    for i, tabela in enumerate(tabelas):
        print(f"🔄 Baixando tabela: {tabela}...")
        
        response = supabase.table(tabela).select("*").execute()
        df_tabela = pd.DataFrame(response.data)

        if not df_tabela.empty:
            
            # Limpa arquivos pesados e fotos para não travar a planilha
            if 'dados_json' in df_tabela.columns:
                for idx, row in df_tabela.iterrows():
                    try:
                        if row['dados_json']:
                            dados = json.loads(row['dados_json'])
                            if 'foto_base64' in dados: del dados['foto_base64']
                            chaves_para_limpar = [k for k, v in dados.items() if isinstance(v, str) and len(v) > 15000]
                            for k in chaves_para_limpar: dados[k] = "[REMOVIDO NO BACKUP]"
                            json_str = json.dumps(dados, ensure_ascii=False)
                            if len(json_str) > 49000: json_str = json_str[:49000] + '... [TRUNCADO]'
                            df_tabela.at[idx, 'dados_json'] = json_str
                    except:
                        continue

            # Prepara a aba no Google Sheets
            if i == 0:
                worksheet = sh.sheet1
                worksheet.update_title(tabela[:31])
            else:
                linhas = max(100, len(df_tabela) + 10)
                colunas = max(10, len(df_tabela.columns))
                worksheet = sh.add_worksheet(title=tabela[:31], rows=str(linhas), cols=str(colunas))

            # Cola os dados
            set_with_dataframe(worksheet, df_tabela)
            print(f"✅ Aba '{tabela}' salva com sucesso.")
        else:
            print(f"ℹ️ Tabela '{tabela}' ignorada (vazia).")

    print(f"🎉 SUCESSO TOTAL! Backup finalizado. Vá conferir a sua pasta no Drive!")

except Exception as e:
    print(f"🛑 ERRO GERAL: {e}")
    exit(1)
