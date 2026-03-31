import streamlit as st
from PIL import Image
import numpy as np
import io
import os
import json
from streamlit_drawable_canvas import st_canvas

def main():
    st.set_page_config(page_title="Sistema de Laudo Venoso Profissional", layout="wide")
    
    # ==========================================
    # TEMA PROFISSIONAL (CSS)
    # ==========================================
    st.markdown("""
        <style>
        .stApp { background-color: #F0F2F6 !important; }
        div[data-testid="stVerticalBlock"] > div.element-container { background-color: transparent; }
        h1, h2, h3 {
            color: #1E3A8A !important;
            font-family: 'Segoe UI', sans-serif;
            border-bottom: 2px solid #DEE2E6;
            padding-bottom: 10px;
        }
        label, p, span { color: #1F2937 !important; font-weight: 600 !important; }
        .stTextArea textarea, .stTextInput input, .stSelectbox div[data-baseweb="select"] {
            background-color: #FFFFFF !important; color: #000000 !important;
            border: 1px solid #D1D5DB !important; border-radius: 8px !important;
        }
        button[kind="primary"] {
            background-color: #EF4444 !important; color: white !important;
            border-radius: 8px !important; border: none !important;
        }
        .stDownloadButton button, .copy-btn {
            background-color: #10B981 !important; color: white !important;
            border-radius: 8px !important; font-weight: bold !important;
            height: 50px !important; width: 100% !important; border: none !important;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1) !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # Inicialização de Variáveis de Sessão
    if 'perf_list' not in st.session_state: st.session_state.perf_list = []
    if 'magna_seg_list' not in st.session_state: st.session_state.magna_seg_list = []
    if 'seg_k' not in st.session_state: st.session_state.seg_k = 0

    # --- CABEÇALHO ---
    colA, colB = st.columns([8, 2])
    with colA:
        st.title("🏥 Sistema de Laudo e Venograma")
    with colB:
        if st.button("🔄 Reiniciar Paciente", type="primary"):
            st.session_state.clear()
            st.rerun()

    # ==========================================
    # 1. IDENTIFICAÇÃO E LATERALIDADE
    # ==========================================
    with st.container():
        st.header("1. Identificação e Lateralidade")
        lat = st.radio("Membro Inferior:", ["Direito", "Esquerdo"], horizontal=True)

    # ==========================================
    # 2. SISTEMAS E ALTERAÇÕES
    # ==========================================
    with st.container():
        st.header("2. Sistemas")
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("2.1 Profundo")
            status_profundo = st.radio("Sistema profundo normal?", ["Normal", "Não"], horizontal=True)
            veias_alt = []
            tipo_alt = ""
            if status_profundo == "Não":
                veias_alt = st.multiselect("Veias profundas alteradas:", ["Femoral comum", "Femoral superficial", "Femoral profunda", "Poplítea", "Tibiais", "Fibulares", "Musculares da panturrilha"])
                tipo_alt = st.selectbox("Tipo de alteração:", ["Trombose Aguda", "Trombose Crônica Não Recanalizada", "Trombose Crônica Parcialmente Recanalizada"])
        
        with c2:
            st.subheader("2.2 Superficial")
            status_sup = st.radio("Sistema superficial normal?", ["Normal", "Não"], horizontal=True)
            achados_sup = []
            if status_sup == "Não":
                achados_sup = st.multiselect("Achados superficiais:", [
                    "Safenectomia Magna Total", "Safenectomia Magna Parcial", 
                    "Safena Magna - Incompetência Parcial", "Safena Magna - Incompetência Total", "Safena Magna - Incompetência Segmentar",
                    "Safenectomia Parva Total", "Safenectomia Parva Parcial",
                    "Safena Parva - Incompetência Parcial", "Safena Parva - Incompetência Total",
                    "Tromboflebite de Safena", "Microvarizes", "Varizes Poplíteas"
                ])

        # --- DETALHES DE ALTERAÇÕES (SÓ ABREM SE SELECIONADOS) ---
        mag_jsf = mag_origem = mag_seg_ori = mag_dist_ori = mag_ref_ori = mag_seg_ext = mag_dist_ext = mag_ref_ext = mag_drenagem = ""
        if any(x in achados_sup for x in ["Safena Magna - Incompetência Parcial", "Safena Magna - Incompetência Segmentar"]):
            with st.expander("📍 Detalhes da Incompetência da Safena Magna", expanded=True):
                mag_jsf = st.radio("Junção Safenofemoral incompetente?", ["Sim", "Não"], horizontal=True)
                if mag_jsf == "Não":
                    col1, col2 = st.columns(2)
                    mag_origem = col1.selectbox("Origem do refluxo:", ["perfurante incompetente", "tributária"])
                    mag_seg_ori = col2.selectbox("Segmento origem:", ["proximal da coxa", "médio da coxa", "distal da coxa", "proximal da perna", "médio da perna", "distal da perna"])
                    mag_dist_ori = st.text_input("Distância Origem (cm):")
                    mag_ref_ori = st.selectbox("Referência Origem:", ["abaixo da junção safenofemoral", "acima da interlinha do joelho", "abaixo da interlinha do joelho"])
                
                mag_seg_ext = st.selectbox("Extensão até o terço:", ["proximal da coxa", "médio da coxa", "distal da coxa", "proximal da perna", "médio da perna", "distal da perna"])
                mag_dist_ext = st.text_input("Distância Extensão (cm):")
                mag_ref_ext = st.selectbox("Referência Extensão:", ["abaixo da junção safenofemoral", "acima da interlinha do joelho", "abaixo da interlinha do joelho"])
                mag_drenagem = st.selectbox("Drenagem de refluxo para:", ["tributárias", "perfurantes"])

                if "Safena Magna - Incompetência Segmentar" in achados_sup:
                    st.markdown("---")
                    st.markdown("**Adicionar Novo Segmento Insuficiente:**")
                    k = st.session_state.seg_k
                    c_s1, c_s2 = st.columns(2)
                    s_origem = c_s1.selectbox("Nova Origem:", ["perfurante incompetente", "tributária"], key=f"o_{k}")
                    s_seg_ori = c_s2.selectbox("Novo Seg. Origem:", ["proximal da coxa", "médio da coxa", "distal da coxa", "proximal da perna", "médio da perna", "distal da perna"], key=f"so_{k}")
                    s_dist_ori = st.text_input("Distância Nova Origem (cm):", key=f"do_{k}")
                    s_ref_ori = st.selectbox("Ref. Nova Origem:", ["abaixo da junção safenofemoral", "acima da interlinha do joelho", "abaixo da interlinha do joelho"], key=f"ro_{k}")
                    s_seg_ext = st.selectbox("Nova Extensão até o terço:", ["proximal da coxa", "médio da coxa", "distal da coxa", "proximal da perna", "médio da perna", "distal da perna"], key=f"se_{k}")
                    s_dist_ext = st.text_input("Distância Nova Extensão (cm):", key=f"de_{k}")
                    s_ref_ext = st.selectbox("Ref. Nova Extensão:", ["abaixo da junção safenofemoral", "acima da interlinha do joelho", "abaixo da interlinha do joelho"], key=f"re_{k}")
                    s_drenagem = st.selectbox("Nova Drenagem para:", ["tributárias", "perfurantes"], key=f"dr_{k}")
                    if st.button("➕ Adicionar Segmento Extra"):
                        novo_seg = f"*Volta a tornar-se incompetente com refluxo proveniente de {s_origem} no segmento {s_seg_ori}, {s_dist_ori} cm {s_ref_ori}, com extensão até o terço {s_seg_ext}, {s_dist_ext} cm {s_ref_ext} e drenagem de refluxo para {s_drenagem}*"
                        st.session_state.magna_seg_list.append(novo_seg)
                        st.session_state.seg_k += 1
                        st.rerun()
                    for s in st.session_state.magna_seg_list: st.info(s)

        par_jsp_incomp = par_ext = par_dren = par_final_dist = par_final_ref = ""
        if "Safena Parva - Incompetência Parcial" in achados_sup:
            with st.expander("📍 Detalhes Safena Parva", expanded=True):
                par_jsp_incomp = st.radio("Junção Safenopoplítea incompetente?", ["Sim", "Não"], horizontal=True)
                par_ext = st.selectbox("Refluxo até segmento:", ["proximal da perna", "médio da perna", "distal da perna"])
                par_dren = st.selectbox("Transferência para:", ["tributárias", "perfurantes"])
                par_final_dist = st.text_input("Distância final (cm):")
                par_final_ref = st.selectbox("Referência final:", ["abaixo da interlinha do joelho", "acima da planta do pé"])

        t_veia = t_local = t_face = t_ext = ""
        if any(x in achados_sup for x in ["Tromboflebite de Safena", "Varizes Poplíteas"]):
            with st.expander("🩸 Detalhes Extras (Flebite/Varizes)", expanded=True):
                if "Tromboflebite de Safena" in achados_sup:
                    t_veia = st.selectbox("Veia com flebite:", ["magna", "parva"])
                    t_local = st.selectbox("Localização:", ["coxa", "perna"])
                    t_face = st.selectbox("Face:", ["anterior", "medial", "lateral", "posterior"])
                    t_ext = st.text_input("Extensão (cm) da flebite:")

    # ==========================================
    # 3. BIOMETRIA VASCULAR (MEDIDAS)
    # ==========================================
    with st.container():
        st.header("3. Biometria Vascular (Medidas)")
        st.markdown("**Veia Safena Magna**")
        if "Safenectomia Magna Parcial" in achados_sup:
            m_c1, m_c2 = st.columns(2)
            m_magna_coxa_dist = m_c1.text_input("Coxa distal (cm)", "xxx")
            m_magna_perna_prox = m_c2.text_input("Perna proximal (cm)", "xxx")
            medidas_magna_txt = f"Mede {m_magna_coxa_dist} cm (coxa distal) e {m_magna_perna_prox} cm (perna proximal)."
        else:
            m1, m2, m3 = st.columns(3)
            m_magna_crossa = m1.text_input("Crossa (cm)", "0,6")
            m_magna_coxa = m2.text_input("Coxa (cm)", "xxx")
            m_magna_perna = m3.text_input("Perna (cm)", "xxx")
            medidas_magna_txt = f"Mede {m_magna_crossa} cm (crossa), {m_magna_coxa} cm (coxa) e {m_magna_perna} cm (perna)."
        st.markdown("**Veia Safena Parva**")
        m_parva = st.text_input("Perna Proximal (cm)", "0,2")

    # ==========================================
    # 4. PERFURANTES
    # ==========================================
    with st.container():
        st.header("4. Veias Perfurantes")
        tem_perf = st.radio("Existem perfurantes insuficientes?", ["Não", "Sim"], horizontal=True)
        if tem_perf == "Sim":
            p_c1, p_c2, p_c3, p_c4 = st.columns(4)
            p_dist = p_c1.text_input("Distância (cm)")
            p_ref = p_c2.selectbox("Referência:", ["Planta do pé", "Junção safenofemoral", "Interlinha do joelho"])
            p_loc = p_c3.selectbox("Localização:", ["Coxa", "Perna"])
            p_face = p_c4.selectbox("Face:", ["Medial", "Lateral", "Anterior", "Posterior"])
            if st.button("➕ Adicionar Perfurante"):
                if p_dist:
                    st.session_state.perf_list.append(f"- Insuficiente localizada a {p_dist} cm da {p_ref.lower()}, na face {p_face.lower()} da {p_loc.lower()}.")
            for p in st.session_state.perf_list: st.info(p)
            if st.button("🗑️ Limpar Perfurantes"): st.session_state.perf_list = []; st.rerun()

    st.divider()

    # ==========================================
    # CÉREBRO: LÓGICA DE MONTAGEM DO LAUDO
    # ==========================================
    metodologia = "METODOLOGIA: Exame realizado em modo bidimensional com transdutor linear multifrequencial."
    header_prof = "Sistema profundo (Veias femoral comum, superficial e profunda; poplítea, tibiais, fibulares e musculares da panturrilha):"
    
    # Sistema Profundo
    if status_profundo == "Não" and veias_alt:
        v_str = ", ".join(veias_alt[:-1]) + " e " + veias_alt[-1] if len(veias_alt) > 1 else veias_alt[0]
        plural = "s" if len(veias_alt) > 1 else ""
        comp_p = "veis" if len(veias_alt) > 1 else "vel"
        if tipo_alt == "Trombose Aguda":
            detalhe = f"\nVeia{plural} {v_str} de calibre{plural} aumentado{plural}, com material hipoecogênico no interior, não compressí{comp_p}, e sem fluxo detectável ao estudo Doppler."
            imp_prof = f"- Sinais de trombose venosa profunda aguda das veias {v_str}."
        elif "Não Recanalizada" in tipo_alt:
            detalhe = f"\nVeia{plural} {v_str} de calibre{plural} levemente aumentado{plural}, com material hiperecogênico no interior, aderido à parede do vaso, não compressí{comp_p}, com discretos sinais de recanalização."
            imp_prof = f"- Sinais de trombose venosa profunda subaguda/crônica não recanalizada das veias {v_str}."
        else:
            detalhe = f"\nVeia{plural} {v_str} de calibre{plural} levemente reduzido{plural} com material hiperecogênico e traves no interior, parcialmente compressí{comp_p}, de paredes espessas e com sinais de recanalização parcial."
            imp_prof = f"- Sinais de trombose venosa profunda crônica parcialmente recanalizada das veias {v_str}."
        txt_profundo = f"{header_prof}\nVeias tronculares pérvias, ausência de refluxo às manobras provocativas.\nAusência de compressão extrínseca ou dilatação.\nFluxo espontâneo e fásico com a respiração.{detalhe}"
    else:
        txt_profundo = f"{header_prof}\nVeias tronculares pérvias, ausência de refluxo às manobras provocativas.\nAusência de compressão extrínseca, dilatação ou trombos.\nFluxo espontâneo e fásico com a respiração."
        imp_prof = "- Sistema profundo pérvio e competente."

    # Magna (Base)
    imp_magna = "- Veia safena magna pérvia e competente em todo trajeto."
    txt_magna_base = "Veia safena magna pérvia e competente em todo trajeto"
    if "Safenectomia Magna Total" in achados_sup:
        txt_magna_base = "Veia safena magna não caracterizada em toda sua extensão (status pós-operatório)."
        imp_magna = "- Sinais de safenectomia magna total."
    elif "Safenectomia Magna Parcial" in achados_sup:
        txt_magna_base = "Veia safena magna não caracterizada nos 2/3 proximais da coxa (status pós-operatório). Demais segmentos pérvios."
        imp_magna = "- Sinais de safenectomia magna parcial."
    elif "Safena Magna - Incompetência Total" in achados_sup:
        txt_magna_base = "Veia safena magna pérvia e incompetente, apresentando refluxo em todo seu trajeto."
        imp_magna = "- Veia safena magna pérvia e incompetente em todo seu trajeto."
    elif "Safena Magna - Incompetência Parcial" in achados_sup or "Safena Magna - Incompetência Segmentar" in achados_sup:
        if mag_jsf == "Sim":
            txt_magna_base = f"Veia safena magna com junção safenofemoral incompetente e com refluxo com extensão até o terço {mag_seg_ext}, {mag_dist_ext} cm {mag_ref_ext} e drenagem de refluxo para {mag_drenagem}"
        else:
            txt_magna_base = f"Veia safena magna com junção safenofemoral competente e com refluxo proveniente de {mag_origem} no segmento {mag_seg_ori}, {mag_dist_ori} cm {mag_ref_ori}, com extensão até o terço {mag_seg_ext}, {mag_dist_ext} cm {mag_ref_ext} e drenagem de refluxo para {mag_drenagem}"
        if "Safena Magna - Incompetência Segmentar" in achados_sup:
            for seg in st.session_state.get('magna_seg_list', []): txt_magna_base += f"\n{seg}"
        imp_magna = "- Veia safena magna pérvia e parcialmente incompetente."

    # Parva (Base)
    imp_parva = "- Veia safena parva pérvia e competente em todo trajeto."
    txt_parva_base = "Veia safena parva pérvia e competente em todo trajeto"
    if "Safenectomia Parva Total" in achados_sup:
        txt_parva_base = "Veia safena parva não caracterizada em toda sua extensão (status pós-operatório)."
        imp_parva = "- Sinais de safenectomia parva total."
    elif "Safenectomia Parva Parcial" in achados_sup:
        txt_parva_base = "Veia safena parva não caracterizada nos segmentos proximal/médio da perna (status pós-operatório). Demais segmentos pérvios."
        imp_parva = "- Sinais de safenectomia parva parcial."
    elif "Safena Parva - Incompetência Total" in achados_sup:
        txt_parva_base = "Veia safena parva pérvia e incompetente, apresentando refluxo em todo seu trajeto."
        imp_parva = "- Veia safena parva pérvia e incompetente em todo seu trajeto."
    elif "Safena Parva - Incompetência Parcial" in achados_sup:
        jsp_status_txt = "incompetente" if par_jsp_incomp == "Sim" else "competente"
        txt_parva_base = f"Veia safena parva com junção safenopoplítea {jsp_status_txt}, com refluxo que se estende até o segmento {par_ext} e transferência para {par_dren}, {par_final_dist} cm {par_final_ref}"
        imp_parva = "- Veia safena parva pérvia e parcialmente incompetente."

    # Injeção da Flebite (ANTES das medidas)
    imp_extras = []
    txt_extras_sec = ""
    if "Tromboflebite de Safena" in achados_sup:
        if t_veia == "magna":
            txt_magna_base += f", de calibre aumentado, com material hipoecogênico, não compressível, na {t_local}, em sua face {t_face}, estendendo-se por {t_ext} cm"
            imp_extras.append(f"- Sinais de tromboflebite de veia safena magna na {t_local}.")
        else:
            txt_parva_base += f", de calibre aumentado, com material hipoecogênico, não compressível, na {t_local}, em sua face {t_face}, estendendo-se por {t_ext} cm"
            imp_extras.append(f"- Sinais de tromboflebite de veia safena parva na {t_local}.")

    # Montagem Final Safenas
    if "Safenectomia Magna Total" in achados_sup: txt_magna = txt_magna_base
    else: txt_magna = f"{txt_magna_base}.\n{medidas_magna_txt}"
    
    if "Safenectomia Parva Total" in achados_sup: txt_parva = txt_parva_base
    else: txt_parva = f"{txt_parva_base}.\nMede {m_parva} cm (perna proximal)."

    # Outros Achados
    if "Microvarizes" in achados_sup:
        txt_extras_sec += "\nMicrovarizes presentes clinicamente sem representação ao estudo Doppler."
        imp_extras.append("- Microvarizes sem representação ao Doppler.")
    if "Varizes Poplíteas" in achados_sup:
        txt_extras_sec += "\nVeias varicosas drenando na veia poplítea."
        imp_extras.append("- Veias varicosas drenando na veia poplítea.")

    imp_perf = "- Perfurante insuficiente." if st.session_state.perf_list else ""
    txt_p_final = "\n".join(st.session_state.perf_list) if st.session_state.perf_list else "Ausência de perfurantes insuficientes."

    laudo_final = f"ECO-DOPPLER VENOSO DE MEMBRO INFERIOR {lat.upper()}\n\n{metodologia}\n\n{txt_profundo}\n\nSistema superficial:\n{txt_magna}\n\n{txt_parva}{txt_extras_sec}\nVarizes superficiais conforme ectoscopia.\n\nPerfurantes:\n{txt_p_final}\n\nIMPRESSÃO DIAGNÓSTICA:\n{imp_prof}\n{imp_magna}\n{imp_parva}\n- Varizes superficiais conforme ectoscopia.\n{''.join([chr(10)+x for x in imp_extras])}\n{imp_perf}"

    # ==========================================
    # 🚀 MOTOR DE PREENCHIMENTO AUTOMÁTICO
    # ==========================================
    initial_drawing = {"objects": []}
    # Coordenadas Calibradas para o box de 600px
    coords = {
        "Direito": {"magna": [135, 120, 130, 420], "profunda": [470, 120, 450, 420]},
        "Esquerdo": {"magna": [190, 120, 195, 420], "profunda": [530, 120, 550, 420]}
    }
    c = coords[lat]
    if "Safena Magna - Incompetência Total" in achados_sup:
        initial_drawing["objects"].append({"type": "line", "x1": c["magna"][0], "y1": c["magna"][1], "x2": c["magna"][2], "y2": c["magna"][3], "stroke": "rgba(255,0,0,0.5)", "strokeWidth": 8})
    if status_profundo == "Não":
        initial_drawing["objects"].append({"type": "line", "x1": c["profunda"][0], "y1": c["profunda"][1], "x2": c["profunda"][2], "y2": c["profunda"][3], "stroke": "rgba(0,0,0,0.6)", "strokeWidth": 10})

    # ==========================================
    # RESULTADO FINAL
    # ==========================================
    c_laudo, c_ven = st.columns([1, 1])

    with c_laudo:
        st.subheader("📄 Laudo Final")
        laudo_edit = st.text_area("Edição:", value=laudo_final.strip(), height=650)
        st.components.v1.html(f"<textarea id='txt' style='opacity:0;position:absolute;'>{laudo_edit}</textarea><button onclick='navigator.clipboard.writeText(document.getElementById(\"txt\").value);alert(\"Copiado!\")' class='copy-btn'>📋 COPIAR LAUDO</button>", height=70)

    with c_ven:
        st.subheader("🎨 Venograma Interativo")
        t_c1, t_c2, t_c3 = st.columns([1.2, 2.2, 1.2])
        tool = t_c1.selectbox("Ferramenta:", ["transform", "line", "freedraw", "circle"], format_func=lambda x: "🖱️ Selecionar" if x=="transform" else "📏 Linha" if x=="line" else "✏️ Lápis" if x=="freedraw" else "⭕ Círculo")
        color = t_c2.radio("Cor:", ["Vermelho", "Preto", "Azul"], horizontal=True)
        weight = t_c3.slider("Espessura:", 1, 20, 6)
        stroke = "rgba(255, 0, 0, 0.6)" if color == "Vermelho" else ("rgba(0, 0, 0, 0.7)" if color == "Preto" else "rgba(0, 102, 204, 0.6)")

        # Carregamento da Imagem
        img_p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "base_venograma.png")
        target_w = 900
        if os.path.exists(img_p):
            bg = Image.open(img_p).convert("RGBA")
            target_h = int(target_w * (bg.height / bg.width))
            bg = bg.resize((target_w, target_h))
        else:
            bg = Image.new("RGBA", (target_w, 400), (255, 255, 255, 255)); target_h = 400

        canvas_result = st_canvas(
            fill_color="rgba(255, 255, 255, 0)",
            stroke_width=weight,
            stroke_color=stroke,
            background_image=bg,
            height=target_h,
            width=target_w,
            drawing_mode=tool,
            initial_drawing=initial_drawing,
            update_streamlit=True,
            key="canvas_auto_select_final",
        )
        
        if canvas_result.image_data is not None:
            drawn = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')
            final = Image.alpha_composite(bg, drawn)
            buf = io.BytesIO(); final.save(buf, format="PNG")
            st.download_button("💾 BAIXAR VENOGRAMA", buf.getvalue(), "venograma.png", "image/png", use_container_width=True)

if __name__ == "__main__":
    main()
