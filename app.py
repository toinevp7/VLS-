"""B777-300ER educational loading dashboard, adapted from VLStest2.ipynb."""
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.path import Path as MplPath
import pandas as pd
import streamlit as st

st.set_page_config(page_title="B777-300ER Visual Loading System", page_icon="✈️", layout="wide")
BASE = Path(__file__).resolve().parent

@st.cache_data
def load_data():
    pax = pd.read_csv(BASE / "pax_configuration.csv", sep=";", decimal=",")
    cargo = pd.read_csv(BASE / "cargo_values.csv", sep=";", decimal=",")
    fuel = pd.read_csv(BASE / "FuelTanks.csv", sep=";", decimal=",")
    return pax, cargo, fuel

pax, cargo, fuel = load_data()
DOW = 171000
DOW_CG = 30.0  # assumed %MAC in source notebook
MZFW, MTOW, MLW = 237682, 351534, 251290
MAC, LEMAC = 278.5, 1174.5
DOW_BA = LEMAC + DOW_CG / 100 * MAC
PAX_WEIGHT = 84  # assumed kg/person in source notebook

# Approximate coordinates transcribed in the original notebook; not certified data.
cg_envelope = [
    (7.5, 204116), (10.5, 237682), (11.5, 251290),
    (15.4, 325996), (17.8, 345455), (22.0, 352441),
    (27.4, 352441), (38.1, 343414), (44.0, 304814),
    (44.0, 279911), (44.0, 224029), (34.1, 158031),
    (26.9, 130000), (7.5, 130000),
]
cg_x, cg_y = zip(*cg_envelope)
envelope = MplPath(cg_envelope)


def calculate_cg(weights, arms):
    total_weight = sum(weights)
    total_moment = sum(w * a for w, a in zip(weights, arms))
    cg_arm = total_moment / total_weight
    cg_mac = (cg_arm - LEMAC) / MAC * 100
    return total_weight, total_moment, cg_arm, cg_mac


def check_limits(weight, cg, maximum):
    if weight > maximum:
        return "OVER WEIGHT LIMIT"
    if not envelope.contains_point((cg, weight), radius=1e-7):
        return "OUTSIDE APPROX. CG ENVELOPE"
    return "WITHIN SIMPLIFIED LIMITS"


def calculate_landing_fuel(takeoff_fuel, trip_fuel):
    """Simplified model from notebook: center tank first, then equal main tank burn."""
    remaining = list(takeoff_fuel)
    fuel_to_burn = min(trip_fuel, sum(remaining))
    center_burn = min(remaining[2], fuel_to_burn)
    remaining[2] -= center_burn
    fuel_to_burn -= center_burn
    while fuel_to_burn > 0.001:
        available = [i for i in (0, 1) if remaining[i] > 0.001]
        if not available:
            break
        share = fuel_to_burn / len(available)
        for i in available:
            burn = min(remaining[i], share)
            remaining[i] -= burn
            fuel_to_burn -= burn
    return remaining


st.title("✈️ Boeing 777-300ER Visual Loading System")
st.caption("Educational demonstration based on the uploaded Jupyter notebook — not for flight operations.")

with st.sidebar:
    st.header("Loading controls")
    st.subheader("Passenger loading")
    pax_numbers = [
        st.slider(f"PAX {i + 1}", 0, int(row.Maxseats), 0, key=f"pax_{i}")
        for i, row in pax.iterrows()
    ]
    st.subheader("Cargo loading (kg)")
    cargo_weights = [
        st.slider(f"Cargo {i + 1}", 0.0, float(row.Maxweight), 0.0, step=100.0, key=f"cargo_{i}")
        for i, row in cargo.iterrows()
    ]
    st.subheader("Take-off fuel (kg)")
    fuel_weights = [
        st.slider(f"{row.Tank}", 0.0, float(row.Maxweight), 0.0, step=500.0, key=f"fuel_{i}")
        for i, row in fuel.iterrows()
    ]
    total_fuel = sum(fuel_weights)
    st.subheader("Trip fuel (kg)")
    # Clamp the retained slider state if fuel load decreases.
    if "trip_fuel" in st.session_state:
        st.session_state["trip_fuel"] = min(st.session_state["trip_fuel"], total_fuel)
    trip_fuel = st.slider(
        "Trip Fuel", min_value=0.0, max_value=max(1.0, total_fuel),
        value=0.0, step=100.0, key="trip_fuel"
    )

landing_fuel = calculate_landing_fuel(fuel_weights, trip_fuel)
pax_weights = [n * PAX_WEIGHT for n in pax_numbers]
weights = [DOW] + cargo_weights + pax_weights
arms = [DOW_BA] + cargo["Balancearm"].tolist() + pax["Arm"].tolist()
fuel_arms = fuel["Balancearm"].tolist()
ZFW, _, _, ZFW_mac = calculate_cg(weights, arms)
TOW, _, _, TOW_mac = calculate_cg(weights + fuel_weights, arms + fuel_arms)
LW, _, _, LW_mac = calculate_cg(weights + landing_fuel, arms + fuel_arms)

