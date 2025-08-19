import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from tespy.components import CycleCloser, Pump, Condenser, Turbine, SimpleHeatExchanger, Source, Sink
from tespy.connections import Connection
from tespy.networks import Network

st.set_page_config(page_title="Coal Power Plant Simulator", layout="wide")
st.markdown(
    "<h1 style='text-align: center; color: black;'>Coal-Fired Power Plant Simulator</h1>",
    unsafe_allow_html=True
)

st.sidebar.header("Cycle Parameters")

# User input for main steam
T_steam = st.sidebar.slider("Live Steam Temperature (°C)", 400.0, 650.0, 603.0, step=1.0)
p_steam = st.sidebar.slider("Live Steam Pressure (bar)", 50.0, 300.0, 278.0, step=1.0)
m_steam = st.sidebar.slider("Live Steam Mass Flow (kg/s)", 400.0, 800.0, 532.0, step=2.0)


# User input for condenser
p_cond = st.sidebar.slider("Condenser Pressure (bar)", 0.01, 2.0, 0.1, step=0.01)

# Cooling water
T_cw_in = st.sidebar.slider("Cooling Water Inlet Temp (°C)", 5.0, 40.0, 20.0, step=1.0)
T_cw_out = st.sidebar.slider("Cooling Water Outlet Temp (°C)", T_cw_in+1.0, 60.0, 30.0, step=1.0)
p_cw = st.sidebar.slider("Cooling Water Pressure (bar)", 0.0, 10.0, 1.2, step=0.1)

st.sidebar.markdown("---")
st.sidebar.markdown("**Component Efficiencies**")
eta_turbine = st.sidebar.slider("Turbine Isentropic Efficiency", 0.7, 1.0, 0.9, step=0.01)
eta_pump = st.sidebar.slider("Pump Isentropic Efficiency", 0.5, 1.0, 0.75, step=0.01)

st.sidebar.markdown("---")
st.sidebar.header("Coal Properties")
coal_cv = st.sidebar.number_input("Coal Calorific Value (kJ/kg)", min_value=1000.0, max_value=40000.0, value=24000.0, step=100.0)
boiler_eff = st.sidebar.slider("Boiler Efficiency (%)", 50, 100, 85, step=1) / 100

# TESPy Model Setup
def run_rankine(T_steam, p_steam, m_steam, p_cond, T_cw_in, T_cw_out, p_cw, eta_turbine, eta_pump):
    nw = Network(fluids=['water'], T_unit='C', p_unit='bar', h_unit='kJ / kg')

    cc = CycleCloser('cycle closer')
    sg = SimpleHeatExchanger('steam generator')
    mc = Condenser('main condenser')
    tu = Turbine('steam turbine')
    fp = Pump('feed pump')
    cwso = Source('cooling water source')
    cwsi = Sink('cooling water sink')

    # Connections (main cycle)
    c1 = Connection(cc, 'out1', tu, 'in1', label='1')
    c2 = Connection(tu, 'out1', mc, 'in1', label='2')
    c3 = Connection(mc, 'out1', fp, 'in1', label='3')
    c4 = Connection(fp, 'out1', sg, 'in1', label='4')
    c0 = Connection(sg, 'out1', cc, 'in1', label='0')

    # Cooling water
    c11 = Connection(cwso, 'out1', mc, 'in2', label='11')
    c12 = Connection(mc, 'out2', cwsi, 'in1', label='12')

    nw.add_conns(c1, c2, c3, c4, c0, c11, c12)

    # Component parameters
    mc.set_attr(pr1=1, pr2=0.98)
    sg.set_attr(pr=0.9)
    tu.set_attr(eta_s=eta_turbine)
    fp.set_attr(eta_s=eta_pump)

    # Boundary conditions (minimal, correct set)
    c1.set_attr(T=T_steam, p=p_steam, m=m_steam, fluid={'water': 1})
    c2.set_attr(p=p_cond)
    c11.set_attr(T=T_cw_in, p=p_cw, fluid={'water': 1})
    c12.set_attr(T=T_cw_out)

    # Solve and return results
    nw.solve('design')
    return nw, [c0, c1, c2, c3, c4, c11, c12], [sg, tu, fp, mc]

