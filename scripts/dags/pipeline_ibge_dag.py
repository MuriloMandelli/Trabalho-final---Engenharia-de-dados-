from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    "owner": "engenharia-dados",
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}

SCRIPTS_DIR = "/opt/airflow/scripts/py"
SPARK_SUBMIT = (
    "docker exec -e HOME=/tmp -e SPARK_JARS_IVY=/tmp/.ivy2 spark_master "
    "/opt/spark/bin/spark-submit --master spark://spark-master:7077 "
    "--conf spark.jars.ivy=/tmp/.ivy2 "
    "--packages io.delta:delta-spark_2.12:3.2.0,org.apache.hadoop:hadoop-aws:3.3.4,com.amazonaws:aws-java-sdk-bundle:1.12.262"
)

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
        bash_command=f"{SPARK_SUBMIT} /opt/spark/work-dir/scripts/py/implement_bronze.py",
    )

    implement_silver = BashOperator(
        task_id="implement_silver",
        bash_command=f"{SPARK_SUBMIT} /opt/spark/work-dir/scripts/py/implement_silver.py",
    )

    implement_gold = BashOperator(
        task_id="implement_gold",
        bash_command=f"{SPARK_SUBMIT} /opt/spark/work-dir/scripts/py/implement_gold.py",
    )

    create_buckets >> feed_landing >> implement_bronze >> implement_silver >> implement_gold