st.subheader("Weight and balance results")
a, b, c = st.columns(3)
a.metric("Zero Fuel Weight (ZFW)", f"{ZFW:,.0f} kg")
b.metric("Take-off Weight (TOW)", f"{TOW:,.0f} kg")
c.metric("Landing Weight (LW)", f"{LW:,.0f} kg")
results = pd.DataFrame({
    "Condition": ["ZFW", "TOW", "LW"],
    "Weight (kg)": [ZFW, TOW, LW],
    "CG (%MAC)": [ZFW_mac, TOW_mac, LW_mac],
    "Status": [check_limits(ZFW, ZFW_mac, MZFW), check_limits(TOW, TOW_mac, MTOW), check_limits(LW, LW_mac, MLW)],
})
st.dataframe(results.round(2), hide_index=True, use_container_width=True)
st.write(f"**Passengers:** {sum(pax_numbers)}  |  **Cargo:** {sum(cargo_weights):,.0f} kg  |  "
         f"**Take-off fuel:** {total_fuel:,.0f} kg  |  **Trip fuel:** {trip_fuel:,.0f} kg  |  "
         f"**Landing fuel:** {sum(landing_fuel):,.0f} kg")

st.subheader("CG envelope")
fig, ax = plt.subplots(figsize=(12, 9))
ax.plot(cg_x + (cg_x[0],), cg_y + (cg_y[0],), color="black", linewidth=1.5)
ax.fill(cg_x, cg_y, color="lightblue", alpha=0.2)
# Approximate grey region, for visual reference only.
ax.fill([34.1, 44.0, 44.0], [158031, 224029, 279911], color="grey", alpha=0.4,
        label="Restricted take-off area (illustrative)")
ax.text(36, 216000, "Do not operate\nin shaded area\nduring takeoff", fontsize=8, ha="center")
ax.text(12, 361000, "MAXIMUM TAXI\nWEIGHT: 352441 KG", fontsize=8, fontweight="bold")
ax.text(31, 361000, "MAXIMUM TAKEOFF\nWEIGHT: 351534 KG", fontsize=8, fontweight="bold")
ax.text(29, 253000, "MAXIMUM LANDING\nWEIGHT: 251290 KG", fontsize=8, fontweight="bold")
ax.text(29, 239000, "MAXIMUM ZERO FUEL\nWEIGHT: 237682 KG", fontsize=8, fontweight="bold")
ax.vlines([24, 27], ymin=130000, ymax=351534, colors="black", linewidth=0.8)
ax.text(23.2, 160000, "24% MAC", rotation=90, fontsize=8)
ax.text(26.2, 160000, "27% MAC", rotation=90, fontsize=8)
ax.annotate("7.5% at 204116 KG", xy=(7.5, 204116), xytext=(9, 208000), fontsize=8)
ax.annotate("17.8% at 345455 KG", xy=(17.8, 345455), xytext=(11, 347000), fontsize=8)
ax.annotate("38.1% at 343414 KG", xy=(38.1, 343414), xytext=(39, 346000), fontsize=8)
ax.annotate("44% at 304814 KG", xy=(44, 304814), xytext=(39, 310000), fontsize=8)
ax.scatter(ZFW_mac, ZFW, color="blue", marker="o", s=130, label="ZFW", zorder=5)
ax.scatter(TOW_mac, TOW, color="red", marker="o", s=130, label="TOW", zorder=5)
ax.scatter(LW_mac, LW, color="green", marker="o", s=130, label="LW", zorder=5)
ax.axhline(MZFW, color="blue", linestyle="--", alpha=0.5)
ax.axhline(MLW, color="green", linestyle="--", alpha=0.5)
ax.axhline(MTOW, color="red", linestyle="--", alpha=0.5)
ax.set_xlabel("CENTER OF GRAVITY - % MAC")
ax.set_ylabel("GROSS WEIGHT - KG")
ax.set_title("Boeing 777-300ER Visual Loading System", fontweight="bold")
ax.set_xlim(5, 50)
ax.set_ylim(120000, 375000)
ax.grid(True, alpha=0.3)
ax.legend(loc="lower right")
st.pyplot(fig, use_container_width=True)
plt.close(fig)

st.warning("EDUCATIONAL MODEL ONLY: DOW CG (30% MAC) and passenger weight (84 kg) are assumptions. "
           "The CG envelope and grey area are approximate; shaded-area and 24%/27% take-off restrictions "
           "are not implemented in the status checks. The fuel-burn sequence is simplified. "
           "This app must not be used for operational aircraft loading or dispatch.")
with st.expander("Source data used in calculations"):
    st.write("Passenger sections")
    st.dataframe(pax, hide_index=True)
    st.write("Cargo sections")
    st.dataframe(cargo, hide_index=True)
    st.write("Fuel tanks")
    st.dataframe(fuel, hide_index=True)
