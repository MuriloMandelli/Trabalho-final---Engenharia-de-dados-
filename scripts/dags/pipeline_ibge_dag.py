from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    "owner": "engenharia-dados",
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}

SCRIPTS_DIR = "/opt/airflow/scripts/py"

with DAG(
    dag_id="pipeline_ibge_lakehouse",
    default_args=default_args,
    description="Executa buckets, landing, bronze, silver e gold do IBGE",
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["ibge", "lakehouse", "delta"],
) as dag:

    create_buckets = BashOperator(
        task_id="create_buckets",
        bash_command=f"python3 {SCRIPTS_DIR}/create_buckets.py",
    )

    feed_landing = BashOperator(
        task_id="feed_landing",
        bash_command=f"python3 {SCRIPTS_DIR}/feed_landing.py",
    )

    implement_bronze = BashOperator(
        task_id="implement_bronze",
        bash_command=f"python3 {SCRIPTS_DIR}/implement_bronze.py",
    )

    implement_silver = BashOperator(
        task_id="implement_silver",
        bash_command=f"python3 {SCRIPTS_DIR}/implement_silver.py",
    )

    implement_gold = BashOperator(
        task_id="implement_gold",
        bash_command=f"python3 {SCRIPTS_DIR}/implement_gold.py",
    )

    create_buckets >> feed_landing >> implement_bronze >> implement_silver >> implement_gold
