
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from io import BytesIO
from datetime import datetime

st.set_page_config(page_title="Dashboard Kepatuhan Pajak (Versi SAFE++)", layout="wide")

# ---------- PANDUAN ----------
with st.expander("📘 Panduan Format Excel (Klik untuk lihat)"):
    st.markdown("""
    Berikut adalah aturan format file Excel yang dapat digunakan:

    ✅ **Kolom Wajib:**
    - `NAMA OP`, `STATUS`, `TMT`

    ✅ **Kolom Pembayaran Bulanan:**
    - Nama kolom bisa `2024-01-01`, `Jan-24`, `Masa Januari`, dll — penting ada tahun pajaknya.
    - Nilai harus berupa angka (jangan pakai teks atau simbol).

    ❌ **Jangan Gunakan:**
    - Kolom berjudul `Total`, `Rata-rata`, `Grand Total`, dll. di tengah kolom pembayaran.

    📁 Gunakan contoh file bernama **CONTOH_FORMAT_SETORAN MASA.xlsx**
    """)

# ---------- INPUT ----------
st.markdown("### 📤 Silakan upload file Excel berisi data setoran masa pajak.")
tahun_pajak = st.selectbox("🗓️ Pilih Tahun Pajak", list(range(2022, datetime.now().year + 2))[::-1])
uploaded_file = st.file_uploader("Upload File Excel", type=["xlsx"], label_visibility="collapsed")

if uploaded_file is None:
    st.warning("⚠️ Silakan upload file terlebih dahulu.")
    st.stop()

# ---------- BACA DATA ----------
df_input = pd.read_excel(uploaded_file)

# ---------- NORMALISASI KOLOM ----------
df_input.columns = [str(c).upper().strip() for c in df_input.columns]
required_cols = ["NAMA OP", "STATUS", "TMT"]
missing = [col for col in required_cols if col not in df_input.columns]
if missing:
    st.error(f"❌ Kolom wajib hilang: {', '.join(missing)}. Harap periksa file Anda.")
    st.stop()

# ---------- PREPROSES ----------
df_input["TMT"] = pd.to_datetime(df_input["TMT"], errors="coerce")
df_input["TAHUN TMT"] = df_input["TMT"].dt.year.fillna(0).astype(int)

# Cari kolom pembayaran valid (berisi tahun pajak di header)
payment_cols = [col for col in df_input.columns if str(tahun_pajak) in col and df_input[col].dtype != "O"]
if not payment_cols:
    st.error("❌ Tidak ditemukan kolom pembayaran murni yang valid.")
    st.stop()

# ---------- HITUNG BULAN AKTIF ----------
def hitung_bulan_aktif(tmt, tahun):
    if pd.isna(tmt):
        return 0
    if tmt.year > tahun:
        return 0
    if tmt.year < tahun:
        return 12
    return 12 - tmt.month + 1

df_input["BULAN AKTIF"] = df_input["TMT"].apply(lambda x: hitung_bulan_aktif(x, tahun_pajak))

# ---------- HITUNG KEPATUHAN ----------
df_input["BULAN PEMBAYARAN"] = df_input[payment_cols].gt(0).sum(axis=1)
df_input["TOTAL PEMBAYARAN"] = df_input[payment_cols].sum(axis=1)
df_input["RATA-RATA PEMBAYARAN"] = df_input["TOTAL PEMBAYARAN"] / df_input["BULAN PEMBAYARAN"].replace(0, np.nan)
df_input["KEPATUHAN (%)"] = (df_input["BULAN PEMBAYARAN"] / df_input["BULAN AKTIF"].replace(0, np.nan)) * 100

def klasifikasi(row):
    if row["BULAN AKTIF"] == 0:
        return "Kurang Patuh"
    gap = row["BULAN AKTIF"] - row["BULAN PEMBAYARAN"]
    if gap > 3:
        return "Kurang Patuh"
    elif gap > 1:
        return "Cukup Patuh"
    else:
        return "Patuh"

df_input["KLASIFIKASI KEPATUHAN"] = df_input.apply(klasifikasi, axis=1)

# ---------- OUTPUT ----------
st.success("✅ Data berhasil diproses dan difilter!")

st.dataframe(df_input.style.format({
    "TOTAL PEMBAYARAN": "{:,.2f}",
    "RATA-RATA PEMBAYARAN": "{:,.2f}",
    "KEPATUHAN (%)": "{:.2f}"
}), use_container_width=True)

# ---------- DOWNLOAD ----------
def to_excel(df):
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Output")
    return buffer

st.download_button("📥 Download Hasil Excel", to_excel(df_input), "dashboard_output.xlsx")

# ---------- GRAFIK ----------
st.markdown("### 📊 Top 20 Pembayar Tertinggi")
top20 = df_input.sort_values(by="TOTAL PEMBAYARAN", ascending=False).head(20)
fig = px.bar(top20, x="NAMA OP", y="TOTAL PEMBAYARAN", text="TOTAL PEMBAYARAN", color="KLASIFIKASI KEPATUHAN")
st.plotly_chart(fig, use_container_width=True)
