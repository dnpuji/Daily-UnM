import streamlit as st
import pandas as pd
import requests
import datetime
import uuid
import plotly.express as px

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Monitoring UnM", page_icon="🌱", layout="centered")

# GANTI DENGAN URL PIPEDREAM BAPAK
PIPEDREAM_URL = "https://eo5jyzaisu8ezte.m.pipedream.net" 

st.markdown("""
    <style>
    .stButton button { width: 100%; border-radius: 8px; font-weight: bold; }
    div[data-testid="stExpander"] { border: 1px solid #e0e0e0; border-radius: 10px; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNGSI FORMAT ANGKA CERDAS (Hapus .0) ---
def fmt_num(val):
    if val is None or val == "": return "0"
    try:
        f = float(val)
        return f"{int(f)}" if f.is_integer() else f"{f}"
    except: return str(val)

# --- INISIALISASI DATABASE LOKAL ---
if 'master_pengawas' not in st.session_state: st.session_state.master_pengawas = ["Nama Pengawas"]
if 'master_kegiatan' not in st.session_state: st.session_state.master_kegiatan = ["Nama Kegiatan"]
if 'master_bahan' not in st.session_state: st.session_state.master_bahan = ["Nama Bahan"]

if 'history' not in st.session_state: st.session_state.history = []
if 'paddocks' not in st.session_state: st.session_state.paddocks = [{"name": "", "luas": None}]
if 'bahans' not in st.session_state: st.session_state.bahans = [{"name": "", "dosis": None, "satuan": "Kg"}]

# --- FUNGSI MEMBERSIHKAN FORM ---
def reset_form():
    for key in list(st.session_state.keys()):
        if any(key.startswith(p) for p in ["in_", "p_n_", "p_l_", "b_n_", "b_d_", "b_s_"]):
            del st.session_state[key]
    st.session_state.paddocks = [{"name": "", "luas": None}]
    st.session_state.bahans = [{"name": "", "dosis": None, "satuan": "Kg"}]

st.title("🌱 GPA Monitoring v6.1")
tab_in, tab_wa, tab_dash, tab_hist, tab_mas = st.tabs(["📝 INPUT", "📱 REKAP", "📊 DASH", "📜 HIST", "⚙️ MASTER"])
# ==========================================
# TAB 1: FORM INPUT
# ==========================================
with tab_in:
    tgl = st.date_input("Tanggal", datetime.date.today(), key="in_tgl")
    pengawas = st.selectbox("Nama Pengawas", st.session_state.master_pengawas, key="in_user")
    
    c1, c2 = st.columns(2)
    kegiatan = c1.selectbox("Kegiatan", st.session_state.master_kegiatan, key="in_keg")
    tipe = c2.selectbox("Tipe Laporan", ["Planning", "Hasil"], key="in_tipe")
    
    # value=None membuat kotak benar-benar kosong, tidak ada angka 0
    hk = st.number_input("Total HK", min_value=0.0, step=0.5, value=None, key="in_hk", placeholder="0")

    st.markdown("---")
    st.subheader("📍 Lokasi Paddock")
    total_luas = 0.0
    for i, p in enumerate(st.session_state.paddocks):
        cols = st.columns([2, 1])
        st.session_state.paddocks[i]["name"] = cols[0].text_input(f"Paddock {i+1}", value=p["name"], key=f"p_n_{i}", placeholder="Nama")
        st.session_state.paddocks[i]["luas"] = cols[1].number_input(f"Ha {i+1}", value=p["luas"], key=f"p_l_{i}", placeholder="0")
        total_luas += (st.session_state.paddocks[i]["luas"] or 0.0)
    
    if st.button("➕ Tambah Paddock"): st.session_state.paddocks.append({"name": "", "luas": None}); st.rerun()

    st.markdown("---")
    st.subheader("🧪 Penggunaan Bahan")
    for i, b in enumerate(st.session_state.bahans):
        b_n = st.selectbox(f"Bahan {i+1}", [""] + st.session_state.master_bahan, key=f"b_n_{i}")
        c3, c4, c5 = st.columns([2, 2, 2])
        b_d = c3.number_input(f"Dosis {i+1}", value=None if b["dosis"] is None else b["dosis"], key=f"b_d_{i}", placeholder="0")
        b_s = c4.selectbox(f"Sat {i+1}", ["Kg", "L", "mL", "Gram", "Pcs"], key=f"b_s_{i}")
        t_kebutuhan = round(total_luas * (b_d or 0.0), 2)
        c5.text_input(f"Total {i+1}", value=f"{fmt_num(t_kebutuhan)} {b_s}", disabled=True)
        st.session_state.bahans[i] = {"name": b_n, "dosis": b_d, "satuan": b_s}

    if st.button("➕ Tambah Bahan"): st.session_state.bahans.append({"name": "", "dosis": None, "satuan": "Kg"}); st.rerun()

    st.markdown("---")
    st.subheader("🚜 Unit & Keterangan")
    unit_nm = st.text_input("Nama Alat/Unit", key="in_unit")
    cx, cy, cz = st.columns(3)
    val_rdy = cx.number_input("🟢 Rdy", value=None, key="in_rdy", placeholder="0")
    val_bdn = cy.number_input("🔴 Bdn", value=None, key="in_bdn", placeholder="0")
    val_sby = cy.number_input("🟡 Sby", value=None, key="in_sby", placeholder="0")
    ket_add = st.text_area("Keterangan Tambahan", key="in_ket")

    if st.button("💾 SIMPAN & KIRIM DATA", type="primary"):
        if not kegiatan or not st.session_state.paddocks[0]["name"]:
            st.error("Mohon isi minimal Kegiatan dan 1 Paddock!")
        else:
            payload = {
                "id": str(uuid.uuid4())[:8], "pengirim": pengawas, "tgl": str(tgl), "type": tipe, 
                "kegiatan": kegiatan, "hk": hk or 0, "unit": unit_nm or "-", 
                "rdy": val_rdy or 0, "bdn": val_bdn or 0, "sby": val_sby or 0, "ket": ket_add or "-",
                "data_paddock": [p for p in st.session_state.paddocks if p["name"]],
                "data_bahan": [b for b in st.session_state.bahans if b["name"]]
            }
            try:
                requests.post(PIPEDREAM_URL, json=payload)
                st.session_state.history.insert(0, payload)
                reset_form()
                st.success("✅ Data Terkirim & Form Dibersihkan!"); st.rerun()
            except Exception as e:
                st.error(f"Gagal: {e}")
# ==========================================
# TAB 2: REKAP WA
# ==========================================
with tab_wa:
    st.subheader("📱 Susun Rekap WA")
    tgl_wa = st.date_input("Pilih Tanggal", datetime.date.today(), key="wa_tgl")
    logs = [d for d in st.session_state.history if d['tgl'] == str(tgl_wa)]
    
    if logs:
        opts = {f"{d['id']} - {d['kegiatan']} ({d['type']})": d for d in logs}
        sel_keys = st.multiselect("Klik laporan sesuai urutan yang diinginkan:", options=list(opts.keys()), default=list(opts.keys()))
        
        # LOGIKA JUDUL DINAMIS
        selected_types = set([opts[k]['type'] for k in sel_keys])
        if "Planning" in selected_types and "Hasil" not in selected_types: judul_laporan = "DAILY PLANNING"
        elif "Hasil" in selected_types and "Planning" not in selected_types: judul_laporan = "DAILY HASIL"
        elif not selected_types: judul_laporan = "LAPORAN HARIAN GPA"
        else: judul_laporan = "DAILY PLANNING & HASIL"

        # FORMAT TANGGAL DD/MM/YYYY
        tgl_indo = datetime.datetime.strptime(str(tgl_wa), "%Y-%m-%d").strftime("%d/%m/%Y")
        rekap = f"*{judul_laporan}*\n📅 *Tanggal:* {tgl_indo}\n"
        
        for key in sel_keys:
            d = opts[key]
            rekap += f"\n*-------------------------*\n"
            rekap += f"👤 *Pengawas:* {d['pengirim']}\n"
            # Label (Planning) atau (Hasil) di sini sudah saya hapus
            rekap += f"📝 *{d['kegiatan']}*\n" 
            
            # Penggunaan fmt_num agar 2.0 jadi 2
            rekap += f"👷 HK: {fmt_num(d['hk'])} | 🚜 Unit: {d['unit']} (R:{fmt_num(d['rdy'])} B:{fmt_num(d['bdn'])} S:{fmt_num(d['sby'])})\n"
            rekap += f"📍 *Paddock:* " + ", ".join([f"{p['name']} ({fmt_num(p['luas'])}Ha)" for p in d['data_paddock']]) + "\n"
            if d['data_bahan']:
                rekap += f"🧪 *Bahan:* " + ", ".join([f"{b['name']} ({fmt_num(b['dosis'])} {b['satuan']}/Ha)" for b in d['data_bahan']]) + "\n"
            rekap += f"ℹ️ *Ket:* {d['ket']}\n"
        
        st.markdown("#### Preview Teks:")
        st.code(rekap, language="text")
        
        st.markdown("#### 🛠️ Edit Semua Item Hari Ini")
        for i, d in enumerate(logs):
            with st.expander(f"Edit Laporan: {d['kegiatan']} ({d['type']}) - {d['id']}"):
                col_e1, col_e2, col_e3 = st.columns(3)
                e_pengawas = col_e1.selectbox("Pengawas", st.session_state.master_pengawas, index=st.session_state.master_pengawas.index(d['pengirim']) if d['pengirim'] in st.session_state.master_pengawas else 0, key=f"e_p_{i}")
                e_keg = col_e2.selectbox("Kegiatan", st.session_state.master_kegiatan, index=st.session_state.master_kegiatan.index(d['kegiatan']) if d['kegiatan'] in st.session_state.master_kegiatan else 0, key=f"e_k_{i}")
                e_tipe = col_e3.selectbox("Tipe", ["Planning", "Hasil"], index=0 if d['type']=="Planning" else 1, key=f"e_t_{i}")
                
                col_u1, col_u2 = st.columns([1, 2])
                e_hk = col_u1.number_input("HK", value=float(d['hk'] or 0), step=0.5, key=f"e_hk_{i}")
                e_unit = col_u2.text_input("Unit", value=d['unit'], key=f"e_u_{i}")
                
                e_rdy = col_u1.number_input("Rdy", value=int(d['rdy'] or 0), key=f"e_r_{i}")
                e_bdn = col_u2.number_input("Bdn", value=int(d['bdn'] or 0), key=f"e_b_{i}")
                e_sby = col_u1.number_input("Sby", value=int(d['sby'] or 0), key=f"e_s_{i}")
                e_ket = col_u2.text_input("Ket", value=d['ket'], key=f"e_ket_{i}")
                
                st.markdown("**Data Paddock (Edit Nama/Luas)**")
                for j, p in enumerate(d['data_paddock']):
                    cp1, cp2 = st.columns(2)
                    d['data_paddock'][j]['name'] = cp1.text_input(f"Paddock {j+1}", value=p['name'], key=f"epn_{i}_{j}")
                    d['data_paddock'][j]['luas'] = cp2.number_input(f"Luas {j+1}", value=float(p['luas'] or 0), key=f"epl_{i}_{j}")

                col_btn1, col_btn2 = st.columns(2)
                if col_btn1.button("💾 Simpan Perubahan", key=f"btn_save_{i}"):
                    d['pengirim'] = e_pengawas; d['kegiatan'] = e_keg; d['type'] = e_tipe; d['hk'] = e_hk
                    d['unit'] = e_unit; d['rdy'] = e_rdy; d['bdn'] = e_bdn; d['sby'] = e_sby; d['ket'] = e_ket
                    st.success("Data Terupdate!"); st.rerun()
                if col_btn2.button("🗑️ Hapus Laporan", key=f"btn_del_{i}"):
                    st.session_state.history = [x for x in st.session_state.history if x['id'] != d['id']]
                    st.rerun()
    else:
        st.info("Belum ada data pada tanggal ini.")
# ==========================================
# TAB 3 & 4: DASHBOARD DAN HISTORY
# ==========================================
with tab_dash:
    st.subheader("📈 Evaluasi Tren Planning vs Hasil")
    if st.session_state.history:
        raw_data = []
        for log in st.session_state.history:
            total_l = sum([float(p["luas"] or 0) for p in log["data_paddock"]])
            raw_data.append({"Tanggal": log["tgl"], "Tipe": log["type"], "Luas": total_l, "HK": log["hk"] or 0})
        
        df = pd.DataFrame(raw_data)
        df['Tanggal'] = pd.to_datetime(df['Tanggal'])
        df = df.sort_values('Tanggal')

        if not df.empty:
            df_trend = df.groupby(['Tanggal', 'Tipe'])['Luas'].sum().reset_index()
            fig = px.line(df_trend, x="Tanggal", y="Luas", color="Tipe", markers=True, color_discrete_map={"Planning": "#3b82f6", "Hasil": "#10b981"})
            fig.update_layout(hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig, use_container_width=True)

            tot_p = df[df['Tipe'] == 'Planning']['Luas'].sum()
            tot_h = df[df['Tipe'] == 'Hasil']['Luas'].sum()
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Plan (Ha)", round(tot_p, 2))
            c2.metric("Realisasi (Ha)", round(tot_h, 2))
            c3.metric("Capaian (%)", f"{int((tot_h / tot_p * 100) if tot_p > 0 else 0)}%")
        else:
            st.info("Tidak ada data evaluasi.")
    else:
        st.info("Silakan input data terlebih dahulu.")

with tab_hist:
    st.subheader("📜 10 History Terakhir")
    for h in st.session_state.history[:10]:
        tgl_indo = datetime.datetime.strptime(str(h['tgl']), "%Y-%m-%d").strftime("%d/%m/%Y")
        st.write(f"- {tgl_indo} | {h['kegiatan']} ({h['type']}) oleh {h['pengirim']}")
# ==========================================
# TAB 5: MASTER DATA
# ==========================================
with tab_mas:
    def manage_master(session_key, label):
        st.subheader(f"⚙️ Kelola Daftar {label}")
        new_val = st.text_input(f"Tambah {label} Baru", key=f"add_{session_key}")
        if st.button(f"➕ Tambah {label}", key=f"btn_add_{session_key}"):
            if new_val and new_val not in st.session_state[session_key]:
                st.session_state[session_key].append(new_val)
                st.rerun()
        
        st.markdown("---")
        for i, val in enumerate(st.session_state[session_key]):
            c1, c2, c3 = st.columns([3, 1, 1])
            new_name = c1.text_input(f"Edit {i}", value=val, key=f"edit_{session_key}_{i}", label_visibility="collapsed")
            if c2.button("💾", key=f"save_{session_key}_{i}"):
                st.session_state[session_key][i] = new_name; st.rerun()
            if c3.button("🗑️", key=f"del_{session_key}_{i}"):
                st.session_state[session_key].pop(i); st.rerun()
        st.markdown("<br>", unsafe_allow_html=True)

    manage_master('master_pengawas', 'Pengawas')
    manage_master('master_kegiatan', 'Kegiatan')
    manage_master('master_bahan', 'Bahan')
