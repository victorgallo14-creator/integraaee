import streamlit as st
import pandas as pd
import json
from streamlit_gsheets import GSheetsConnection
from supabase import create_client

print("🤖 A iniciar a rotina de backup automático...")

try:
    # 1. Conecta ao Supabase usando os seus segredos
    supa_url = st.secrets["SUPABASE_URL"]
    supa_key = st.secrets["SUPABASE_KEY"]
    supabase = create_client(supa_url, supa_key)

    # Puxa a tabela inteira de alunos
    response = supabase.table("Alunos").select("*").execute()
    df_backup = pd.DataFrame(response.data)

    if not df_backup.empty:
        print(f"✅ Banco lido com sucesso. A preparar {len(df_backup)} registos...")
        
        # 2. FILTRO: Remove a foto pesada e textos gigantes para não travar o Google Sheets
        df_limpo = df_backup.copy()
        if 'dados_json' in df_limpo.columns:
            for idx, row in df_limpo.iterrows():
                try:
                    if row['dados_json']:
                        dados = json.loads(row['dados_json'])
                        
                        # Remove a foto principal explicitamente
                        if 'foto_base64' in dados:
                            del dados['foto_base64']
                            
                        # BLINDAGEM: Limpa qualquer outro campo que seja gigante (textos colados ou outras imagens)
                        chaves_para_limpar = []
                        for k, v in dados.items():
                            if isinstance(v, str) and len(v) > 15000: # Se for maior que 15.000 caracteres
                                chaves_para_limpar.append(k)
                                
                        for k in chaves_para_limpar:
                            dados[k] = "[TEXTO/IMAGEM REMOVIDA NO BACKUP POR EXCEDER LIMITE DO GOOGLE SHEETS]"
                            
                        dados['info_backup'] = "Filtrado para Google Sheets (Limite 50k chars)"
                        
                        json_str = json.dumps(dados, ensure_ascii=False)
                        
                        # ÚLTIMA BARREIRA DE SEGURANÇA: Se a string do JSON ainda passar do limite global, trunca no final
                        if len(json_str) > 49000:
                            json_str = json_str[:49000] + '... [TRUNCADO POR LIMITE DE CARACTERES]'
                            
                        df_limpo.at[idx, 'dados_json'] = json_str
                except Exception as e:
                    print(f"Erro ao processar a linha {idx}: {e}")
                    continue

        # Cria a data e hora do backup (Horário de Brasília)
        agora_str = pd.Timestamp.now(tz="America/Sao_Paulo").strftime("%d/%m/%Y %H:%M")
        df_limpo.insert(0, "DATA_DO_BACKUP", agora_str)

        # 3. Conecta ao Google Sheets
        conn_backup = st.connection("gsheets", type=GSheetsConnection)
        
        try:
            df_historico_antigo = conn_backup.read(worksheet="Cofre_Historico", ttl=0)
        except Exception:
            df_historico_antigo = pd.DataFrame()

        # 4. Acumula os dados antigos com os de hoje
        if not df_historico_antigo.empty and len(df_historico_antigo.columns) > 0:
            df_final = pd.concat([df_historico_antigo, df_limpo], ignore_index=True)
        else:
            df_final = df_limpo

        # 5. Guarda tudo no Google Sheets
        conn_backup.update(worksheet="Cofre_Historico", data=df_final)
        print(f"🎉 SUCESSO! Backup das {agora_str} guardado no Cofre_Historico.")

    else:
        print("⚠️ O banco do Supabase está vazio. Nenhum backup realizado.")

except Exception as e:
    print(f"🛑 ERRO no backup: {e}")
    exit(1) # Avisa o GitHub que algo correu mal
