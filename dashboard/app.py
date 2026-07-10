"""
Streamlit dashboard for FitNova Sales-Call Intelligence.

Why this approach:
Streamlit provides a fast, pure-Python way to build high-fidelity interactive UIs. 
This dashboard connects directly to the FastAPI backend, implementing three separate 
corporate roles (Sales Director, Team Leader, Advisor) in a unified interface.
It features custom glassmorphic styling, interactive call ingestion & processing, 
chronological transcript views, and dispute resolution widgets.
"""

import os
import requests
import streamlit as st
import pandas as pd
from datetime import datetime

# Set up page configurations
st.set_page_config(
    page_title="FitNova Call Intelligence",
    page_icon="💪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API endpoint configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")

# Injected custom CSS for premium styling
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] {
    font-family: 'Outfit', sans-serif;
}
.metric-card {
    background: rgba(255, 255, 255, 0.05);
    backdrop-filter: blur(10px);
    border-radius: 12px;
    padding: 20px;
    border: 1px solid rgba(255, 255, 255, 0.1);
    box-shadow: 0 4px 15px 0 rgba(0, 0, 0, 0.1);
    margin-bottom: 20px;
}
.metric-title {
    font-size: 14px;
    color: #888ea8;
    margin-bottom: 5px;
    text-transform: uppercase;
    font-weight: 500;
}
.metric-value {
    font-size: 32px;
    font-weight: 700;
    color: #1ba0e1;
    background: linear-gradient(45deg, #1ba0e1, #a855f7);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.tag-badge {
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: 600;
    display: inline-block;
}
.tag-badge-critical {
    background-color: rgba(239, 68, 68, 0.15);
    color: #ef4444;
    border: 1px solid #ef4444;
}
.tag-badge-warning {
    background-color: rgba(245, 158, 11, 0.15);
    color: #f59e0b;
    border: 1px solid #f59e0b;
}
.tag-badge-info {
    background-color: rgba(59, 130, 246, 0.15);
    color: #3b82f6;
    border: 1px solid #3b82f6;
}
.transcript-line {
    padding: 10px 15px;
    border-radius: 8px;
    margin: 8px 0;
    line-height: 1.5;
}
.transcript-advisor {
    background-color: rgba(27, 160, 225, 0.08);
    border-left: 4px solid #1ba0e1;
}
.transcript-customer {
    background-color: rgba(168, 85, 247, 0.08);
    border-left: 4px solid #a855f7;
}
.transcript-speaker {
    font-weight: 700;
    font-size: 13px;
    margin-bottom: 3px;
}
</style>
""", unsafe_allow_html=True)

# Helper functions for API calls
def api_get(endpoint: str):
    """Sends a GET request to the FastAPI server."""
    try:
        res = requests.get(f"{API_URL}{endpoint}", timeout=10)
        if res.status_code == 200:
            return res.json()
        return None
    except Exception as e:
        st.sidebar.error(f"API Connection error: {e}")
        return None

def api_post(endpoint: str, payload: dict = None):
    """Sends a POST request to the FastAPI server."""
    try:
        res = requests.post(f"{API_URL}{endpoint}", json=payload, timeout=60)
        if res.status_code in [200, 201]:
            return res.json()
        return None
    except Exception as e:
        st.sidebar.error(f"API Connection error: {e}")
        return None

# Sidebar layout
st.sidebar.image("https://fitnova.com.au/wp-content/uploads/2021/07/cropped-Fitnova-Logo-Standard-No-Tagline.png", width=180)
st.sidebar.title("Navigation")
role = st.sidebar.radio(
    "Select View Perspective",
    ["👥 Sales Director (Org)", "👔 Team Leader (Team)", "🤝 Advisor (Individual)"]
)

st.sidebar.markdown("---")
st.sidebar.markdown(f"**Target API:** `{API_URL}`")

# ----------------- 👥 SALES DIRECTOR (ORGANIZATION VIEW) -----------------
if role == "👥 Sales Director (Org)":
    st.title("👥 Sales Director Dashboard")
    st.subheader("Organization Performance & Operations")

    # Ingestion Actions
    col_act1, col_act2 = st.columns([1, 4])
    with col_act1:
        if st.button("🔄 Scan Ingestion Folder", type="primary", use_container_width=True):
            with st.spinner("Scanning for calls..."):
                res = api_post("/calls/ingest")
                if res is not None:
                    st.success(f"Discovered and staged {len(res)} new calls.")
                else:
                    st.error("Ingestion failed or no new calls found.")
                    
    # Org rollup data
    org_summary = api_get("/orgs/1/summary")
    if org_summary:
        # Display rollup stats
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">Total Processed Calls</div>
                <div class="metric-value">{org_summary['total_calls']}</div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">Org Quality Score Average</div>
                <div class="metric-value">{org_summary['overall_average']:.2f} / 5.0</div>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">Compliance Tags Raised</div>
                <div class="metric-value" style="color: #ef4444;">{org_summary['compliance_tag_count']}</div>
            </div>
            """, unsafe_allow_html=True)
            
        # Display Dimension Rollups
        st.markdown("### Dimension Evaluation Breakdown")
        df_dim = pd.DataFrame([
            {"Dimension": "Needs Discovery", "Average Score": org_summary["dimension_averages"]["needs_discovery"]},
            {"Dimension": "Product Knowledge", "Average Score": org_summary["dimension_averages"]["product_knowledge"]},
            {"Dimension": "Objection Handling", "Average Score": org_summary["dimension_averages"]["objection_handling"]},
            {"Dimension": "Compliance Audits", "Average Score": org_summary["dimension_averages"]["compliance"]},
            {"Dimension": "Trial Booking", "Average Score": org_summary["dimension_averages"]["trial_booking"]},
        ])
        st.bar_chart(df_dim.set_index("Dimension"))

    # Table of all calls
    st.markdown("### All Call Records")
    calls = api_get("/calls")
    if calls:
        df_calls = []
        for c in calls:
            created_dt = datetime.fromisoformat(c["created_at"].replace("Z", "+00:00"))
            df_calls.append({
                "ID": c["id"],
                "Source Call ID": c["source_call_id"],
                "Date Ingested": created_dt.strftime("%Y-%m-%d %H:%M"),
                "Status": c["status"].upper(),
                "Action": "Process" if c["status"] == "pending" else "Done"
            })
            
        df = pd.DataFrame(df_calls)
        st.dataframe(df, use_container_width=True)
        
        # Action selector for processing pending calls
        pending_calls = [c for c in calls if c["status"] in ["pending", "failed"]]
        if pending_calls:
            st.markdown("### Run Processing Pipeline")
            select_call = st.selectbox(
                "Select a Pending / Failed Call to Run Pipeline:",
                options=[c["id"] for c in pending_calls],
                format_func=lambda cid: f"Call ID: {cid} ({next(c['source_call_id'] for c in pending_calls if c['id'] == cid)})"
            )
            if st.button("🚀 Process Selected Call", type="primary"):
                with st.spinner("Executing transcription, scoring, and verifier pipeline..."):
                    res = api_post(f"/calls/{select_call}/process")
                    if res:
                        st.success(f"Call {select_call} processed successfully. Status: {res['status']}")
                        st.rerun()
                    else:
                        st.error(f"Pipeline failed for Call {select_call}.")
    else:
        st.info("No calls ingested yet. Click 'Scan Ingestion Folder' to discover calls.")


