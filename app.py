import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Retell / ElevenLabs TTS Cost Simulator",
    page_icon="🔊",
    layout="wide",
)

# ── Constants ─────────────────────────────────────────────────────────────────
RETELL_INFRA  = 0.055
EL_TTS_RATE   = 0.040
ALT_TTS_RATE  = 0.015
PRE_MAR23_RATE = 0.070   # $/min — legacy bundled rate (Retell + ElevenLabs, pre Mar 23)
CHARS_PER_MIN = 750

ELEVENLABS_PLANS = [
    {"name": "Starter",  "monthly": 5,    "credits": 30_000,     "overage_per_1k": 0.30},
    {"name": "Creator",  "monthly": 22,   "credits": 100_000,    "overage_per_1k": 0.30},
    {"name": "Pro",      "monthly": 99,   "credits": 500_000,    "overage_per_1k": 0.24},
    {"name": "Scale",    "monthly": 330,  "credits": 2_000_000,  "overage_per_1k": 0.18},
    {"name": "Business", "monthly": 1320, "credits": 11_000_000, "overage_per_1k": 0.12},
]

# Plans to show in side-by-side comparison (subset of above)
COMPARE_PLANS = ["Creator", "Pro", "Scale", "Business"]

PLAN_COLORS = {
    "Retell + ElevenLabs (pre Mar 23)":  "#888780",
    "Retell + ElevenLabs (post Mar 23)": "#378ADD",
    "Retell + ElevenLabs": "#378ADD",
    "Retell + Alt TTS":    "#1D9E75",
    "Creator":             "#534AB7",
    "Pro":                 "#D85A30",
    "Scale":               "#BA7517",
    "Business":            "#A32D2D",
}

LOB_DEFAULTS = {
    "Commercial": {"pct": 0.53, "color": "#378ADD"},
    "Medicare":   {"pct": 0.14, "color": "#1D9E75"},
    "Medicaid":   {"pct": 0.14, "color": "#D85A30"},
    "No LOB":     {"pct": 0.19, "color": "#888780"},
}

# ── Helpers ───────────────────────────────────────────────────────────────────
def get_plan(name):
    return next(p for p in ELEVENLABS_PLANS if p["name"] == name)

def best_el_plan(chars):
    for plan in ELEVENLABS_PLANS:
        if plan["credits"] >= chars:
            return plan
    return ELEVENLABS_PLANS[-1]

def el_overage(chars, plan):
    if chars <= plan["credits"]:
        return 0.0
    return ((chars - plan["credits"]) / 1000) * plan["overage_per_1k"]

def compute_tts_costs(minutes, chars, enterprise_discount):
    """
    Returns costs for Retell + ElevenLabs, Retell + Alt TTS, and every
    direct ElevenLabs plan side by side. Enterprise discount applies to
    all direct plans equally (base cost + overage). To the best of my knowledge, no discount is available
    on Retell-bundled flat per-minute rates.
    """
    disc       = 1 - enterprise_discount / 100
    retell_el  = (RETELL_INFRA + EL_TTS_RATE)  * minutes
    retell_alt = (RETELL_INFRA + ALT_TTS_RATE) * minutes

    plan_costs = {}
    for plan in ELEVENLABS_PLANS:
        overage       = el_overage(chars, plan)
        disc_base     = plan["monthly"] * disc
        disc_overage  = overage         * disc
        total         = disc_base + disc_overage + (RETELL_INFRA * minutes)
        plan_costs[plan["name"]] = {
            "plan":         plan,
            "disc_base":    disc_base,
            "disc_overage": disc_overage,
            "retell_infra": RETELL_INFRA * minutes,
            "total":        total,
            "over_credits": chars > plan["credits"],
        }

    best_plan = best_el_plan(chars)

    return {
        "minutes":    minutes,
        "chars":      chars,
        "retell_el":  retell_el,
        "retell_alt": retell_alt,
        "direct_el":  plan_costs[best_plan["name"]]["total"],  # LOB tab compat
        "best_plan":  best_plan,
        "plan_costs": plan_costs,
        "breakdown": {
            "Retell + ElevenLabs": {
                "Retell infra":   RETELL_INFRA * minutes,
                "ElevenLabs TTS": EL_TTS_RATE  * minutes,
            },
            "Retell + Alt TTS": {
                "Retell infra": RETELL_INFRA * minutes,
                "Alt TTS":      ALT_TTS_RATE * minutes,
            },
        },
    }

