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
from ui.componentes import renderizar_cabecalho_institucional, renderizar_titulo_secao

CHAVES_ESTADO_PACIENTE = ["perf_list", "magna_seg_list", "seg_k", "protocolo_numero"]


def _renderizar_barra_acoes() -> None:
    _, col_btn = st.columns([6, 2])
    with col_btn:
        if st.button("Reiniciar paciente", type="primary", use_container_width=True):
            st.session_state["confirmar_reset"] = True

    if st.session_state.get("confirmar_reset"):
        st.warning(
            "Isso vai limpar todos os dados preenchidos deste exame "
            "(achados, medidas, perfurantes e venograma). Esta ação não pode ser desfeita."
        )
        c_sim, c_nao, _ = st.columns([1, 1, 4])
        if c_sim.button("Confirmar limpeza", use_container_width=True):
            for chave in CHAVES_ESTADO_PACIENTE:
                st.session_state.pop(chave, None)
            st.session_state["confirmar_reset"] = False
            st.rerun()
        if c_nao.button("Cancelar", use_container_width=True):
            st.session_state["confirmar_reset"] = False
            st.rerun()


def coletar_dados_exame() -> DadosExame:
    dados = DadosExame()

    with st.container(border=True):
        dados.lateralidade = renderizar_identificacao()
    st.session_state["lateralidade_atual"] = dados.lateralidade

    with st.container(border=True):
        renderizar_titulo_secao("02", "Sistemas Venosos", "Avaliação dos sistemas profundo e superficial")
        c1, c2 = st.columns(2)
        with c1:
            dados.sistema_profundo = renderizar_sistema_profundo()
        with c2:
            dados.achados_superficiais = renderizar_sistema_superficial()

        dados.dados_magna = renderizar_detalhes_magna(dados.achados_superficiais)
        dados.dados_parva = renderizar_detalhes_parva(dados.achados_superficiais)
        dados.dados_flebite = renderizar_detalhes_flebite_varizes(dados.achados_superficiais)

    with st.container(border=True):
        dados.biometria_magna, dados.medida_parva_cm = renderizar_biometria(dados.achados_superficiais)

    with st.container(border=True):
        dados.perfurantes = renderizar_perfurantes()

    return dados


def main() -> None:
    st.set_page_config(
        page_title="Sistema de Laudo Venoso Profissional",
        page_icon="🩺",
        layout="wide",
    )
    st.markdown(CSS_TEMA, unsafe_allow_html=True)

    renderizar_cabecalho_institucional(lateralidade=st.session_state.get("lateralidade_atual"))
    _renderizar_barra_acoes()

    dados = coletar_dados_exame()

    erros = validar_exame(dados)
    for erro in erros:
        st.error(erro)

    laudo_final = gerar_laudo_completo(dados)

    with st.container(border=True):
        c_laudo, c_ven = st.columns([1, 1])
        with c_laudo:
            renderizar_laudo_editavel(laudo_final)
        with c_ven:
            renderizar_venograma(dados)


if __name__ == "__main__":
    main()