# Run simulation
with st.spinner("Running TESPy simulation..."):
    try:
        nw, conns, comps = run_rankine(
            T_steam, p_steam, m_steam, p_cond, T_cw_in, T_cw_out, p_cw, eta_turbine, eta_pump
        )
        
    except Exception as e:
        st.error(f"Simulation failed: {e}")
        st.stop()

# --- Calculate Key Performance Indicators (KPIs) ---
boiler_heat_duty = comps[0].Q.val / 1000  # kJ/s
turbine_power = abs(comps[1].P.val/1e3)   # kW (absolute value)
pump_power = comps[2].P.val/1e3           # kW
net_power_output = turbine_power - pump_power  # kW
thermal_efficiency = (net_power_output * 1000) / comps[0].Q.val * 100  # %
coal_flow = boiler_heat_duty / (coal_cv * boiler_eff)  # kg/s
cw_flow = conns[5].m.val if conns[5].m.val is not None else 0  # Cooling water flow (kg/s)

# ---------- Custom Style for Matrix Cards ----------
st.markdown(
    """
    <style>
    .metric-card {
        background-color: #e0f2fe;
        border-radius: 12px;
        padding: 1rem;
        text-align: center;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
        margin-bottom: 10px;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #0369a1;
        font-weight: 1000;
    }
    .metric-value {
        font-size: 1.5rem;
        font-weight: bold;
        color: #111827;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ---------- Helper Function ----------
def render_metric(label, value, unit=""):
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value} {unit}</div>
        </div>
    """, unsafe_allow_html=True)

# ---------- Display Matrix ----------
row1 = st.columns(4)
row2 = st.columns(4)

with row1[0]: render_metric("⚡ Net Power Output", f"{net_power_output/1000:,.2f}", "MW")
with row1[1]: render_metric("🎯 Turbine Output", f"{turbine_power/1000:,.2f}", "MW")
with row1[2]: render_metric("🔄 Pump Input", f"{pump_power/1000:,.2f}", "MW")
with row1[3]: render_metric("🔥 Boiler Heat Duty", f"{boiler_heat_duty/1000:,.2f}", "MW")

with row2[0]: render_metric("⚙️ Thermal Efficiency", f"{thermal_efficiency:.2f}", "%")
with row2[1]: render_metric("🪨 Coal Flow", f"{coal_flow*3.6:.3f}", "T/hr")
with row2[2]: render_metric("🔥 Boiler Efficiency", f"{boiler_eff*100:.1f}", "%")
with row2[3]: render_metric("💧 Cooling Water Flow", f"{cw_flow/1000:.2f}", "m³/s")



# Calculate energy flows (all in MW for clarity)
boiler_heat_mw = comps[0].Q.val / 1e6
turbine_power_mw = abs(comps[1].P.val / 1e6)
pump_power_mw = comps[2].P.val / 1e6
condenser_heat_mw = abs(comps[3].Q.val / 1e6)
net_power_mw = turbine_power_mw - pump_power_mw
coal_input_mw = boiler_heat_mw / boiler_eff
boiler_loss_mw = coal_input_mw - boiler_heat_mw

# Labels with values beneath
labels = [
    f"Coal Chemical Energy<br><b>{coal_input_mw:.2f} MW</b>",
    f"Boiler Heat Input<br><b>{boiler_heat_mw:.2f} MW</b>",
    f"Turbine Output<br><b>{turbine_power_mw:.2f} MW</b>",
    f"Pump Input<br><b>{pump_power_mw:.2f} MW</b>",
    f"Condenser Loss<br><b>{condenser_heat_mw:.2f} MW</b>",
    f"Net Power Output<br><b>{net_power_mw:.2f} MW</b>",
    f"Boiler Loss<br><b>{boiler_loss_mw:.2f} MW</b>",
]

node_colors = [
    "#4B0082",   # Coal: indigo
    "#FF8C00",   # Boiler: orange
    "#228B22",   # Turbine: green
    "#1E90FF",   # Pump: blue
    "#DC143C",   # Condenser: crimson
    "#FFD700",   # Net Power: gold
    "#A9A9A9",   # Boiler Loss: dark gray
]

link_colors = [
    "rgba(75,0,130,0.4)",   # Coal -> Boiler
    "rgba(128,128,128,0.4)", # Coal -> Boiler Loss
    "rgba(255,140,0,0.4)",  # Boiler -> Turbine
    "rgba(255,140,0,0.4)",  # Boiler -> Condenser
    "rgba(34,139,34,0.4)",  # Turbine -> Net Power
    "rgba(34,139,34,0.4)",  # Turbine -> Pump
]

