# -*- coding: utf-8 -*-
"""
app.py — Streamlit web demo modulu Náklady řízení.

Verze: layout v jedné obrazovce (jako desktop), výsledek v modálním dialogu.

Autor enginu: Mgr. Pavel Tureček, civilní soudce, OS Pardubice.
Web frontend: pro účely sdílení s kolegy.

Spuštění lokálně:
    pip install streamlit
    streamlit run app.py
"""
import streamlit as st
from datetime import datetime, date
from naklady_engine import CalculationEngine


# ═══════════════════════════════════════════════════════════════
# § 1  STRÁNKA — config + custom CSS pro barevné zónování
# ═══════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Náklady řízení — kalkulátor",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom CSS — barevné zónování sekcí, kompaktnější layout
st.markdown("""
<style>
    /* Skrýt sidebar úplně — chceme jednoobrazovkový layout */
    section[data-testid="stSidebar"] { display: none; }

    /* Hlavní container — užší padding */
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        max-width: 1280px;
    }

    /* Zone styling přes wrapper divy */
    .zone {
        padding: 14px 20px;
        border-radius: 8px;
        margin-bottom: 12px;
        border-left: 4px solid #16a085;
    }
    .zone-basic   { background: #fdfdf8; }
    .zone-tariff  { background: #fef9e7; }
    .zone-acts    { background: #eafaf1; }
    .zone-travel  { background: #fdedec; }
    .zone-sop     { background: #ebf5fb; }

    .zone-title {
        font-size: 14px;
        font-weight: 700;
        color: #2c3e50;
        text-transform: uppercase;
        letter-spacing: 0.4px;
        margin-bottom: 8px;
        border-bottom: 2px solid #16a085;
        padding-bottom: 4px;
        display: inline-block;
    }

    /* Kompaktnější Streamlit number inputy */
    div[data-testid="stNumberInput"] label,
    div[data-testid="stTextInput"] label,
    div[data-testid="stSelectbox"] label,
    div[data-testid="stDateInput"] label {
        font-size: 11px;
        font-weight: 600;
        color: #5d6d7e;
        text-transform: uppercase;
    }

    /* Header */
    .app-header {
        background: linear-gradient(180deg, #16a085 0%, #138c72 100%);
        color: white;
        padding: 16px 24px;
        border-radius: 10px;
        margin-bottom: 16px;
    }
    .app-header h1 {
        margin: 0;
        font-size: 24px;
        font-weight: 700;
    }
    .app-header .sub {
        font-size: 12px;
        opacity: 0.9;
        font-style: italic;
        margin-top: 4px;
    }
</style>
""", unsafe_allow_html=True)