def minutes_for_calls(calls_per_day, avg_dur, agents, growth_pct):
    factor  = 1 + growth_pct / 100
    minutes = calls_per_day * avg_dur * agents * 30 * factor
    chars   = minutes * CHARS_PER_MIN
    return minutes, chars

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Usage parameters")

    calls_per_day = st.slider("Calls per day", 1, 200, 10)
    avg_duration  = st.slider("Avg call duration (min)", 1.0, 30.0, 5.2, step=0.1,
                              format="%.1f min")
    agents        = st.slider("Active agents", 1, 20, 2)
    growth_pct    = st.slider("Monthly growth projection (%)", 0, 300, 0, step=10)

    st.divider()
    st.subheader("Enterprise discount")
    st.caption(
        "Applies to all Direct ElevenLabs plans — reduces plan base cost "
        "and overage rate, simulating a negotiated contract. "
        "To the best of my knowledge, no discount is available on Retell-bundled flat per-minute rates."
    )
    enterprise_discount = st.slider(
        "Direct ElevenLabs discount (%)", 0, 50, 0, step=5, format="%d%%",
        help="Retell previously held a contract tier with ElevenLabs before March 23. "
             "This models what a similar negotiated rate could look like if we go direct."
    )

    st.divider()
    st.subheader("Outcome metrics")
    total_patients_input = st.number_input(
        "Total patients per month", min_value=1, value=199,
        help="Used to calculate cost per patient"
    )
    conversion_rate = st.slider(
        "Scheduling conversion rate (%)", 1, 100, 18, step=1, format="%d%%"
    ) / 100

    st.divider()
    st.caption("Base rates")
    st.markdown(f"""
| Component | Rate |
|---|---|
| Retell infrastructure | ${RETELL_INFRA}/min |
| ElevenLabs via Retell | ${EL_TTS_RATE}/min |
| Alt TTS (Cartesia etc.) | ${ALT_TTS_RATE}/min |
| Chars/min estimate | {CHARS_PER_MIN:,} |
""")

# ── Compute base ──────────────────────────────────────────────────────────────
base_mins, base_chars = minutes_for_calls(calls_per_day, avg_duration, agents, 0)
base = compute_tts_costs(base_mins, base_chars, enterprise_discount)
calls_per_month     = calls_per_day * agents * 30
scheduled_per_month = round(total_patients_input * conversion_rate)

# ── Header ────────────────────────────────────────────────────────────────────
st.title("🔊 Retell / ElevenLabs TTS Cost Simulator")
st.caption(
    "Compares Retell + ElevenLabs, Retell + Alt TTS, and direct ElevenLabs "
    "plans (Creator, Pro, Scale, Business) side by side."
)

