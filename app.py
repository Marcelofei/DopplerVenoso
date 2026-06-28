"""
Sistema de Laudo e Venograma — Eco-Doppler Venoso de Membro Inferior.

ARQUIVO ÚNICO (intencional): este projeto é editado diretamente pela
interface web do GitHub, sem terminal/git local. Por isso, em vez de
separar em módulos (logica/, ui/), tudo vive em app.py — um arquivo só
para copiar/colar/editar é muito mais simples de manter nesse fluxo de
trabalho do que múltiplos arquivos em pastas.

O código é organizado em seções bem delimitadas (procure pelos blocos
"# ===== ... ====="), na seguinte ordem:
    1. Constantes e enums (texto clínico)
    2. Estado da sessão (inicialização)
    3. Funções de geração de texto do laudo (lógica pura)
    4. Funções de geração do venograma automático (SVG)
    5. Componentes visuais (cabeçalho, título de seção)
    6. Seções da interface (cada bloco do formulário)
    7. main() — orquestra tudo
"""
from __future__ import annotations

import html
import io
import json
import os
import random
from dataclasses import dataclass, field
from datetime import date

import streamlit as st
from PIL import Image, ImageDraw

try:
    from streamlit_drawable_canvas import st_canvas
    CANVAS_DISPONIVEL = True
except ImportError:
    CANVAS_DISPONIVEL = False


# =====================================================================
# 0. CONFIGURAÇÃO DE PÁGINA E TEMA VISUAL
# =====================================================================

st.set_page_config(
    page_title="Sistema de Laudo Venoso",
    page_icon="🩺",
    layout="wide",
)

CSS_TEMA = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;650;700&family=IBM+Plex+Mono:wght@400;500;600&family=Inter:wght@400;500;600;700&display=swap');

:root {
    --color-ink: #0B2942;
    --color-accent: #155E75;
    --color-accent-soft: #E5EEF1;
    --color-bg: #F7F9FA;
    --color-surface: #FFFFFF;
    --color-muted: #5B6B79;
    --color-line: #DCE3E8;
    --color-danger: #B91C1C;
    --color-danger-soft: #FBEAEA;
    --color-success: #0F766E;
    --color-success-soft: #E6F2F0;
    --color-warning: #B45309;
    --color-warning-soft: #FDF1E1;
    --font-display: 'IBM Plex Sans', sans-serif;
    --font-body: 'Inter', sans-serif;
    --font-mono: 'IBM Plex Mono', monospace;
}

.stApp { background-color: var(--color-bg) !important; font-family: var(--font-body); }
div[data-testid="stVerticalBlock"] > div.element-container { background-color: transparent; }
#MainMenu, footer, header[data-testid="stHeader"] { background-color: transparent; }
html, body, [class*="css"] { font-family: var(--font-body); }

