# Boeing 777-300ER Visual Loading System
# Streamlit adaptation of "Visual Loading System(1).ipynb"
# Educational model only. NOT for operational aircraft loading.

from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.path import Path as MplPath
import pandas as pd
import streamlit as st

st.set_page_config(page_title="B777-300ER Visual Loading System", layout="wide")
BASE = Path(__file__).resolve().parent

@st.cache_data
def load_data():
    pax = pd.read_csv(BASE / "pax_configuration.csv", sep=";", decimal=",")
    cargo = pd.read_csv(BASE / "cargo_values.csv", sep=";", decimal=",")
    fuel = pd.read_csv(BASE / "FuelTanks.csv", sep=";", decimal=",")
    return pax, cargo, fuel

try:
    pax, cargo, fuel = load_data()
except (OSError, pd.errors.ParserError) as exc:
    st.error(f"Could not read the CSV files: {exc}")
    st.stop()

DOW = 171000
DOW_CG = 30.0
MZFW = 237682
MTOW = 351534
MLW = 251290
MAC = 278.5
LEMAC = 1174.5
DOW_BA = LEMAC + (DOW_CG / 100) * MAC
PAX_WEIGHT = 84

cg_envelope = [
    (7.5, 204116), (10.5, 237682), (11.5, 251290),
    (15.4, 325996), (17.8, 345455), (22.0, 352441),
    (27.4, 352441), (38.1, 343414), (44.0, 304814),
    (44.0, 279911), (44.0, 224029), (34.1, 158031),
    (26.9, 130000), (7.5, 130000), (7.5, 204116)
]
envelope = MplPath(cg_envelope)

def calculate_cg(weights, arms):
    if len(weights) != len(arms):
        raise ValueError("Weights and balance arms must have matching lengths.")
    total_weight = sum(weights)
    total_moment = sum(w * a for w, a in zip(weights, arms))
    cg_arm = total_moment / total_weight
    cg_mac = ((cg_arm - LEMAC) / MAC) * 100
    return total_weight, total_moment, cg_arm, cg_mac

def check_limits(weight, cg, max_weight):
    return ("WITHIN LIMITS" if weight <= max_weight
            and envelope.contains_point((cg, weight)) else "OUTSIDE LIMITS")

def calculate_landing_fuel(takeoff_fuel, trip_fuel):
    # Educational assumption: burn center first, then main tanks equally.
    remaining = list(takeoff_fuel)
    to_burn = trip_fuel
    if len(remaining) >= 3:
        center_burn = min(remaining[2], to_burn)
        remaining[2] -= center_burn
        to_burn -= center_burn
    while to_burn > 0.001:
        available = [i for i in (0, 1) if i < len(remaining) and remaining[i] > 0.001]
        if not available:
            break
        share = to_burn / len(available)
        for i in available:
            burn = min(remaining[i], share)
            remaining[i] -= burn
            to_burn -= burn
    return remaining

st.title("Boeing 777-300ER Visual Loading System")
st.caption("Interactive educational weight-and-balance model — not for flight operations.")
st.info("The shaded take-off restriction and 24%/27% MAC reference lines are visual only; "
        "the automated status checks maximum weight and the main CG polygon.")

with st.sidebar:
    st.header("Passenger Loading")
    pax_numbers = []
    for i, row in pax.iterrows():
        pax_numbers.append(st.slider(
            f"PAX {int(row['section'])}", 0, int(row["Maxseats"]), 0, 1,
            key=f"pax_{i}"
        ))

    st.header("Cargo Loading")
    cargo_weights = []
    for i, row in cargo.iterrows():
        label = "Bulk Cargo" if i == len(cargo) - 1 and len(cargo) == 5 else f"Cargo {int(row['Section'])}"
        cargo_weights.append(st.slider(
            f"{label} (kg)", min_value=0.0, max_value=float(row["Maxweight"]),
            value=0.0, step=10.0, key=f"cargo_{i}"
        ))

    st.header("Take-off Fuel")
    fuel_weights = []
    for i, row in fuel.iterrows():
        fuel_weights.append(st.slider(
            f"{row['Tank']} (kg)", min_value=0.0, max_value=float(row["Maxweight"]),
            value=0.0, step=100.0, key=f"fuel_{i}"
        ))

    total_fuel = sum(fuel_weights)
    trip_fuel = st.slider(
        "Trip Fuel (kg)", min_value=0.0,
        max_value=float(total_fuel), value=0.0, step=100.0,
        key="trip_fuel"
    ) if total_fuel > 0 else 0.0

