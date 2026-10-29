# Boeing 777-300ER Visual Loading System

A Streamlit web adaptation of `VLStest2.ipynb` with passenger, cargo, take-off fuel, and trip fuel sliders; ZFW/TOW/LW calculations; and an annotated CG envelope.

**Educational demonstration only — not for aircraft operations.** The 30% MAC dry operating CG, 84 kg per passenger, approximate envelope, shaded take-off area, and simplified fuel-burn sequence are assumptions. The take-off shaded-area and 24%/27% MAC restrictions are not validated in the status column.

## Run locally

From this folder, run:

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Publish using GitHub and Streamlit Community Cloud

1. Create a GitHub repository (for example `B777-Loading-System`).
2. Upload **the contents of this folder** to the repository root: `app.py`, `requirements.txt`, all three CSV files, and optionally the original notebook and this README. Do not upload the ZIP as a single file.
3. Visit https://share.streamlit.io and sign in with GitHub.
4. Choose to deploy an app from an existing repository; select the repository, `main` branch, and `app.py` as the main file path.
5. Deploy. Streamlit installs the requirements and provides a shareable `.streamlit.app` URL.

## Test configuration

Passengers: 30, 110, 120, 90. Cargo: 4000, 9000, 7000, 4000 kg. Take-off fuel: 25000, 25000, 40000 kg. Trip fuel: 65000 kg.

Expected ZFW = **224400 kg**, TOW = **314400 kg**, LW = **249400 kg**. CG status is a simplified educational check.
