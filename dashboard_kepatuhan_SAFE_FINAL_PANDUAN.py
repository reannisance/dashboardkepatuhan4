
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from io import BytesIO

st.set_page_config(page_title="Dashboard Kepatuhan Pajak", layout="wide")

st.title("📊 Dashboard Kepatuhan Pajak (Versi SAFE++)")

with st.expander("📎 Panduan Format Excel (Klik untuk lihat)"):
    st.markdown("""
**Berikut adalah aturan format file Excel yang dapat digunakan:**

✅ **Kolom Wajib:**
- `NAMA OP`, `STATUS`, `TMT`

✅ **Kolom Pembayaran Bulanan:**
- Nama kolom bisa `2024-01-01`, `Jan-24`, `Masa Januari`, dll — penting ada tahun pajaknya.
- Nilai harus berupa angka (jangan pakai teks atau simbol).

❌ **Jangan Gunakan:**
- Kolom berjudul `Total`, `Rata-rata`, `Grand Total`, dsb. di tengah kolom pembayaran.

📁 Gunakan contoh file bernama **CONTOH_FORMAT_SETORAN MASA.xlsx**
""")


st.markdown("### 📥 Silakan upload file Excel berisi data setoran masa pajak.")
tahun_pajak = st.selectbox("📅 Pilih Tahun Pajak", list(range(2022, datetime.now().year + 2))[::-1])

uploaded_file = st.file_uploader("Upload File Excel", type=["xlsx"])

def hitung_bulan_aktif(tmt, tahun_pajak):
    if pd.isnull(tmt):
        return 0
    if tmt.year < tahun_pajak:
        return 12
    elif tmt.year == tahun_pajak:
        return 12 - (tmt.month - 1)
    else:
        return 0

def hitung_kepatuhan(row):
    if row['Bulan Pembayaran'] == 0:
        return 0
    if row['Gap 3 Bulan'] >= 1:
        return 0
    return 100

def klasifikasi_kepatuhan(kepatuhan):
    if kepatuhan == 100:
        return "Patuh"
    elif 50 <= kepatuhan < 100:
        return "Cukup Patuh"
    else:
        return "Kurang Patuh"

if uploaded_file:
    try:
        df_raw = pd.read_excel(uploaded_file, sheet_name=None)
        sheet_name = st.selectbox("📄 Pilih Nama Sheet", df_raw.keys())
        df = df_raw[sheet_name]

        df.columns = [str(col).strip().upper() for col in df.columns]
        kolom_wajib = ['TMT', 'NAMA OP', 'STATUS']
        if not all(col in df.columns for col in kolom_wajib):
            st.error("❌ Kolom wajib hilang: TMT, NAMA OP, STATUS. Harap periksa file Anda.")
        else:
            df['TMT'] = pd.to_datetime(df['TMT'], errors='coerce')
            bulan_cols = [col for col in df.columns if any(str(tahun_pajak) in str(col) or f"{str(tahun_pajak)[2:]}" in str(col) for bln in range(1,13))]
            payment_cols = bulan_cols.copy()
            df['Total Pembayaran'] = df[bulan_cols].fillna(0).sum(axis=1)
            df['Bulan Pembayaran'] = df[bulan_cols].gt(0).sum(axis=1)
            df['Bulan Aktif'] = df['TMT'].apply(lambda x: hitung_bulan_aktif(x, tahun_pajak))
            df['Rata-Rata Pembayaran'] = df['Total Pembayaran'] / df['Bulan Pembayaran'].replace(0, np.nan)

            # Deteksi gap >= 3 bulan kosong
            def hitung_gap(row):
                gaps = (row[bulan_cols] == 0).astype(int)
                count, max_gap = 0, 0
                for val in gaps:
                    if val:
                        count += 1
                        max_gap = max(max_gap, count)
                    else:
                        count = 0
                return 1 if max_gap >= 3 else 0

            df['Gap 3 Bulan'] = df.apply(hitung_gap, axis=1)
            df['Kepatuhan (%)'] = df.apply(hitung_kepatuhan, axis=1)
            df['Klasifikasi Kepatuhan'] = df['Kepatuhan (%)'].apply(klasifikasi_kepatuhan)

            df_display = df[['NAMA OP', 'STATUS', 'Total Pembayaran', 'Bulan Aktif', 'Bulan Pembayaran', 'Rata-Rata Pembayaran', 'Kepatuhan (%)', 'Klasifikasi Kepatuhan']].copy()
            df_display['Total Pembayaran'] = df_display['Total Pembayaran'].apply(lambda x: f"{x:,.2f}")
            df_display['Kepatuhan (%)'] = df_display['Kepatuhan (%)'].apply(lambda x: f"{x:.2f}")

            st.success("✅ Data berhasil diproses dan difilter!")
            st.dataframe(df_display, use_container_width=True)

            # Top 20 Pembayar
            st.subheader("📊 Top 20 Pembayar Tertinggi")
            top20 = df.sort_values("Total Pembayaran", ascending=False).head(20)
            fig = px.bar(top20, x="NAMA OP", y="Total Pembayaran", title="Top 20 Pembayar", labels={"Total Pembayaran": "Rp"}, height=450)
            st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Terjadi kesalahan saat memproses file: {e}")
