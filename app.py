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
    2. Modelos de dados e estado isolado por exame
    3. Validação e normalização de medidas
    4. Geração de texto do laudo (lógica pura)
    5. Venograma manual em canvas isolado
    6. Componentes visuais e seções da interface
    7. Orquestração e autotestes
"""
from __future__ import annotations

import html
import io
import json
import os
import re
import uuid
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from datetime import date

import streamlit as st
from PIL import Image

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
@import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:wght@500;600&family=IBM+Plex+Mono:wght@400;500;600&family=Inter:wght@400;500;600;700&display=swap');

:root {
    /* Paleta clínica sóbria: grafite azulado, sem tons "SaaS genérico"
       (nada de roxo/violeta ou gradientes chapados). Pensada para uso
       prolongado em ambiente de exame com luminosidade reduzida. */
    --color-bg: #10161F;          /* fundo principal — quase preto, levemente azulado */
    --color-surface: #1A222E;     /* cartões/painéis */
    --color-surface-2: #212B39;   /* inputs, expanders */
    --color-surface-raised: #232E3D; /* header, elementos elevados */
    --color-ink: #E7EAEE;         /* texto principal */
    --color-ink-soft: #C4CBD6;    /* texto secundário */
    --color-muted: #8996A8;       /* labels, hints */
    --color-line: #2D3947;        /* divisores e bordas */
    --color-line-soft: #232C38;
    --color-accent: #4FA8D8;      /* azul acinzentado — clínico, não "tech blue" */
    --color-accent-strong: #7EC1E6;
    --color-accent-soft: #1C3040; /* fundo de tags/expanders abertos */
    --color-danger: #D97373;      /* vermelho terroso, menos "alerta de app" */
    --color-danger-soft: #33201F;
    --color-success: #5FAE8C;     /* verde acinzentado */
    --color-success-soft: #1A2C26;
    --color-warning: #C9A24B;
    --color-warning-soft: #2E2818;
    --font-display: 'Source Serif 4', Georgia, serif;
    --font-body: 'Inter', sans-serif;
    --font-mono: 'IBM Plex Mono', monospace;
    --radius-sm: 6px;
    --radius-md: 8px;
    --radius-lg: 12px;
}

.stApp { background-color: var(--color-bg) !important; font-family: var(--font-body); }
div[data-testid="stVerticalBlock"] > div.element-container { background-color: transparent; }
#MainMenu, footer, header[data-testid="stHeader"] { background-color: transparent; }
html, body, [class*="css"] { font-family: var(--font-body); }
.block-container { padding-top: 2rem !important; max-width: 1240px !important; }

/* ---------------------------------------------------------------- */
/* Cabeçalho institucional                                          */
/* ---------------------------------------------------------------- */
.laudo-header {
    position: relative;
    background: var(--color-surface-raised);
    border: 1px solid var(--color-line);
    border-left: 3px solid var(--color-accent);
    border-radius: var(--radius-lg);
    padding: 24px 28px 20px 26px;
    margin-bottom: 20px;
}
.laudo-header__eyebrow {
    font-family: var(--font-mono); font-size: 11px; letter-spacing: 0.13em;
    text-transform: uppercase; color: var(--color-accent-strong); font-weight: 500; margin: 0 0 6px 0;
}
.laudo-header__title {
    font-family: var(--font-display); font-size: 25px; font-weight: 600;
    letter-spacing: -0.01em; color: #FFFFFF; margin: 0;
}
.laudo-header__sub { font-size: 13px; color: var(--color-ink-soft); margin: 4px 0 0 0; }
.laudo-header__meta {
    display: flex; gap: 26px; margin-top: 16px; padding-top: 14px;
    border-top: 1px solid var(--color-line-soft); flex-wrap: wrap;
}
.laudo-header__meta-item { display: flex; flex-direction: column; gap: 2px; }
.laudo-header__meta-label {
    font-family: var(--font-mono); font-size: 10px; letter-spacing: 0.1em;
    text-transform: uppercase; color: var(--color-muted);
}
.laudo-header__meta-value { font-family: var(--font-mono); font-size: 13px; color: var(--color-ink); font-weight: 500; }

h1, h2, h3 { font-family: var(--font-display) !important; }
.secao-protocolo {
    display: flex; align-items: flex-start; gap: 12px; margin: 4px 0 14px 0;
    padding-bottom: 10px; border-bottom: 1px solid var(--color-line);
}
.secao-protocolo__numero {
    font-family: var(--font-mono); font-size: 11px; font-weight: 600;
    color: var(--color-accent-strong); background: var(--color-accent-soft);
    border-radius: var(--radius-sm); padding: 3px 8px; line-height: 1.4; white-space: nowrap; margin-top: 2px;
}
.secao-protocolo__texto h3 {
    margin: 0 !important; padding: 0 !important; border: none !important;
    color: var(--color-ink) !important; font-size: 16.5px !important; font-weight: 600 !important;
    font-family: var(--font-body) !important;
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
.laudo-header__eyebrow { color: var(--color-accent-strong) !important; }
.laudo-header__title { color: #FFFFFF !important; }
.laudo-header__sub { color: var(--color-ink-soft) !important; }
.laudo-header__meta-label { color: var(--color-muted) !important; }
.laudo-header__meta-value { color: var(--color-ink) !important; }

div[data-testid="stVerticalBlockBorderWrapper"] {
    background: var(--color-surface); border: 1px solid var(--color-line);
    border-radius: var(--radius-lg); box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
}
div[data-testid="stVerticalBlockBorderWrapper"] > div { padding: 4px 2px; }

.stTextArea textarea, .stTextInput input, .stNumberInput input {
    background-color: var(--color-surface-2) !important; color: var(--color-ink) !important;
    border: 1.5px solid var(--color-line) !important; border-radius: var(--radius-sm) !important;
    font-family: var(--font-mono) !important; font-size: 13.5px !important;
}
.stTextArea textarea::placeholder, .stTextInput input::placeholder, .stNumberInput input::placeholder {
    color: var(--color-muted) !important; opacity: 0.7;
}
.stTextArea textarea:focus, .stTextInput input:focus, .stNumberInput input:focus {
    border-color: var(--color-accent) !important; box-shadow: 0 0 0 3px var(--color-accent-soft) !important;
}

/* Selects e multiselects — Streamlit ≥1.5x usa combobox baseado em
   react-aria (sem os antigos data-baseweb). O campo em si e o popover de
   opções são elementos separados no DOM (o popover fica direto sob
   <body>), então os seletores por role/testid abaixo cobrem os dois. */
.react-aria-ComboBox [role="group"] {
    background-color: var(--color-surface-2) !important;
    border: 1.5px solid var(--color-line) !important;
    border-radius: var(--radius-sm) !important;
}
.react-aria-ComboBox input {
    background-color: transparent !important; color: var(--color-ink) !important;
}
.react-aria-ComboBox input::placeholder { color: var(--color-muted) !important; opacity: 0.8; }
.react-aria-ComboBox button svg { color: var(--color-muted) !important; }
[data-testid="stMultiSelectTagsContainer"] span[data-tag] {
    background-color: var(--color-accent-soft) !important; color: var(--color-accent-strong) !important;
    border-radius: 5px !important; border: 1px solid var(--color-accent) !important;
}
[data-testid="stMultiSelectTagsContainer"] span[data-tag] button { color: var(--color-accent-strong) !important; }

/* Popover que envolve o listbox (react-aria monta com fundo branco por
   padrão — sem isso sobra uma moldura branca em volta da caixa escura). */
div[role="listbox"], div[role="listbox"] > div, div:has(> div[role="listbox"]) {
    background-color: var(--color-surface-2) !important;
    border: 1px solid var(--color-line) !important;
    border-radius: var(--radius-sm) !important;
    box-shadow: 0 8px 20px -6px rgba(0, 0, 0, 0.5) !important;
}
div[role="option"] {
    color: var(--color-ink) !important; background-color: transparent !important;
}
div[role="option"]:hover, div[role="option"][aria-selected="true"] {
    background-color: var(--color-accent-soft) !important;
}

/* Radio/checkbox: marcadores precisam ser visíveis no escuro */
.stRadio div[role="radiogroup"] label, .stCheckbox label { color: var(--color-ink) !important; }

.streamlit-expanderHeader, div[data-testid="stExpander"] summary {
    background-color: var(--color-accent-soft) !important; border-radius: 8px !important;
    font-weight: 600 !important; color: var(--color-ink) !important;
}
div[data-testid="stExpander"] {
    border: 1px solid var(--color-line) !important; border-radius: 8px !important;
    background-color: var(--color-surface) !important;
}
div[data-testid="stExpander"] > div { background-color: var(--color-surface) !important; }

.stButton button {
    border-radius: var(--radius-sm) !important; font-weight: 600 !important; font-family: var(--font-body) !important;
    border: 1.5px solid var(--color-line) !important; background-color: var(--color-surface-2) !important;
    color: var(--color-ink) !important; transition: all 0.12s ease;
}
.stButton button:hover { border-color: var(--color-accent) !important; color: var(--color-accent-strong) !important; }

/* "Reiniciar paciente" — ação destrutiva, mas discreta até ser confirmada;
   nada de botão vermelho cheio disparando alarme visual o tempo todo. */
button[kind="primary"] {
    background-color: transparent !important; color: var(--color-muted) !important;
    border: 1.5px solid var(--color-line) !important; border-radius: var(--radius-sm) !important;
    font-weight: 500 !important; font-size: 13px !important; box-shadow: none !important;
}
button[kind="primary"]:hover {
    border-color: var(--color-danger) !important; color: var(--color-danger) !important;
    background-color: var(--color-danger-soft) !important;
}

.stDownloadButton button, .copy-btn {
    background-color: var(--color-surface-2) !important; color: var(--color-ink) !important;
    border: 1.5px solid var(--color-accent) !important; border-radius: var(--radius-sm) !important;
    font-weight: 600 !important; font-family: var(--font-body) !important; height: 44px !important;
    width: 100% !important; box-shadow: none !important;
    cursor: pointer; transition: all 0.12s ease;
}
.stDownloadButton button:hover, .copy-btn:hover {
    background-color: var(--color-accent) !important; color: #0E1620 !important;
}

/* Alerts (st.warning / st.error / st.info / st.success) com cores legíveis no escuro */
div[data-testid="stAlert"] { border-radius: var(--radius-sm) !important; border-left: 3px solid var(--color-accent) !important; }
div[data-testid="stAlert"], div[data-testid="stAlertContainer"] {
    background-color: var(--color-surface-2) !important;
}
div[data-testid="stAlert"] p, div[data-testid="stAlert"] div { color: var(--color-ink) !important; font-weight: 500 !important; }

hr { border-color: var(--color-line) !important; margin: 22px 0 !important; }

/* Iframe do canvas de desenho: sem borda própria feia do navegador, e
   centralizado no card (a largura do canvas é menor que o card, ver
   CANVAS_LARGURA em app.py, para nunca ficar cortado). */
.stCustomComponentV1 iframe { margin: 0 auto; display: block; }
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
}


# =====================================================================
# 2. MODELOS DE DADOS E ESTADO DO EXAME
# =====================================================================

# Mantemos o app em arquivo único de propósito, mas o estado de cada exame é
# namespaced por uma "época". Ao reiniciar o paciente, a época muda e nenhum
# widget antigo (inclusive canvas) pode vazar para o exame seguinte.

ECTOSCOPIA_OPCOES = [
    "Varizes superficiais conforme ectoscopia",
    "Sem varizes superficiais significativas",
    "Não informar no laudo",
]

MARCACOES_VENOGRAMA = {
    "Refluxo": "rgba(185, 28, 28, 0.85)",
    "Trombo": "rgba(15, 23, 32, 0.9)",
    "Veia normal": "rgba(21, 94, 117, 0.85)",
}


def _novo_protocolo() -> str:
    """Identificador legível com entropia suficiente para não colidir no dia."""
    return f"{date.today().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"


def _epoch() -> int:
    return int(st.session_state.get("paciente_epoch", 0))


def k(nome: str) -> str:
    """Chave de widget/estado isolada para o exame atual."""
    return f"{nome}__exame_{_epoch()}"


def _lista_estado(nome: str) -> list:
    chave = k(nome)
    if chave not in st.session_state:
        st.session_state[chave] = []
    return st.session_state[chave]


def inicializar_estado() -> None:
    if "paciente_epoch" not in st.session_state:
        st.session_state["paciente_epoch"] = 0
    if "confirmar_reset" not in st.session_state:
        st.session_state["confirmar_reset"] = False

    defaults_exame = {
        "protocolo_numero": _novo_protocolo(),
        "lateralidade": "Direito",
        "perf_list": [],
        "magna_seg_list": [],
        "seg_k": 0,
        "canvas_epoch": 0,
        "laudo_modo_manual": False,
        "laudo_manual": "",
        "laudo_base_manual": "",
    }
    for nome, valor in defaults_exame.items():
        chave = k(nome)
        if chave not in st.session_state:
            st.session_state[chave] = valor


def reiniciar_exame() -> None:
    """Descarta integralmente o namespace do exame atual e cria outro."""
    antigo = _epoch()
    sufixo = f"__exame_{antigo}"
    for chave in list(st.session_state.keys()):
        if isinstance(chave, str) and (chave.endswith(sufixo) or f"{sufixo}_" in chave):
            st.session_state.pop(chave, None)
    st.session_state["paciente_epoch"] = antigo + 1
    st.session_state["confirmar_reset"] = False
    inicializar_estado()


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
            f"- Insuficiente localizada a {_med(self.distancia_cm)} cm da "
            f"{self.referencia.lower()}, na face {self.face.lower()} "
            f"da {self.localizacao.lower()}."
        )

    @property
    def localizacao_norm(self) -> str:
        return self.localizacao.lower()


@dataclass
class DadosExame:
    lateralidade: str = "Direito"
    sp_status: str = "Normal"
    sp_veias: list[str] = field(default_factory=list)
    sp_tipo_alteracao: str = ""
    sup_status: str = "Normal"
    achados_superficiais: list[str] = field(default_factory=list)
    ectoscopia_status: str = ECTOSCOPIA_OPCOES[0]

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
    bio_coxa_distal: str = ""
    bio_perna_proximal_posop: str = ""
    bio_crossa: str = ""
    bio_coxa: str = ""
    bio_perna: str = ""
    medida_parva_cm: str = ""

    perfurantes: list[DadosPerfurante] = field(default_factory=list)

    def tem(self, achado: str) -> bool:
        return achado in self.achados_superficiais

    def algum(self, achados: list[str]) -> bool:
        return any(a in self.achados_superficiais for a in achados)


# =====================================================================
# 3. MEDIDAS, VALIDAÇÃO E REGRAS PURAS
# =====================================================================


def normalizar_medida(valor: str) -> tuple[str, str | None]:
    """Aceita vírgula ou ponto, rejeita negativos/texto e devolve decimal pt-BR."""
    bruto = (valor or "").strip().lower().replace("cm", "").strip()
    if not bruto:
        return "", "não informada"
    if not re.fullmatch(r"(?:\d+(?:[\.,]\d+)?|[\.,]\d+)", bruto):
        return "", "formato inválido"
    if bruto.startswith((",", ".")):
        bruto = "0" + bruto
    try:
        numero = Decimal(bruto.replace(",", "."))
    except InvalidOperation:
        return "", "formato inválido"
    if numero < 0:
        return "", "não pode ser negativa"
    normal = format(numero, "f")
    if "." in normal:
        normal = normal.rstrip("0").rstrip(".")
    return normal.replace(".", ","), None


def _med(valor: str) -> str:
    normal, erro = normalizar_medida(valor)
    return normal if not erro else "___"


def _exigir_medida(erros: list[str], valor: str, rotulo: str) -> None:
    _, erro = normalizar_medida(valor)
    if erro:
        erros.append(f"{rotulo}: {erro}.")


def validar_exame(d: DadosExame) -> tuple[list[str], list[str]]:
    """Retorna (erros bloqueantes, avisos não bloqueantes)."""
    erros: list[str] = []
    avisos: list[str] = []

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

    if d.sp_status == "Não":
        if not d.sp_veias:
            erros.append("Sistema profundo alterado sem nenhuma veia selecionada.")
        if not d.sp_tipo_alteracao:
            erros.append("Sistema profundo alterado sem tipo de alteração informado.")

    if d.sup_status == "Não" and not d.achados_superficiais:
        erros.append("Sistema superficial marcado como alterado sem nenhum achado selecionado.")

    # Biometria: safenectomia total não exige medida do segmento ausente.
    if d.tem("Safenectomia Magna Total"):
        pass
    elif d.tem("Safenectomia Magna Parcial"):
        _exigir_medida(erros, d.bio_coxa_distal, "Biometria da safena magna — coxa distal")
        _exigir_medida(erros, d.bio_perna_proximal_posop, "Biometria da safena magna — perna proximal")
    else:
        _exigir_medida(erros, d.bio_crossa, "Biometria da safena magna — crossa")
        _exigir_medida(erros, d.bio_coxa, "Biometria da safena magna — coxa")
        _exigir_medida(erros, d.bio_perna, "Biometria da safena magna — perna")

    if not d.tem("Safenectomia Parva Total"):
        _exigir_medida(erros, d.medida_parva_cm, "Biometria da safena parva — perna proximal")

    # Campos condicionais de refluxo.
    if d.algum(["Safena Magna - Incompetência Parcial", "Safena Magna - Incompetência Segmentar"]):
        _exigir_medida(erros, d.magna_dist_extensao, "Safena magna — distância da extensão do refluxo")
        if not d.magna_drenagem:
            erros.append("Safena magna — informe a drenagem do refluxo.")
        if not d.magna_jsf_incompetente:
            _exigir_medida(erros, d.magna_dist_origem, "Safena magna — distância da origem do refluxo")
            if not d.magna_origem:
                erros.append("Safena magna — informe a origem do refluxo.")
        if d.tem("Safena Magna - Incompetência Segmentar") and not d.magna_segmentos_extra:
            avisos.append("Incompetência segmentar da safena magna sem segmento adicional cadastrado; confirme se o segmento principal é suficiente.")

    if d.tem("Safena Parva - Incompetência Parcial"):
        _exigir_medida(erros, d.parva_dist_final, "Safena parva — distância final do refluxo")
        if not d.parva_drenagem:
            erros.append("Safena parva — informe a transferência/drenagem do refluxo.")

    if d.tem("Tromboflebite de Safena"):
        _exigir_medida(erros, d.flebite_extensao_cm, "Tromboflebite — extensão")
        if not d.flebite_veia:
            erros.append("Tromboflebite — informe a veia acometida.")

    for i, perf in enumerate(d.perfurantes, start=1):
        _exigir_medida(erros, perf.distancia_cm, f"Perfurante {i} — distância")

    return erros, avisos


# =====================================================================
# 4. GERAÇÃO DO LAUDO — LÓGICA PURA
# =====================================================================

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
    return veias[0] if veias else ""


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
    plural = len(veias) > 1
    sujeito = f"As veias {v_str}" if plural else f"A veia {v_str}"
    calibre = "calibres aumentados" if plural else "calibre aumentado"
    compressao = "não compressíveis" if plural else "não compressível"

    if d.sp_tipo_alteracao == "Trombose Aguda":
        detalhe = (
            f"{sujeito} apresenta(m) {calibre}, material hipoecogênico no interior, "
            f"{compressao} e sem fluxo detectável ao estudo Doppler."
        ).replace(" apresenta(m)", " apresentam" if plural else " apresenta")
        impressao = (
            f"- Sinais de trombose venosa profunda aguda nas veias {v_str}."
            if plural else f"- Sinais de trombose venosa profunda aguda na veia {v_str}."
        )
    elif d.sp_tipo_alteracao == "Trombose Crônica Não Recanalizada":
        detalhe = (
            f"{sujeito} apresenta(m) material hiperecogênico aderido à parede, "
            f"{compressao} e sem sinais de recanalização ao estudo Doppler."
        ).replace(" apresenta(m)", " apresentam" if plural else " apresenta")
        impressao = (
            f"- Sinais de trombose venosa profunda crônica não recanalizada nas veias {v_str}."
            if plural else f"- Sinais de trombose venosa profunda crônica não recanalizada na veia {v_str}."
        )
    else:
        detalhe = (
            f"{sujeito} apresenta(m) {'calibres levemente reduzidos' if plural else 'calibre levemente reduzido'}, material hiperecogênico e "
            f"traves no interior, parcialmente {'compressíveis' if plural else 'compressível'}, "
            "paredes espessas e sinais de recanalização parcial."
        ).replace(" apresenta(m)", " apresentam" if plural else " apresenta")
        impressao = (
            f"- Sinais de trombose venosa profunda crônica parcialmente recanalizada nas veias {v_str}."
            if plural else f"- Sinais de trombose venosa profunda crônica parcialmente recanalizada na veia {v_str}."
        )

    veias_normais = [v for v in VEIAS_PROFUNDAS if v not in veias]
    linhas = [HEADER_PROFUNDO, detalhe]
    if veias_normais:
        linhas.append(
            "Demais veias do sistema profundo pérvias, compressíveis, sem trombos e com "
            "fluxo espontâneo e fásico com a respiração."
        )
    linhas.append("Ausência de compressão extrínseca nas demais estruturas avaliadas.")
    return "\n".join(linhas), impressao


def gerar_texto_biometria_magna(d: DadosExame) -> str:
    if d.bio_safenectomia_parcial:
        return f"Mede {_med(d.bio_coxa_distal)} cm (coxa distal) e {_med(d.bio_perna_proximal_posop)} cm (perna proximal)."
    return f"Mede {_med(d.bio_crossa)} cm (crossa), {_med(d.bio_coxa)} cm (coxa) e {_med(d.bio_perna)} cm (perna)."


def gerar_secao_magna(d: DadosExame) -> tuple[str, str, str]:
    """Retorna (texto descritivo completo, base sem medidas, impressão)."""
    achados = d.achados_superficiais

    if "Safenectomia Magna Total" in achados:
        base = "Veia safena magna não caracterizada em toda sua extensão (status pós-operatório)."
        return base, base, "- Sinais de safenectomia magna total."

    if "Safenectomia Magna Parcial" in achados:
        base = (
            "Veia safena magna não caracterizada nos 2/3 proximais da coxa "
            "(status pós-operatório). Demais segmentos pérvios."
        )
        completo = f"{base}\n{gerar_texto_biometria_magna(d)}"
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
                f"{_med(d.magna_dist_extensao)} cm {d.magna_ref_extensao} e drenagem de "
                f"refluxo para {d.magna_drenagem}"
            )
        else:
            base = (
                "Veia safena magna com junção safenofemoral competente e com "
                f"refluxo proveniente de {d.magna_origem} no segmento "
                f"{d.magna_seg_origem}, {_med(d.magna_dist_origem)} cm {d.magna_ref_origem}, "
                f"com extensão até o terço {d.magna_seg_extensao}, "
                f"{_med(d.magna_dist_extensao)} cm {d.magna_ref_extensao} e drenagem de "
                f"refluxo para {d.magna_drenagem}"
            )
        if "Safena Magna - Incompetência Segmentar" in achados:
            for seg in d.magna_segmentos_extra:
                base += (
                    f"\n*Volta a tornar-se incompetente com refluxo proveniente de "
                    f"{seg.origem} no segmento {seg.seg_origem}, {_med(seg.dist_origem)} cm "
                    f"{seg.ref_origem}, com extensão até o terço {seg.seg_extensao}, "
                    f"{_med(seg.dist_extensao)} cm {seg.ref_extensao} e drenagem de refluxo "
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
            f"{_med(d.flebite_extensao_cm)} cm"
        )

    completo = f"{base.rstrip('.')}.\n{gerar_texto_biometria_magna(d)}"
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
        completo = f"{base}\nMede {_med(d.medida_parva_cm)} cm (perna proximal)."
        return completo, "- Sinais de safenectomia parva parcial."

    if "Safena Parva - Incompetência Total" in achados:
        base = "Veia safena parva pérvia e incompetente, apresentando refluxo em todo seu trajeto"
        impressao = "- Veia safena parva pérvia e incompetente em todo seu trajeto."
    elif "Safena Parva - Incompetência Parcial" in achados:
        jsp_txt = "incompetente" if d.parva_jsp_incompetente else "competente"
        base = (
            f"Veia safena parva com junção safenopoplítea {jsp_txt}, com refluxo "
            f"que se estende até o segmento {d.parva_extensao_segmento} e "
            f"transferência para {d.parva_drenagem}, {_med(d.parva_dist_final)} cm "
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
            f"{_med(d.flebite_extensao_cm)} cm"
        )

    completo = f"{base.rstrip('.')}.\nMede {_med(d.medida_parva_cm)} cm (perna proximal)."
    return completo, impressao


def gerar_impressoes_extras(d: DadosExame) -> list[str]:
    extras: list[str] = []
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
    linhas: list[str] = []
    achados = d.achados_superficiais
    if "Microvarizes" in achados:
        linhas.append("Microvarizes presentes clinicamente sem representação ao estudo Doppler.")
    if "Varizes Poplíteas" in achados:
        linhas.append("Veias varicosas drenando na veia poplítea.")
    return "\n".join(linhas)


def gerar_ectoscopia(d: DadosExame) -> tuple[str, str]:
    if d.ectoscopia_status == "Varizes superficiais conforme ectoscopia":
        return "Varizes superficiais conforme ectoscopia.", "- Varizes superficiais conforme ectoscopia."
    if d.ectoscopia_status == "Sem varizes superficiais significativas":
        return "Ausência de varizes superficiais significativas à ectoscopia.", "- Ausência de varizes superficiais significativas à ectoscopia."
    return "", ""


def gerar_laudo_completo(d: DadosExame) -> str:
    desc_profundo, imp_profundo = gerar_secao_profundo(d)
    texto_magna, _, imp_magna = gerar_secao_magna(d)
    texto_parva, imp_parva = gerar_secao_parva(d)
    texto_extras = gerar_texto_extras_descritivo(d)
    impressoes_extras = gerar_impressoes_extras(d)
    ecto_desc, ecto_imp = gerar_ectoscopia(d)

    texto_perf = "\n".join(p.to_texto() for p in d.perfurantes) if d.perfurantes else "Ausência de perfurantes insuficientes."
    if len(d.perfurantes) == 1:
        imp_perf = "- Perfurante insuficiente."
    elif len(d.perfurantes) > 1:
        imp_perf = "- Perfurantes insuficientes."
    else:
        imp_perf = ""

    descricao_superficial = "\n".join(x for x in [texto_magna, texto_parva, texto_extras, ecto_desc] if x)
    impressoes = [imp_profundo, imp_magna, imp_parva, ecto_imp, *impressoes_extras]
    if imp_perf:
        impressoes.append(imp_perf)
    bloco_impressoes = "\n".join(x for x in impressoes if x)

    laudo = f"""ECO-DOPPLER VENOSO DE MEMBRO INFERIOR {d.lateralidade.upper()}