.laudo-header {
    background: linear-gradient(135deg, var(--color-ink) 0%, #0E3A5C 100%);
    border-radius: 10px;
    padding: 26px 30px 20px 30px;
    margin-bottom: 22px;
    box-shadow: 0 8px 24px -8px rgba(11, 41, 66, 0.35);
}
.laudo-header__eyebrow {
    font-family: var(--font-mono); font-size: 11px; letter-spacing: 0.14em;
    text-transform: uppercase; color: #9FC4D6; font-weight: 500; margin: 0 0 6px 0;
}
.laudo-header__title {
    font-family: var(--font-display); font-size: 24px; font-weight: 650;
    letter-spacing: -0.01em; color: #FFFFFF; margin: 0;
}
.laudo-header__sub { font-size: 13px; color: #C7D9E2; margin: 4px 0 0 0; }
.laudo-header__meta {
    display: flex; gap: 26px; margin-top: 16px; padding-top: 14px;
    border-top: 1px solid rgba(255,255,255,0.14); flex-wrap: wrap;
}
.laudo-header__meta-item { display: flex; flex-direction: column; gap: 2px; }
.laudo-header__meta-label {
    font-family: var(--font-mono); font-size: 10px; letter-spacing: 0.1em;
    text-transform: uppercase; color: #7FA8BC;
}
.laudo-header__meta-value { font-family: var(--font-mono); font-size: 13px; color: #EAF2F5; font-weight: 500; }

h1, h2, h3 { font-family: var(--font-display) !important; }
.secao-protocolo {
    display: flex; align-items: flex-start; gap: 12px; margin: 4px 0 14px 0;
    padding-bottom: 10px; border-bottom: 1px solid var(--color-line);
}
.secao-protocolo__numero {
    font-family: var(--font-mono); font-size: 12px; font-weight: 600;
    color: var(--color-accent); background: var(--color-accent-soft);
    border-radius: 6px; padding: 3px 8px; line-height: 1.4; white-space: nowrap; margin-top: 2px;
}
.secao-protocolo__texto h3 {
    margin: 0 !important; padding: 0 !important; border: none !important;
    color: var(--color-ink) !important; font-size: 17px !important; font-weight: 600 !important;
}
.secao-protocolo__desc { font-size: 12px; color: var(--color-muted); margin: 2px 0 0 0; }

label, p, span, .stMarkdown { color: var(--color-ink) !important; }
label { font-weight: 500 !important; font-size: 13.5px !important; color: var(--color-muted) !important; }

/* Exceções: textos dentro do cabeçalho escuro precisam permanecer claros.
   Sem isso, a regra genérica "p, span { color: var(--color-ink) }" acima
   vence as cores claras definidas em .laudo-header__*, deixando o texto
   praticamente invisível (azul escuro sobre fundo azul escuro). */
.laudo-header__eyebrow,
.laudo-header__title,
.laudo-header__sub,
.laudo-header__meta-label,
.laudo-header__meta-value {
    color: inherit !important;
}
.laudo-header__eyebrow { color: #9FC4D6 !important; }
.laudo-header__title { color: #FFFFFF !important; }
.laudo-header__sub { color: #C7D9E2 !important; }
.laudo-header__meta-label { color: #7FA8BC !important; }
.laudo-header__meta-value { color: #EAF2F5 !important; }

div[data-testid="stVerticalBlockBorderWrapper"] {
    background: var(--color-surface); border: 1px solid var(--color-line);
    border-radius: 10px; box-shadow: 0 1px 3px rgba(11, 41, 66, 0.04);
}

.stTextArea textarea, .stTextInput input, .stNumberInput input {
    background-color: var(--color-surface) !important; color: var(--color-ink) !important;
    border: 1.5px solid var(--color-line) !important; border-radius: 7px !important;
    font-family: var(--font-mono) !important; font-size: 13.5px !important;
}
.stTextArea textarea:focus, .stTextInput input:focus, .stNumberInput input:focus {
    border-color: var(--color-accent) !important; box-shadow: 0 0 0 3px var(--color-accent-soft) !important;
}
.stSelectbox div[data-baseweb="select"], .stMultiSelect div[data-baseweb="select"] {
    background-color: var(--color-surface) !important; border-radius: 7px !important;
}
span[data-baseweb="tag"] { background-color: var(--color-accent) !important; border-radius: 5px !important; }

.streamlit-expanderHeader, div[data-testid="stExpander"] summary {
    background-color: var(--color-accent-soft) !important; border-radius: 8px !important;
    font-weight: 600 !important; color: var(--color-ink) !important;
}
div[data-testid="stExpander"] { border: 1px solid var(--color-line) !important; border-radius: 8px !important; }

.stButton button {
    border-radius: 7px !important; font-weight: 600 !important; font-family: var(--font-body) !important;
    border: 1.5px solid var(--color-line) !important; background-color: var(--color-surface) !important;
    color: var(--color-ink) !important; transition: all 0.12s ease;
}
.stButton button:hover { border-color: var(--color-accent) !important; color: var(--color-accent) !important; }

button[kind="primary"] {
    background-color: var(--color-danger) !important; color: white !important; border: none !important;
    border-radius: 7px !important; box-shadow: 0 2px 6px -1px rgba(185, 28, 28, 0.35) !important;
}
button[kind="primary"]:hover { background-color: #9B1818 !important; }

.stDownloadButton button, .copy-btn {
    background-color: var(--color-success) !important; color: white !important; border-radius: 8px !important;
    font-weight: 600 !important; font-family: var(--font-body) !important; height: 46px !important;
    width: 100% !important; border: none !important; box-shadow: 0 4px 10px -3px rgba(15, 118, 110, 0.4) !important;
    cursor: pointer; transition: background-color 0.12s ease;
}
.stDownloadButton button:hover, .copy-btn:hover { background-color: #0B5C56 !important; }

div[data-testid="stAlert"] { border-radius: 8px !important; border-left: 4px solid var(--color-accent) !important; }
div[data-testid="stAlert"] p { font-weight: 500 !important; }
hr { border-color: var(--color-line) !important; margin: 22px 0 !important; }

.legenda-venograma {
    display: flex; gap: 16px; flex-wrap: wrap; margin-top: 10px;
    font-family: var(--font-mono); font-size: 11.5px; color: var(--color-muted);
}
.legenda-item { display: flex; align-items: center; gap: 6px; }
.legenda-cor { width: 14px; height: 14px; border-radius: 3px; display: inline-block; }

.dica-ajuda {
    background: var(--color-accent-soft); border-left: 3px solid var(--color-accent);
    border-radius: 6px; padding: 10px 14px; font-size: 12.5px; color: var(--color-ink) !important;
    margin: 6px 0 14px 0;
}
</style>
"""

st.markdown(CSS_TEMA, unsafe_allow_html=True)


# =====================================================================
# 1. CONSTANTES, ENUMS E TEXTOS DE AJUDA
# =====================================================================
# Strings centralizadas aqui (em vez de espalhadas pelo código) para
# evitar erro de digitação silencioso em comparações.

LATERALIDADES = ["Direito", "Esquerdo"]

VEIAS_PROFUNDAS = [
    "Femoral comum", "Femoral superficial", "Femoral profunda",
    "Poplítea", "Tibiais", "Fibulares", "Musculares da panturrilha",
]

TIPOS_TROMBOSE = [
    "Trombose Aguda",
    "Trombose Crônica Não Recanalizada",
    "Trombose Crônica Parcialmente Recanalizada",
]

ACHADOS_SUPERFICIAIS = [
    "Safenectomia Magna Total", "Safenectomia Magna Parcial",
    "Safena Magna - Incompetência Parcial", "Safena Magna - Incompetência Total",
    "Safena Magna - Incompetência Segmentar",
    "Safenectomia Parva Total", "Safenectomia Parva Parcial",
    "Safena Parva - Incompetência Parcial", "Safena Parva - Incompetência Total",
    "Tromboflebite de Safena", "Microvarizes", "Varizes Poplíteas",
]

# Grupos mutuamente exclusivos — não faz sentido clínico ter mais de um
# achado do mesmo grupo simultaneamente (ex.: veia retirada + veia incompetente).
GRUPO_EXCLUSIVO_MAGNA = [
    "Safenectomia Magna Total", "Safenectomia Magna Parcial",
    "Safena Magna - Incompetência Parcial", "Safena Magna - Incompetência Total",
    "Safena Magna - Incompetência Segmentar",
]
GRUPO_EXCLUSIVO_PARVA = [
    "Safenectomia Parva Total", "Safenectomia Parva Parcial",
    "Safena Parva - Incompetência Parcial", "Safena Parva - Incompetência Total",
]

ORIGENS_REFLUXO = ["perfurante incompetente", "tributária"]
SEGMENTOS_MEMBRO = [
    "proximal da coxa", "médio da coxa", "distal da coxa",
    "proximal da perna", "médio da perna", "distal da perna",
]
REFERENCIAS_ANATOMICAS = [
    "abaixo da junção safenofemoral", "acima da interlinha do joelho", "abaixo da interlinha do joelho",
]
REFERENCIAS_FINAL_PARVA = ["abaixo da interlinha do joelho", "acima da planta do pé"]
DRENAGENS_REFLUXO = ["tributárias", "perfurantes"]
VEIAS_FLEBITE = ["magna", "parva"]
LOCALIZACOES_MEMBRO = ["coxa", "perna"]
FACES_MEMBRO = ["anterior", "medial", "lateral", "posterior"]
REFERENCIAS_PERFURANTE = ["Planta do pé", "Junção safenofemoral", "Interlinha do joelho"]
FACES_PERFURANTE = ["Medial", "Lateral", "Anterior", "Posterior"]

CORES_DESENHO = ["Azul (normal)", "Vermelho (refluxo)", "Preto (trombo)"]
STROKE_POR_COR = {
    "Azul (normal)": "rgba(21, 94, 117, 0.85)",
    "Vermelho (refluxo)": "rgba(185, 28, 28, 0.85)",
    "Preto (trombo)": "rgba(15, 23, 32, 0.9)",
}

FERRAMENTAS_DESENHO = ["transform", "line", "freedraw", "circle"]
LABEL_FERRAMENTA = {
    "transform": "🖱️ Selecionar/Mover",
    "line": "📏 Linha",
    "freedraw": "✏️ Lápis livre",
    "circle": "⭕ Círculo",
}

# Textos de ajuda — aparecem como ícone "?" ao lado do campo (parâmetro help=).
# Escritos para quem NÃO é da área de saúde.
AJUDA = {
    "lateralidade": "Em qual perna (membro inferior) o exame está sendo feito.",
    "sistema_profundo": (
        "As veias profundas ficam no meio da perna, perto dos ossos — são as mais "
        "importantes porque levam a maior parte do sangue de volta ao coração. "
        "Se há suspeita de trombose, é aqui que se verifica primeiro."
    ),
    "veias_alteradas": "Marque qual(is) veia(s) profunda(s) está(ão) com problema.",
    "tipo_alteracao": (
        "Aguda = trombo recente (mais grave, sangue não passa).\n"
        "Crônica não recanalizada = trombo antigo, vaso ainda bloqueado.\n"
        "Crônica parcialmente recanalizada = trombo antigo, mas o corpo já abriu "
        "parte do caminho para o sangue passar de novo."
    ),
    "sistema_superficial": (
        "As veias superficiais ficam mais perto da pele — são as 'veias da "
        "safena', frequentemente associadas a varizes."
    ),
    "achados_superficiais": (
        "Safenectomia = a veia foi removida em cirurgia anterior.\n"
        "Incompetência = a veia existe, mas a válvula não fecha bem e o sangue "
        "reflui (volta) em vez de subir — é a causa mais comum de varizes."
    ),
    "jsf": (
        "Junção Safenofemoral (JSF) é o ponto onde a veia safena magna se conecta "
        "com a veia profunda da virilha. Se essa 'válvula de entrada' não fecha "
        "bem, o refluxo começa logo ali."
    ),
    "jsp": (
        "Junção Safenopoplítea (JSP) é o ponto onde a veia safena parva se conecta "
        "com a veia poplítea, atrás do joelho."
    ),
    "origem_refluxo": (
        "De onde está vindo o refluxo, quando não é direto da virilha (JSF): "
        "de uma veia perfurante (que atravessa o músculo) ou de uma tributária "
        "(um ramo menor que se conecta à safena)."
    ),
    "drenagem": "Para onde o sangue que está refluindo está sendo desviado/escoado.",
    "distancia_cm": "Distância em centímetros até o ponto de referência indicado ao lado.",
    "perfurantes": (
        "Veias perfurantes atravessam o músculo conectando o sistema superficial "
        "ao profundo. Quando 'insuficientes', também causam varizes e ficam "
        "marcadas como pontos no desenho da perna."
    ),
    "biometria": "Medidas do calibre (diâmetro) da veia em cada ponto, em centímetros.",
    "flebite": "Inflamação da veia com formação de coágulo dentro dela, geralmente na veia safena.",
    "venograma_auto": (
        "Este desenho é gerado automaticamente a partir do que você preencheu "
        "acima. Azul = normal, vermelho = refluxo, preto = trombo, pontos = "
        "perfurantes. Você ainda pode desenhar por cima manualmente, se quiser "
        "ajustar ou adicionar algo."
    ),
}


# =====================================================================
# 2. MODELOS DE DADOS (dataclasses simples — sem lógica, só estado)
# =====================================================================

@dataclass
class SegmentoMagnaExtra:
    origem: str
    seg_origem: str
    dist_origem: str
    ref_origem: str
    seg_extensao: str
    dist_extensao: str
    ref_extensao: str
    drenagem: str


@dataclass
class DadosPerfurante:
    distancia_cm: str
    referencia: str
    localizacao: str
    face: str

    def to_texto(self) -> str:
        return (
            f"- Insuficiente localizada a {self.distancia_cm} cm da "
            f"{self.referencia.lower()}, na face {self.face.lower()} "
            f"da {self.localizacao.lower()}."
        )

    @property
    def localizacao_norm(self) -> str:
        """'Coxa'/'Perna' -> 'coxa'/'perna', usado para mapear no venograma."""
        return self.localizacao.lower()


def inicializar_estado() -> None:
    """Garante que todas as chaves de sessão existem antes de usá-las."""
    defaults = {
        "perf_list": [],
        "magna_seg_list": [],
        "seg_k": 0,
        "confirmar_reset": False,
        "protocolo_numero": f"{date.today().strftime('%Y%m%d')}-{random.randint(1000, 9999)}",
    }
    for chave, valor in defaults.items():
        if chave not in st.session_state:
            st.session_state[chave] = valor


CHAVES_ESTADO_PACIENTE = ["perf_list", "magna_seg_list", "seg_k", "protocolo_numero"]


# =====================================================================
# 3. VENOGRAMA AUTOMÁTICO (overlay sobre imagem anatômica de referência)
# =====================================================================
# A imagem `base_venograma.png` deve estar na raiz do repositório.
# É o template anatômico real (3 painéis: SUPERFICIAL-JSF, SUPERFICIAL,
# SISTEMA PROFUNDO), com MID e MIE em cada painel. Ao carregar, este
# código desenha em CIMA da imagem os traços coloridos correspondentes
# aos achados do exame e os pontos de perfurante, e devolve uma PIL.Image
# pronta — que é usada tanto para exibição estática quanto como background
# do canvas editável (para a assistente desenhar ajustes manuais por cima).
#
# Cores: azul = normal/competente, vermelho = refluxo/perfurante,
# preto = trombo.

COR_NORMAL = (21, 94, 117, 255)      # azul (#155E75)
COR_REFLUXO = (185, 28, 28, 255)     # vermelho (#B91C1C)
COR_TROMBO = (11, 19, 32, 255)       # preto/grafite (#0B1320)
COR_PERFURANTE = (185, 28, 28, 255)  # vermelho (mesmo do refluxo, conforme pedido)

LARGURA_BASE = 1180
ALTURA_BASE = 680
LARGURA_TRACO = 6
RAIO_PONTO = 9

# --- Coordenadas calibradas sobre a imagem base 1180x680 ---
# Calibradas visualmente conferindo os marcos anatômicos (virilha, joelho,
# tornozelo) sobre os pontos brancos do template original. Cada painel
# tem suas próprias coordenadas porque os 3 painéis não são alinhados
# pixel-a-pixel entre si na imagem fonte.
#
# Convenção: P1 e P3 mostram MID à esquerda do painel e MIE à direita;
# P2 está invertido (MIE à esquerda, MID à direita) como na imagem original.

COORDS_VENOGRAMA = {
    "P1": {  # Superficial-JSF
        "MID":  {"virilha": (135, 110), "joelho": (130, 350), "tornozelo": (130, 600)},
        "MIE":  {"virilha": (245, 110), "joelho": (250, 350), "tornozelo": (255, 600)},
    },
    "P2": {  # Superficial
        "MIE":  {"virilha": (510, 240), "joelho": (510, 390), "tornozelo": (520, 595)},
        "MID":  {"virilha": (650, 240), "joelho": (650, 390), "tornozelo": (640, 595)},
    },
    "P3": {  # Sistema Profundo
        "MID":  {"virilha": (920, 100), "joelho": (915, 360), "tornozelo": (905, 595)},
        "MIE":  {"virilha": (1060, 100), "joelho": (1065, 360), "tornozelo": (1075, 595)},
    },
}

# Onde cada nome de segmento clínico cai ao longo da trilha virilha→joelho→tornozelo
# (valor entre 0 = virilha e 1 = tornozelo). Coxa = 0..joelho, Perna = joelho..tornozelo.
FRACAO_SEGMENTO = {
    "proximal da coxa": 0.10, "médio da coxa": 0.25, "distal da coxa": 0.40,
    "proximal da perna": 0.58, "médio da perna": 0.75, "distal da perna": 0.92,
}
FRACAO_JOELHO = 0.50  # ponto onde a coxa termina e a perna começa
FRACAO_PARVA_INICIO = 0.52  # safena parva começa logo abaixo do joelho


def _interpolar(p1: tuple[int, int], p2: tuple[int, int], t: float) -> tuple[int, int]:
    """Interpola linearmente entre dois pontos."""
    return (
        int(p1[0] + (p2[0] - p1[0]) * t),
        int(p1[1] + (p2[1] - p1[1]) * t),
    )


def _ponto_na_trilha(painel: str, lado: str, fracao: float) -> tuple[int, int]:
    """
    Posição (x, y) na imagem base correspondente a uma fração 0..1 da
    trilha anatômica virilha→joelho→tornozelo, no painel/lado indicados.
    """
    marcos = COORDS_VENOGRAMA[painel][lado]
    if fracao <= FRACAO_JOELHO:
        # coxa: virilha (fracao=0) -> joelho (fracao=FRACAO_JOELHO)
        t = fracao / FRACAO_JOELHO if FRACAO_JOELHO > 0 else 0
        return _interpolar(marcos["virilha"], marcos["joelho"], t)
    # perna: joelho -> tornozelo
    t = (fracao - FRACAO_JOELHO) / (1.0 - FRACAO_JOELHO)
    return _interpolar(marcos["joelho"], marcos["tornozelo"], t)


def _fracao_para_segmento(segmento: str) -> float:
    return FRACAO_SEGMENTO.get(segmento, 0.5)


def _carregar_base() -> Image.Image:
    """Carrega a imagem do template anatômico, ou cria fundo neutro se ausente."""
    caminho = os.path.join(os.path.dirname(os.path.abspath(__file__)), "base_venograma.png")
    if os.path.exists(caminho):
        return Image.open(caminho).convert("RGBA")
    # Fallback: fundo branco com aviso (não quebra o app se o asset não foi subido ainda)
    bg = Image.new("RGBA", (LARGURA_BASE, ALTURA_BASE), (245, 247, 250, 255))
    return bg


def _desenhar_segmento_magna(draw: ImageDraw.ImageDraw, painel: str, lado: str, dados: DadosExame) -> None:
    """Desenha o trajeto da safena magna (virilha → tornozelo) com cores conforme achados."""
    achados = dados.achados_superficiais

    def linha(f1, f2, cor):
        p1 = _ponto_na_trilha(painel, lado, f1)
        p2 = _ponto_na_trilha(painel, lado, f2)
        draw.line([p1, p2], fill=cor, width=LARGURA_TRACO)

    if "Safenectomia Magna Total" in achados:
        return  # nada a desenhar
    if "Safenectomia Magna Parcial" in achados:
        # mantém apenas o terço distal da perna
        linha(0.80, 1.00, COR_NORMAL)
        return
    if "Safena Magna - Incompetência Total" in achados:
        linha(0.0, 1.0, COR_REFLUXO)
        return
    if dados.algum(["Safena Magna - Incompetência Parcial", "Safena Magna - Incompetência Segmentar"]):
        f_inicio = 0.0 if dados.magna_jsf_incompetente else _fracao_para_segmento(dados.magna_seg_origem)
        f_fim = _fracao_para_segmento(dados.magna_seg_extensao)
        f_a, f_b = min(f_inicio, f_fim), max(f_inicio, f_fim)
        if f_a > 0:
            linha(0, f_a, COR_NORMAL)
        if f_b > f_a:
            linha(f_a, f_b, COR_REFLUXO)
        if f_b < 1.0:
            linha(f_b, 1.0, COR_NORMAL)
        for seg in dados.magna_segmentos_extra:
            fs = _fracao_para_segmento(seg.seg_origem)
            fe = _fracao_para_segmento(seg.seg_extensao)
            linha(min(fs, fe), max(fs, fe), COR_REFLUXO)
        return

    linha(0.0, 1.0, COR_NORMAL)


def _desenhar_segmento_parva(draw: ImageDraw.ImageDraw, painel: str, lado: str, dados: DadosExame) -> None:
    """Desenha o trajeto da safena parva (do joelho ao tornozelo) — só faz sentido no Painel 2."""
    achados = dados.achados_superficiais

    def linha(f1, f2, cor):
        # Parva existe só a partir do joelho; deslocamos lateralmente um pouco
        # para não ficar exatamente em cima da magna no mesmo painel.
        p1 = _ponto_na_trilha(painel, lado, f1)
        p2 = _ponto_na_trilha(painel, lado, f2)
        # deslocamento lateral (para fora do corpo) — direção depende do lado
        dx = 9 if lado == "MID" else -9
        draw.line([(p1[0] + dx, p1[1]), (p2[0] + dx, p2[1])], fill=cor, width=LARGURA_TRACO)

    if "Safenectomia Parva Total" in achados:
        return
    if "Safenectomia Parva Parcial" in achados:
        linha(0.75, 1.0, COR_NORMAL)
        return
    if "Safena Parva - Incompetência Total" in achados:
        linha(FRACAO_PARVA_INICIO, 1.0, COR_REFLUXO)
        return
    if "Safena Parva - Incompetência Parcial" in achados:
        f_fim = max(FRACAO_PARVA_INICIO, _fracao_para_segmento(dados.parva_extensao_segmento))
        linha(FRACAO_PARVA_INICIO, f_fim, COR_REFLUXO)
        if f_fim < 1.0:
            linha(f_fim, 1.0, COR_NORMAL)
        return

    linha(FRACAO_PARVA_INICIO, 1.0, COR_NORMAL)


def _desenhar_segmento_profundo(draw: ImageDraw.ImageDraw, painel: str, lado: str, dados: DadosExame) -> None:
    """Desenha o trajeto do sistema profundo (preto se trombose, azul se normal)."""
    cor = COR_TROMBO if (dados.sp_status == "Não" and dados.sp_veias) else COR_NORMAL
    largura = LARGURA_TRACO + 2 if cor == COR_TROMBO else LARGURA_TRACO
    p1 = _ponto_na_trilha(painel, lado, 0.0)
    p2 = _ponto_na_trilha(painel, lado, 0.5)
    p3 = _ponto_na_trilha(painel, lado, 1.0)
    draw.line([p1, p2], fill=cor, width=largura)
    draw.line([p2, p3], fill=cor, width=largura)


def _desenhar_ponto_jsf(draw: ImageDraw.ImageDraw, painel: str, lado: str, dados: DadosExame) -> None:
    """Marca a Junção Safenofemoral (bolinha na virilha) — vermelha se incompetente."""
    jsf_incompetente = (
        "Safena Magna - Incompetência Total" in dados.achados_superficiais
        or (dados.algum(["Safena Magna - Incompetência Parcial", "Safena Magna - Incompetência Segmentar"])
            and dados.magna_jsf_incompetente)
    )
    cor = COR_REFLUXO if jsf_incompetente else COR_NORMAL
    x, y = _ponto_na_trilha(painel, lado, 0.0)
    r = RAIO_PONTO + 1
    draw.ellipse([x - r, y - r, x + r, y + r], fill=cor, outline=(255, 255, 255, 255), width=2)


def _desenhar_perfurantes(draw: ImageDraw.ImageDraw, painel: str, lado: str, dados: DadosExame) -> None:
    """Marca as perfurantes insuficientes como bolinhas vermelhas no Painel 2 (superficial)."""
    contador: dict[tuple[str, str], int] = {}
    for p in dados.perfurantes:
        chave = (p.localizacao_norm, p.face.lower())
        idx = contador.get(chave, 0)
        contador[chave] = idx + 1

        # Localização aproximada: 0.25 (coxa) ou 0.75 (perna) na trilha,
        # com deslocamento vertical para perfurantes repetidas na mesma região
        fracao_base = 0.30 if p.localizacao_norm == "coxa" else 0.78
        fracao = min(0.95, fracao_base + idx * 0.06)
        x, y = _ponto_na_trilha(painel, lado, fracao)
        # Deslocamento lateral conforme face medial/lateral
        dx = -12 if p.face.lower() in ("medial", "anterior") else 12
        if lado == "MIE":
            dx = -dx
        r = RAIO_PONTO
        draw.ellipse(
            [x + dx - r, y - r, x + dx + r, y + r],
            fill=COR_PERFURANTE, outline=(255, 255, 255, 255), width=2,
        )


def desenhar_venograma(dados: DadosExame) -> Image.Image:
    """
    Gera a imagem completa do venograma: imagem base + overlay clínico.
    Retorna uma PIL.Image RGBA pronta para exibir ou usar como background de canvas.
    """
    base = _carregar_base().copy()
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    lado_alvo = "MID" if dados.lateralidade == "Direito" else "MIE"
    lado_outro = "MIE" if lado_alvo == "MID" else "MID"

    # Painel 1 (Superficial-JSF): trajeto da magna + ponto JSF
    for lado in ("MID", "MIE"):
        dados_lado = dados if lado == lado_alvo else None
        if dados_lado is None:
            # Lado não examinado: desenha em azul normal (sem dados clínicos para ele)
            p1 = _ponto_na_trilha("P1", lado, 0.0)
            p2 = _ponto_na_trilha("P1", lado, 1.0)
            draw.line([p1, p2], fill=COR_NORMAL, width=LARGURA_TRACO)
            x, y = p1
            r = RAIO_PONTO + 1
            draw.ellipse([x-r, y-r, x+r, y+r], fill=COR_NORMAL, outline=(255,255,255,255), width=2)
        else:
            _desenhar_segmento_magna(draw, "P1", lado, dados)
            _desenhar_ponto_jsf(draw, "P1", lado, dados)

    # Painel 2 (Superficial): magna + parva + perfurantes
    for lado in ("MID", "MIE"):
        if lado != lado_alvo:
            p1 = _ponto_na_trilha("P2", lado, 0.0)
            p2 = _ponto_na_trilha("P2", lado, 1.0)
            draw.line([p1, p2], fill=COR_NORMAL, width=LARGURA_TRACO)
        else:
            _desenhar_segmento_magna(draw, "P2", lado, dados)
            _desenhar_segmento_parva(draw, "P2", lado, dados)
            _desenhar_perfurantes(draw, "P2", lado, dados)

    # Painel 3 (Sistema Profundo)
    for lado in ("MID", "MIE"):
        if lado != lado_alvo:
            p1 = _ponto_na_trilha("P3", lado, 0.0)
            p2 = _ponto_na_trilha("P3", lado, 1.0)
            draw.line([p1, p2], fill=COR_NORMAL, width=LARGURA_TRACO)
        else:
            _desenhar_segmento_profundo(draw, "P3", lado, dados)

    return Image.alpha_composite(base, overlay)


def venograma_para_bytes(img: Image.Image) -> bytes:
    """Converte a imagem do venograma para bytes PNG (para download)."""
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# =====================================================================
# 4. ESTADO AGREGADO DO EXAME + GERAÇÃO DE TEXTO DO LAUDO
# =====================================================================

@dataclass
class DadosExame:
    lateralidade: str = "Direito"
    sp_status: str = "Normal"
    sp_veias: list[str] = field(default_factory=list)
    sp_tipo_alteracao: str = ""
    achados_superficiais: list[str] = field(default_factory=list)

    magna_jsf_incompetente: bool = True
    magna_origem: str = ""
    magna_seg_origem: str = ""
    magna_dist_origem: str = ""
    magna_ref_origem: str = ""
    magna_seg_extensao: str = "proximal da coxa"
    magna_dist_extensao: str = ""
    magna_ref_extensao: str = ""
    magna_drenagem: str = ""
    magna_segmentos_extra: list[SegmentoMagnaExtra] = field(default_factory=list)

    parva_jsp_incompetente: bool = True
    parva_extensao_segmento: str = "proximal da perna"
    parva_drenagem: str = ""
    parva_dist_final: str = ""
    parva_ref_final: str = ""

    flebite_veia: str = ""
    flebite_local: str = ""
    flebite_face: str = ""
    flebite_extensao_cm: str = ""

    bio_safenectomia_parcial: bool = False
    bio_coxa_distal: str = "xxx"
    bio_perna_proximal_posop: str = "xxx"
    bio_crossa: str = "0,6"
    bio_coxa: str = "xxx"
    bio_perna: str = "xxx"
    medida_parva_cm: str = "0,2"

    perfurantes: list[DadosPerfurante] = field(default_factory=list)

    def tem(self, achado: str) -> bool:
        return achado in self.achados_superficiais

    def algum(self, achados: list[str]) -> bool:
        return any(a in self.achados_superficiais for a in achados)


def validar_exame(d: DadosExame) -> list[str]:
    erros = []
    sel_magna = [a for a in GRUPO_EXCLUSIVO_MAGNA if d.tem(a)]
    if len(sel_magna) > 1:
        erros.append(
            f"Combinação inválida na Safena Magna: {', '.join(sel_magna)} não podem "
            "ser marcados juntos — escolha apenas um status para essa veia."
        )
    sel_parva = [a for a in GRUPO_EXCLUSIVO_PARVA if d.tem(a)]
    if len(sel_parva) > 1:
        erros.append(
            f"Combinação inválida na Safena Parva: {', '.join(sel_parva)} não podem "
            "ser marcados juntos — escolha apenas um status para essa veia."
        )
    if d.sp_status == "Não" and not d.sp_veias:
        erros.append(
            "Sistema profundo foi marcado como alterado, mas nenhuma veia foi "
            "selecionada. Selecione ao menos uma veia ou marque como Normal."
        )
    return erros


METODOLOGIA = (
    "METODOLOGIA: Exame realizado em modo bidimensional com transdutor "
    "linear multifrequencial."
)
HEADER_PROFUNDO = (
    "Sistema profundo (Veias femoral comum, superficial e profunda; "
    "poplítea, tibiais, fibulares e musculares da panturrilha):"
)


def _lista_veias_str(veias: list[str]) -> str:
    if len(veias) > 1:
        return ", ".join(veias[:-1]) + " e " + veias[-1]
    return veias[0]


def gerar_secao_profundo(d: DadosExame) -> tuple[str, str]:
    if not (d.sp_status == "Não" and d.sp_veias):
        descricao = (
            f"{HEADER_PROFUNDO}\nVeias tronculares pérvias, ausência de refluxo às "
            "manobras provocativas.\nAusência de compressão extrínseca, dilatação ou "
            "trombos.\nFluxo espontâneo e fásico com a respiração."
        )
        return descricao, "- Sistema profundo pérvio e competente."

    veias = d.sp_veias
    v_str = _lista_veias_str(veias)
    plural = "s" if len(veias) > 1 else ""
    comp_p = "veis" if len(veias) > 1 else "vel"

    if d.sp_tipo_alteracao == "Trombose Aguda":
        detalhe = (
            f"\nVeia{plural} {v_str} de calibre{plural} aumentado{plural}, com "
            f"material hipoecogênico no interior, não compressí{comp_p}, e sem "
            "fluxo detectável ao estudo Doppler."
        )
        impressao = f"- Sinais de trombose venosa profunda aguda das veias {v_str}."
    elif d.sp_tipo_alteracao == "Trombose Crônica Não Recanalizada":
        detalhe = (
            f"\nVeia{plural} {v_str} de calibre{plural} levemente aumentado{plural}, "
            f"com material hiperecogênico no interior, aderido à parede do vaso, "
            f"não compressí{comp_p}, com discretos sinais de recanalização."
        )
        impressao = f"- Sinais de trombose venosa profunda subaguda/crônica não recanalizada das veias {v_str}."
    else:
        detalhe = (
            f"\nVeia{plural} {v_str} de calibre{plural} levemente reduzido{plural} "
            f"com material hiperecogênico e traves no interior, parcialmente "
            f"compressí{comp_p}, de paredes espessas e com sinais de recanalização parcial."
        )
        impressao = f"- Sinais de trombose venosa profunda crônica parcialmente recanalizada das veias {v_str}."

    descricao = (
        f"{HEADER_PROFUNDO}\nVeias tronculares pérvias, ausência de refluxo às "
        "manobras provocativas.\nAusência de compressão extrínseca ou dilatação.\n"
        f"Fluxo espontâneo e fásico com a respiração.{detalhe}"
    )
    return descricao, impressao


def gerar_texto_biometria_magna(d: DadosExame) -> str:
    if d.bio_safenectomia_parcial:
        return f"Mede {d.bio_coxa_distal} cm (coxa distal) e {d.bio_perna_proximal_posop} cm (perna proximal)."
    return f"Mede {d.bio_crossa} cm (crossa), {d.bio_coxa} cm (coxa) e {d.bio_perna} cm (perna)."


def gerar_secao_magna(d: DadosExame) -> tuple[str, str, str]:
    """Retorna (texto_descritivo_completo, base_sem_medidas, impressao)."""
    achados = d.achados_superficiais

    if "Safenectomia Magna Total" in achados:
        base = "Veia safena magna não caracterizada em toda sua extensão (status pós-operatório)."
        return base, base, "- Sinais de safenectomia magna total."

    if "Safenectomia Magna Parcial" in achados:
        base = (
            "Veia safena magna não caracterizada nos 2/3 proximais da coxa "
            "(status pós-operatório). Demais segmentos pérvios."
        )
        completo = f"{base}.\n{gerar_texto_biometria_magna(d)}"
        return completo, base, "- Sinais de safenectomia magna parcial."

    incompetencia_parcial_ou_seg = d.algum([
        "Safena Magna - Incompetência Parcial", "Safena Magna - Incompetência Segmentar",
    ])

    if "Safena Magna - Incompetência Total" in achados:
        base = "Veia safena magna pérvia e incompetente, apresentando refluxo em todo seu trajeto"
        impressao = "- Veia safena magna pérvia e incompetente em todo seu trajeto."
    elif incompetencia_parcial_ou_seg:
        if d.magna_jsf_incompetente:
            base = (
                "Veia safena magna com junção safenofemoral incompetente e com "
                f"refluxo com extensão até o terço {d.magna_seg_extensao}, "
                f"{d.magna_dist_extensao} cm {d.magna_ref_extensao} e drenagem de "
                f"refluxo para {d.magna_drenagem}"
            )
        else:
            base = (
                "Veia safena magna com junção safenofemoral competente e com "
                f"refluxo proveniente de {d.magna_origem} no segmento "
                f"{d.magna_seg_origem}, {d.magna_dist_origem} cm {d.magna_ref_origem}, "
                f"com extensão até o terço {d.magna_seg_extensao}, "
                f"{d.magna_dist_extensao} cm {d.magna_ref_extensao} e drenagem de "
                f"refluxo para {d.magna_drenagem}"
            )
        if "Safena Magna - Incompetência Segmentar" in achados:
            for seg in d.magna_segmentos_extra:
                base += (
                    f"\n*Volta a tornar-se incompetente com refluxo proveniente de "
                    f"{seg.origem} no segmento {seg.seg_origem}, {seg.dist_origem} cm "
                    f"{seg.ref_origem}, com extensão até o terço {seg.seg_extensao}, "
                    f"{seg.dist_extensao} cm {seg.ref_extensao} e drenagem de refluxo "
                    f"para {seg.drenagem}*"
                )
        impressao = "- Veia safena magna pérvia e parcialmente incompetente."
    else:
        base = "Veia safena magna pérvia e competente em todo trajeto"
        impressao = "- Veia safena magna pérvia e competente em todo trajeto."

    if "Tromboflebite de Safena" in achados and d.flebite_veia == "magna":
        base += (
            f", de calibre aumentado, com material hipoecogênico, não compressível, "
            f"na {d.flebite_local}, em sua face {d.flebite_face}, estendendo-se por "
            f"{d.flebite_extensao_cm} cm"
        )

    completo = f"{base}.\n{gerar_texto_biometria_magna(d)}"
    return completo, base, impressao


def gerar_secao_parva(d: DadosExame) -> tuple[str, str]:
    achados = d.achados_superficiais

    if "Safenectomia Parva Total" in achados:
        base = "Veia safena parva não caracterizada em toda sua extensão (status pós-operatório)."
        return base, "- Sinais de safenectomia parva total."

    if "Safenectomia Parva Parcial" in achados:
        base = (
            "Veia safena parva não caracterizada nos segmentos proximal/médio da "
            "perna (status pós-operatório). Demais segmentos pérvios."
        )
        completo = f"{base}.\nMede {d.medida_parva_cm} cm (perna proximal)."
        return completo, "- Sinais de safenectomia parva parcial."

    if "Safena Parva - Incompetência Total" in achados:
        base = "Veia safena parva pérvia e incompetente, apresentando refluxo em todo seu trajeto"
        impressao = "- Veia safena parva pérvia e incompetente em todo seu trajeto."
    elif "Safena Parva - Incompetência Parcial" in achados:
        jsp_txt = "incompetente" if d.parva_jsp_incompetente else "competente"
        base = (
            f"Veia safena parva com junção safenopoplítea {jsp_txt}, com refluxo "
            f"que se estende até o segmento {d.parva_extensao_segmento} e "
            f"transferência para {d.parva_drenagem}, {d.parva_dist_final} cm "
            f"{d.parva_ref_final}"
        )
        impressao = "- Veia safena parva pérvia e parcialmente incompetente."
    else:
        base = "Veia safena parva pérvia e competente em todo trajeto"
        impressao = "- Veia safena parva pérvia e competente em todo trajeto."

    if "Tromboflebite de Safena" in achados and d.flebite_veia == "parva":
        base += (
            f", de calibre aumentado, com material hipoecogênico, não compressível, "
            f"na {d.flebite_local}, em sua face {d.flebite_face}, estendendo-se por "
            f"{d.flebite_extensao_cm} cm"
        )

    completo = f"{base}.\nMede {d.medida_parva_cm} cm (perna proximal)."
    return completo, impressao


def gerar_impressoes_extras(d: DadosExame) -> list[str]:
    extras = []
    achados = d.achados_superficiais
    if "Tromboflebite de Safena" in achados:
        nome_veia = d.flebite_veia or "—"
        extras.append(f"- Sinais de tromboflebite de veia safena {nome_veia} na {d.flebite_local}.")
    if "Microvarizes" in achados:
        extras.append("- Microvarizes sem representação ao Doppler.")
    if "Varizes Poplíteas" in achados:
        extras.append("- Veias varicosas drenando na veia poplítea.")
    return extras


def gerar_texto_extras_descritivo(d: DadosExame) -> str:
    texto = ""
    achados = d.achados_superficiais
    if "Microvarizes" in achados:
        texto += "\nMicrovarizes presentes clinicamente sem representação ao estudo Doppler."
    if "Varizes Poplíteas" in achados:
        texto += "\nVeias varicosas drenando na veia poplítea."
    return texto


def gerar_laudo_completo(d: DadosExame) -> str:
    desc_profundo, imp_profundo = gerar_secao_profundo(d)
    texto_magna, _, imp_magna = gerar_secao_magna(d)
    texto_parva, imp_parva = gerar_secao_parva(d)
    texto_extras = gerar_texto_extras_descritivo(d)
    impressoes_extras = gerar_impressoes_extras(d)
    texto_perf = "\n".join(p.to_texto() for p in d.perfurantes) if d.perfurantes else "Ausência de perfurantes insuficientes."
    imp_perf = "- Perfurante insuficiente." if d.perfurantes else ""
    linhas_extras = "".join(f"\n{x}" for x in impressoes_extras)

    laudo = f"""ECO-DOPPLER VENOSO DE MEMBRO INFERIOR {d.lateralidade.upper()}

{METODOLOGIA}

{desc_profundo}

Sistema superficial:
{texto_magna}

{texto_parva}{texto_extras}
Varizes superficiais conforme ectoscopia.

Perfurantes:
{texto_perf}

IMPRESSÃO DIAGNÓSTICA:
{imp_profundo}
{imp_magna}
{imp_parva}
- Varizes superficiais conforme ectoscopia.{linhas_extras}
{imp_perf}"""
    return laudo.strip()


# =====================================================================
# 5. COMPONENTES VISUAIS REUTILIZÁVEIS
# =====================================================================

def renderizar_cabecalho_institucional(lateralidade: str) -> None:
    data_str = date.today().strftime("%d/%m/%Y")
    # NOTA: as cores são definidas inline aqui (não via classe CSS) porque
    # regras genéricas como `h1, p, span { color: var(--color-ink) }` em
    # outras partes do CSS estavam vencendo as cores claras definidas em
    # .laudo-header__* — deixando título invisível sobre o fundo escuro.
    # Estilo inline tem especificidade máxima e é à prova de qualquer override.
    st.markdown(
        f"""
        <div class="laudo-header">
            <p class="laudo-header__eyebrow" style="color:#9FC4D6 !important; font-family: 'IBM Plex Mono', monospace; font-size: 11px; letter-spacing: 0.14em; text-transform: uppercase; font-weight: 500; margin: 0 0 6px 0;">Ecografia Vascular · Sistema Venoso</p>
            <h1 class="laudo-header__title" style="color:#FFFFFF !important; font-family: 'IBM Plex Sans', sans-serif; font-size: 26px; font-weight: 650; letter-spacing: -0.01em; margin: 0; padding: 0; border: none;">Laudo de Eco-Doppler Venoso</h1>
            <p class="laudo-header__sub" style="color:#C7D9E2 !important; font-size: 13px; margin: 6px 0 0 0;">Assistente de preenchimento durante o exame — membro inferior</p>
            <div class="laudo-header__meta" style="display: flex; gap: 26px; margin-top: 16px; padding-top: 14px; border-top: 1px solid rgba(255,255,255,0.14); flex-wrap: wrap;">
                <div style="display: flex; flex-direction: column; gap: 2px;">
                    <span style="color:#7FA8BC !important; font-family: 'IBM Plex Mono', monospace; font-size: 10px; letter-spacing: 0.1em; text-transform: uppercase;">Protocolo</span>
                    <span style="color:#EAF2F5 !important; font-family: 'IBM Plex Mono', monospace; font-size: 14px; font-weight: 500;">{st.session_state['protocolo_numero']}</span>
                </div>
                <div style="display: flex; flex-direction: column; gap: 2px;">
                    <span style="color:#7FA8BC !important; font-family: 'IBM Plex Mono', monospace; font-size: 10px; letter-spacing: 0.1em; text-transform: uppercase;">Data</span>
                    <span style="color:#EAF2F5 !important; font-family: 'IBM Plex Mono', monospace; font-size: 14px; font-weight: 500;">{data_str}</span>
                </div>
                <div style="display: flex; flex-direction: column; gap: 2px;">
                    <span style="color:#7FA8BC !important; font-family: 'IBM Plex Mono', monospace; font-size: 10px; letter-spacing: 0.1em; text-transform: uppercase;">Membro</span>
                    <span style="color:#EAF2F5 !important; font-family: 'IBM Plex Mono', monospace; font-size: 14px; font-weight: 500;">{html.escape(lateralidade)}</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def titulo_secao(numero: str, titulo: str, descricao: str = "") -> None:
    desc_html = f'<p class="secao-protocolo__desc">{html.escape(descricao)}</p>' if descricao else ""
    st.markdown(
        f"""
        <div class="secao-protocolo">
            <span class="secao-protocolo__numero">{numero}</span>
            <div class="secao-protocolo__texto">
                <h3>{html.escape(titulo)}</h3>
                {desc_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def dica(texto: str) -> None:
    """Caixa de dica/explicação visível diretamente na tela (não só tooltip)."""
    st.markdown(f'<div class="dica-ajuda">💡 {html.escape(texto)}</div>', unsafe_allow_html=True)


# =====================================================================
# 6. SEÇÕES DA INTERFACE
# =====================================================================

def secao_identificacao() -> str:
    titulo_secao("01", "Identificação e Lateralidade", "Membro examinado")
    return st.radio(
        "Membro Inferior:", LATERALIDADES, horizontal=True,
        help=AJUDA["lateralidade"],
    )


def secao_sistema_profundo() -> tuple[str, list[str], str]:
    st.markdown("**Sistema Profundo**", help=AJUDA["sistema_profundo"])
    status = st.radio(
        "Sistema profundo normal?", ["Normal", "Não"], horizontal=True,
        key="sp_status_radio",
    )
    veias: list[str] = []
    tipo_alt = ""
    if status == "Não":
        veias = st.multiselect(
            "Veias profundas alteradas:", VEIAS_PROFUNDAS,
            help=AJUDA["veias_alteradas"],
        )
        tipo_alt = st.selectbox(
            "Tipo de alteração:", TIPOS_TROMBOSE,
            help=AJUDA["tipo_alteracao"],
        )
        if not veias:
            st.warning(
                "⚠️ Você marcou o sistema profundo como alterado, mas ainda não "
                "selecionou nenhuma veia. Selecione ao menos uma — sem isso, o "
                "laudo vai sair como se tudo estivesse normal."
            )
    return status, veias, tipo_alt


def secao_sistema_superficial() -> list[str]:
    st.markdown("**Sistema Superficial**", help=AJUDA["sistema_superficial"])
    status_sup = st.radio(
        "Sistema superficial normal?", ["Normal", "Não"], horizontal=True,
        key="sup_status_radio",
    )
    if status_sup == "Normal":
        return []
    return st.multiselect(
        "Achados superficiais:", ACHADOS_SUPERFICIAIS,
        help=AJUDA["achados_superficiais"],
    )


def secao_detalhes_magna(achados_sup: list[str], d: DadosExame) -> None:
    if not any(x in achados_sup for x in (
        "Safena Magna - Incompetência Parcial", "Safena Magna - Incompetência Segmentar",
    )):
        return

    with st.expander("Detalhes da Incompetência — Safena Magna", expanded=True):
        jsf_sim = st.radio(
            "Junção Safenofemoral incompetente?", ["Sim", "Não"], horizontal=True,
            help=AJUDA["jsf"], key="magna_jsf_radio",
        )
        d.magna_jsf_incompetente = jsf_sim == "Sim"

        if not d.magna_jsf_incompetente:
            col1, col2 = st.columns(2)
            d.magna_origem = col1.selectbox("Origem do refluxo:", ORIGENS_REFLUXO, help=AJUDA["origem_refluxo"])
            d.magna_seg_origem = col2.selectbox("Segmento origem:", SEGMENTOS_MEMBRO)
            d.magna_dist_origem = st.text_input("Distância Origem (cm):", help=AJUDA["distancia_cm"])
            d.magna_ref_origem = st.selectbox("Referência Origem:", REFERENCIAS_ANATOMICAS)

        d.magna_seg_extensao = st.selectbox("Extensão do refluxo até o terço:", SEGMENTOS_MEMBRO)
        d.magna_dist_extensao = st.text_input("Distância Extensão (cm):", help=AJUDA["distancia_cm"])
        d.magna_ref_extensao = st.selectbox("Referência Extensão:", REFERENCIAS_ANATOMICAS)
        d.magna_drenagem = st.selectbox("Drenagem de refluxo para:", DRENAGENS_REFLUXO, help=AJUDA["drenagem"])

        if "Safena Magna - Incompetência Segmentar" in achados_sup:
            d.magna_segmentos_extra = _ui_segmentos_extra_magna()


def _ui_segmentos_extra_magna() -> list[SegmentoMagnaExtra]:
    st.markdown("---")
    st.markdown("**Adicionar Novo Segmento Insuficiente**")
    dica("Use isso quando a veia volta a ficar incompetente em mais de um trecho separado, não num trajeto único.")
    k = st.session_state.seg_k
    c1, c2 = st.columns(2)
    s_origem = c1.selectbox("Nova Origem:", ORIGENS_REFLUXO, key=f"o_{k}")
    s_seg_ori = c2.selectbox("Novo Seg. Origem:", SEGMENTOS_MEMBRO, key=f"so_{k}")
    s_dist_ori = st.text_input("Distância Nova Origem (cm):", key=f"do_{k}", help=AJUDA["distancia_cm"])
    s_ref_ori = st.selectbox("Ref. Nova Origem:", REFERENCIAS_ANATOMICAS, key=f"ro_{k}")
    s_seg_ext = st.selectbox("Nova Extensão até o terço:", SEGMENTOS_MEMBRO, key=f"se_{k}")
    s_dist_ext = st.text_input("Distância Nova Extensão (cm):", key=f"de_{k}", help=AJUDA["distancia_cm"])
    s_ref_ext = st.selectbox("Ref. Nova Extensão:", REFERENCIAS_ANATOMICAS, key=f"re_{k}")
    s_drenagem = st.selectbox("Nova Drenagem para:", DRENAGENS_REFLUXO, key=f"dr_{k}")

    if st.button("Adicionar segmento extra", use_container_width=True):
        if not s_dist_ori or not s_dist_ext:
            st.error("Informe as distâncias de origem e extensão antes de adicionar.")
        else:
            st.session_state.magna_seg_list.append(SegmentoMagnaExtra(
                origem=s_origem, seg_origem=s_seg_ori, dist_origem=s_dist_ori, ref_origem=s_ref_ori,
                seg_extensao=s_seg_ext, dist_extensao=s_dist_ext, ref_extensao=s_ref_ext, drenagem=s_drenagem,
            ))
            st.session_state.seg_k += 1
            st.rerun()

    for i, seg in enumerate(st.session_state.magna_seg_list):
        col_info, col_del = st.columns([5, 1])
        col_info.info(
            f"Origem: {seg.origem} ({seg.seg_origem}, {seg.dist_origem} cm {seg.ref_origem}) "
            f"→ Extensão: {seg.seg_extensao}, {seg.dist_extensao} cm {seg.ref_extensao} "
            f"→ Drenagem: {seg.drenagem}"
        )
        if col_del.button("🗑️", key=f"del_seg_{i}"):
            st.session_state.magna_seg_list.pop(i)
            st.rerun()

    return list(st.session_state.magna_seg_list)


def secao_detalhes_parva(achados_sup: list[str], d: DadosExame) -> None:
    if "Safena Parva - Incompetência Parcial" not in achados_sup:
        return
    with st.expander("Detalhes — Safena Parva", expanded=True):
        jsp_sim = st.radio(
            "Junção Safenopoplítea incompetente?", ["Sim", "Não"], horizontal=True,
            help=AJUDA["jsp"], key="parva_jsp_radio",
        )
        d.parva_jsp_incompetente = jsp_sim == "Sim"
        d.parva_extensao_segmento = st.selectbox("Refluxo até segmento:", ["proximal da perna", "médio da perna", "distal da perna"])
        d.parva_drenagem = st.selectbox("Transferência para:", DRENAGENS_REFLUXO, help=AJUDA["drenagem"])
        d.parva_dist_final = st.text_input("Distância final (cm):", help=AJUDA["distancia_cm"])
        d.parva_ref_final = st.selectbox("Referência final:", REFERENCIAS_FINAL_PARVA)


def secao_detalhes_flebite(achados_sup: list[str], d: DadosExame) -> None:
    precisa_flebite = "Tromboflebite de Safena" in achados_sup
    precisa_varizes = "Varizes Poplíteas" in achados_sup
    if not (precisa_flebite or precisa_varizes):
        return
    with st.expander("Detalhes Adicionais — Tromboflebite / Varizes", expanded=True):
        if not precisa_flebite:
            return
        dica(AJUDA["flebite"])
        d.flebite_veia = st.selectbox("Veia com flebite:", VEIAS_FLEBITE)
        d.flebite_local = st.selectbox("Localização:", LOCALIZACOES_MEMBRO)
        d.flebite_face = st.selectbox("Face:", FACES_MEMBRO)
        d.flebite_extensao_cm = st.text_input("Extensão (cm) da flebite:", help=AJUDA["distancia_cm"])


def secao_biometria(achados_sup: list[str], d: DadosExame) -> None:
    titulo_secao("03", "Biometria Vascular", "Medidas das veias safenas")
    dica(AJUDA["biometria"])
    st.markdown("**Veia Safena Magna**")

    d.bio_safenectomia_parcial = "Safenectomia Magna Parcial" in achados_sup
    if d.bio_safenectomia_parcial:
        c1, c2 = st.columns(2)
        d.bio_coxa_distal = c1.text_input("Coxa distal (cm)", "xxx")
        d.bio_perna_proximal_posop = c2.text_input("Perna proximal (cm)", "xxx")
    else:
        c1, c2, c3 = st.columns(3)
        d.bio_crossa = c1.text_input("Crossa (cm)", "0,6")
        d.bio_coxa = c2.text_input("Coxa (cm)", "xxx")
        d.bio_perna = c3.text_input("Perna (cm)", "xxx")

    st.markdown("**Veia Safena Parva**")
    d.medida_parva_cm = st.text_input("Perna Proximal (cm)", "0,2")


def secao_perfurantes() -> list[DadosPerfurante]:
    titulo_secao("04", "Veias Perfurantes", "Pontos de insuficiência identificados")
    dica(AJUDA["perfurantes"])

    tem_perf = st.radio("Existem perfurantes insuficientes?", ["Não", "Sim"], horizontal=True)
    if tem_perf == "Sim":
        c1, c2, c3, c4 = st.columns(4)
        p_dist = c1.text_input("Distância (cm)", help=AJUDA["distancia_cm"])
        p_ref = c2.selectbox("Referência:", REFERENCIAS_PERFURANTE)
        p_loc = c3.selectbox("Localização:", ["Coxa", "Perna"])
        p_face = c4.selectbox("Face:", FACES_PERFURANTE)

        col_add, col_clear = st.columns(2)
        if col_add.button("Adicionar perfurante", use_container_width=True):
            if not p_dist:
                st.error("Informe a distância antes de adicionar a perfurante.")
            else:
                st.session_state.perf_list.append(DadosPerfurante(p_dist, p_ref, p_loc, p_face))
                st.rerun()
        if col_clear.button("Limpar lista", use_container_width=True):
            st.session_state.perf_list = []
            st.rerun()

        for i, p in enumerate(st.session_state.perf_list):
            col_info, col_del = st.columns([5, 1])
            col_info.info(p.to_texto())
            if col_del.button("🗑️", key=f"del_perf_{i}"):
                st.session_state.perf_list.pop(i)
                st.rerun()

    return list(st.session_state.perf_list)


def secao_laudo_editavel(laudo_final: str) -> None:
    titulo_secao("05", "Laudo Final", "Revise e edite antes de finalizar")
    laudo_edit = st.text_area(
        "Texto do laudo:", value=laudo_final.strip(), height=560,
        label_visibility="collapsed",
    )
    texto_json = json.dumps(laudo_edit)
    componente_html = f"""
        <textarea id="txt_laudo" style="display:none;">{html.escape(laudo_edit)}</textarea>
        <button onclick='navigator.clipboard.writeText({texto_json}); this.innerText="Laudo copiado ✓"; setTimeout(() => this.innerText="Copiar laudo", 1800);' class="copy-btn">
            Copiar laudo
        </button>
    """
    st.components.v1.html(componente_html, height=64)


def secao_venograma(d: DadosExame) -> None:
    titulo_secao("06", "Venograma", "Mapa anatômico anotado automaticamente")
    dica(AJUDA["venograma_auto"])

    # Gera a imagem do venograma com as marcações automáticas (azul=normal,
    # vermelho=refluxo/perfurante, preto=trombo) sobrepostas na imagem
    # anatômica de referência. Esta mesma imagem servirá como fundo do
    # canvas, permitindo à assistente desenhar ajustes manuais por cima
    # — não há mais "imagem automática" + "canvas separado", é tudo um só.
    venograma_img = desenhar_venograma(d)

    # Legenda
    st.markdown(
        """
        <div class="legenda-venograma">
            <span class="legenda-item"><span class="legenda-cor" style="background:#155E75;"></span>Normal (azul)</span>
            <span class="legenda-item"><span class="legenda-cor" style="background:#B91C1C;"></span>Refluxo (vermelho)</span>
            <span class="legenda-item"><span class="legenda-cor" style="background:#0B1320;"></span>Trombo (preto)</span>
            <span class="legenda-item"><span class="legenda-cor" style="background:#B91C1C; border-radius:50%;"></span>Perfurante (bolinha vermelha)</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not CANVAS_DISPONIVEL:
        # Fallback: se a biblioteca de canvas não está instalada, mostra só a imagem estática.
        st.info(
            "Desenho manual indisponível (biblioteca `streamlit-drawable-canvas-fix` "
            "não instalada neste ambiente). O venograma automático abaixo continua funcionando."
        )
        st.image(venograma_img, use_container_width=True)
        st.download_button(
            "Baixar venograma (PNG)", venograma_para_bytes(venograma_img),
            "venograma.png", "image/png", use_container_width=True,
        )
        return

    st.markdown("**Ajuste manual (opcional)**")
    dica(
        "Você pode desenhar diretamente em cima do venograma automático para "
        "adicionar ou ajustar qualquer marcação. As alterações ficam sobre a "
        "mesma figura — não é um desenho separado."
    )

    t1, t2, t3 = st.columns([1.2, 2.2, 1.2])
    tool = t1.selectbox("Ferramenta:", FERRAMENTAS_DESENHO, format_func=lambda x: LABEL_FERRAMENTA[x])
    cor = t2.radio("Cor:", CORES_DESENHO, horizontal=True)
    peso = t3.slider("Espessura:", 1, 20, 6)
    stroke = STROKE_POR_COR[cor]

    # O canvas usa exatamente a imagem do venograma automático como background.
    # Assim, qualquer traço manual da assistente é desenhado SOBRE o mapa já
    # marcado — não há mais "duas figuras separadas".
    largura_canvas = LARGURA_BASE
    altura_canvas = ALTURA_BASE

    canvas_result = st_canvas(
        fill_color="rgba(255, 255, 255, 0)",
        stroke_width=peso,
        stroke_color=stroke,
        background_image=venograma_img,
        height=altura_canvas,
        width=largura_canvas,
        drawing_mode=tool,
        update_streamlit=True,
        key="canvas_venograma",
    )

    # Combina o desenho manual (overlay do canvas) com o venograma automático
    # para gerar a imagem final baixável — é literalmente a figura completa.
    #
    # IMPORTANTE: o streamlit-drawable-canvas retorna `image_data` com as
    # dimensões REAIS de renderização no navegador (que podem diferir dos
    # `width`/`height` que pedimos, dependendo do dispositivo/zoom/DPR).
    # Por isso precisamos redimensionar o overlay manual para o tamanho do
    # venograma antes de compor — caso contrário Pillow levanta
    # "ValueError: images do not match".
    final = venograma_img
    if canvas_result.image_data is not None:
        try:
            manual = Image.fromarray(canvas_result.image_data.astype("uint8"), "RGBA")
            base_rgba = venograma_img.convert("RGBA")
            if manual.size != base_rgba.size:
                manual = manual.resize(base_rgba.size, Image.LANCZOS)
            final = Image.alpha_composite(base_rgba, manual)
        except (ValueError, OSError) as e:
            # Em caso de qualquer erro na composição, cai de volta para a
            # imagem do venograma automático sem o overlay manual — o app
            # continua usável, só perde os traços feitos manualmente.
            st.warning(
                "Não foi possível combinar o desenho manual com o venograma. "
                "O download a seguir contém apenas as marcações automáticas. "
                f"(Detalhe técnico: {type(e).__name__})"
            )
            final = venograma_img

    st.download_button(
        "Baixar venograma (PNG)", venograma_para_bytes(final),
        "venograma.png", "image/png", use_container_width=True,
    )


# =====================================================================
# 7. ORQUESTRAÇÃO PRINCIPAL
# =====================================================================

def renderizar_barra_acoes() -> None:
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
    d = DadosExame()

    with st.container(border=True):
        d.lateralidade = secao_identificacao()

    with st.container(border=True):
        titulo_secao("02", "Sistemas Venosos", "Avaliação dos sistemas profundo e superficial")
        c1, c2 = st.columns(2)
        with c1:
            d.sp_status, d.sp_veias, d.sp_tipo_alteracao = secao_sistema_profundo()
        with c2:
            d.achados_superficiais = secao_sistema_superficial()

        secao_detalhes_magna(d.achados_superficiais, d)
        secao_detalhes_parva(d.achados_superficiais, d)
        secao_detalhes_flebite(d.achados_superficiais, d)

    with st.container(border=True):
        secao_biometria(d.achados_superficiais, d)

    with st.container(border=True):
        d.perfurantes = secao_perfurantes()

    return d


def main() -> None:
    inicializar_estado()
    renderizar_cabecalho_institucional(st.session_state.get("lateralidade_atual", "—"))
    renderizar_barra_acoes()

    dados = coletar_dados_exame()
    st.session_state["lateralidade_atual"] = dados.lateralidade

    erros = validar_exame(dados)
    for erro in erros:
        st.error(erro)

    laudo_final = gerar_laudo_completo(dados)

    with st.container(border=True):
        c_laudo, c_ven = st.columns([1, 1])
        with c_laudo:
            secao_laudo_editavel(laudo_final)
        with c_ven:
            secao_venograma(dados)


if __name__ == "__main__":
    main()