sources = [0, 0, 1, 1, 2, 2]
targets = [1, 6, 2, 4, 5, 3]
values = [
    boiler_heat_mw,        # Coal -> Boiler
    boiler_loss_mw,        # Coal -> Boiler Loss
    turbine_power_mw,      # Boiler -> Turbine
    condenser_heat_mw,     # Boiler -> Condenser
    net_power_mw,          # Turbine -> Net Power
    pump_power_mw,         # Turbine -> Pump
]

link_labels = [
    f"To Boiler ({boiler_heat_mw:.2f} MW)",
    f"Boiler Loss ({boiler_loss_mw:.2f} MW)",
    f"To Turbine ({turbine_power_mw:.2f} MW)",
    f"To Condenser ({condenser_heat_mw:.2f} MW)",
    f"Net Power Output ({net_power_mw:.2f} MW)",
    f"Pump Power ({pump_power_mw:.2f} MW)"
]

fig = go.Figure(go.Sankey(
    arrangement="snap",
    node=dict(
        pad=20,
        thickness=30,
        line=dict(color="black", width=0.5),
        label=labels,
        color=node_colors,
        hovertemplate='%{label}<extra></extra>',
    ),
    link=dict(
        source=sources,
        target=targets,
        value=values,
        color=link_colors,
        label=link_labels,
        hovertemplate='%{label}: %{value:.2f} MW<extra></extra>',
    )
))

fig.update_layout(
    title_text="Energy Flow Diagram (Sankey) for Coal-Fired Power Plant",
    font_size=15,
    margin=dict(l=10, r=10, t=40, b=20)
)

st.subheader("Energy Flow Diagram (Sankey)")
st.plotly_chart(fig, use_container_width=True)



st.caption("Edit parameters in the sidebar and rerun for new results.")

# --- Main Cycle State Points Table (Collapsed) ---
with st.expander("Main Cycle State Points", expanded=False):
    # Map your connections to the correct physical labels
    state_points = [
        ("Boiler Inlet (c4)", conns[3]),       # c4: Pump outlet (to boiler)
        ("Boiler Outlet (c1)", conns[0]),      # c1: Boiler outlet (to turbine)
        ("Turbine Exhaust (c2)", conns[1]),    # c2: Turbine outlet (to condenser)
        ("Condenser Outlet (c3)", conns[2]),   # c3: Condenser outlet (to pump)
        ("CW Inlet (c11)", conns[5]),          # c11: Cooling water in
        ("CW Outlet (c12)", conns[6])          # c12: Cooling water out
    ]
    data = []
    for label, c in state_points:
        data.append({
            "Label": label,
            "Mass Flow (kg/s)": f"{c.m.val:.2f}" if c.m.val is not None else "N/A",
            "Pressure (bar)": f"{c.p.val:.2f}" if c.p.val is not None else "N/A",
            "Temperature (°C)": f"{c.T.val:.2f}" if c.T.val is not None else "N/A",
            "Enthalpy (kJ/kg)": f"{c.h.val:.2f}" if c.h.val is not None else "N/A"
        })
    df = pd.DataFrame(data)
    st.table(df)


# --- Component Performance Table (Collapsed) ---
with st.expander("Component Performance", expanded=False):
    data2 = []
    for comp in comps:
        if hasattr(comp, 'P') and comp.P.val is not None:
            data2.append({
                "Component": comp.label,
                "Power (kW)": f"{comp.P.val/1e3:.2f}"
            })
        elif hasattr(comp, 'Q') and comp.Q.val is not None:
            data2.append({
                "Component": comp.label,
                "Heat Duty (kW)": f"{comp.Q.val/1e3:.2f}"
            })
    st.table(pd.DataFrame(data2))

# --- Coal Flow Calculation Details (Collapsed) ---
with st.expander("Coal Consumption Calculation", expanded=False):
    st.write(f"**Boiler Heat Duty:** {boiler_heat_duty:,.2f} kJ/s")
    st.write(f"**Coal Calorific Value:** {coal_cv:,.0f} kJ/kg")
    st.write(f"**Boiler Efficiency:** {boiler_eff*100:.1f} %")
    st.write(f"### Required Coal Flow: {coal_flow:.3f} kg/s")