tab1, tab2 = st.tabs(["📊 Cost Overview", "🏥 Line of Business"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — COST OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════
with tab1:

    # Usage summary
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Minutes / month",    f"{base['minutes']:,.0f}")
    c2.metric("Characters / month", f"{base['chars']/1_000:,.0f}k")
    c3.metric("Calls / month",      f"{calls_per_month:,.0f}")
    c4.metric("Patients / month",   f"{total_patients_input:,}")
    c5.metric("Scheduled / month",  f"{scheduled_per_month:,}")

    st.divider()

    # ── Section 1: Retell-bundled options ────────────────────────────────────
    st.subheader("Retell-bundled TTS options")
    st.caption("Flat per-minute rates — no volume discount available.")

    pre_mar23_cost = PRE_MAR23_RATE * base["minutes"]

    bundled = [
        {
            "label":    "Retell + ElevenLabs",
            "sublabel": "Pre Mar 23 — legacy bundled pricing",
            "cost":     pre_mar23_cost,
            "breakdown": {
                "Bundled voice engine (all-in)": pre_mar23_cost,
            },
            "legacy": True,
        },
        {
            "label":    "Retell + ElevenLabs",
            "sublabel": "Current setup — post Mar 23 pricing",
            "cost":     base["retell_el"],
            "breakdown": base["breakdown"]["Retell + ElevenLabs"],
            "legacy": False,
        },
        {
            "label":    "Retell + Alt TTS",
            "sublabel": "e.g. Cartesia, Fish Audio, OpenAI, Retell voices",
            "cost":     base["retell_alt"],
            "breakdown": base["breakdown"]["Retell + Alt TTS"],
            "legacy": False,
        },
    ]

    bundled_cheapest = min(s["cost"] for s in bundled)
    b_cols = st.columns(3)
    for col, s in zip(b_cols, bundled):
        with col:
            with st.container(border=True):
                if s.get("legacy"):
                    st.warning("⏪ Pre Mar 23 baseline")
                elif s["cost"] == bundled_cheapest:
                    st.success("✓ Lowest among bundled")
                st.markdown(f"**{s['label']}**")
                st.caption(s["sublabel"])
                st.metric("Monthly cost", f"${s['cost']:,.2f}")
                cpp = s["cost"] / total_patients_input
                cps = s["cost"] / scheduled_per_month if scheduled_per_month else 0
                st.caption(f"Per patient: **${cpp:,.2f}** · Per scheduled: **${cps:,.2f}**")
                with st.expander("Breakdown"):
                    for k, v in s["breakdown"].items():
                        st.markdown(f"- {k}: **${v:,.2f}**")
                if s.get("legacy"):
                    delta = base["retell_el"] - pre_mar23_cost
                    st.caption(f"Post Mar 23 ElevenLabs costs **${abs(delta):,.2f} {'more' if delta > 0 else 'less'}**/month vs. this baseline.")

    st.divider()

    # ── Section 2: Direct ElevenLabs plans ───────────────────────────────────
    disc_label = f" ({int(enterprise_discount)}% disc applied)" if enterprise_discount > 0 else ""
    st.subheader(f"Direct ElevenLabs plans{disc_label}")
    st.caption(
        "Purchase directly from ElevenLabs + pay Retell infrastructure separately. "
        "Plans with insufficient credits show overage charges. "
        + ("Enterprise discount applied to plan base and overage." if enterprise_discount > 0
           else "Use the sidebar discount slider to model a negotiated Enterprise rate.")
    )

    # Flag best-fit plan
    best_name = base["best_plan"]["name"]

    plan_cols = st.columns(len(COMPARE_PLANS))
    for col, pname in zip(plan_cols, COMPARE_PLANS):
        pc   = base["plan_costs"][pname]
        plan = pc["plan"]
        is_best_fit  = (pname == best_name)
        is_cheapest  = (pc["total"] == min(
            base["plan_costs"][n]["total"] for n in COMPARE_PLANS
        ))
        over = pc["over_credits"]

        with col:
            with st.container(border=True):
                if is_best_fit:
                    st.info("★ Best-fit plan")
                if is_cheapest and not is_best_fit:
                    st.success("✓ Lowest direct cost")
                st.markdown(f"**ElevenLabs {pname}**")
                st.caption(
                    f"${plan['monthly']}/mo · {plan['credits']//1000:,}k credits"
                )
                st.metric("Monthly total", f"${pc['total']:,.2f}")
                cpp = pc["total"] / total_patients_input
                cps = pc["total"] / scheduled_per_month if scheduled_per_month else 0
                st.caption(f"Per patient: **${cpp:,.2f}** · Per scheduled: **${cps:,.2f}**")
                with st.expander("Breakdown"):
                    disc_note = f" ({int(enterprise_discount)}% disc)" if enterprise_discount > 0 else ""
                    st.markdown(f"- Plan base{disc_note}: **${pc['disc_base']:,.2f}**")
                    if over:
                        st.markdown(f"- Overage{disc_note}: **${pc['disc_overage']:,.2f}** ⚠️")
                    else:
                        st.markdown(f"- Overage: **$0.00** (within credits)")
                    st.markdown(f"- Retell infra: **${pc['retell_infra']:,.2f}**")
                if over:
                    st.warning("Exceeds plan credits — overage applies")

    st.divider()

    # ── Section 3: Full summary table ────────────────────────────────────────
    st.subheader("Full comparison summary")

    all_scenarios = [
                        ("Retell + ElevenLabs (pre Mar 23)", pre_mar23_cost),
                        ("Retell + ElevenLabs (post Mar 23)", base["retell_el"]),
                        ("Retell + Alt TTS",                  base["retell_alt"]),
                    ] + [(n, base["plan_costs"][n]["total"]) for n in COMPARE_PLANS]

    summary_rows = []
    for label, cost in all_scenarios:
        cpp = cost / total_patients_input
        cps = cost / scheduled_per_month if scheduled_per_month else 0
        summary_rows.append({
            "Scenario":           label,
            "Monthly cost":       f"${cost:,.2f}",
            "Annual cost":        f"${cost*12:,.2f}",
            "Cost per patient":   f"${cpp:,.2f}",
            "Cost per scheduled": f"${cps:,.2f}",
            "vs. pre Mar 23":     f"${cost - pre_mar23_cost:+,.2f}",
        })
    st.dataframe(pd.DataFrame(summary_rows), hide_index=True, use_container_width=True)

    saving = base["retell_el"] - base["retell_alt"]
    st.info(
        f"💡 Switching Retell + ElevenLabs → Retell + Alt TTS saves "
        f"**${saving:,.2f}/month** (**${saving*12:,.2f}/year**) at current usage."
    )

    st.divider()

    # ── Section 4: 6-month projection ────────────────────────────────────────
    st.subheader("6-month cost projection")

    month_labels = [f"Month {i+1}" for i in range(6)]
    series = {
        "Retell + ElevenLabs (pre Mar 23)":  [],
        "Retell + ElevenLabs (post Mar 23)": [],
        "Retell + Alt TTS":                  [],
    }
    for pname in COMPARE_PLANS:
        series[pname] = []

    for i in range(6):
        g     = growth_pct * i / 5
        m, ch = minutes_for_calls(calls_per_day, avg_duration, agents, g)
        c     = compute_tts_costs(m, ch, enterprise_discount)
        series["Retell + ElevenLabs (pre Mar 23)"].append(round(PRE_MAR23_RATE * m, 2))
        series["Retell + ElevenLabs (post Mar 23)"].append(round(c["retell_el"],  2))
        series["Retell + Alt TTS"].append(round(c["retell_alt"], 2))
        for pname in COMPARE_PLANS:
            series[pname].append(round(c["plan_costs"][pname]["total"], 2))

    chart_colors = {
        "Retell + ElevenLabs (pre Mar 23)":  "#888780",
        "Retell + ElevenLabs (post Mar 23)": "#378ADD",
        "Retell + Alt TTS":                  "#1D9E75",
    }
    chart_colors.update(PLAN_COLORS)

    fig = go.Figure()
    for label, values in series.items():
        is_legacy = "pre Mar 23" in label
        fig.add_trace(go.Scatter(
            x=month_labels, y=values, name=label,
            mode="lines+markers",
            line=dict(color=chart_colors.get(label, "#888780"), width=2,
                      dash="dash" if is_legacy else "solid"),
            marker=dict(size=6),
        ))
    fig.update_layout(
        margin=dict(l=0, r=0, t=20, b=0),
        yaxis=dict(tickprefix="$", tickformat=",.0f"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor="rgba(128,128,128,0.15)")
    st.plotly_chart(fig, use_container_width=True)

    # ── ElevenLabs plan reference ─────────────────────────────────────────────
    with st.expander("📋 ElevenLabs plan reference"):
        plan_rows = []
        for plan in ELEVENLABS_PLANS:
            chars_covered = plan["credits"] / CHARS_PER_MIN
            plan_rows.append({
                "Plan":                  plan["name"],
                "Monthly ($)":           f"${plan['monthly']}",
                "Included credits":      f"{plan['credits']:,}",
                "Est. TTS minutes":      f"~{chars_covered:,.0f} min",
                "Overage per 1k chars":  f"${plan['overage_per_1k']}",
            })
        st.dataframe(pd.DataFrame(plan_rows), hide_index=True, use_container_width=True)
        st.caption(
            f"Minutes estimated at {CHARS_PER_MIN} chars/min. "
            "Retell infrastructure ($0.055/min) is not included in plan pricing — "
            "it applies on top in all direct scenarios."
        )

    st.divider()
    st.markdown("#### 📝 Methodology notes")
    st.caption(
        "Characters per minute (750 chars/min): ElevenLabs plans are priced in credits, "
        "where 1 credit = 1 character of text on standard models. To convert call minutes into "
        "characters, this simulator uses an estimate of 750 characters per minute of spoken audio. "
        "This is based on an average English speech rate of ~150 words per minute, multiplied by "
        "an average of ~5 characters per word (150 x 5 = 750). So for every minute our agent "
        "speaks, approximately 750 characters of text are processed to generate that audio."
    )
    st.caption(
        "Overage calculation: When monthly character usage exceeds a plan's included credits, "
        "overage is charged per 1,000 characters above the limit. Formula: "
        "(chars used - included credits) / 1,000 x overage rate. "
        "Overage rates vary by plan: "
        "Creator $0.30/1k "
        "Pro $0.24/1k "
        "Scale $0.18/1k "
        "Business $0.12/1k "
    )
    st.caption(
        "Enterprise discount: Applied to both the plan base cost and overage rate on the "
        "Direct ElevenLabs path. This simulates a negotiated contract rate — the same type of "
        "arrangement Retell previously held with ElevenLabs before March 23, 2026."
    )
    st.caption(
        "Direct ElevenLabs route assumes Retell supports bring-your-own-API-key (BYOK) - "
        "confirm with Retell support before committing to a direct plan."
    )
    st.caption(
        "Usage stats (top metrics row): Minutes/month = calls per day x avg call duration x "
        "active agents x 30 days. Characters/month = minutes/month x 750 chars/min. "
        "Calls/month = calls per day x active agents x 30 days. "
        "Patients/month is entered directly in the sidebar. "
        "Scheduled/month = patients/month x scheduling conversion rate (default 18%, based on "
        "pilot data: 36 patients scheduled out of 199)."
    )
    st.caption(
        "Retell infrastructure fee is $0.055/min. This is Retell's core platform charge, "
        "billed per minute of active call time regardless of which TTS provider you use. It covers "
        "Retell's turn-taking model, orchestration engine, transcription (ASR), and telephony "
        "infrastructure. It is separate from — and in addition to — any TTS cost (ElevenLabs, "
        "Alt TTS, or a direct plan). "
        "Formula: total minutes/month x $0.055."
        "For example, at 3,120 minutes/month: 3,120 x $0.055 = $171.60/month in Retell infra alone."
    )
    st.caption(
        "Cost per scheduled patient: Monthly total cost / scheduled patients per month. "
        "Scheduled patients = total patients x scheduling conversion rate (default 18%, based on "
        "pilot data: 36 scheduled out of 199). This metric answers: 'What did it cost in TTS and "
        "infrastructure to get one patient onto the schedule?' — making it a practical benchmark "
        "for clinical and ops stakeholders evaluating cost-per-outcome rather than cost-per-minute."
    )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — LINE OF BUSINESS
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.title("🏥 TTS Cost by Line of Business")
    st.caption("Breaks down TTS costs per LOB based on patient mix and per-LOB call volume.")

    col1, col2 = st.columns(2)
    lob_pcts              = {}
    lob_calls_per_patient = {}

    with col1:
        st.markdown("**LOB patient mix (%)**")
        for lob, d in LOB_DEFAULTS.items():
            lob_pcts[lob] = st.slider(
                lob, 0, 100, int(d["pct"] * 100),
                step=1, key=f"lob_pct_{lob}", format="%d%%"
            ) / 100

    with col2:
        st.markdown("**Avg calls per patient by LOB**")
        lob_call_defaults = {"Commercial": 7, "Medicare": 9, "Medicaid": 6, "No LOB": 9}
        for lob in LOB_DEFAULTS:
            lob_calls_per_patient[lob] = st.slider(
                f"{lob} calls/patient", 1, 20,
                lob_call_defaults[lob], step=1,
                key=f"lob_calls_{lob}",
            )

    total_pct = sum(lob_pcts.values())
    if abs(total_pct - 1.0) > 0.02:
        st.warning(f"⚠️ LOB mix sums to {total_pct*100:.0f}% — adjust to total 100% for accurate results.")

    norm = {lob: v / total_pct for lob, v in lob_pcts.items()} if total_pct > 0 else lob_pcts

    st.divider()

    # Scenario selector — now includes Creator and Pro
    lob_scenario_options = ["Retell + ElevenLabs", "Retell + Alt TTS"] + COMPARE_PLANS
    lob_scenario_sel = st.radio(
        "View LOB breakdown for:", lob_scenario_options, horizontal=True
    )

    # Compute per-LOB
    chart_lob_labels = []
    chart_series     = {s: [] for s in lob_scenario_options}
    cpp_series       = {s: [] for s in lob_scenario_options}
    table_rows       = []

    for lob, weight in norm.items():
        lob_patients  = total_patients_input * weight
        lob_calls     = lob_patients * lob_calls_per_patient[lob]
        lob_minutes   = lob_calls * avg_duration
        lob_chars     = lob_minutes * CHARS_PER_MIN
        lob_scheduled = round(lob_patients * conversion_rate)

        c = compute_tts_costs(lob_minutes, lob_chars, enterprise_discount)

        costs_by_scenario = {
            "Retell + ElevenLabs": c["retell_el"],
            "Retell + Alt TTS":    c["retell_alt"],
        }
        for pname in COMPARE_PLANS:
            costs_by_scenario[pname] = c["plan_costs"][pname]["total"]

        chart_lob_labels.append(lob)
        for s in lob_scenario_options:
            cost = costs_by_scenario[s]
            cpp  = cost / lob_patients if lob_patients else 0
            chart_series[s].append(round(cost, 2))
            cpp_series[s].append(round(cpp, 2))

        sel_cost = costs_by_scenario[lob_scenario_sel]
        sel_cpp  = sel_cost / lob_patients if lob_patients else 0
        sel_cps  = sel_cost / lob_scheduled if lob_scheduled else 0
        table_rows.append({
            "LOB":           lob,
            "Patients":      f"{round(lob_patients):,}",
            "Calls":         f"{round(lob_calls):,}",
            "Minutes":       f"{round(lob_minutes):,}",
            "Monthly cost":  f"${sel_cost:,.2f}",
            "Per patient":   f"${sel_cpp:,.2f}",
            "Per scheduled": f"${sel_cps:,.2f}",
        })

    st.dataframe(pd.DataFrame(table_rows), hide_index=True, use_container_width=True)

    st.divider()

    # Grouped bar — monthly cost by LOB
    st.subheader("Monthly TTS cost by LOB — all scenarios")
    fig_lob = go.Figure()
    for s in lob_scenario_options:
        fig_lob.add_trace(go.Bar(
            name=s, x=chart_lob_labels, y=chart_series[s],
            marker_color=PLAN_COLORS.get(s, "#888780"),
            text=[f"${v:,.0f}" for v in chart_series[s]],
            textposition="outside",
        ))
    fig_lob.update_layout(
        barmode="group", margin=dict(l=0, r=0, t=30, b=0),
        yaxis=dict(tickprefix="$", tickformat=",.0f", title="Monthly cost"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    )
    fig_lob.update_xaxes(showgrid=False)
    fig_lob.update_yaxes(showgrid=True, gridcolor="rgba(128,128,128,0.15)")
    st.plotly_chart(fig_lob, use_container_width=True)

    # Cost per patient by LOB
    st.subheader("TTS cost per patient by LOB — all scenarios")
    fig_cpp = go.Figure()
    for s in lob_scenario_options:
        fig_cpp.add_trace(go.Bar(
            name=s, x=chart_lob_labels, y=cpp_series[s],
            marker_color=PLAN_COLORS.get(s, "#888780"),
            text=[f"${v:,.2f}" for v in cpp_series[s]],
            textposition="outside",
        ))
    fig_cpp.update_layout(
        barmode="group", margin=dict(l=0, r=0, t=30, b=0),
        yaxis=dict(tickprefix="$", tickformat=",.2f", title="Cost per patient"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    )
    fig_cpp.update_xaxes(showgrid=False)
    fig_cpp.update_yaxes(showgrid=True, gridcolor="rgba(128,128,128,0.15)")
    st.plotly_chart(fig_cpp, use_container_width=True)

    # Patient distribution pie
    st.subheader("Patient distribution by LOB")
    fig_pie = go.Figure(go.Pie(
        labels=chart_lob_labels,
        values=[round(total_patients_input * norm[lob]) for lob in chart_lob_labels],
        marker_colors=[LOB_DEFAULTS[lob]["color"] for lob in chart_lob_labels],
        hole=0.4, textinfo="label+percent",
    ))
    fig_pie.update_layout(
        margin=dict(l=0, r=0, t=20, b=0),
        showlegend=False, paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig_pie, use_container_width=True)

    st.caption(
        f"Scheduling conversion rate: {conversion_rate*100:.0f}%. "
        "Calls per patient defaults reflect O/I pilot data. "
        "Retell infrastructure fee ($0.055/min) is included in all direct plan scenarios."
    )