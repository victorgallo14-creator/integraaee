        st.warning("Base curricular ainda não cadastrada para esta combinação.")
        return
    tabs = st.tabs(["🧭 Currículo & percurso", "📝 Mapa da avaliação", "👥 Tabulação", "🧠 Conceituação"])
    with tabs[0]:
        _curriculo_tab(repo, ctx, base)
    with tabs[1]:
        _blueprint_tab(repo, ctx, base)
    with tabs[2]:
        _tabulacao_tab(repo, ctx, base, alunos)
    with tabs[3]:
        _conceituacao_tab(repo, ctx, base, alunos)


# -----------------------------------------------------------------------------
# Entrada pública do módulo
# -----------------------------------------------------------------------------
def renderizar_avaliacao(
    supabase: Any,
    matriz_professores: Optional[pd.DataFrame] = None,
    usuario_nome: Optional[str] = None,
    usuario_matricula: Optional[str] = None,
    sql_instalacao: Optional[str] = None,
) -> None:
    """Renderiza o módulo completo dentro do app_pei.py existente."""
    _css()
    usuario_nome = usuario_nome or st.session_state.get("usuario_nome", "Usuário")
    usuario_matricula = usuario_matricula or st.session_state.get("usuario_matricula", "")
    gestor = _eh_gestor(usuario_matricula, usuario_nome)

    if sql_instalacao is None:
        sql_instalacao = SQL_INSTALACAO

    # Contexto disponível no banco curricular do módulo
    anos = _anos_disponiveis()
    c_top1, c_top2, c_top3 = st.columns([1, 1, 1.3])
    with c_top1:
        ano_letivo = int(st.number_input("Ano letivo", min_value=2025, max_value=2035, value=date.today().year, step=1, key="av_ano_letivo"))
    with c_top2:
        ano_escolar = st.selectbox("Ano de escolaridade", anos, format_func=lambda x: f"{x}º ano", key="av_ano_escolar")
    trimestres = _trimestres_disponiveis(ano_escolar)
    with c_top3:
        trimestre = st.selectbox("Trimestre", trimestres, format_func=lambda x: f"{x}º trimestre", key="av_trimestre")

    turmas = _turmas_permitidas(matriz_professores, usuario_nome, gestor, supabase, ano_escolar)
    if not turmas:
        st.warning(f"Não encontrei turmas do {ano_escolar}º ano vinculadas ao seu usuário na matriz de professores nem no Carômetro.")
        return
    turma = st.selectbox("Turma", turmas, key="av_turma")
    alunos = _alunos_da_turma(supabase, turma)
    disponiveis = _componentes_disponiveis(ano_escolar, trimestre)
    componentes = _componentes_permitidos(matriz_professores, usuario_nome, gestor, turma, disponiveis)

    ctx_base = Contexto(ano_letivo, ano_escolar, trimestre, turma, "")
    _header(ctx_base, usuario_nome)
    if not alunos:
        st.info("A turma foi localizada, mas o Carômetro ainda não tem estudantes vinculados exatamente a essa turma. O currículo pode ser consultado, porém a tabulação ficará indisponível até o cadastro dos alunos.")

    repo = AvaliacaoRepo(supabase, usuario_nome)
    ok, erro = repo.disponivel()
    if not ok:
        _show_setup(sql_instalacao, erro)
        return

    menu = st.radio(
        "Área do módulo",
        ["📊 Painel", "📚 Componente curricular", "🔎 Perfil do estudante", "🏛️ Conselho de Ciclo"],
        horizontal=True,
        key="av_area",
    )
    if menu == "📊 Painel":
        _painel_tab(repo, ctx_base, componentes, alunos)
    elif menu == "📚 Componente curricular":
        comp = st.selectbox("Componente", componentes, key="av_comp")
        ctx = Contexto(ano_letivo, ano_escolar, trimestre, turma, comp)
        _render_componente(repo, ctx, alunos)
    elif menu == "🔎 Perfil do estudante":
        _perfil_tab(repo, ctx_base, componentes, alunos)
    elif menu == "🏛️ Conselho de Ciclo":
        _conselho_tab(repo, ctx_base, componentes, alunos)


SQL_INSTALACAO = r"""
create extension if not exists pgcrypto;

create table if not exists public."Avaliacao" (
    id uuid primary key default gen_random_uuid(),
    chave text not null unique,
    tipo text not null,
    ano_letivo integer not null,
    ano_escolar integer not null,
    trimestre integer not null check (trimestre between 1 and 3),
    turma text not null,
    componente text not null default '',
    aluno_nome text,
    dados_json jsonb not null default '{}'::jsonb,
    atualizado_por text,
    atualizado_em timestamptz not null default now()
);

create index if not exists avaliacao_contexto_idx
on public."Avaliacao" (ano_letivo, ano_escolar, trimestre, turma, componente, tipo);

create index if not exists avaliacao_aluno_idx
on public."Avaliacao" (turma, aluno_nome);

-- O Integra atual usa a chave configurada no servidor. Se o projeto adotar RLS,
-- substitua estas políticas pela política de autenticação oficial da aplicação.
alter table public."Avaliacao" disable row level security;
""".strip()


__all__ = [
    "renderizar_avaliacao",
    "calcular_conceito_sugerido",
    "construir_perfil_aluno",
    "gerar_pdf_perfil",
    "gerar_pdf_turma",
]
