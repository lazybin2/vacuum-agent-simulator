import time
import pandas as pd
import streamlit as st
from vacuum_agent import AdvancedVacuumAgent, VacuumEnvironment

# Page Configuration
st.set_page_config(
    page_title="Professional AI Vacuum Simulator",
    page_icon="🤖",
    layout="wide",
)

# Custom Glassmorphism UI Styling
st.markdown(
    """
    <style>
    .big-title {
        text-align: center !important;
        font-size: 42px !important;
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
    '<div class="big-title">🤖 Autonomous AI Vacuum Cleaner Simulator</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="big-subtitle">Goal-Based Vacuum Agent & PEAS Architecture'
    " Environment</div>",
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
      elif env.grid[r][c] == 2:
        row.append("🧱 Wall")
      elif env.grid[r][c] == 1:
        row.append("🧹 Dirt")
      elif (r, c) in env.visited_trail:
        row.append("✨ Done")
      else:
        row.append("⬜ Clean")
    matrix.append(row)

  df = pd.DataFrame(
      matrix,
      columns=[f"Col {i+1}" for i in range(env.size)],
      index=[f"Row {i+1}" for i in range(env.size)],
  )

  def color_cells(val):
    if "Agent" in val:
      return "background-color: #a0c4ff; color: black; font-weight: bold; text-align: center;"
    elif "Wall" in val:
      return "background-color: #343a40; color: white; font-weight: bold; text-align: center;"
    elif "Dirt" in val:
      return "background-color: #ffadad; color: black; font-weight: bold; text-align: center;"
    elif "Trail" in val:
      return "background-color: #e4c1f9; color: black; text-align: center;"
    else:
      return "background-color: #caffbf; color: black; text-align: center;"

  return df.style.map(color_cells)


# Sidebar Controls
st.sidebar.header("🎛️ System Configurations")
selected_algo = st.sidebar.selectbox(
    "Select Search Algorithm", ["A* Search", "BFS", "Dijkstra"]
)
grid_size = st.sidebar.slider("Environment Size (N x N)", 3, 10, 5)
dirt_prob = st.sidebar.slider("Initial Dirt Density", 0.1, 0.4, 0.2)
wall_prob = st.sidebar.slider("Wall Density", 0.0, 0.3, 0.15)
sim_speed = st.sidebar.slider("Execution Speed (sec)", 0.05, 0.5, 0.2)

# Session State Initialization
if (
    "env" not in st.session_state
    or st.session_state.env.size != grid_size
    or st.sidebar.button("🔄 Initialize New Environment")
):
  st.session_state.env = VacuumEnvironment(
      size=grid_size, dirt_probability=dirt_prob, wall_probability=wall_prob
  )
  st.session_state.agent = AdvancedVacuumAgent(
      st.session_state.env, algorithm=selected_algo
  )

env = st.session_state.env
agent = st.session_state.agent
agent.algorithm = selected_algo  # Update algorithm on change

# UI Layout 
col_grid, col_analytics = st.columns([1.2, 1])

with col_grid:
  st.markdown("### 🏢 Live Simulation Grid")
  grid_container = st.empty()
  grid_container.dataframe(render_grid_table(env), use_container_width=True)

with col_analytics:
  st.markdown("### 📈 Real-time Analytics Chart")
  chart_container = st.empty()
  if agent.history_steps:
    chart_df = pd.DataFrame(agent.history_steps).set_index("Step")
    chart_container.line_chart(chart_df)
  else:
    chart_container.info(
        "Chart will update live once the simulation starts running."
    )

run_button = st.button(
    "🚀 Run Autonomous Cleaning Agent", use_container_width=True
)

st.markdown("---")

# Performance KPI Metrics & State Section
col_m1, col_m2, col_m3, col_m4 = st.columns(4)

initial_dirt = env.initial_dirt_count if env.initial_dirt_count > 0 else 1
cleaned_pct = int((agent.cleaned_count / initial_dirt) * 100)

with col_m1:
  m1 = st.metric("Total Steps", agent.total_steps)
with col_m2:
  m2 = st.metric("Cleaned Spots", agent.cleaned_count)
with col_m3:
  m3 = st.metric("Efficiency (%)", f"{cleaned_pct}%")
with col_m4:
  m4 = st.metric("Algorithm", selected_algo)

status_display = st.empty()

# Execution Logic
if run_button:
  status_display.warning(f"Agent running using {selected_algo} algorithm...")
  while not env.is_clean():
    moved = agent.step()
    if not moved:
      break

    grid_container.dataframe(render_grid_table(env), use_container_width=True)
    if agent.history_steps:
      chart_df = pd.DataFrame(agent.history_steps).set_index("Step")
      chart_container.line_chart(chart_df)

    cleaned_pct = int((agent.cleaned_count / initial_dirt) * 100)
    m1.metric("Total Steps", agent.total_steps)
    m2.metric("Cleaned Spots", agent.cleaned_count)
    m3.metric("Efficiency (%)", f"{cleaned_pct}%")

    time.sleep(sim_speed)

  st.balloons()
  status_display.success("✅ Goal Achieved Successfully!")