{METODOLOGIA}

{desc_profundo}

Sistema superficial:
{descricao_superficial}

Perfurantes:
{texto_perf}

IMPRESSÃO DIAGNÓSTICA:
{bloco_impressoes}"""
    return laudo.strip()


# =====================================================================
# 5. VENOGRAMA — ASSET CACHEADO E FRAGMENTO INDEPENDENTE
# =====================================================================

LARGURA_BASE = 1178
ALTURA_BASE = 678
CANVAS_LARGURA = 980
CANVAS_ALTURA = round(CANVAS_LARGURA * ALTURA_BASE / LARGURA_BASE)


@st.cache_data(show_spinner=False)
def _ler_base_venograma_bytes(caminho: str, mtime: float) -> bytes:
    # mtime participa da chave para o cache invalidar quando o asset mudar.
    del mtime
    with open(caminho, "rb") as f:
        return f.read()


def _carregar_base_venograma() -> Image.Image:
    caminho = os.path.join(os.path.dirname(os.path.abspath(__file__)), "base_venograma.png")
    if os.path.exists(caminho):
        dados = _ler_base_venograma_bytes(caminho, os.path.getmtime(caminho))
        return Image.open(io.BytesIO(dados)).convert("RGBA")
    return Image.new("RGBA", (LARGURA_BASE, ALTURA_BASE), (30, 41, 59, 255))


def venograma_para_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


fragmento = getattr(st, "fragment", lambda func: func)


@fragmento
def secao_venograma() -> None:
    titulo_secao("06", "Venograma", "Anotação manual sobre o mapa anatômico")
    fundo = _carregar_base_venograma()

    if not CANVAS_DISPONIVEL:
        st.info(
            "Desenho indisponível neste ambiente (`streamlit-drawable-canvas-fix` não instalada). "
            "Exibindo o template anatômico estático."
        )
        st.image(fundo, use_container_width=True)
        st.download_button(
            "Baixar venograma (PNG)", venograma_para_bytes(fundo),
            "venograma.png", "image/png", use_container_width=True,
        )
        return

    st.caption("Escolha o que quer marcar e desenhe diretamente no mapa. O restante do formulário não é reprocessado a cada traço.")
    c1, c2 = st.columns([2.2, 1])
    marcacao = c1.radio(
        "Marcação rápida", ["Refluxo", "Trombo", "Veia normal"],
        horizontal=True, key=k("venograma_marcacao"),
    )
    peso = c2.slider("Espessura", 1, 20, 6, key=k("venograma_peso"))

    with st.expander("Ferramentas de desenho", expanded=False):
        ferramenta_label = st.radio(
            "Ferramenta", ["Lápis livre", "Linha", "Círculo", "Selecionar / Mover"],
            horizontal=True, key=k("venograma_ferramenta"),
        )
        mapa_ferramenta = {
            "Lápis livre": "freedraw",
            "Linha": "line",
            "Círculo": "circle",
            "Selecionar / Mover": "transform",
        }
        desenho_modo = mapa_ferramenta[ferramenta_label]

        if st.button("Limpar desenho", key=k("limpar_canvas"), use_container_width=True):
            st.session_state[k("canvas_epoch")] = int(st.session_state.get(k("canvas_epoch"), 0)) + 1
            st.session_state.pop(k("canvas_json"), None)
            st.rerun(scope="fragment") if hasattr(st, "fragment") else st.rerun()

    canvas_key = f"{k('canvas_venograma')}_{st.session_state.get(k('canvas_epoch'), 0)}"
    kwargs_canvas = dict(
        fill_color="rgba(255, 255, 255, 0)",
        stroke_width=peso,
        stroke_color=MARCACOES_VENOGRAMA[marcacao],
        background_image=fundo,
        height=CANVAS_ALTURA,
        width=CANVAS_LARGURA,
        drawing_mode=desenho_modo,
        update_streamlit=True,
        key=canvas_key,
    )
    desenho_salvo = st.session_state.get(k("canvas_json"))
    if desenho_salvo:
        kwargs_canvas["initial_drawing"] = desenho_salvo

    canvas_result = st_canvas(**kwargs_canvas)
    if getattr(canvas_result, "json_data", None):
        st.session_state[k("canvas_json")] = canvas_result.json_data

    final = fundo
    if canvas_result.image_data is not None:
        try:
            manual = Image.fromarray(canvas_result.image_data.astype("uint8"), "RGBA")
            base_rgba = fundo.convert("RGBA")
            if manual.size != base_rgba.size:
                manual = manual.resize(base_rgba.size, Image.LANCZOS)
            final = Image.alpha_composite(base_rgba, manual)
        except (ValueError, OSError, TypeError) as e:
            st.warning(
                "Não foi possível combinar o desenho com o template. O download contém apenas "
                f"o template em branco. (Detalhe técnico: {type(e).__name__})"
            )
            final = fundo

    st.download_button(
        "Baixar venograma (PNG)", venograma_para_bytes(final),
        "venograma.png", "image/png", use_container_width=True,
    )


# =====================================================================
# 6. COMPONENTES VISUAIS REUTILIZÁVEIS
# =====================================================================


def renderizar_cabecalho_institucional(lateralidade: str) -> None:
    data_str = date.today().strftime("%d/%m/%Y")
    st.markdown(
        f"""
        <div class="laudo-header">
            <p class="laudo-header__eyebrow" style="color:#7EC1E6 !important; font-family:'IBM Plex Mono',monospace; font-size:11px; letter-spacing:.13em; text-transform:uppercase; font-weight:500; margin:0 0 6px 0;">Ecografia Vascular · Sistema Venoso</p>
            <h1 class="laudo-header__title" style="color:#FFFFFF !important; font-family:'Source Serif 4',Georgia,serif; font-size:25px; font-weight:600; margin:0; padding:0; border:none;">Laudo de Eco-Doppler Venoso</h1>
            <p class="laudo-header__sub" style="color:#C4CBD6 !important; font-size:13px; margin:6px 0 0 0;">Assistente de preenchimento durante o exame — membro inferior</p>
            <div class="laudo-header__meta" style="display:flex; gap:26px; margin-top:16px; padding-top:14px; border-top:1px solid #232C38; flex-wrap:wrap;">
                <div style="display:flex;flex-direction:column;gap:2px;"><span style="color:#8996A8 !important;font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:.1em;text-transform:uppercase;">Protocolo</span><span style="color:#E7EAEE !important;font-family:'IBM Plex Mono',monospace;font-size:14px;font-weight:500;">{html.escape(st.session_state[k('protocolo_numero')])}</span></div>
                <div style="display:flex;flex-direction:column;gap:2px;"><span style="color:#8996A8 !important;font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:.1em;text-transform:uppercase;">Data</span><span style="color:#E7EAEE !important;font-family:'IBM Plex Mono',monospace;font-size:14px;font-weight:500;">{data_str}</span></div>
                <div style="display:flex;flex-direction:column;gap:2px;"><span style="color:#8996A8 !important;font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:.1em;text-transform:uppercase;">Membro</span><span style="color:#E7EAEE !important;font-family:'IBM Plex Mono',monospace;font-size:14px;font-weight:500;">{html.escape(lateralidade)}</span></div>
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
            <span class="secao-protocolo__numero">{html.escape(numero)}</span>
            <div class="secao-protocolo__texto"><h3>{html.escape(titulo)}</h3>{desc_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =====================================================================
# 7. SEÇÕES DA INTERFACE — PROGRESSIVE DISCLOSURE
# =====================================================================


def aplicar_exame_sem_alteracoes() -> None:
    """Atalho: mantém sistemas normais e perfurantes ausentes; medidas seguem manuais."""
    st.session_state[k("sp_status_radio")] = "Normal"
    st.session_state[k("sup_status_radio")] = "Normal"
    st.session_state[k("sup_achados")] = []
    st.session_state[k("perf_status_radio")] = "Não"
    st.session_state[k("ectoscopia")] = "Sem varizes superficiais significativas"
    st.session_state[k("perf_list")] = []
    st.session_state[k("magna_seg_list")] = []


def secao_identificacao() -> str:
    titulo_secao("01", "Identificação e Lateralidade", "Comece pelo membro examinado")
    c1, c2 = st.columns([2, 1.4])
    lateralidade = c1.radio(
        "Membro inferior", LATERALIDADES, horizontal=True,
        help=AJUDA["lateralidade"], key=k("lateralidade"),
    )
    c2.write("")
    c2.button(
        "✓ Exame sem alterações", on_click=aplicar_exame_sem_alteracoes,
        use_container_width=True, help="Define profundo e superficial como normais e perfurantes como ausentes. As medidas continuam para preenchimento.",
        key=k("atalho_normal"),
    )
    return lateralidade


def secao_sistema_profundo() -> tuple[str, list[str], str]:
    st.markdown("**Sistema Profundo**", help=AJUDA["sistema_profundo"])
    status = st.radio(
        "Situação", ["Normal", "Não"], horizontal=True,
        key=k("sp_status_radio"), format_func=lambda x: "✓ Normal" if x == "Normal" else "Alterado",
    )
    veias: list[str] = []
    tipo_alt = ""
    if status == "Não":
        veias = st.multiselect(
            "Veias profundas alteradas", VEIAS_PROFUNDAS,
            help=AJUDA["veias_alteradas"], key=k("sp_veias"),
        )
        tipo_alt = st.selectbox(
            "Tipo de alteração", TIPOS_TROMBOSE,
            help=AJUDA["tipo_alteracao"], key=k("sp_tipo"),
        )
        if not veias:
            st.warning("Selecione ao menos uma veia alterada.")
    else:
        st.caption("Sem detalhes adicionais necessários.")
    return status, veias, tipo_alt


def secao_sistema_superficial() -> tuple[str, list[str], str]:
    st.markdown("**Sistema Superficial**", help=AJUDA["sistema_superficial"])
    status_sup = st.radio(
        "Situação", ["Normal", "Não"], horizontal=True,
        key=k("sup_status_radio"), format_func=lambda x: "✓ Normal" if x == "Normal" else "Alterado",
    )
    achados: list[str] = []
    if status_sup == "Não":
        achados = st.multiselect(
            "Achados superficiais", ACHADOS_SUPERFICIAIS,
            help=AJUDA["achados_superficiais"], key=k("sup_achados"),
        )
        if not achados:
            st.warning("Selecione ao menos um achado superficial.")
    else:
        st.caption("Sem detalhes adicionais necessários.")

    ectoscopia = st.selectbox(
        "Ectoscopia", ECTOSCOPIA_OPCOES, key=k("ectoscopia"),
        help="Torna explícita a frase de ectoscopia que antes era incluída automaticamente em todos os laudos.",
    )
    return status_sup, achados, ectoscopia


def secao_detalhes_magna(achados_sup: list[str], d: DadosExame) -> None:
    if not any(x in achados_sup for x in (
        "Safena Magna - Incompetência Parcial", "Safena Magna - Incompetência Segmentar",
    )):
        return

    with st.expander("Detalhes da incompetência — Safena Magna", expanded=True):
        jsf_sim = st.radio(
            "Junção Safenofemoral incompetente?", ["Sim", "Não"], horizontal=True,
            help=AJUDA["jsf"], key=k("magna_jsf_radio"),
        )
        d.magna_jsf_incompetente = jsf_sim == "Sim"
        if not d.magna_jsf_incompetente:
            col1, col2 = st.columns(2)
            d.magna_origem = col1.selectbox("Origem do refluxo", ORIGENS_REFLUXO, help=AJUDA["origem_refluxo"], key=k("magna_origem"))
            d.magna_seg_origem = col2.selectbox("Segmento origem", SEGMENTOS_MEMBRO, key=k("magna_seg_origem"))
            d.magna_dist_origem = st.text_input("Distância origem (cm)", help=AJUDA["distancia_cm"], key=k("magna_dist_origem"))
            d.magna_ref_origem = st.selectbox("Referência origem", REFERENCIAS_ANATOMICAS, key=k("magna_ref_origem"))

        d.magna_seg_extensao = st.selectbox("Extensão do refluxo até", SEGMENTOS_MEMBRO, key=k("magna_seg_extensao"))
        d.magna_dist_extensao = st.text_input("Distância da extensão (cm)", help=AJUDA["distancia_cm"], key=k("magna_dist_extensao"))
        d.magna_ref_extensao = st.selectbox("Referência da extensão", REFERENCIAS_ANATOMICAS, key=k("magna_ref_extensao"))
        d.magna_drenagem = st.selectbox("Drenagem do refluxo para", DRENAGENS_REFLUXO, help=AJUDA["drenagem"], key=k("magna_drenagem"))

        if "Safena Magna - Incompetência Segmentar" in achados_sup:
            d.magna_segmentos_extra = _ui_segmentos_extra_magna()


def _ui_segmentos_extra_magna() -> list[SegmentoMagnaExtra]:
    st.markdown("---")
    st.markdown("**Adicionar segmento insuficiente adicional**")
    contador_key = k("seg_k")
    contador = int(st.session_state.get(contador_key, 0))
    c1, c2 = st.columns(2)
    s_origem = c1.selectbox("Nova origem", ORIGENS_REFLUXO, key=k(f"o_{contador}"))
    s_seg_ori = c2.selectbox("Novo seg. origem", SEGMENTOS_MEMBRO, key=k(f"so_{contador}"))
    s_dist_ori = st.text_input("Distância nova origem (cm)", key=k(f"do_{contador}"), help=AJUDA["distancia_cm"])
    s_ref_ori = st.selectbox("Ref. nova origem", REFERENCIAS_ANATOMICAS, key=k(f"ro_{contador}"))
    s_seg_ext = st.selectbox("Nova extensão até", SEGMENTOS_MEMBRO, key=k(f"se_{contador}"))
    s_dist_ext = st.text_input("Distância nova extensão (cm)", key=k(f"de_{contador}"), help=AJUDA["distancia_cm"])
    s_ref_ext = st.selectbox("Ref. nova extensão", REFERENCIAS_ANATOMICAS, key=k(f"re_{contador}"))
    s_drenagem = st.selectbox("Nova drenagem para", DRENAGENS_REFLUXO, key=k(f"dr_{contador}"))

    if st.button("Adicionar segmento extra", use_container_width=True, key=k(f"add_seg_{contador}")):
        dist_ori, erro_ori = normalizar_medida(s_dist_ori)
        dist_ext, erro_ext = normalizar_medida(s_dist_ext)
        if erro_ori or erro_ext:
            st.error("Informe distâncias válidas para origem e extensão (use números, com vírgula ou ponto).")
        else:
            _lista_estado("magna_seg_list").append(SegmentoMagnaExtra(
                origem=s_origem, seg_origem=s_seg_ori, dist_origem=dist_ori, ref_origem=s_ref_ori,
                seg_extensao=s_seg_ext, dist_extensao=dist_ext, ref_extensao=s_ref_ext, drenagem=s_drenagem,
            ))
            st.session_state[contador_key] = contador + 1
            st.rerun()

    lista = _lista_estado("magna_seg_list")
    for i, seg in enumerate(list(lista)):
        col_info, col_del = st.columns([5, 1])
        col_info.info(
            f"Origem: {seg.origem} ({seg.seg_origem}, {seg.dist_origem} cm {seg.ref_origem}) "
            f"→ Extensão: {seg.seg_extensao}, {seg.dist_extensao} cm {seg.ref_extensao} "
            f"→ Drenagem: {seg.drenagem}"
        )
        if col_del.button("Remover", key=k(f"del_seg_{i}"), use_container_width=True):
            lista.pop(i)
            st.rerun()
    return list(lista)


def secao_detalhes_parva(achados_sup: list[str], d: DadosExame) -> None:
    if "Safena Parva - Incompetência Parcial" not in achados_sup:
        return
    with st.expander("Detalhes — Safena Parva", expanded=True):
        jsp_sim = st.radio(
            "Junção Safenopoplítea incompetente?", ["Sim", "Não"], horizontal=True,
            help=AJUDA["jsp"], key=k("parva_jsp_radio"),
        )
        d.parva_jsp_incompetente = jsp_sim == "Sim"
        d.parva_extensao_segmento = st.selectbox("Refluxo até segmento", ["proximal da perna", "médio da perna", "distal da perna"], key=k("parva_extensao"))
        d.parva_drenagem = st.selectbox("Transferência para", DRENAGENS_REFLUXO, help=AJUDA["drenagem"], key=k("parva_drenagem"))
        d.parva_dist_final = st.text_input("Distância final (cm)", help=AJUDA["distancia_cm"], key=k("parva_dist_final"))
        d.parva_ref_final = st.selectbox("Referência final", REFERENCIAS_FINAL_PARVA, key=k("parva_ref_final"))


def secao_detalhes_flebite(achados_sup: list[str], d: DadosExame) -> None:
    if "Tromboflebite de Safena" not in achados_sup:
        return
    with st.expander("Detalhes — Tromboflebite", expanded=True):
        d.flebite_veia = st.selectbox("Veia com flebite", VEIAS_FLEBITE, key=k("flebite_veia"))
        d.flebite_local = st.selectbox("Localização", LOCALIZACOES_MEMBRO, key=k("flebite_local"))
        d.flebite_face = st.selectbox("Face", FACES_MEMBRO, key=k("flebite_face"))
        d.flebite_extensao_cm = st.text_input("Extensão (cm) da flebite", help=AJUDA["distancia_cm"], key=k("flebite_extensao"))


def secao_biometria(achados_sup: list[str], d: DadosExame) -> None:
    titulo_secao("03", "Biometria Vascular", "Aceita vírgula ou ponto; valores inválidos são sinalizados antes da finalização")

    st.markdown("**Veia Safena Magna**")
    d.bio_safenectomia_parcial = "Safenectomia Magna Parcial" in achados_sup
    if "Safenectomia Magna Total" in achados_sup:
        st.caption("Safenectomia magna total: biometria da magna não é exigida.")
    elif d.bio_safenectomia_parcial:
        c1, c2 = st.columns(2)
        d.bio_coxa_distal = c1.text_input("Coxa distal (cm)", placeholder="ex: 0,5", key=k("bio_coxa_distal"))
        d.bio_perna_proximal_posop = c2.text_input("Perna proximal (cm)", placeholder="ex: 0,3", key=k("bio_perna_posop"))
    else:
        c1, c2, c3 = st.columns(3)
        d.bio_crossa = c1.text_input("Crossa (cm)", placeholder="ex: 0,6", key=k("bio_crossa"))
        d.bio_coxa = c2.text_input("Coxa (cm)", placeholder="ex: 0,5", key=k("bio_coxa"))
        d.bio_perna = c3.text_input("Perna (cm)", placeholder="ex: 0,3", key=k("bio_perna"))

    st.markdown("**Veia Safena Parva**")
    if "Safenectomia Parva Total" in achados_sup:
        st.caption("Safenectomia parva total: biometria da parva não é exigida.")
    else:
        d.medida_parva_cm = st.text_input("Perna proximal (cm)", placeholder="ex: 0,2", key=k("medida_parva"))


def secao_perfurantes() -> list[DadosPerfurante]:
    titulo_secao("04", "Veias Perfurantes", "Pontos de insuficiência identificados")
    tem_perf = st.radio(
        "Existem perfurantes insuficientes?", ["Não", "Sim"], horizontal=True,
        key=k("perf_status_radio"),
    )
    if tem_perf == "Não":
        return []

    c1, c2, c3, c4 = st.columns(4)
    p_dist = c1.text_input("Distância (cm)", help=AJUDA["distancia_cm"], key=k("perf_dist_nova"))
    p_ref = c2.selectbox("Referência", REFERENCIAS_PERFURANTE, key=k("perf_ref_nova"))
    p_loc = c3.selectbox("Localização", ["Coxa", "Perna"], key=k("perf_loc_nova"))
    p_face = c4.selectbox("Face", FACES_PERFURANTE, key=k("perf_face_nova"))

    col_add, col_clear = st.columns(2)
    if col_add.button("Adicionar perfurante", use_container_width=True, key=k("add_perf")):
        normal, erro = normalizar_medida(p_dist)
        if erro:
            st.error("Informe uma distância válida antes de adicionar a perfurante.")
        else:
            _lista_estado("perf_list").append(DadosPerfurante(normal, p_ref, p_loc, p_face))
            st.rerun()
    if col_clear.button("Limpar lista", use_container_width=True, key=k("clear_perf")):
        st.session_state[k("perf_list")] = []
        st.rerun()

    lista = _lista_estado("perf_list")
    for i, p in enumerate(list(lista)):
        col_info, col_del = st.columns([5, 1])
        col_info.info(p.to_texto())
        if col_del.button("Remover", key=k(f"del_perf_{i}"), use_container_width=True):
            lista.pop(i)
            st.rerun()
    return list(lista)


def renderizar_status_exame(d: DadosExame, erros: list[str], avisos: list[str]) -> None:
    titulo_secao("05", "Status do Exame", "Pendências antes de finalizar")
    if not erros and not avisos:
        st.success("✓ Exame consistente e sem pendências detectadas. O laudo pode ser finalizado.")
        return
    if erros:
        st.error(f"{len(erros)} pendência(s) bloqueante(s). Corrija antes de copiar o laudo.")
    if avisos:
        st.warning(f"{len(avisos)} aviso(s) para conferência — não bloqueiam a finalização.")
    with st.expander("Ver pendências", expanded=True):
        for item in erros:
            st.markdown(f"🔴 {html.escape(item)}")
        for item in avisos:
            st.markdown(f"🟡 {html.escape(item)}")


def _componente_copiar(texto: str) -> None:
    texto_json = json.dumps(texto)
    componente_html = f"""
        <button id="copy" class="copy-btn">Copiar laudo</button>
        <div id="copy_status" style="font:12px Inter,sans-serif;color:#8996A8;margin-top:6px;"></div>
        <script>
        const btn = document.getElementById('copy');
        const status = document.getElementById('copy_status');
        btn.onclick = async () => {{
          try {{
            await navigator.clipboard.writeText({texto_json});
            btn.innerText = 'Laudo copiado ✓'; status.innerText = '';
            setTimeout(() => btn.innerText = 'Copiar laudo', 1800);
          }} catch (e) {{
            status.innerText = 'Não foi possível copiar automaticamente. Selecione o texto acima e copie manualmente.';
          }}
        }};
        </script>
    """
    st.components.v1.html(componente_html, height=82)


def _ativar_edicao_manual(laudo_final: str) -> None:
    st.session_state[k("laudo_modo_manual")] = True
    st.session_state[k("laudo_manual")] = laudo_final
    st.session_state[k("laudo_base_manual")] = laudo_final


def _regenerar_laudo_manual(laudo_final: str) -> None:
    st.session_state[k("laudo_manual")] = laudo_final
    st.session_state[k("laudo_base_manual")] = laudo_final


def _voltar_laudo_automatico() -> None:
    st.session_state[k("laudo_modo_manual")] = False


def secao_laudo_editavel(laudo_final: str, erros: list[str]) -> None:
    titulo_secao("06", "Laudo Final", "Gerado a partir dos achados; edição manual é preservada")
    modo_key = k("laudo_modo_manual")
    manual_key = k("laudo_manual")
    base_key = k("laudo_base_manual")

    modo_manual = bool(st.session_state.get(modo_key, False))
    if not modo_manual:
        st.caption("✓ Modo automático — alterações nos achados atualizam o texto.")
        preview_key = k("laudo_preview_auto")
        st.session_state[preview_key] = laudo_final
        st.text_area(
            "Texto do laudo", height=560,
            disabled=True, label_visibility="collapsed", key=preview_key,
        )
        st.button(
            "✏️ Editar texto manualmente", use_container_width=True, key=k("ativar_manual"),
            on_click=_ativar_edicao_manual, args=(laudo_final,),
        )
        texto_atual = laudo_final
    else:
        if manual_key not in st.session_state:
            st.session_state[manual_key] = laudo_final
            st.session_state[base_key] = laudo_final
        if st.session_state.get(base_key) != laudo_final:
            st.warning("Os achados acima mudaram depois que você iniciou a edição manual. Seu texto foi preservado. Use “Regenerar” se quiser substituí-lo pelos achados atuais.")
        texto_atual = st.text_area(
            "Texto do laudo", height=560, label_visibility="collapsed", key=manual_key,
        )
        c1, c2 = st.columns(2)
        c1.button(
            "↻ Regenerar a partir dos achados", use_container_width=True, key=k("regen_laudo"),
            on_click=_regenerar_laudo_manual, args=(laudo_final,),
        )
        c2.button(
            "Voltar ao modo automático", use_container_width=True, key=k("auto_laudo"),
            on_click=_voltar_laudo_automatico,
        )

    if erros:
        st.warning("Copiar laudo está bloqueado enquanto houver pendências críticas. O texto permanece visível para revisão.")
    else:
        _componente_copiar(texto_atual)


# =====================================================================
# 8. AÇÕES E ORQUESTRAÇÃO PRINCIPAL
# =====================================================================


def _solicitar_reset() -> None:
    st.session_state["confirmar_reset"] = True


def _cancelar_reset() -> None:
    st.session_state["confirmar_reset"] = False


def renderizar_barra_acoes() -> None:
    _, col_btn = st.columns([9, 1.7])
    with col_btn:
        st.button(
            "Reiniciar paciente", type="primary", use_container_width=True, key=k("pedir_reset"),
            on_click=_solicitar_reset,
        )

    if st.session_state.get("confirmar_reset"):
        st.warning(
            "Isso vai limpar integralmente este exame — achados, medidas, listas, edição manual e venograma. "
            "O próximo paciente começará com estado novo."
        )
        c_sim, c_nao, _ = st.columns([1.2, 1, 4])
        c_sim.button(
            "Confirmar limpeza", use_container_width=True, key=k("confirm_reset"),
            on_click=reiniciar_exame,
        )
        c_nao.button(
            "Cancelar", use_container_width=True, key=k("cancel_reset"),
            on_click=_cancelar_reset,
        )


def coletar_dados_exame() -> DadosExame:
    d = DadosExame()
    with st.container(border=True):
        d.lateralidade = secao_identificacao()

    with st.container(border=True):
        titulo_secao("02", "Sistemas Venosos", "Normal por padrão; detalhes aparecem somente quando necessários")
        c1, c2 = st.columns(2)
        with c1:
            d.sp_status, d.sp_veias, d.sp_tipo_alteracao = secao_sistema_profundo()
        with c2:
            d.sup_status, d.achados_superficiais, d.ectoscopia_status = secao_sistema_superficial()

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
    # A lateralidade já vive no session_state antes de o widget ser renderizado,
    # portanto o cabeçalho nunca fica um rerun atrasado.
    renderizar_cabecalho_institucional(st.session_state[k("lateralidade")])
    renderizar_barra_acoes()

    dados = coletar_dados_exame()
    erros, avisos = validar_exame(dados)
    laudo_final = gerar_laudo_completo(dados)

    with st.container(border=True):
        renderizar_status_exame(dados, erros, avisos)

    # O venograma é opt-in. Assim o canvas pesado não é carregado durante o
    # preenchimento normal do laudo. Quando aberto, roda em fragmento próprio.
    destino = st.radio(
        "Finalização", ["📄 Laudo", "🩻 Venograma"], horizontal=True,
        key=k("finalizacao_view"), label_visibility="collapsed",
    )
    if destino == "📄 Laudo":
        with st.container(border=True):
            secao_laudo_editavel(laudo_final, erros)
    else:
        with st.container(border=True):
            secao_venograma()


def executar_autotestes() -> None:
    """Testes rápidos das regras puras; execute com LAUDO_SELF_TEST=1 python app.py."""
    assert normalizar_medida("0,50") == ("0,5", None)
    assert normalizar_medida(",5") == ("0,5", None)
    assert normalizar_medida("-1")[1] is not None

    normal = DadosExame(
        bio_crossa="0,6", bio_coxa="0,5", bio_perna="0,3", medida_parva_cm="0,2"
    )
    assert validar_exame(normal) == ([], [])
    assert "___" not in gerar_laudo_completo(normal)

    cronica = DadosExame(
        sp_status="Não", sp_veias=["Femoral comum"],
        sp_tipo_alteracao="Trombose Crônica Não Recanalizada",
        bio_crossa="0,6", bio_coxa="0,5", bio_perna="0,3", medida_parva_cm="0,2",
    )
    profundo, impressao = gerar_secao_profundo(cronica)
    assert "sem sinais de recanalização" in profundo
    assert "Veias tronculares pérvias" not in profundo
    assert "não recanalizada" in impressao

    multiperf = DadosExame(
        bio_crossa="0,6", bio_coxa="0,5", bio_perna="0,3", medida_parva_cm="0,2",
        perfurantes=[
            DadosPerfurante("5", "Planta do pé", "Perna", "Medial"),
            DadosPerfurante("8", "Planta do pé", "Perna", "Lateral"),
        ],
    )
    assert "- Perfurantes insuficientes." in gerar_laudo_completo(multiperf)

    posop = DadosExame(
        achados_superficiais=["Safenectomia Magna Parcial", "Safenectomia Parva Parcial"],
        bio_coxa_distal="0,5", bio_perna_proximal_posop="0,3", medida_parva_cm="0,2",
    )
    assert ".." not in gerar_laudo_completo(posop)


if __name__ == "__main__":
    if os.environ.get("LAUDO_SELF_TEST") == "1":
        executar_autotestes()
        print("Autotestes concluídos com sucesso.")
    else:
        main()
