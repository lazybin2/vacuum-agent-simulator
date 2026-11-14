import io
import time

import pandas as pd
import streamlit as st

from database import get_db_history, init_db, log_to_db
from vacuum_agent import EnterpriseVacuumAgent, VacuumEnvironment

# Page Configuration
st.set_page_config(
    page_title="Enterprise AI Vacuum Simulator", page_icon="🤖", layout="wide"
)

# Initialize Database
init_db()

# Custom Glassmorphism UI Styling
st.markdown(
    """
    <style>
    .big-title {
        text-align: center !important;
        font-size: 40px !important;
        font-weight: 900 !important;
        color: #00ADB5 !important;
        width: 100% !important;
        display: block !important;
        margin-top: 5px !important;
        margin-bottom: 5px !important;
    }
    .big-subtitle {
        text-align: center !important;
        font-size: 18px !important;
        font-weight: 600 !important;
        color: #A6ACAF !important;
        width: 100% !important;
        display: block !important;
        margin-bottom: 25px !important;
    }
    .stMetric {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
    }
    </style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="big-title">🤖 Enterprise Autonomous AI Vacuum Simulator</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="big-subtitle">PEAS-Based Autonomous Agent Simulator with A*,'
    " BFS & Dijkstra</div>",
    unsafe_allow_html=True,
)
st.markdown("---")


def stretch(widget, *args, **kwargs):
    """Full-width widget that works on old AND new Streamlit versions."""
    try:
        return widget(*args, width="stretch", **kwargs)
    except TypeError:
        return widget(*args, use_container_width=True, **kwargs)


# Rendering helpers
# The grid is drawn as a FIXED-SIZE HTML table that is updated in place
# (no st.dataframe, no st.rerun on every step) -> no flicker / no resizing.
def render_grid_html(env):
    size = env.size
    cell = max(42, min(70, 640 // size))
    font = max(14, int(cell * 0.40))
    small = max(9, int(cell * 0.22))
    agent_at = {(a["x"], a["y"]): a for a in env.agents}

    rows = []
    for r in range(size):
        tds = []
        for c in range(size):
            pos = (r, c)
            fg = "#111111"
            if pos in agent_at:
                a = agent_at[pos]
                bg = "#9bf6ff" if pos in env.dock_positions else "#a0c4ff"
                body = (
                    f"🤖A{a['id']}<br>"
                    f"<span style='font-size:{small}px'>{a['battery']}%</span>"
                )
            elif pos in env.dock_positions:
                bg = "#9bf6ff"
                body = f"⚡<br><span style='font-size:{small}px'>Power</span>"
            elif pos == env.static_hazard:
                bg = "#ffb703"
                body = "⚠️"
            elif env.grid[r][c] == 2:
                bg, fg = "#343a40", "#ffffff"
                body = "🧱"
            elif env.grid[r][c] == 1:
                bg = "#ffadad"
                body = "🧹"
            elif pos in env.swept_cells:
                bg = "#e4c1f9"
                body = "✨"
            else:
                bg = "#caffbf"
                body = ""
            tds.append(
                f"<td style='width:{cell}px;height:{cell}px;min-width:{cell}px;"
                f"background:{bg};color:{fg};text-align:center;"
                f"vertical-align:middle;font-size:{font}px;font-weight:700;"
                f"line-height:1.1;border:none;padding:0;border-radius:8px;'>"
                f"{body}</td>"
            )
        rows.append("<tr>" + "".join(tds) + "</tr>")

    return (
        "<div style='overflow-x:auto;'>"
        "<table style='border-collapse:separate;border-spacing:3px;"
        "margin:0 auto;table-layout:fixed;width:auto;border:none;'>"
        + "".join(rows)
        + "</table></div>"
    )


def render_telemetry(env):
    lines = []
    for ag in env.agents:
        lines.append(
            f"**Agent {ag['id']}**: Loc: ({ag['x'] + 1},{ag['y'] + 1}) | "
            f"Battery: {ag['battery']}% | Status: {ag['status']} | "
            f"Cleaned: {ag['cleaned']}"
        )
    return "\n\n".join(lines)


# Sidebar Controls
st.sidebar.header("🎛️ Enterprise Configurations")
selected_algo = st.sidebar.selectbox(
    "Search Algorithm",
    ["A* Search", "BFS", "Dijkstra", "Q-Learning (RL)"],
)
num_agents = st.sidebar.slider("Swarm Agents Count", 1, 3, 1)
grid_size = st.sidebar.slider("Environment Size (N x N)", 5, 10, 6)
dirt_prob = st.sidebar.slider("Initial Dirt Density", 0.1, 0.4, 0.2)
wall_prob = st.sidebar.slider("Wall Density", 0.0, 0.3, 0.15)
enable_battery = st.sidebar.checkbox(
    "Enable Battery & Power Station", value=True
)
sim_speed = st.sidebar.slider("Execution Speed (sec)", 0.02, 0.5, 0.15)
seed = st.sidebar.number_input(
    "Random Seed (0 = random)", min_value=0, max_value=99999, value=0, step=1
)
init_button = st.sidebar.button("🔄 Initialize New Environment")

# Session State
if "sim_running" not in st.session_state:
    st.session_state.sim_running = False

config_sig = (
    grid_size, dirt_prob, wall_prob, num_agents, enable_battery, int(seed)
)

# A new environment is built when the button is pressed OR when any
# environment setting (size, agents, dirt, walls, battery, seed) changes.
if (
    "env" not in st.session_state
    or st.session_state.get("config_sig") != config_sig
    or init_button
):
    st.session_state.env = VacuumEnvironment(
        size=grid_size,
        dirt_probability=dirt_prob,
        wall_probability=wall_prob,
        num_agents=num_agents,
        enable_battery=enable_battery,
        seed=int(seed),
    )
    st.session_state.agent_runner = EnterpriseVacuumAgent(
        st.session_state.env, algorithm=selected_algo
    )
    st.session_state.config_sig = config_sig
    st.session_state.sim_running = False
    st.session_state.status_msg = None
    st.session_state.celebrate = False

env = st.session_state.env
agent_runner = st.session_state.agent_runner
agent_runner.algorithm = selected_algo


# Tabs Navigation
tab1, tab2, tab3 = st.tabs(
    ["🏢 Live Simulation", "📊 Analytics & Leaderboard", "📑 Export Reports"]
)

with tab1:
    col_grid, col_info = st.columns([1.3, 1])

    with col_grid:
        st.markdown("### Live Swarm Grid Architecture")
        grid_ph = st.empty()
        st.caption(
            "🤖 Agent  |  ⚡ Power Station  |  ⚠️ Hazard (avoid)  |  🧱 Wall  |"
            "  🧹 Dirt  |  ✨ Swept  |  🟩 Clean"
        )

    with col_info:
        st.markdown("### ⚙️ Agent State & Swarm Telemetry")
        state_ph = st.empty()

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        run_button = stretch(
            st.button,
            "🚀 Run Autonomous Swarm Cleaning Mission",
            disabled=st.session_state.sim_running,
        )
    with col_btn2:
        stop_button = stretch(
            st.button,
            "⏹️ Stop Mission",
            disabled=not st.session_state.sim_running,
        )

    if run_button:
        if env.is_clean():
            st.session_state.status_msg = (
                "info",
                "Environment is already clean. Press 'Initialize New"
                " Environment' to start again.",
            )
        else:
            st.session_state.sim_running = True
            st.session_state.status_msg = None
        st.rerun()

    if stop_button:
        st.session_state.sim_running = False
        st.session_state.status_msg = ("info", "⏹️ Mission stopped by user.")
        st.rerun()

    st.markdown("---")

    col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
    m1 = col_m1.empty()
    m2 = col_m2.empty()
    m3 = col_m3.empty()
    m4 = col_m4.empty()
    m5 = col_m5.empty()

    status_display = st.empty()


def refresh_ui():
    """Redraw grid, telemetry and metrics IN PLACE (no page rerun)."""
    grid_ph.markdown(render_grid_html(env), unsafe_allow_html=True)
    state_ph.info(render_telemetry(env))

    total_steps = sum(ag["steps"] for ag in env.agents)
    total_cleaned = sum(ag["cleaned"] for ag in env.agents)
    initial_dirt = env.initial_dirt_count if env.initial_dirt_count > 0 else 1
    cleaned_pct = int((total_cleaned / initial_dirt) * 100)

    m1.metric("Total Steps", total_steps)
    m2.metric("Cleaned Spots", total_cleaned)
    m3.metric("Efficiency (%)", f"{cleaned_pct}%")
    m4.metric("Algorithm", selected_algo)
    m5.metric("Nodes Expanded", agent_runner.nodes_expanded)
    return total_steps, total_cleaned, cleaned_pct


refresh_ui()

msg = st.session_state.get("status_msg")
if msg and not st.session_state.sim_running:
    getattr(status_display, msg[0])(msg[1])
    if st.session_state.get("celebrate"):
        st.balloons()
        st.session_state.celebrate = False


# Analytics tab
with tab2:
    st.markdown("### 🏆 Historical Leaderboard & Database Analytics")
    db_df = get_db_history()

    if not db_df.empty:
        stretch(st.dataframe, db_df)
        st.markdown("#### Performance Benchmark Chart")
        st.bar_chart(
            db_df.set_index("timestamp")[["total_steps", "cleaned_spots"]]
        )
    else:
        st.info(
            "No simulation runs recorded in the database yet. Run a simulation"
            " first!"
        )

# Export tab
with tab3:
    st.markdown("### 📑 Export Professional Simulation Reports")
    st.markdown(
        "Download complete analytics telemetry and performance metrics for"
        " executive presentations."
    )

    export_df = get_db_history()

    if not export_df.empty:
        csv_data = export_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download CSV Report",
            data=csv_data,
            file_name="vacuum_simulation_report.csv",
            mime="text/csv",
        )

        try:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                export_df.to_excel(
                    writer, sheet_name="Simulation_Report", index=False
                )
            buffer.seek(0)
            st.download_button(
                label="📊 Download Excel Report (.xlsx)",
                data=buffer,
                file_name="vacuum_simulation_report.xlsx",
                mime=(
                    "application/vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"
                ),
            )
        except Exception:
            st.warning(
                "Excel export needs the 'xlsxwriter' package:"
                " pip install xlsxwriter"
            )
    else:
        st.warning("No data available for export.")


# Simulation loop (runs at the very end so every tab is already drawn).
# It updates the placeholders in place - the page is NOT rerun per step,
# which removes the flicker / "mini grid" problem.
if st.session_state.sim_running:
    status_display.warning(f"Mission active using {selected_algo}...")
    max_ticks = env.size * env.size * 80
    result = None

    while True:
        if env.is_clean():
            result = "done"
            break
        if env.ticks >= max_ticks:
            result = "stuck"
            break

        env.ticks += 1
        any_moved = False
        for ag in env.agents:
            if agent_runner.step_agent(ag):
                any_moved = True

        refresh_ui()

        if not any_moved:
            result = "stuck"
            break
        time.sleep(sim_speed)

    total_steps, total_cleaned, cleaned_pct = refresh_ui()

    if not env.logged:
        log_to_db(
            selected_algo,
            grid_size,
            total_steps,
            total_cleaned,
            float(cleaned_pct),
        )
        env.logged = True

    if result == "done":
        st.session_state.status_msg = (
            "success",
            "✅ Mission Accomplished Successfully!",
        )
        st.session_state.celebrate = True
    else:
        st.session_state.status_msg = (
            "warning",
            "Mission ended: agents are stuck or the time limit was reached.",
        )

    st.session_state.sim_running = False
    st.rerun()