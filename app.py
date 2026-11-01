import time
import pandas as pd
import streamlit as st
from vacuum_agent import GoalBasedVacuumAgent, VacuumEnvironment

# Page Configuration
st.set_page_config(
    page_title="Professional AI Vacuum Simulator",
    page_icon="🤖",
    layout="wide",
)

# Custom Professional Styling with !important to force large size and center
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
        margin-top: 10px !important;
        margin-bottom: 5px !important;
    }
    .big-subtitle {
        text-align: center !important;
        font-size: 20px !important;
        font-weight: 600 !important;
        color: #D5DBDB !important;
        width: 100% !important;
        display: block !important;
        margin-bottom: 30px !important;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# Render Centered & Large Title using HTML div
st.markdown(
    '<div class="big-title">🤖 Autonomous AI Vacuum Cleaner Simulator</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="big-subtitle">Goal-Based Intelligent Agent & Optimal Path'
    " Planning System</div>",
    unsafe_allow_html=True,
)
st.markdown("---")


def render_grid_table(env):
    matrix = []
    for r in range(env.size):
        row = []
        for c in range(env.size):
            if r == env.agent_x and c == env.agent_y:
                row.append("🤖 Agent")
            elif env.grid[r][c] == 1:
                row.append("🧹 Dirt")
            else:
                row.append("⬜ Clean")
        matrix.append(row)
    return pd.DataFrame(
        matrix,
        columns=[f"Col {i+1}" for i in range(env.size)],
        index=[f"Row {i+1}" for i in range(env.size)],
    )


# Sidebar Controls
st.sidebar.header("🎛️ System Configurations")
grid_size = st.sidebar.slider("Environment Size (N x N)", 3, 10, 5)
dirt_prob = st.sidebar.slider("Initial Dirt Density", 0.1, 0.5, 0.3)
sim_speed = st.sidebar.slider("Execution Speed (sec)", 0.05, 0.5, 0.2)

# Session State Initialization
if (
    "env" not in st.session_state
    or st.session_state.env.size != grid_size
    or st.sidebar.button("🔄 Initialize New Environment")
):
    st.session_state.env = VacuumEnvironment(
        size=grid_size, dirt_probability=dirt_prob
    )
    st.session_state.agent = GoalBasedVacuumAgent(st.session_state.env)

env = st.session_state.env
agent = st.session_state.agent

# --- UI Layout: Using st.table for perfect auto-sizing ---
st.markdown("### 🏢 Live Simulation Grid")
grid_container = st.empty()
grid_container.table(render_grid_table(env))

# Run Button
run_button = st.button(
    "🚀 Run Autonomous Cleaning Agent", use_container_width=True
)

st.markdown("---")

# Metrics and State Section
col_metric, col_state = st.columns(2)

with col_metric:
    st.markdown("### 📊 Performance Metrics")
    m1 = st.metric("Total Steps Taken", agent.total_steps)
    m2 = st.metric("Cleaned Spots", agent.cleaned_count)
    status_display = st.empty()

with col_state:
    st.markdown("### ⚙️ Agent State & Info")
    state_box = st.empty()
    env_status = "Cleaned" if env.is_clean() else "Cleaning in progress..."
    state_box.info(
        f"**Agent Current Location:** Row {env.agent_x+1}, Col"
        f" {env.agent_y+1}\n\n**Environment Status:** {env_status}"
    )

# Execution Logic
if run_button:
    status_display.warning("Agent is running...")
    while not env.is_clean():
        moved = agent.step()
        if not moved:
            break

        grid_container.table(render_grid_table(env))
        m1.metric("Total Steps Taken", agent.total_steps)
        m2.metric("Cleaned Spots", agent.cleaned_count)
        state_box.info(
            f"**Agent Current Location:** Row {env.agent_x+1}, Col"
            f" {env.agent_y+1}\n\n**Environment Status:** Cleaning in"
            " progress..."
        )
        time.sleep(sim_speed)

    st.balloons()
    status_display.success("✅ Goal Achieved Successfully!")
    state_box.success(
        "**Agent Status:** Room is completely clean! Mission accomplished."
    )