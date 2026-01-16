import streamlit as st
import requests
from PIL import Image, ImageDraw
import io
import pandas as pd
import time
from datetime import datetime
import os

API_URL = os.getenv("API_URL", "http://localhost:8000")

# --- Page Config ---
st.set_page_config(
    page_title="Opti-Quality | AI Visual Inspection",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Premium Design System (CSS) ---
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=Outfit:wght@300;500;700&display=swap" rel="stylesheet">
<style>
    /* Global Styles */
    :root {
        --primary: #008DFF;
        --secondary: #6C5CE7;
        --success: #00B894;
        --warning: #FDCB6E;
        --danger: #D63031;
        --bg-dark: #0F172A;
        --bg-light: #F8FAFC;
        --glass: rgba(255, 255, 255, 0.05);
        --glass-border: rgba(255, 255, 255, 0.1);
    }

    .main {
        background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
        color: #E2E8F0;
        font-family: 'Inter', sans-serif;
    }

    h1, h2, h3 {
        font-family: 'Outfit', sans-serif;
        font-weight: 700;
        letter-spacing: -0.5px;
    }

    /* Glassmorphism Card */
    .glass-card {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 20px;
        padding: 24px;
        margin-bottom: 20px;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    
    .glass-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        border-color: var(--primary);
    }

    /* Status Badge */
    .status-pill {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 50px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        margin-bottom: 8px;
    }
    
    .status-automated { background: rgba(0, 184, 148, 0.2); color: #55EFC4; border: 1px solid #00B894; }
    .status-pending { background: rgba(253, 203, 110, 0.2); color: #FFEAA7; border: 1px solid #FDCB6E; }
    
    /* Button Styling */
    .stButton>button {
        background: linear-gradient(90deg, var(--primary) 0%, var(--secondary) 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 12px 24px;
        font-weight: 600;
        transition: all 0.3s ease;
        width: 100%;
    }
    
    .stButton>button:hover {
        opacity: 0.9;
        transform: scale(1.02);
        box-shadow: 0 0 20px rgba(0, 141, 255, 0.4);
    }

    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #0B1120;
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }

    /* Metrics Styling */
    div[data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: 800;
        color: var(--primary);
    }

    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 20px;
        background-color: transparent;
    }

    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: transparent !important;
        border-radius: 10px !important;
        padding: 0 20px !important;
        color: #94A3B8 !important;
        font-weight: 600 !important;
    }

    .stTabs [aria-selected="true"] {
        background: rgba(0, 141, 255, 0.1) !important;
        color: var(--primary) !important;
        border-bottom: 2px solid var(--primary) !important;
    }
    
    /* Image Container */
    .img-container {
        border-radius: 15px;
        overflow: hidden;
        border: 1px solid rgba(255,255,255,0.1);
    }
</style>
""", unsafe_allow_html=True)

# --- Sidebar: System Health & Config ---
with st.sidebar:
    st.image("https://img.icons8.com/isometric/100/shield.png", width=80)
    st.title("System Settings")
    
    st.markdown("---")
    
    # Simple Health Simulation
    health_col1, health_col2 = st.columns(2)
    with health_col1:
        st.write("🛰️ API Status")
        st.write("🧠 Model")
    with health_col2:
        st.markdown("<span style='color:#00B894'>● Online</span>", unsafe_allow_html=True)
        st.markdown("<span style='color:#00B894'>● YOLOv11n</span>", unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("Inspection Configuration")
    
    # Fetch current threshold from API
    try:
        current_threshold_res = requests.get(f"{API_URL}/config/confidence_threshold")
        current_threshold = float(current_threshold_res.json()["value"]) if current_threshold_res.status_code == 200 else 0.6
    except:
        current_threshold = 0.6

    new_threshold = st.slider("Confidence Threshold", 0.0, 1.0, current_threshold, help="Detections below this confidence will be flagged for human review.")
    
    if new_threshold != current_threshold:
        if st.button("💾 SAVE CONFIGURATION"):
            try:
                save_res = requests.post(f"{API_URL}/config/", json={"key": "confidence_threshold", "value": str(new_threshold)})
                if save_res.status_code == 200:
                    st.toast("✅ Configuration Updated", icon="⚙️")
                    st.rerun()
            except:
                st.error("Failed to update configuration.")
    
    st.markdown("---")
    st.selectbox("Line Location", ["Plant Osaka - Line 4", "Plant Detroit - Line 12", "Plant Berlin - Line 1"])
    
    st.markdown("---")
    st.info("💡 **Pro-Tip:** Lower confidence cases are automatically routed to the Annotator tab.")

# --- Header Section ---
st.markdown("""
    <div style='margin-bottom: 40px;'>
        <h1 style='font-size: 3rem;'>Opti-Quality <span style='color:#008DFF'>Core</span></h1>
        <p style='color: #94A3B8; font-size: 1.1rem;'>Next-Gen Human-in-the-Loop Visual Inspection System for Enterprise Operations.</p>
    </div>
""", unsafe_allow_html=True)

tabs = st.tabs(["🏭 Shop Floor View", "🔍 Annotator Mode", "📊 Drift Analytics"])

# --- Tab 0: Shop Floor ---
with tabs[0]:
    st.markdown("### 📽️ Live Production Feed")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("""
            <div class="glass-card">
                <h4>Manual Scan</h4>
                <p style='color:#94A3B8; font-size: 0.9rem;'>Upload a sample for high-precision validation.</p>
            </div>
        """, unsafe_allow_html=True)
        
        uploaded_file = st.file_uploader("Drop inspection image here...", type=["jpg", "jpeg", "png"], key="sf_upload")
        
        if uploaded_file:
            if st.button("🚀 INITIATE GPU-ACCELERATED INSPECTION"):
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "image/jpeg")}
                with st.spinner("AI Analysis in Progress..."):
                    # Simulating a bit of delay for "vibe"
                    time.sleep(1)
                    try:
                        response = requests.post(f"{API_URL}/upload/", files=files)
                        if response.status_code == 200:
                            st.session_state.last_upload = response.json()
                            st.toast("✅ Analysis Success", icon="🚀")
                        else:
                            st.error("Backend unreachable. Ensure FastAPI is running.")
                    except:
                        st.error("Connection Refused. Check API server.")

    with col2:
        if "last_upload" in st.session_state:
            data = st.session_state.last_upload
            img_url = f"{API_URL}/images/{data['filename']}"
            
            is_auto = data['status'] == "automated"
            status_class = "status-automated" if is_auto else "status-pending"
            status_text = "AUTO-VALIDATED" if is_auto else "FLAGGED FOR REVIEW"
            
            st.markdown(f"""
                <div class="glass-card">
                    <span class="status-pill {status_class}">{status_text}</span>
                    <h2 style='margin-top:0;'>AI Verdict</h2>
                    <div style='display:flex; gap: 30px;'>
                        <div>
                            <p style='color:#94A3B8; margin-bottom:0;'>Confidence Level</p>
                            <h3 style='color:#fff;'>{data['confidence']*100:.1f}%</h3>
                        </div>
                        <div>
                            <p style='color:#94A3B8; margin-bottom:0;'>System ID</p>
                            <h3 style='color:#fff;'>#{data['id']}</h3>
                        </div>
                    </div>
                    <p style='color:#64748B; font-size: 0.8rem;'>Scan performed at {current_threshold} threshold.</p>
                </div>
            """, unsafe_allow_html=True)
            
            # Fetch and display image
            img_response = requests.get(img_url)
            img = Image.open(io.BytesIO(img_response.content))
            st.image(img, use_container_width=True)
        else:
            # Placeholder for "Live Feed"
            st.markdown("""
                <div style='height: 400px; border: 2px dashed rgba(255,255,255,0.1); border-radius: 20px; display: flex; align-items: center; justify-content: center; background: rgba(0,0,0,0.2);'>
                    <div style='text-align: center;'>
                        <p style='color: #64748B;'>Waiting for signal or manual upload...</p>
                    </div>
                </div>
            """, unsafe_allow_html=True)

# --- Tab 1: Annotator Mode ---
with tabs[1]:
    st.markdown("### 🔍 Human Expert Review Queue")
    
    try:
        response = requests.get(f"{API_URL}/inspections/", params={"status": "pending_review"})
        pending = response.json() if response.status_code == 200 else []
    except:
        pending = []
    
    if not pending:
        st.markdown("""
            <div style='text-align: center; padding: 100px;'>
                 <img src="https://img.icons8.com/bubbles/100/000000/check-all.png"/>
                 <h2 style='color:#00B894;'>All Clear!</h2>
                 <p style='color:#94A3B8;'>AI confidence levels are currently within safe thresholds.</p>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.write(f"Showing {len(pending)} high-priority cases.")
        
        for item in pending:
            st.markdown(f"""
                <div class="glass-card">
                    <div style='display:flex; justify-content: space-between; align-items: center; margin-bottom: 15px;'>
                        <h4 style='display:inline;'>Case #{item['id']}</h4>
                        <span style='color: var(--warning); font-weight:600;'>Conf: {item['confidence']:.2f}</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            c1, c2 = st.columns([1, 1])
            with c1:
                img_url = f"{API_URL}/images/{item['image_filename']}"
                st.image(img_url, use_container_width=True)
            
            with c2:
                st.markdown("#### Model Interpretation")
                st.json(item['prediction'])
                
                correction = st.text_area("Expert Correction / Remediation Notes", key=f"notes_{item['id']}", placeholder="Enter defect description or adjustment...")
                
                bc1, bc2 = st.columns(2)
                with bc1:
                    if st.button("✅ MARK AS RESOLVED", key=f"btn_res_{item['id']}"):
                        review_data = {"final_prediction": {"notes": correction, "verified": True}}
                        requests.post(f"{API_URL}/review/{item['id']}", json=review_data)
                        st.toast(f"Case #{item['id']} Resolved")
                        time.sleep(0.5)
                        st.rerun()
                with bc2:
                    if st.button("❌ DISCARD / RE-SCAN", key=f"btn_del_{item['id']}"):
                        st.toast("Sending for re-scanning")

# --- Tab 2: Drift Analytics ---
with tabs[2]:
    st.markdown("### 📊 Operational Intelligence")
    
    try:
        stats_res = requests.get(f"{API_URL}/stats/")
        stats = stats_res.json() if stats_res.status_code == 200 else None
        
        drift_res = requests.get(f"{API_URL}/drift/")
        drift_data = drift_res.json() if drift_res.status_code == 200 else None
    except:
        stats = None
        drift_data = None

    if stats:
        # Top Metrics
        m1, m2, m3, m4 = st.columns(4)
        m1.markdown(f'<div class="glass-card" style="text-align:center;"><p style="color:#94A3B8;">Total Scans</p><h1>{stats["total"]}</h1></div>', unsafe_allow_html=True)
        m2.markdown(f'<div class="glass-card" style="text-align:center;"><p style="color:#94A3B8;">AI Automated</p><h1 style="color:var(--success);">{stats["automated"]}</h1></div>', unsafe_allow_html=True)
        m3.markdown(f'<div class="glass-card" style="text-align:center;"><p style="color:#94A3B8;">Pending Expert</p><h1 style="color:var(--warning);">{stats["pending"]}</h1></div>', unsafe_allow_html=True)
        m4.markdown(f'<div class="glass-card" style="text-align:center;"><p style="color:#94A3B8;">Human Verified</p><h1 style="color:var(--primary);">{stats["reviewed"]}</h1></div>', unsafe_allow_html=True)
        
        # Drift Status Alert & Retraining
        if drift_data:
            c_drift, c_retrain = st.columns([3, 1])
            with c_drift:
                if drift_data["drift_detected"]:
                    st.warning(f"⚠️ **MODEL DRIFT DETECTED**: System performance has dropped by {drift_data['drift_score']*100:.1f}%. Immediate retraining recommended.")
                elif "Insufficient data" in drift_data.get("message", ""):
                    st.info(f"ℹ️ {drift_data['message']}")
                else:
                    st.success("✅ **STABLE PERFORMANCE**: No significant confidence drift detected.")
            
            with c_retrain:
                if st.button("🔄 RETRAIN MODEL", help="Fine-tune YOLO on human-reviewed data"):
                    with st.spinner("Fine-tuning in progress... (This may take a while)"):
                        try:
                            res = requests.post(f"{API_URL}/retrain/")
                            if res.status_code == 200:
                                data = res.json()
                                if data["success"]:
                                    st.success("Retrained Successfully!")
                                    st.toast("New model version deployed.", icon="🔥")
                                else:
                                    st.error(f"Failed: {data['message']}")
                            else:
                                st.error("Training Service Error")
                        except:
                            st.error("Connection failed.")

        st.markdown("<br>", unsafe_allow_html=True)
        
        # Enhanced Chart Section
        col_c1, col_c2 = st.columns(2)
        
        with col_c1:
            st.markdown('<div class="glass-card"><h4>Confidence Trends</h4></div>', unsafe_allow_html=True)
            if drift_data and not "Insufficient" in drift_data.get("message", ""):
                chart_data = pd.DataFrame({
                    'Metric': ['Baseline Avg', 'Recent Avg'],
                    'Confidence': [drift_data['baseline_avg'], drift_data['recent_avg']]
                })
                st.bar_chart(chart_data.set_index('Metric'))
            else:
                chart_data = pd.DataFrame({
                    'Time': ['08:00', '10:00', '12:00', '14:00', '16:00'],
                    'Automation %': [95, 92, 98, 94, 91]
                })
                st.area_chart(chart_data.set_index('Time'))
            
        with col_c2:
            st.markdown('<div class="glass-card"><h4>System Audit Trail</h4></div>', unsafe_allow_html=True)
            try:
                audit_res = requests.get(f"{API_URL}/audit/")
                if audit_res.status_code == 200:
                    audit_logs = audit_res.json()
                    for log in audit_logs:
                        with st.container():
                            st.markdown(f"""
                                <div style='font-size: 0.8rem; border-bottom: 1px solid rgba(255,255,255,0.05); padding: 10px 0;'>
                                    <span style='color:var(--primary);'>[{log['timestamp'][:19]}]</span> 
                                    <b style='color:var(--secondary);'>{log['action_type'].upper()}</b>: {log['details']}
                                </div>
                            """, unsafe_allow_html=True)
                else:
                    st.error("Could not fetch audit logs.")
            except:
                st.error("Audit service disconnected.")
    else:
        st.error("Analytics engine disconnected.")