# Hlavička
st.markdown("""
<div class="app-header">
    <h1>⚖️ Kalkulátor nákladů řízení</h1>
    <div class="sub">Civilní řízení · ČR · vyhláška 177/1996 Sb. · z. č. 549/1991 Sb. · §§ 137–151 OSŘ</div>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
# § 2  ENGINE — instance v cache
# ═══════════════════════════════════════════════════════════════

@st.cache_resource
def get_engine():
    return CalculationEngine()

engine = get_engine()


# ═══════════════════════════════════════════════════════════════
# § 3  SESSION STATE — pro persistenci hodnot mezi rerendery
# ═══════════════════════════════════════════════════════════════

if "result" not in st.session_state:
    st.session_state.result = None
if "perfacts_for_text" not in st.session_state:
    st.session_state.perfacts_for_text = []


# ═══════════════════════════════════════════════════════════════
# § 4  MODAL DIALOG — definice (otevírá se přes show_result_dialog())
# ═══════════════════════════════════════════════════════════════

@st.dialog("✅ Výsledek výpočtu", width="large")
def show_result_dialog():
    """Modální dialog s výsledkem výpočtu — varianta A z mockupu."""
    result = st.session_state.result
    if not result:
        st.warning("Nejdřív vyplň formulář a klikni na Spočítat.")
        return

    # 3 metriky nahoře
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric(
            "Náhrada k přiznání",
            f"{result.get('final_reimbursement', 0):,.0f} Kč".replace(",", " "),
        )
    with col_b:
        st.metric(
            "% úspěchu žalobce",
            f"{result.get('plaintiff_success_pct', 0):.1f} %",
        )
    with col_c:
        wp = result.get("winning_party_label", "—")
        st.metric("Vítězná strana", wp)

    st.markdown("---")

    # Detailní rozpis
    st.markdown("##### 📊 Detailní rozpis")
    details = [
        ("Odměna advokáta (před DPH)", result.get("total_fee_base", 0)),
        ("Režijní paušál (úkonový)",   result.get("total_overhead", 0)),
        ("Cestovné + amortizace",       result.get("total_travel_expense", 0)),
        ("Náhrada za ztrátu času",       result.get("total_time_loss_comp", 0)),
        ("Soudní poplatek (SOP)",        result.get("court_fee", 0)),
        ("Ostatní hotové výdaje",        result.get("total_other_expenses", 0)),
        ("DPH 21 % (z odměny + paušálu)", result.get("total_vat", 0)),
    ]
    for label, val in details:
        if val:
            st.markdown(
                f"<div style='display: flex; justify-content: space-between; padding: 3px 0; border-bottom: 1px dashed #e1e8ed;'>"
                f"<span>{label}</span><span><strong>{val:,.2f} Kč</strong></span>"
                f"</div>".replace(",", " "),
                unsafe_allow_html=True,
            )
    st.markdown(
        f"<div style='display: flex; justify-content: space-between; padding: 6px 0; margin-top: 4px; border-top: 2px solid #16a085; font-weight: 700;'>"
        f"<span>CELKEM po zohlednění úspěchu</span>"
        f"<span>{result.get('final_reimbursement', 0):,.2f} Kč</span>".replace(",", " ") +
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # Text výroku
    st.markdown("##### 📄 Text výroku")
    try:
        legal_text = engine.generate_legal_text(
            result, st.session_state.perfacts_for_text)
        st.text_area(
            "Zkopíruj do rozsudku / usnesení",
            value=legal_text,
            height=280,
            label_visibility="collapsed",
        )
    except Exception as exc:
        st.warning(f"Generování textu výroku selhalo: {exc}")

    # Souhrn pro kontrolu (collapsed)
    with st.expander("🔍 Souhrn pro kontrolu (technické detaily)"):
        try:
            summary = engine.generate_calculation_summary(
                result, st.session_state.perfacts_for_text)
            st.text(summary)
        except Exception as exc:
            st.info(f"(Souhrn nedostupný: {exc})")

    # Sazby info (collapsed)
    with st.expander("ℹ️ Aktuální sazby používané enginem (read-only)"):
        st.markdown("""
**Od 1. 1. 2025** (vyhláška 475/2024 Sb. + 177/1996 Sb. v aktuálním znění):

- režijní paušál (§ 13 odst. 4): **450 Kč** / úkon
- formulářový paušál: **100 Kč** / úkon
- náhrada za ztrátu času: **150 Kč** / započatých 30 min
- benzín: **35,80 Kč/l**, nafta: 34,70 Kč/l, elektřina: 7,70 Kč/kWh
- amortizace: **5,80 Kč** / km
- specifické tarify (neurčitelná hodnota / opatrovnické / osobnostní práva / ústavní stížnost)

**Do 31. 12. 2024:** režijní paušál 300 Kč.

*Sazby jsou v `naklady_engine.py` (CalculationEngine.DEFAULT_RATES + get_rates_for_date).*
        """)


# ═══════════════════════════════════════════════════════════════
# § 5  ZÁKLADNÍ PARAMETRY ŘÍZENÍ (zóna basic)
# ═══════════════════════════════════════════════════════════════

st.markdown('<div class="zone zone-basic"><span class="zone-title">📋 Základní parametry řízení</span></div>',
            unsafe_allow_html=True)

col_b1, col_b2, col_b3 = st.columns([1, 1.2, 2])
with col_b1:
    default_date = st.date_input("Datum pro výpočet", value=date.today())
with col_b2:
    proc_type = st.selectbox(
        "Typ řízení",
        options=["klasika", "formularove", "sazebnik"],
        format_func=lambda x: {
            "klasika": "Klasické",
            "formularove": "Formulářové (§ 14b)",
            "sazebnik": "Sazebník (§ 12a)",
        }[x],
    )
with col_b3:
    popis = st.text_input("Popis sporu", placeholder="o zaplacení X Kč s přísl.")

col_c1, col_c2, col_c3 = st.columns(3)
with col_c1:
    is_vat_payer = st.checkbox("Plátce DPH", value=True)
    unrepresented = st.checkbox("Nezastoupený účastník")
with col_c2:
    defendant_won = st.checkbox("Žalovaný vyhrál 100 %")
    accessory_fail = st.checkbox("Neúspěch jen v příslušenství")
with col_c3:
    plaintiff_is_woman = st.checkbox("Žalobce — žena (gramatika)")
    defendant_is_woman = st.checkbox("Žalovaný — žena (gramatika)")


# ═══════════════════════════════════════════════════════════════
# § 6  TARIFNÍ HODNOTA (6 jistin + checkboxy)
# ═══════════════════════════════════════════════════════════════

st.markdown('<div class="zone zone-tariff"><span class="zone-title">💰 Tarifní hodnota — žaloba a přiznáno</span></div>',
            unsafe_allow_html=True)

tariff_cols = st.columns(6)
tariff_vals = []
tariff_awarded = []
default_values = [100000, 0, 0, 0, 0, 0]
for i, col in enumerate(tariff_cols):
    with col:
        v = st.number_input(
            f"Jistina {i+1}", min_value=0, value=default_values[i],
            step=1000, key=f"tariff_{i}",
        )
        a = st.checkbox("přiznáno", value=(default_values[i] > 0), key=f"awarded_{i}")
        tariff_vals.append(v)
        tariff_awarded.append(a)

total_tariff = sum(tariff_vals)
total_awarded = sum(v for v, a in zip(tariff_vals, tariff_awarded) if a)
auto_pct = (total_awarded / total_tariff * 100) if total_tariff > 0 else 0
st.markdown(
    f"<div style='text-align: right; font-size: 13px; font-weight: 600; margin-top: 4px;'>"
    f"Celkem: <strong>{total_tariff:,} Kč</strong>  ·  "
    f"Přiznáno: <strong>{total_awarded:,} Kč</strong>  ·  "
    f"Auto úspěch: <strong>{auto_pct:.1f} %</strong>".replace(",", " ") +
    "</div>",
    unsafe_allow_html=True,
)

col_m1, col_m2 = st.columns([1, 1])
with col_m1:
    manual_pct = st.text_input(
        "Manuální % úspěchu (přebije auto)", placeholder="prázdné = auto",
    )
with col_m2:
    modification = st.selectbox(
        "Modifikace", options=["none", "zuzeni", "zpetvzeti"],
        format_func=lambda x: {
            "none": "žádná", "zuzeni": "zúžení", "zpetvzeti": "zpětvzetí",
        }[x],
    )


# ═══════════════════════════════════════════════════════════════
# § 7  ÚKONY ADVOKÁTA (3 sloupce)
# ═══════════════════════════════════════════════════════════════

st.markdown('<div class="zone zone-acts"><span class="zone-title">📝 Úkony advokáta (počet podle typu)</span></div>',
            unsafe_allow_html=True)

col_d1, col_d2 = st.columns([1, 2])
with col_d1:
    act_date = st.date_input("Datum úkonu", value=default_date, key="act_date")
with col_d2:
    act_comment = st.text_input("Společný komentář (volitelný)")

# Úkony do 3 sloupců
acts = list(engine.LEGAL_ACTS.keys())
n_per_col = (len(acts) + 2) // 3
cols_acts = st.columns(3)
act_counts = {}

for i, col in enumerate(cols_acts):
    start = i * n_per_col
    end = min(start + n_per_col, len(acts))
    with col:
        for name in acts[start:end]:
            info = engine.LEGAL_ACTS[name]
            suffix = " (½)" if info.get("type") == "half" else ""
            act_counts[name] = st.number_input(
                f"{name}{suffix}",
                min_value=0, max_value=20, value=0, step=1,
                key=f"act_{name}",
            )


# ═══════════════════════════════════════════════════════════════
# § 8  SOUDNÍ POPLATEK (SOP)
# ═══════════════════════════════════════════════════════════════

st.markdown('<div class="zone zone-sop"><span class="zone-title">🏛 Soudní poplatek (SOP)</span></div>',
            unsafe_allow_html=True)

col_s1, col_s2, col_s3, col_s4 = st.columns(4)
with col_s1:
    sop_mode = st.selectbox(
        "SOP režim", options=["kalkulovat", "rucne", "domer"],
        format_func=lambda x: {
            "kalkulovat": "kalkulovat", "rucne": "zadat ručně", "domer": "doměřit",
        }[x],
    )
with col_s2:
    sop_manual = st.number_input("SOP (Kč)", min_value=0, value=0, step=100)
with col_s3:
    sop_domer = st.number_input("Doměření (Kč)", min_value=0, value=0, step=100)
with col_s4:
    sop_refund = st.number_input("Vrácení SOP (Kč)", min_value=0, value=0, step=100)


# ═══════════════════════════════════════════════════════════════
# § 9  CESTOVNÉ A ZTRÁTA ČASU
# ═══════════════════════════════════════════════════════════════

st.markdown('<div class="zone zone-travel"><span class="zone-title">🚗 Cestovné a ztráta času (volitelné)</span></div>',
            unsafe_allow_html=True)

col_t1, col_t2, col_t3, col_t4, col_t5 = st.columns(5)
with col_t1:
    travel_dist = st.number_input("Vzdálenost (km)", min_value=0, value=0, step=10)
with col_t2:
    travel_time = st.number_input("Doba cesty (min)", min_value=0, value=0, step=5)
with col_t3:
    fuel_type = st.selectbox("Palivo", options=["benzín", "nafta", "elektřina"])
with col_t4:
    engine_volume = st.number_input("Objem (cm³)", min_value=0, value=1600, step=100)
with col_t5:
    parking = st.number_input("Parkovné (Kč)", min_value=0, value=0, step=10)


# ═══════════════════════════════════════════════════════════════
# § 10  AKČNÍ TLAČÍTKA
# ═══════════════════════════════════════════════════════════════

st.markdown("---")
col_btn1, col_btn2, col_btn3 = st.columns([2, 1, 1])
with col_btn1:
    do_calc = st.button(
        "🧮 Spočítat náklady",
        type="primary",
        use_container_width=True,
    )
with col_btn2:
    do_recalc = st.button("🔄 Přepočítat", use_container_width=True)
with col_btn3:
    do_clear = st.button("⚙️ Smazat", use_container_width=True)


# ═══════════════════════════════════════════════════════════════
# § 11  ZPRACOVÁNÍ AKCÍ
# ═══════════════════════════════════════════════════════════════

if do_clear:
    # Stránka se sama obnoví na defaults — Streamlit ji rerendruje
    for key in list(st.session_state.keys()):
        if key.startswith(("tariff_", "awarded_", "act_")):
            del st.session_state[key]
    st.session_state.result = None
    st.rerun()


def run_calculation():
    """Sestavit data dict a spustit engine.calculate_all."""
    performed_acts = []
    for name, count in act_counts.items():
        for _ in range(int(count)):
            performed_acts.append({
                "name": name,
                "date": datetime.combine(act_date, datetime.min.time()),
                "before_representation": False,
            })

    data = {
        "tariff_values": tariff_vals,
        "tariff_awarded_flags": tariff_awarded,
        "tariff_value": total_tariff,
        "awarded_amount": total_awarded,
        "proceeding_type": proc_type,
        "is_vat_payer": is_vat_payer,
        "defendant_won": defendant_won,
        "unrepresented_party": unrepresented,
        "plaintiff_is_woman": plaintiff_is_woman,
        "defendant_is_woman": defendant_is_woman,
        "performed_acts": performed_acts,
        "vat_on_tickets": False,
        "court_fee_option": sop_mode,
        "manual_court_fee": sop_manual,
        "domer_court_fee": sop_domer,
        "modification": modification,
        "refund_sop_value": sop_refund,
        "currency_mode": "CZK",
        "exchange_rate": 25.0,
        "accessory_failure": accessory_fail,
        "popis": popis,
    }

    if manual_pct.strip():
        try:
            data["manual_success_pct"] = float(manual_pct.replace(",", "."))
        except ValueError:
            st.error("Manuální % má být číslo (např. 75 nebo 75,5).")
            return None

    if travel_dist > 0:
        data["travel_acts"] = [{
            "city": "_demo_",
            "distance_km": travel_dist,
            "time_min": travel_time,
            "fuel_type": fuel_type,
            "engine_volume": engine_volume,
            "parking_fee": parking,
            "date": datetime.combine(act_date, datetime.min.time()),
        }]

    try:
        result = engine.calculate_all(data)
        st.session_state.result = result
        st.session_state.perfacts_for_text = performed_acts
        return result
    except Exception as exc:
        st.error(f"Chyba výpočtu: {exc}")
        import traceback
        with st.expander("Stack trace"):
            st.code(traceback.format_exc())
        return None


if do_calc or do_recalc:
    result = run_calculation()
    if result is not None:
        show_result_dialog()


# ═══════════════════════════════════════════════════════════════
# § 12  FOOTER
# ═══════════════════════════════════════════════════════════════

st.markdown("---")
st.caption(
    "💼 Engine ze stejného kódu jako desktop aplikace OSspravce. "
    "Autor: **Mgr. Pavel Tureček**, civilní soudce, OS Pardubice. "
    "Demo — v reálném řízení vždy zkontroluj proti aktuálním vyhláškám."
)