pax_arms = pax["Arm"].astype(float).tolist()
cargo_arms = cargo["Balancearm"].astype(float).tolist()
fuel_arms = fuel["Balancearm"].astype(float).tolist()
pax_weights = [n * PAX_WEIGHT for n in pax_numbers]
landing_fuel = calculate_landing_fuel(fuel_weights, trip_fuel)

zfw_weights = [DOW] + cargo_weights + pax_weights
zfw_arms = [DOW_BA] + cargo_arms + pax_arms
ZFW, _, _, ZFW_mac = calculate_cg(zfw_weights, zfw_arms)
TOW, _, _, TOW_mac = calculate_cg(zfw_weights + fuel_weights, zfw_arms + fuel_arms)
LW, _, _, LW_mac = calculate_cg(zfw_weights + landing_fuel, zfw_arms + fuel_arms)

results = pd.DataFrame({
    "Condition": ["ZFW", "TOW", "LW"],
    "Weight (kg)": [ZFW, TOW, LW],
    "CG (%MAC)": [ZFW_mac, TOW_mac, LW_mac],
    "Status": [
        check_limits(ZFW, ZFW_mac, MZFW),
        check_limits(TOW, TOW_mac, MTOW),
        check_limits(LW, LW_mac, MLW)
    ]
})
st.subheader("Weight and Balance Results")
a, b, c = st.columns(3)
a.metric("Take-off fuel", f"{total_fuel:,.0f} kg")
b.metric("Trip fuel", f"{trip_fuel:,.0f} kg")
c.metric("Landing fuel", f"{sum(landing_fuel):,.0f} kg")
st.dataframe(results.round(2), use_container_width=True, hide_index=True)

st.subheader("Center of Gravity Envelope")
fig, ax = plt.subplots(figsize=(12, 9))
cg_x = [point[0] for point in cg_envelope]
cg_y = [point[1] for point in cg_envelope]
ax.plot(cg_x, cg_y, color="black", linewidth=1.5, label="CG Envelope")
ax.fill(cg_x, cg_y, color="lightblue", alpha=0.2)
ax.fill([34.1, 44.0, 44.0], [158031, 224029, 279911],
        color="grey", alpha=0.4, label="Restricted take-off area")
ax.text(36, 216000, "Do not operate\nin shaded area\nduring takeoff",
        fontsize=8, ha="center")
ax.text(12, 361000, "MAXIMUM TAXI\nWEIGHT: 352441 KG", fontsize=8, fontweight="bold")
ax.text(31, 361000, "MAXIMUM TAKEOFF\nWEIGHT: 351534 KG", fontsize=8, fontweight="bold")
ax.text(29, 253000, "MAXIMUM LANDING\nWEIGHT: 251290 KG", fontsize=8, fontweight="bold")
ax.text(29, 239000, "MAXIMUM ZERO FUEL\nWEIGHT: 237682 KG", fontsize=8, fontweight="bold")
ax.vlines([24, 27], ymin=130000, ymax=351534, colors="black", linewidth=0.8)
ax.text(23.2, 160000, "24% MAC", rotation=90, fontsize=8)
ax.text(26.2, 160000, "27% MAC", rotation=90, fontsize=8)
for text, xy, xytext in [
    ("7.5% at 204116 KG", (7.5, 204116), (9, 208000)),
    ("17.8% at 345455 KG", (17.8, 345455), (11, 347000)),
    ("38.1% at 343414 KG", (38.1, 343414), (39, 346000)),
    ("44% at 304814 KG", (44, 304814), (39, 310000))
]:
    ax.annotate(text, xy=xy, xytext=xytext, fontsize=8)
for cg, weight, color, name in [
    (ZFW_mac, ZFW, "blue", "ZFW"),
    (TOW_mac, TOW, "red", "TOW"),
    (LW_mac, LW, "green", "LW")
]:
    ax.scatter(cg, weight, color=color, marker="o", s=130, label=name, zorder=5)
for weight, color in [(MZFW, "blue"), (MLW, "green"), (MTOW, "red")]:
    ax.axhline(weight, color=color, linestyle="--", alpha=0.5)
ax.set_xlabel("CENTER OF GRAVITY - % MAC")
ax.set_ylabel("GROSS WEIGHT - KG")
ax.set_title("Boeing 777-300ER Visual Loading System", fontsize=14, fontweight="bold")
ax.set_xlim(5, 50)
ax.set_ylim(120000, 375000)
ax.grid(True, alpha=0.3)
ax.legend(loc="lower right")
st.pyplot(fig)
plt.close(fig)

with st.expander("Show source loading data"):
    st.write("Passenger sections")
    st.dataframe(pax, hide_index=True)
    st.write("Cargo compartments")
    st.dataframe(cargo, hide_index=True)
    st.write("Fuel tanks")
    st.dataframe(fuel, hide_index=True)
