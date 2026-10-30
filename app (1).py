"""Boeing 777-300ER Visual Loading System — Streamlit edition.
Run: streamlit run app.py
Requires the three original CSV files, or upload them in the sidebar.
Educational model only; not for operational flight planning.
"""
from pathlib import Path
import io
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.path import Path as MplPath
import streamlit as st

st.set_page_config(page_title="B777-300ER Visual Loading System", layout="wide")
st.title("Boeing 777-300ER Visual Loading System")
st.caption("Educational weight-and-balance model — not approved for aircraft operations.")

DOW, DOW_CG = 171000, 30.0
MZFW, MTOW, MLW = 237682, 351534, 251290
MAC, LEMAC = 278.5, 1174.5
DOW_BA = LEMAC + DOW_CG / 100 * MAC
pax_weight = 84
cg_envelope = [
    (7.5,204116),(10.5,237682),(11.5,251290),(15.4,325996),
    (17.8,345455),(22.0,352441),(27.4,352441),(38.1,343414),
    (44.0,304814),(44.0,279911),(44.0,224029),(34.1,158031),
    (26.9,130000),(7.5,130000),(7.5,204116)
]
cg_x = [p[0] for p in cg_envelope]
cg_y = [p[1] for p in cg_envelope]
envelope = MplPath(cg_envelope)

def calculate_cg(weights, arms):
    total_weight = sum(weights)
    total_moment = sum(w * a for w, a in zip(weights, arms))
    cg_arm = total_moment / total_weight
    return total_weight, total_moment, cg_arm, (cg_arm - LEMAC) / MAC * 100

def check_limits(weight, cg, max_weight):
    return "WITHIN LIMITS" if weight <= max_weight and envelope.contains_point((cg, weight)) else "OUTSIDE LIMITS"

def load_csv(filename, uploaded):
    if uploaded is not None:
        return pd.read_csv(uploaded, sep=";", decimal=",")
    path = Path(__file__).resolve().parent / filename
    if path.exists():
        return pd.read_csv(path, sep=";", decimal=",")
    return None

st.sidebar.header("Data files")
st.sidebar.caption("Place CSV files next to app.py or upload them here.")
uploads = {name: st.sidebar.file_uploader(name, type="csv", key=name) for name in
           ("pax_configuration.csv", "cargo_values.csv", "FuelTanks.csv")}
pax = load_csv("pax_configuration.csv", uploads["pax_configuration.csv"])
cargo = load_csv("cargo_values.csv", uploads["cargo_values.csv"])
fuel = load_csv("FuelTanks.csv", uploads["FuelTanks.csv"])
if any(df is None for df in (pax, cargo, fuel)):
    st.warning("To start, provide all three original CSV files: pax_configuration.csv, cargo_values.csv and FuelTanks.csv.")
    st.stop()
try:
    for df, cols in [(pax,["Maxseats","Arm"]),(cargo,["Maxweight","Balancearm"]),(fuel,["Maxweight","Balancearm"])]:
        for col in cols:
            df[col] = pd.to_numeric(df[col], errors="raise")
    if len(pax) != 4 or len(cargo) != 5 or len(fuel) != 3:
        raise ValueError("Expected 4 passenger sections, 5 cargo sections, and 3 fuel tanks.")
except (KeyError, ValueError, TypeError) as exc:
    st.error(f"CSV data does not match the notebook format: {exc}")
    st.stop()

pax_arms = pax["Arm"].tolist()
cargo_arms = cargo["Balancearm"].tolist()
fuel_arms = fuel["Balancearm"].tolist()

st.header("Loading controls")
col1, col2, col3 = st.columns(3)
with col1:
    st.subheader("Passenger loading")
    pax_numbers = [st.slider(f"PAX section {i+1}", 0, int(pax['Maxseats'].iloc[i]), 0, 1, key=f"pax{i}") for i in range(4)]
with col2:
    st.subheader("Cargo loading")
    cargo_labels = ["Cargo fwd 1", "Cargo fwd 2", "Cargo aft 1", "Cargo aft 2", "Bulk Cargo"]
    cargo_weights = [st.slider(cargo_labels[i] + " (kg)", 0.0, float(cargo['Maxweight'].iloc[i]), 0.0, 100.0, key=f"cargo{i}") for i in range(5)]
with col3:
    st.subheader("Take-off fuel")
    fuel_labels = ["Main Tank 1", "Main Tank 2", "Center Tank"]
    fuel_weights = [st.slider(fuel_labels[i] + " (kg)", 0.0, float(fuel['Maxweight'].iloc[i]), 0.0, 500.0, key=f"fuel{i}") for i in range(3)]
    total_fuel = sum(fuel_weights)
    st.subheader("Trip fuel")
    trip_fuel = st.slider("Trip fuel (kg)", 0.0, float(max(1.0, total_fuel)), 0.0, 100.0, key="trip_fuel")
    trip_fuel = min(trip_fuel, total_fuel)