# ----------------- 👔 TEAM LEADER (TEAM VIEW) -----------------
elif role == "👔 Team Leader (Team)":
    st.title("👔 Team Leader Dashboard")
    st.subheader("Team Performance & Dispute Resolution")
    
    # Team rollup data
    team_summary = api_get("/teams/1/summary")
    if team_summary:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">Team</div>
                <div class="metric-value">{team_summary['team_name']}</div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">Total Calls</div>
                <div class="metric-value">{team_summary['total_calls']}</div>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">Overall Score Avg</div>
                <div class="metric-value">{team_summary['overall_average']:.2f}</div>
            </div>
            """, unsafe_allow_html=True)
        with col4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">Pending Disputes</div>
                <div class="metric-value" style="color: #ef4444;">{team_summary['pending_contests_count']}</div>
            </div>
            """, unsafe_allow_html=True)
            
        # Display Advisor Leaderboard
        st.markdown("### Advisor Leaderboard")
        adv_rows = []
        for adv in team_summary["advisors"]:
            adv_rows.append({
                "Advisor ID": adv["advisor_id"],
                "Advisor Name": adv["advisor_name"],
                "Calls Processed": adv["total_calls"],
                "Quality Average": f"{adv['overall_average']:.2f} / 5.0" if adv["total_calls"] > 0 else "N/A"
            })
        if adv_rows:
            st.table(pd.DataFrame(adv_rows))
            
    # Dispute Resolving Section
    st.markdown("---")
    st.markdown("### ⚖️ Pending Compliance Disputes")
    pending_disputes = api_get("/contests/pending")
    
    if pending_disputes:
        for disp in pending_disputes:
            with st.expander(f"Dispute #{disp['contest_id']} - Advisor: {disp['advisor_name']} on Call #{disp['call_id']}"):
                st.markdown(f"**Compliance Issue:** `{disp['tag_type']}`")
                st.markdown(f"**AI Reason:** {disp['reason']}")
                st.markdown(f"**Contested Quote:**")
                st.info(f"\"{disp['quoted_line']}\"")
                st.markdown(f"**Advisor Note:**")
                st.warning(disp['advisor_note'])
                
                # Dispute Resolution inputs
                tl_note = st.text_input("Resolution Note", key=f"note_{disp['contest_id']}", placeholder="Enter reasons for decision...")
                col_btn1, col_btn2 = st.columns(2)
                
                with col_btn1:
                    if st.button("✅ Uphold Tag (Confirm Penalty)", key=f"uphold_{disp['contest_id']}", use_container_width=True):
                        if len(tl_note) < 3:
                            st.error("Please provide a brief resolution note.")
                        else:
                            res = api_post(
                                f"/contests/{disp['contest_id']}/resolve",
                                payload={"resolved_by": 1, "resolution_note": tl_note, "decision": "upheld"}
                            )
                            if res:
                                st.success("Dispute resolved: Tag upheld.")
                                st.rerun()
                                
                with col_btn2:
                    if st.button("❌ Overturn Tag (Remove Penalty)", key=f"overturn_{disp['contest_id']}", use_container_width=True):
                        if len(tl_note) < 3:
                            st.error("Please provide a brief resolution note.")
                        else:
                            res = api_post(
                                f"/contests/{disp['contest_id']}/resolve",
                                payload={"resolved_by": 1, "resolution_note": tl_note, "decision": "overturned"}
                            )
                            if res:
                                st.success("Dispute resolved: Tag overturned and scores recalculated.")
                                st.rerun()
    else:
        st.info("No pending disputes to resolve.")


