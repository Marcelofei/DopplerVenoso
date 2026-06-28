"""
Sistema de Laudo e Venograma — ponto de entrada do app Streamlit.

Esta camada apenas ORQUESTRA: chama funções de `ui` para coletar dados via
widgets, monta um `DadosExame`, valida, gera o laudo via `logica`, e
renderiza o resultado. Nenhuma regra clínica deve viver neste arquivo —
toda regra de negócio fica em `logica/`, testável sem o Streamlit.
"""
from __future__ import annotations

import streamlit as st

from logica import DadosExame, gerar_laudo_completo, validar_exame
from ui import (
    CSS_TEMA,
    renderizar_biometria,
    renderizar_detalhes_flebite_varizes,
    renderizar_detalhes_magna,
    renderizar_detalhes_parva,
    renderizar_identificacao,
    renderizar_laudo_editavel,
    renderizar_perfurantes,
    renderizar_sistema_profundo,
    renderizar_sistema_superficial,
    renderizar_venograma,
)

CHAVES_ESTADO_PACIENTE = ["perf_list", "magna_seg_list", "seg_k"]


def _renderizar_cabecalho() -> None:
    colA, colB = st.columns([8, 2])
    with colA:
        st.title("🏥 Sistema de Laudo e Venograma")
    with colB:
        if st.button("🔄 Reiniciar Paciente", type="primary"):
            st.session_state["confirmar_reset"] = True

    if st.session_state.get("confirmar_reset"):
        st.warning("Tem certeza que deseja limpar todos os dados deste paciente?")
        c_sim, c_nao = st.columns(2)
        if c_sim.button("✅ Sim, limpar tudo"):
            for chave in CHAVES_ESTADO_PACIENTE:
                st.session_state.pop(chave, None)
            st.session_state["confirmar_reset"] = False
            st.rerun()
        if c_nao.button("❌ Cancelar"):
            st.session_state["confirmar_reset"] = False
            st.rerun()


def coletar_dados_exame() -> DadosExame:
    dados = DadosExame()

    with st.container():
        dados.lateralidade = renderizar_identificacao()

    with st.container():
        st.header("2. Sistemas")
        c1, c2 = st.columns(2)
        with c1:
            dados.sistema_profundo = renderizar_sistema_profundo()
        with c2:
            dados.achados_superficiais = renderizar_sistema_superficial()

        dados.dados_magna = renderizar_detalhes_magna(dados.achados_superficiais)
        dados.dados_parva = renderizar_detalhes_parva(dados.achados_superficiais)
        dados.dados_flebite = renderizar_detalhes_flebite_varizes(dados.achados_superficiais)

    with st.container():
        dados.biometria_magna, dados.medida_parva_cm = renderizar_biometria(dados.achados_superficiais)

    with st.container():
        dados.perfurantes = renderizar_perfurantes()

    return dados


def main() -> None:
    st.set_page_config(page_title="Sistema de Laudo Venoso Profissional", layout="wide")
    st.markdown(CSS_TEMA, unsafe_allow_html=True)

    _renderizar_cabecalho()

    dados = coletar_dados_exame()

    st.divider()

    erros = validar_exame(dados)
    for erro in erros:
        st.error(f"⚠️ {erro}")

    laudo_final = gerar_laudo_completo(dados)

    c_laudo, c_ven = st.columns([1, 1])
    with c_laudo:
        renderizar_laudo_editavel(laudo_final)
    with c_ven:
        renderizar_venograma(dados)


if __name__ == "__main__":
    main()
