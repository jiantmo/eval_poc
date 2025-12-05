import streamlit as st
import json
import pandas as pd
import time
import uuid
import os
from datetime import datetime

from dataset.model import load_dataset, EvalRecord
from environment.config import AuroraEnvConfig
from evaluation.config import EvaluationSuiteConfig, EvaluatorConfig
from evaluation.engine import EvaluationEngine
from runner import EvalRunner
from runs.store import DataStore, RunRecord, DatasetRecord, EnvironmentRecord, EvaluatorRecord, TestSuiteRecord

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
        ["Dashboard", "Runs", "Test Suites", "Datasets", "Environments", "Evaluators"],
        index=1
    )
    st.divider()
    st.caption("v0.1.0 POC")

# --- Helper Functions ---
def run_evaluation_logic(run_id, run_name, dataset_record, env_record, selected_evaluators):
    """
    Executes the evaluation and updates the run record.
    """
    # 1. Create Initial Record
    # Find evaluator IDs
    all_evals = store.list_evaluators()
    selected_ids = [e.id for e in all_evals if e.name in selected_evaluators]

    new_run = RunRecord(
        id=run_id,
        name=run_name,
        environment=env_record.name,
        agent=env_record.agent_name,
        dataset=dataset_record.name,
        status="Running",
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        dataset_id=dataset_record.id,
        environment_id=env_record.id,
        evaluator_ids=selected_ids
    )
    store.save_run(new_run)
    
    start_time = time.time()
    
    try:
        # 2. Load Data & Config
        # records = load_dataset(dataset_record.file_path)
        records = [EvalRecord.from_dict(r) for r in dataset_record.content]
        
        env_config = AuroraEnvConfig(
            env_id=env_record.env_id,
            env_version=env_record.env_version,
            agent_name=env_record.agent_name,
            api_endpoint=env_record.api_endpoint
        )
        
        # 3. Setup Runner & Engine
        runner = EvalRunner(env_config)
        
        # Load available evaluators from store
        # all_evals = store.list_evaluators()
        
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
            parsed_content = json.loads(file_content)
            
            # Save to file (Optional, maybe skip or keep for backup)
            # filename = f"dataset/{name.lower().replace(' ', '_')}_{int(time.time())}.json"
            # os.makedirs("dataset", exist_ok=True)
            # with open(filename, "w", encoding="utf-8") as f:
            #     f.write(file_content)
                
            store.save_dataset(DatasetRecord(
                id=str(uuid.uuid4()),
                name=name,
                description=desc,
                file_path=None,
                content=parsed_content,
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

@st.dialog("New Test Suite")
def new_test_suite_dialog():
    st.write("Create a reusable Test Suite configuration.")
    
    name = st.text_input("Suite Name", placeholder="e.g. Regression Suite v1")
    description = st.text_area("Description", placeholder="Purpose of this suite...")
    
    # Load options
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

    st.divider()
    st.subheader("Select Evaluators")
    
    # Group by category
    evaluators_by_category = {}
    for e in evaluators:
        if e.category not in evaluators_by_category:
            evaluators_by_category[e.category] = []
        evaluators_by_category[e.category].append(e.name)

    # Step 1: Select Categories
    all_categories = list(evaluators_by_category.keys())
    selected_categories = st.multiselect(
        "1. Select Evaluator Categories", 
        all_categories, 
        default=all_categories
    )

    # Step 2: Select Metrics for each category
    selected_evals = []
    if selected_categories:
        st.write("2. Select Metrics")
        for cat in selected_categories:
            names = evaluators_by_category[cat]
            sel = st.multiselect(
                f"{cat} Metrics", 
                names, 
                default=names, 
                key=f"ts_dlg_{cat}"
            )
            selected_evals.extend(sel)

    if st.button("Save Test Suite", type="primary"):
        if not name or not selected_ds_name or not selected_env_name:
            st.error("Please complete all fields.")
            return
        
        if not selected_evals:
            st.error("Please select at least one evaluator.")
            return
            
        # Find evaluator IDs
        selected_ids = [e.id for e in evaluators if e.name in selected_evals]

        store.save_test_suite(TestSuiteRecord(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            dataset_id=ds_map[selected_ds_name].id,
            environment_id=env_map[selected_env_name].id,
            evaluator_ids=selected_ids,
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        st.rerun()

@st.dialog("New Evaluation Run")
def new_run_dialog():
    st.write("Select Test Suites to run.")
    
    run_name_base = st.text_input("Run Name Prefix", value=f"Eval Run {datetime.now().strftime('%Y%m%d-%H%M')}")
    
    test_suites = store.list_test_suites()
    
    if not test_suites:
        st.warning("No Test Suites found. Please create one first.")
        return

    # Allow multiple selection
    ts_map = {ts.name: ts for ts in test_suites}
    selected_suites = st.multiselect("Select Test Suites", list(ts_map.keys()))
    
    if selected_suites:
        st.divider()
        st.caption("Preview Selected Suites")
        
        # Pre-fetch data for preview
        all_datasets = {d.id: d.name for d in store.list_datasets()}
        all_envs = {e.id: e.name for e in store.list_environments()}
        all_evals = {e.id: e.name for e in store.list_evaluators()}
        
        for suite_name in selected_suites:
            suite = ts_map[suite_name]
            ds_name = all_datasets.get(suite.dataset_id, "Unknown")
            env_name = all_envs.get(suite.environment_id, "Unknown")
            eval_names = [all_evals.get(eid, "Unknown") for eid in suite.evaluator_ids]
            
            with st.expander(f"📄 {suite_name}", expanded=False):
                st.markdown(f"**Dataset:** {ds_name}")
                st.markdown(f"**Environment:** {env_name}")
                st.markdown(f"**Evaluators ({len(eval_names)}):** {', '.join(eval_names)}")

    if st.button("Start Evaluation", type="primary"):
        if not selected_suites:
            st.error("Please select at least one Test Suite.")
            return
            
        # Load all necessary data once
        all_datasets = {d.id: d for d in store.list_datasets()}
        all_envs = {e.id: e for e in store.list_environments()}
        all_evals = {e.id: e for e in store.list_evaluators()}
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, suite_name in enumerate(selected_suites):
            suite = ts_map[suite_name]
            status_text.text(f"Running suite: {suite_name}...")
            
            # Resolve references
            dataset = all_datasets.get(suite.dataset_id)
            env = all_envs.get(suite.environment_id)
            
            # Resolve evaluator names for the logic function
            suite_eval_names = []
            for eid in suite.evaluator_ids:
                if eid in all_evals:
                    suite_eval_names.append(all_evals[eid].name)
            
            if dataset and env:
                run_id = str(uuid.uuid4())
                run_name = f"{run_name_base} - {suite_name}"
                
                run_evaluation_logic(
                    run_id, 
                    run_name, 
                    dataset, 
                    env, 
                    suite_eval_names
                )
            else:
                st.error(f"Skipping suite '{suite_name}': Missing dataset or environment.")
            
            progress_bar.progress((i + 1) / len(selected_suites))
            
        status_text.text("All runs completed!")
        time.sleep(1)
        st.rerun()

# --- Page Views ---

def render_dashboard_view():
    st.markdown('<div class="main-header">Dashboard</div>', unsafe_allow_html=True)
    
    runs = store.list_runs()
    if not runs:
        st.info("No runs available for analysis.")
        return

    # Prepare Data
    df = pd.DataFrame([r.to_dict() for r in runs])
    df['created_at'] = pd.to_datetime(df['created_at'])
    df = df.sort_values('created_at')

    # Top Level Metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Runs", len(df))
    col2.metric("Avg Pass Rate", f"{df['pass_rate'].mean():.1f}%")
    col3.metric("Total Tests", df['total_records'].sum())
    col4.metric("Latest Pass Rate", f"{df.iloc[-1]['pass_rate']}%")

    st.divider()

    # Charts
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("Pass Rate Trend")
        st.line_chart(df.set_index('created_at')['pass_rate'])
    
    with c2:
        st.subheader("Run Status Distribution")
        status_counts = df['status'].value_counts()
        st.bar_chart(status_counts)

    st.subheader("Recent Runs")
    st.dataframe(
        df[['name', 'environment', 'pass_rate', 'created_at']].sort_values('created_at', ascending=False).head(5),
        use_container_width=True,
        hide_index=True
    )

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

    # Summary Table
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

    # Run Report Section
    st.divider()
    st.subheader("Run Report")
    
    run_options = {f"{r.name} ({r.created_at})": r for r in runs}
    selected_run_key = st.selectbox("Select a run to view details:", list(run_options.keys()), index=0)
    
    if selected_run_key:
        run = run_options[selected_run_key]
        
        # Run Metadata
        with st.expander("Run Configuration", expanded=False):
            c1, c2, c3 = st.columns(3)
            c1.write(f"**ID:** {run.id}")
            c1.write(f"**Environment:** {run.environment}")
            c2.write(f"**Agent:** {run.agent}")
            c2.write(f"**Dataset:** {run.dataset}")
            c3.write(f"**Created:** {run.created_at}")
            c3.write(f"**Duration:** {run.duration}")

        # Results Analysis
        if run.results:
            results_df = pd.DataFrame(run.results)
            
            # Metrics Summary
            st.write("#### Metrics Summary")
            
            # Flatten metrics for aggregation
            all_metrics = []
            for res in run.results:
                if "metrics" in res:
                    all_metrics.append(res["metrics"])
            
            if all_metrics:
                metrics_df = pd.DataFrame(all_metrics)
                st.dataframe(metrics_df.describe(), use_container_width=True)

            # Detailed Results
            st.write("#### Detailed Results")
            
            filter_failed = st.checkbox("Show Failed Only", value=False)
            
            display_df = results_df.copy()
            if filter_failed:
                display_df = display_df[display_df['passed'] == False]
            
            # Format for display
            st.dataframe(
                display_df, 
                column_config={
                    "passed": st.column_config.CheckboxColumn(
                        "Passed",
                        help="Did the test pass?",
                        default=False,
                    ),
                    "metrics": st.column_config.Column(
                        "Metrics Scores",
                        width="medium"
                    )
                },
                use_container_width=True,
                hide_index=True
            )
            
            # Detail Inspector
            st.write("#### Inspect Record")
            selected_idx = st.number_input("Row Index to Inspect", min_value=0, max_value=len(display_df)-1 if not display_df.empty else 0, step=1)
            
            if not display_df.empty:
                record = display_df.iloc[selected_idx]
                c1, c2 = st.columns(2)
                with c1:
                    st.write("**Input:**")
                    st.json(record['input'])
                    st.write("**Expected:**")
                    st.json(record['expected'])
                with c2:
                    st.write("**Actual Output:**")
                    st.info(record['actual'])
                    st.write("**Metrics:**")
                    st.json(record['metrics'])
        else:
            st.info("No detailed results available for this run.")

def render_test_suites_view():
    col_title, col_action = st.columns([6, 1])
    with col_title:
        st.markdown('<div class="main-header">Test Suites</div>', unsafe_allow_html=True)
    with col_action:
        if st.button("➕ New Suite", type="primary"):
            new_test_suite_dialog()

    suites = store.list_test_suites()
    if not suites:
        st.info("No test suites found.")
        return

    # Resolve names for display
    datasets = {d.id: d.name for d in store.list_datasets()}
    envs = {e.id: e.name for e in store.list_environments()}
    
    data = []
    for s in suites:
        data.append({
            "Name": s.name,
            "Description": s.description,
            "Dataset": datasets.get(s.dataset_id, "Unknown"),
            "Environment": envs.get(s.environment_id, "Unknown"),
            "Evaluators Count": len(s.evaluator_ids),
            "Created": s.created_at
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

    data = [{"Name": d.name, "Description": d.description, "Created": d.created_at} for d in datasets]
    st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Edit Dataset")
    
    dataset_names = [d.name for d in datasets]
    selected_dataset_name = st.selectbox("Select a dataset to edit:", dataset_names, index=None)
    
    if selected_dataset_name:
        selected_dataset = next((d for d in datasets if d.name == selected_dataset_name), None)
        
        if selected_dataset:
            # Convert content to formatted JSON string for editing
            current_content = json.dumps(selected_dataset.content, indent=2) if selected_dataset.content else "[]"
            
            new_content_str = st.text_area(
                f"JSON Content for '{selected_dataset.name}'", 
                value=current_content,
                height=400
            )
            
            if st.button("Save Changes", type="primary"):
                try:
                    updated_content = json.loads(new_content_str)
                    if not isinstance(updated_content, list):
                        st.error("Dataset must be a JSON list of records.")
                    else:
                        selected_dataset.content = updated_content
                        store.save_dataset(selected_dataset)
                        st.success(f"Dataset '{selected_dataset.name}' updated successfully!")
                        time.sleep(1)
                        st.rerun()
                except json.JSONDecodeError as e:
                    st.error(f"Invalid JSON: {e}")

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

if selected_page == "Dashboard":
    render_dashboard_view()
elif selected_page == "Runs":
    render_runs_view()
elif selected_page == "Test Suites":
    render_test_suites_view()
elif selected_page == "Datasets":
    render_datasets_view()
elif selected_page == "Environments":
    render_environments_view()
elif selected_page == "Evaluators":
    render_evaluators_view()
