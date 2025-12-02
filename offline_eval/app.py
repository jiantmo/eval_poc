import streamlit as st
import json
import pandas as pd
import time
import uuid
import os
from datetime import datetime

from dataset.model import load_dataset
from environment.config import AuroraEnvConfig
from evaluation.config import EvaluationSuiteConfig, EvaluatorConfig
from evaluation.engine import EvaluationEngine
from runner import EvalRunner
from runs.store import DataStore, RunRecord, DatasetRecord, EnvironmentRecord, EvaluatorRecord

# --- Page Configuration ---
st.set_page_config(
    page_title="MOS Eval POC",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS ---
st.markdown("""
<style>
    .main-header {
        font-size: 1.8rem;
        font-weight: 600;
        color: #333;
        margin-bottom: 1rem;
    }
    .stButton>button {
        border-radius: 4px;
    }
    .status-badge {
        padding: 4px 8px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 500;
    }
</style>
""", unsafe_allow_html=True)

# --- State Management ---
if 'store' not in st.session_state:
    st.session_state.store = DataStore()

store = st.session_state.store

# --- Sidebar Navigation ---
with st.sidebar:
    st.title("AI Eval Center")
    selected_page = st.radio(
        "Navigation", 
        ["Runs", "Datasets", "Environments", "Evaluators"],
        index=0
    )
    st.divider()
    st.caption("v0.1.0 POC")

# --- Helper Functions ---
def run_evaluation_logic(run_id, run_name, dataset_record, env_record, selected_evaluators):
    """
    Executes the evaluation and updates the run record.
    """
    # 1. Create Initial Record
    new_run = RunRecord(
        id=run_id,
        name=run_name,
        environment=env_record.name,
        agent=env_record.agent_name,
        dataset=dataset_record.name,
        status="Running",
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    store.save_run(new_run)
    
    start_time = time.time()
    
    try:
        # 2. Load Data & Config
        records = load_dataset(dataset_record.file_path)
        
        env_config = AuroraEnvConfig(
            env_id=env_record.env_id,
            env_version=env_record.env_version,
            agent_name=env_record.agent_name,
            api_endpoint=env_record.api_endpoint
        )
        
        # 3. Setup Runner & Engine
        runner = EvalRunner(env_config)
        
        # Load available evaluators from store
        all_evals = store.list_evaluators()
        
        active_eval_configs = []
        for e_rec in all_evals:
            if e_rec.name in selected_evaluators:
                active_eval_configs.append(EvaluatorConfig(
                    name=e_rec.name,
                    category=e_rec.category,
                    type=e_rec.type,
                    target=e_rec.target,
                    pass_threshold=e_rec.pass_threshold,
                    parameters=e_rec.parameters
                ))
                
        suite_config = EvaluationSuiteConfig(suite_name=run_name, evaluators=active_eval_configs)
        engine = EvaluationEngine(suite_config)

        # 4. Execute
        time.sleep(1) 
        execution_results = runner.run_dataset(records)
        eval_results = engine.evaluate_run(execution_results)

        # 5. Calculate Stats
        duration = time.time() - start_time
        total = len(eval_results)
        passed = sum(1 for r in eval_results if r.passed)
        pass_rate = (passed / total * 100) if total > 0 else 0

        # 6. Update Record
        new_run.status = "Succeeded"
        new_run.duration = f"{duration:.1f}s"
        new_run.pass_rate = round(pass_rate, 1)
        new_run.total_records = total
        
        # Serialize results
        serialized_results = []
        for res in eval_results:
            row = {
                "input": str(res.execution_result.record.input),
                "expected": str(res.execution_result.record.expected),
                "actual": str(res.execution_result.actual_output),
                "passed": res.passed,
                "metrics": {k: v.get("score") for k, v in res.metrics.items()}
            }
            serialized_results.append(row)
        new_run.results = serialized_results
        
        store.save_run(new_run)
        st.toast(f"Run '{run_name}' completed successfully!", icon="✅")
        
    except Exception as e:
        new_run.status = "Failed"
        new_run.duration = f"{time.time() - start_time:.1f}s"
        store.save_run(new_run)
        st.error(f"Run failed: {e}")

# --- Dialogs ---

@st.dialog("New Dataset")
def new_dataset_dialog():
    st.write("Upload or create a new test dataset.")
    name = st.text_input("Dataset Name")
    desc = st.text_area("Description")
    
    tab1, tab2 = st.tabs(["Upload File", "Manual Entry"])
    
    file_content = None
    
    with tab1:
        uploaded_file = st.file_uploader("Choose a JSON file", type="json")
        if uploaded_file is not None:
            file_content = uploaded_file.getvalue().decode("utf-8")
            
    with tab2:
        manual_json = st.text_area("Paste JSON Content", height=200, placeholder='[{"input": {"question": "..."}}]')
        if manual_json:
            file_content = manual_json

    if st.button("Save Dataset", type="primary"):
        if not name or not file_content:
            st.error("Name and Content are required.")
            return
        
        try:
            # Validate JSON
            json.loads(file_content)
            
            # Save to file
            filename = f"dataset/{name.lower().replace(' ', '_')}_{int(time.time())}.json"
            os.makedirs("dataset", exist_ok=True)
            with open(filename, "w", encoding="utf-8") as f:
                f.write(file_content)
                
            store.save_dataset(DatasetRecord(
                id=str(uuid.uuid4()),
                name=name,
                description=desc,
                file_path=filename,
                created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
            st.rerun()
        except json.JSONDecodeError:
            st.error("Invalid JSON content.")

@st.dialog("New Environment")
def new_env_dialog():
    st.write("Configure a new AI Application Environment.")
    name = st.text_input("Environment Name", placeholder="e.g. Dev Staging 01")
    
    col1, col2 = st.columns(2)
    with col1:
        env_id = st.text_input("Aurora Env ID")
        agent_name = st.text_input("Agent Name")
    with col2:
        env_version = st.text_input("Env Version")
        api_endpoint = st.text_input("API Endpoint", value="http://mock-endpoint")
        
    if st.button("Save Environment", type="primary"):
        if not name or not env_id or not agent_name:
            st.error("Name, Env ID and Agent Name are required.")
            return
            
        store.save_environment(EnvironmentRecord(
            id=str(uuid.uuid4()),
            name=name,
            env_id=env_id,
            env_version=env_version,
            agent_name=agent_name,
            api_endpoint=api_endpoint,
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        st.rerun()

@st.dialog("New Evaluator")
def new_evaluator_dialog():
    st.write("Register a new custom evaluator.")
    name = st.text_input("Evaluator Name")
    category = st.selectbox("Category", ["Automated - Rule-based", "Automated - Semantic", "LLM-as-a-judge", "Human evaluation"])
    
    col1, col2 = st.columns(2)
    with col1:
        eval_type = st.selectbox("Type", ["custom-service", "local-function", "azure-builtin"])
        target = st.text_input("Target (Endpoint/Func Name)", placeholder="http://localhost:8000/eval")
    with col2:
        pass_threshold = st.number_input("Pass Threshold", min_value=0.0, value=0.5)
    
    if st.button("Save Evaluator", type="primary"):
        if not name or not target:
            st.error("Name and Target are required.")
            return
            
        store.save_evaluator(EvaluatorRecord(
            id=str(uuid.uuid4()),
            name=name,
            category=category,
            type=eval_type,
            target=target,
            pass_threshold=pass_threshold,
            parameters={},
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        st.rerun()

@st.dialog("New Evaluation Run")
def new_run_dialog():
    st.write("Configure your evaluation run parameters.")
    
    with st.form("new_run_form"):
        run_name = st.text_input("Run Name", value=f"Eval Run {datetime.now().strftime('%Y%m%d-%H%M')}")
        
        # Load options from store
        datasets = store.list_datasets()
        envs = store.list_environments()
        evaluators = store.list_evaluators()
        
        col1, col2 = st.columns(2)
        with col1:
            ds_map = {d.name: d for d in datasets}
            selected_ds_name = st.selectbox("Dataset", list(ds_map.keys()) if ds_map else [])
            
        with col2:
            env_map = {e.name: e for e in envs}
            selected_env_name = st.selectbox("Environment", list(env_map.keys()) if env_map else [])

        st.subheader("Select Evaluators")
        
        # Group by category
        evaluators_by_category = {}
        for e in evaluators:
            if e.category not in evaluators_by_category:
                evaluators_by_category[e.category] = []
            evaluators_by_category[e.category].append(e.name)

        selected_evals = []
        for cat, names in evaluators_by_category.items():
            with st.expander(cat, expanded=False):
                sel = st.multiselect(f"Metrics", names, default=names, key=f"dlg_{cat}")
                selected_evals.extend(sel)

        submitted = st.form_submit_button("Start Evaluation", type="primary")
        
        if submitted:
            if not run_name or not selected_ds_name or not selected_env_name:
                st.error("Please complete all fields.")
                return
            
            run_id = str(uuid.uuid4())
            run_evaluation_logic(
                run_id, 
                run_name, 
                ds_map[selected_ds_name], 
                env_map[selected_env_name], 
                selected_evals
            )
            st.rerun()

# --- Page Views ---

def render_runs_view():
    col_title, col_action = st.columns([6, 1])
    with col_title:
        st.markdown('<div class="main-header">Runs</div>', unsafe_allow_html=True)
    with col_action:
        if st.button("➕ New Run", type="primary"):
            new_run_dialog()

    runs = store.list_runs()
    if not runs:
        st.info("No runs found.")
        return

    data = []
    for r in runs:
        status_icon = "⚪"
        if r.status == "Succeeded": status_icon = "🟢"
        elif r.status == "Failed": status_icon = "🔴"
        elif r.status == "Running": status_icon = "🔵"
        
        data.append({
            "Status": status_icon,
            "Name": r.name,
            "Environment": r.environment,
            "Agent": r.agent,
            "Dataset": r.dataset,
            "Pass Rate": f"{r.pass_rate}%",
            "Tests": r.total_records,
            "Duration": r.duration,
            "Created": r.created_at,
        })
    
    st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

def render_datasets_view():
    col_title, col_action = st.columns([6, 1])
    with col_title:
        st.markdown('<div class="main-header">Datasets</div>', unsafe_allow_html=True)
    with col_action:
        if st.button("➕ New Dataset", type="primary"):
            new_dataset_dialog()

    datasets = store.list_datasets()
    if not datasets:
        st.info("No datasets found.")
        return

    data = [{"Name": d.name, "Description": d.description, "File Path": d.file_path, "Created": d.created_at} for d in datasets]
    st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

def render_environments_view():
    col_title, col_action = st.columns([6, 1])
    with col_title:
        st.markdown('<div class="main-header">Environments</div>', unsafe_allow_html=True)
    with col_action:
        if st.button("➕ New Environment", type="primary"):
            new_env_dialog()

    envs = store.list_environments()
    if not envs:
        st.info("No environments found.")
        return

    data = [{"Name": e.name, "Env ID": e.env_id, "Version": e.env_version, "Agent": e.agent_name, "Endpoint": e.api_endpoint} for e in envs]
    st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

def render_evaluators_view():
    col_title, col_action = st.columns([6, 1])
    with col_title:
        st.markdown('<div class="main-header">Evaluators</div>', unsafe_allow_html=True)
    with col_action:
        if st.button("➕ New Evaluator", type="primary"):
            new_evaluator_dialog()

    evals = store.list_evaluators()
    if not evals:
        st.info("No evaluators found.")
        return

    data = [{"Name": e.name, "Category": e.category, "Type": e.type, "Target": e.target, "Threshold": e.pass_threshold} for e in evals]
    st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

# --- Main Routing ---

if selected_page == "Runs":
    render_runs_view()
elif selected_page == "Datasets":
    render_datasets_view()
elif selected_page == "Environments":
    render_environments_view()
elif selected_page == "Evaluators":
    render_evaluators_view()