landing_fuel = fuel_weights.copy()
fuel_to_burn = trip_fuel
burn = min(landing_fuel[2], fuel_to_burn)
landing_fuel[2] -= burn
fuel_to_burn -= burn
while fuel_to_burn > 0.001:
    available = [i for i in (0,1) if landing_fuel[i] > 0.001]
    if not available:
        break
    share = fuel_to_burn / len(available)
    for i in available:
        burn = min(landing_fuel[i], share)
        landing_fuel[i] -= burn
        fuel_to_burn -= burn

pax_weights = [n * pax_weight for n in pax_numbers]
weights = [DOW] + cargo_weights + pax_weights
arms = [DOW_BA] + cargo_arms + pax_arms
ZFW, ZFW_moment, ZFW_arm, ZFW_mac = calculate_cg(weights, arms)
TOW, TOW_moment, TOW_arm, TOW_mac = calculate_cg(weights + fuel_weights, arms + fuel_arms)
LW, LW_moment, LW_arm, LW_mac = calculate_cg(weights + landing_fuel, arms + fuel_arms)
ZFW_status = check_limits(ZFW, ZFW_mac, MZFW)
TOW_status = check_limits(TOW, TOW_mac, MTOW)
LW_status = check_limits(LW, LW_mac, MLW)

st.header("Weight and balance results")
a,b,c,d = st.columns(4)
a.metric("Passengers", f"{sum(pax_numbers):,}")
b.metric("Cargo", f"{sum(cargo_weights):,.0f} kg")
c.metric("Take-off fuel", f"{total_fuel:,.0f} kg")
d.metric("Landing fuel", f"{sum(landing_fuel):,.0f} kg")
st.caption(f"Trip fuel: {trip_fuel:,.0f} kg")
results = pd.DataFrame({"Condition":["ZFW","TOW","LW"],
    "Weight (kg)":[ZFW,TOW,LW], "CG (%MAC)":[ZFW_mac,TOW_mac,LW_mac],
    "Status":[ZFW_status,TOW_status,LW_status]})
st.dataframe(results.style.format({"Weight (kg)":"{:,.0f}","CG (%MAC)":"{:.2f}"}), hide_index=True, use_container_width=True)

st.subheader("CG envelope")
def draw_chart():
# CREATE CG ENVELOPE GRAPH
    fig = plt.figure(figsize=(12, 9))

    # CG envelope boundary
    plt.plot(
        cg_x, cg_y,
        color="black",
        linewidth=1.5
    )

    plt.fill(
        cg_x, cg_y,
        color="lightblue",
        alpha=0.2
    )

# GREY RESTRICTED TAKE-OFF AREA
    # Approximate shaded area from reference diagram
    grey_x = [34.1, 44.0, 44.0]
    grey_y = [158031, 224029, 279911]

    plt.fill(
        grey_x,
        grey_y,
        color="grey",
        alpha=0.4,
        label="Restricted take-off area"
    )

    # Restricted area warning
    plt.text(
        36, 216000,
        "Do not operate\nin shaded area\nduring takeoff",
        fontsize=8,
        ha="center"
    )

# MAXIMUM WEIGHT LABELS
    plt.text(
        12, 361000,
        "MAXIMUM TAXI\nWEIGHT: 352441 KG",
        fontsize=8,
        fontweight="bold"
    )

    plt.text(
        31, 361000,
        "MAXIMUM TAKEOFF\nWEIGHT: 351534 KG",
        fontsize=8,
        fontweight="bold"
    )

    plt.text(
        29, 253000,
        "MAXIMUM LANDING\nWEIGHT: 251290 KG",
        fontsize=8,
        fontweight="bold"
    )

    plt.text(
        29, 239000,
        "MAXIMUM ZERO FUEL\nWEIGHT: 237682 KG",
        fontsize=8,
        fontweight="bold"
    )

# TAKE-OFF CG REFERENCE LINES
    plt.vlines(
        [24, 27],
        ymin=130000,
        ymax=351534,
        colors="black",
        linewidth=0.8
    )

    plt.text(
        23.2, 140000,
        "Alternate Forward C.G. Limit for Takeoff I 24%",
        rotation=90,
        fontsize=8
    )

    plt.text(
        26.2, 140000,
        "Alternate Forward C.G. Limit for Takeoff II 27%",
        rotation=90,
        fontsize=8
    )