# ----------------- 🤝 ADVISOR (INDIVIDUAL VIEW) -----------------
elif role == "🤝 Advisor (Individual)":
    st.title("🤝 Advisor Performance Dashboard")
    
    # Advisor selector
    advisors_list = api_get("/teams/1/summary")
    if advisors_list:
        adv_options = {adv["advisor_name"]: adv["advisor_id"] for adv in advisors_list["advisors"]}
        selected_adv_name = st.selectbox("Select Advisor:", list(adv_options.keys()))
        selected_adv_id = adv_options[selected_adv_name]
        
        # Load advisor summary
        adv_summary = api_get(f"/advisors/{selected_adv_id}/summary")
        if adv_summary:
            # Metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">Advisor Name</div>
                    <div class="metric-value">{adv_summary['advisor_name']}</div>
                </div>
                """, unsafe_allow_html=True)
            with col2:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">Calls Evaluated</div>
                    <div class="metric-value">{adv_summary['total_calls']}</div>
                </div>
                """, unsafe_allow_html=True)
            with col3:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">Quality Overall Avg</div>
                    <div class="metric-value">{adv_summary['overall_average']:.2f} / 5.0</div>
                </div>
                """, unsafe_allow_html=True)
                
            # Dimension Breakdown
            col_left, col_right = st.columns([1, 1])
            with col_left:
                st.markdown("### Quality Dimension scorecard")
                for dim, score in adv_summary["dimension_averages"].items():
                    st.markdown(f"**{dim.replace('_', ' ').title()}:** {score:.2f} / 5.0")
                    st.progress(score / 5.0)
                    
            with col_right:
                # Call history select
                st.markdown("### Call History")
                recent_calls = adv_summary["recent_calls"]
                if recent_calls:
                    call_options = {
                        f"Call ID: {rc['call_id']} ({rc['source_call_id']}) - Score: {rc['overall_score'] if rc['overall_score'] is not None else 'N/A'} - {rc['status'].upper()}": rc["call_id"]
                        for rc in recent_calls
                    }
                    selected_call_label = st.selectbox("Select a Call to Review Details:", list(call_options.keys()))
                    selected_call_id = call_options[selected_call_label]
                    
                    # ----------------- CALL DETAIL RENDER -----------------
                    st.markdown("---")
                    st.subheader(f"🔍 Detailed Audit for Call ID: {selected_call_id}")
                    
                    detail = api_get(f"/calls/{selected_call_id}")
                    if detail:
                        meta_col1, meta_col2, meta_col3 = st.columns(3)
                        with meta_col1:
                            st.write(f"**Status:** `{detail['status'].upper()}`")
                        with meta_col2:
                            st.write(f"**Diarisation Confidence:** `{detail['transcript']['diarisation_confidence'].upper() if detail['transcript'] else 'N/A'}`")
                        with meta_col3:
                            st.write(f"**Source:** `{detail['source_system']}`")
                            
                        # Show scorecard
                        if detail["scores"]:
                            st.markdown("#### Call scorecard Breakdown")
                            sc1, sc2, sc3, sc4, sc5 = st.columns(5)
                            sc1.metric("Discovery", f"{detail['scores']['needs_discovery']:.1f}")
                            sc2.metric("Product", f"{detail['scores']['product_knowledge']:.1f}")
                            sc3.metric("Objections", f"{detail['scores']['objection_handling']:.1f}")
                            sc4.metric("Compliance", f"{detail['scores']['compliance']:.1f}")
                            sc5.metric("Trial Booking", f"{detail['scores']['trial_booking']:.1f}")
                            
                        # Tags audit
                        st.markdown("#### Compliance Audit Flags")
                        if detail["tags"]:
                            for tag in detail["tags"]:
                                severity_class = f"tag-badge-{tag['severity'].lower()}"
                                st.markdown(f"""
                                <div>
                                    <span class="tag-badge {severity_class}">{tag['severity'].upper()}</span>
                                    <strong>Issue:</strong> <code>{tag['type']}</code>
                                </div>
                                """, unsafe_allow_html=True)
                                st.markdown(f"**Reasoning:** {tag['reason']}")
                                st.info(f"**Exposed Substring:** \"{tag['quoted_line']}\" (at {tag['timestamp_sec']:.1f}s)")
                                
                                # Contest dispute section
                                if tag["contest_status"] == "none":
                                    advisor_note = st.text_area("File Dispute Note", key=f"contest_note_{tag['id']}", placeholder="Provide context why this tag is a false-positive...", max_chars=500)
                                    if st.button("⚖️ File Dispute", key=f"file_contest_{tag['id']}"):
                                        if len(advisor_note) < 3:
                                            st.error("Please provide a note explaining the dispute.")
                                        else:
                                            res = api_post(f"/tags/{tag['id']}/contest", payload={"advisor_note": advisor_note})
                                            if res:
                                                st.success("Dispute filed successfully!")
                                                st.rerun()
                                elif tag["contest_status"] == "pending":
                                    st.warning("⚠️ Dispute Pending TL Review")
                                elif tag["contest_status"] == "overturned":
                                    st.success("✅ Dispute Approved: Tag Overturned (Deduction Removed)")
                                elif tag["contest_status"] == "upheld":
                                    st.error("❌ Dispute Declined: Tag Upheld (Violation Maintained)")
                                st.markdown("---")
                        else:
                            st.success("No compliance violations flagged for this call.")
                            
                        # Transcript dialogue bubble render
                        st.markdown("#### Chronological Call Transcript")
                        if detail["transcript"]:
                            for seg in detail["transcript"]["segments_json"]:
                                speaker = seg.get("speaker", "Speaker")
                                text = seg.get("text", "")
                                start = seg.get("start", 0.0)
                                
                                bubble_class = "transcript-advisor" if speaker.lower() in ["advisor", "speaker_0"] else "transcript-customer"
                                display_speaker = "Advisor (Rohan)" if speaker.lower() in ["advisor", "speaker_0"] else "Customer"
                                
                                st.markdown(f"""
                                <div class="transcript-line {bubble_class}">
                                    <div class="transcript-speaker">{display_speaker} ({start:.1f}s)</div>
                                    <div>{text}</div>
                                </div>
                                """, unsafe_allow_html=True)
                        else:
                            st.info("Transcript unavailable. Run processing first.")
                else:
                    st.info("No calls processed for this advisor yet.")