# ENVELOPE BOUNDARY ANNOTATIONS
    plt.annotate(
        "11.5%",
        xy=(11.5, 251290),
        xytext=(11.0, 258000),
        fontsize=8,
        ha="right",
        arrowprops=dict(arrowstyle="-", color="black", lw=0.5)
    )

    plt.annotate(
        "10.5%",
        xy=(10.5, 237682),
        xytext=(10.0, 245000),
        fontsize=8,
        ha="right",
        arrowprops=dict(arrowstyle="-", color="black", lw=0.5)
    )
    plt.annotate(
        "22.0%",
        xy=(22.0, 351534),
        xytext=(22.0, 357000),
        fontsize=8,
        ha="center",
        arrowprops=dict(arrowstyle="-", color="black", lw=0.5)
    )


    plt.annotate(
        "27.4%",
        xy=(27.4, 351534),
        xytext=(27.4, 357000),
        fontsize=8,
        ha="center",
        arrowprops=dict(arrowstyle="-", color="black", lw=0.5)
    )


    plt.annotate(
        "26.9%",
        xy=(26.9, 130000),
        xytext=(26.5, 135000),
        fontsize=8,
        ha="right",
        arrowprops=dict(arrowstyle="-", color="black", lw=0.5)
    )
    
    plt.annotate(
        "204116 KG at 7.5%",
        xy=(7.5, 204116),
        xytext=(9, 208000),
        fontsize=8,
        va="center",
        arrowprops=dict(arrowstyle="-", color="black", lw=0.5)
    )
    plt.annotate(
        "325996 KG\nat 15.4%",
        xy=(15.4, 325996),
        xytext=(14.4, 325996),
        fontsize=8,
        ha="right",
        va="center",
        arrowprops=dict(arrowstyle="-", color="black", lw=0.5)
    )
    
    plt.annotate(
        "345455 KG\nat 17.8%",
        xy=(17.8, 345455),
        xytext=(17, 345455),
        fontsize=8,
        ha="right",
        va="center",
        arrowprops=dict(arrowstyle="-", color="black", lw=0.5)
    )

    plt.annotate(
        "343414 KG\nat 38.1%",
        xy=(38.1, 343414),
        xytext=(39.2, 343414),
        fontsize=8,
        ha="left",
        va="center",
        arrowprops=dict(arrowstyle="-", color="black", lw=0.5)
    )

    plt.annotate(
        "279911 KG\nat 44.0%",
        xy=(44, 279911),
        xytext=(45.5, 279911),
        fontsize=8,
        ha="left",
        va="center",
        arrowprops=dict(arrowstyle="-", color="black", lw=0.5)
    )
    
    plt.annotate(
        "224029 KG\nat 44.0%",
        xy=(44, 224029),
        xytext=(45.5, 224029),
        fontsize=8,
        ha="left",
        va="center",
        arrowprops=dict(arrowstyle="-", color="black", lw=0.5)
    )

    plt.annotate(
        "158031 KG\nat 34.1%",
        xy=(34.1, 158031),
        xytext=(35, 155000),
        fontsize=8,
        ha="left",
        va="center",
        arrowprops=dict(arrowstyle="-", color="black", lw=0.5)
    )
        
    plt.annotate(
        "304814 KG\nat 44.0% at",
        xy=(44, 304814),
        xytext=(45, 310000),
        fontsize=8,
        ha="left",
        va="center",
        arrowprops=dict(arrowstyle="-", color="black", lw=0.5)
    )

# PLOT AIRCRAFT CG POINTS
    # Zero Fuel Weight
    plt.scatter(
        ZFW_mac, ZFW,
        color="blue",
        marker="o",
        s=130,
        label="ZFW",
        zorder=5
    )

    # Take-off Weight
    plt.scatter(
        TOW_mac, TOW,
        color="red",
        marker="o",
        s=130,
        label="TOW",
        zorder=5
    )

    # Landing Weight
    plt.scatter(
        LW_mac, LW,
        color="green",
        marker="o",
        s=130,
        label="LW",
        zorder=5
    )

# MAXIMUM WEIGHT LIMIT LINES
    plt.axhline(
        MZFW,
        color="blue",
        linestyle="--",
        alpha=0.5
    )

    plt.axhline(
        MLW,
        color="green",
        linestyle="--",
        alpha=0.5
    )

    plt.axhline(
        MTOW,
        color="red",
        linestyle="--",
        alpha=0.5
    )

# GRAPH SETTINGS
    plt.xlabel("CENTER OF GRAVITY - % MAC")
    plt.ylabel("GROSS WEIGHT - KG")

    plt.title(
        "Boeing 777-300ER Visual Loading System",
        fontsize=14,
        fontweight="bold"
    )

    plt.xlim(5, 50)
    plt.ylim(120000, 375000)

    plt.xticks(range(5,51,5))
    plt.yticks(range(120000,375001,10000))

    plt.minorticks_on()
    plt.grid(True, alpha=0.3)
    plt.legend(loc="lower right")

    st.pyplot(fig, clear_figure=True)
    plt.close(fig)


draw_chart()
with st.expander("Show source CSV data"):
    st.write("Passenger configuration", pax)
    st.write("Cargo values", cargo)
    st.write("Fuel tanks", fuel)
