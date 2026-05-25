"""
Spark Service Layer

Bridges FastAPI with Spark job orchestration.
Provides high-level service methods for running data pipelines.
"""

import os
import subprocess
from typing import Dict, Any, Optional
from pathlib import Path
import asyncio
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class SparkService:
    """
    Service for managing Spark pipeline execution.
    
    Can run Spark jobs either:
    1. In-process (for development)
    2. Via spark-submit (for production)
    """
    
    def __init__(self, use_spark_submit: bool = False):
        """
        Initialize Spark service.
        
        Args:
            use_spark_submit: If True, use spark-submit; if False, use in-process
        """
        self.use_spark_submit = use_spark_submit
        self.output_dir = "data/processed"
        self.metadata_dir = "data/metadata"
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Create necessary directories."""
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        Path(self.metadata_dir).mkdir(parents=True, exist_ok=True)
    
    def run_full_pipeline(self, input_path: str) -> Dict[str, Any]:
        """
        Run complete data pipeline.
        
        Args:
            input_path: Path to raw CSV data
            
        Returns:
            Pipeline results metadata
        """
        logger.info(f"[SPARK_SERVICE] Starting full pipeline on {input_path}")
        
        if self.use_spark_submit:
            return self._run_with_spark_submit("full_pipeline", input_path)
        else:
            return self._run_in_process(input_path)
    
    def _run_in_process(self, input_path: str) -> Dict[str, Any]:
        """
        Run Spark pipeline in-process (development mode).
        
        Args:
            input_path: Input data path
            
        Returns:
            Pipeline execution results
        """
        try:
            from spark.orchestrator import SparkJobOrchestrator
            
            orchestrator = SparkJobOrchestrator()
            result = orchestrator.run_full_pipeline(input_path)
            
            logger.info("[SPARK_SERVICE] Pipeline completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"[SPARK_SERVICE] Pipeline failed: {str(e)}")
            raise
    
    def _run_with_spark_submit(self, job_type: str, input_path: str) -> Dict[str, Any]:
        """
        Run Spark job via spark-submit.
        
        Args:
            job_type: Type of job to run
            input_path: Input data path
            
        Returns:
            Job execution results
        """
        # Create Python script that will be submitted
        spark_script = self._create_spark_script(job_type, input_path)
        
        spark_home = os.getenv("SPARK_HOME", "/opt/spark")
        spark_submit = os.path.join(spark_home, "bin", "spark-submit")
        
        cmd = [
            spark_submit,
            "--master", os.getenv("SPARK_MASTER", "local[*]"),
            "--driver-memory", "4g",
            "--executor-memory", "4g",
            spark_script,
            input_path
        ]
        
        logger.info(f"[SPARK_SERVICE] Running: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
            
            if result.returncode == 0:
                logger.info("[SPARK_SERVICE] spark-submit job completed")
                return self._parse_spark_output(result.stdout)
            else:
                logger.error(f"[SPARK_SERVICE] spark-submit failed: {result.stderr}")
                raise RuntimeError(f"Spark job failed: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            logger.error("[SPARK_SERVICE] Spark job timeout")
            raise RuntimeError("Spark job timed out (1 hour limit)")
    
    def _create_spark_script(self, job_type: str, input_path: str) -> str:
        """Create temporary Spark script for spark-submit."""
        script_content = f"""
from spark.orchestrator import SparkJobOrchestrator
import json

orchestrator = SparkJobOrchestrator()
result = orchestrator.run_full_pipeline('{input_path}')
print(json.dumps(result, indent=2, default=str))
"""
        script_path = "/tmp/spark_job_temp.py"
        with open(script_path, 'w') as f:
            f.write(script_content)
        return script_path
    
    def _parse_spark_output(self, output: str) -> Dict[str, Any]:
        """Parse spark-submit output to extract results."""
        # Extract JSON from output
        lines = output.split('\n')
        for line in reversed(lines):
            if line.strip().startswith('{'):
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    continue
        
        # Fallback
        return {
            "status": "COMPLETED",
            "output_sample": output[-500:] if output else ""
        }
    
    async def run_pipeline_async(self, input_path: str) -> Dict[str, Any]:
        """
        Run pipeline asynchronously (for long-running jobs).
        
        Args:
            input_path: Input data path
            
        Returns:
            Pipeline results
        """
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, 
            self.run_full_pipeline, 
            input_path
        )
        return result
    
    def get_pipeline_status(self) -> Dict[str, Any]:
        """
        Get status of processed data.
        
        Returns:
            Status of latest pipeline run
        """
        metadata_files = list(Path(self.metadata_dir).glob("*.json"))
        
        if not metadata_files:
            return {"status": "NO_DATA"}
        
        # Get latest metadata
        latest_file = max(metadata_files, key=os.path.getctime)
        
        with open(latest_file, 'r') as f:
            latest_metadata = json.load(f)
        
        return {
            "status": "READY",
            "last_update": latest_file.stat().st_mtime,
            "metadata": latest_metadata
        }
    
    def export_processed_data(self, output_format: str = "parquet") -> str:
        """
        Export processed data in specified format.
        
        Args:
            output_format: "parquet", "csv", or "json"
            
        Returns:
            Path to exported data
        """
        from spark.spark_session import get_spark
        
        spark = get_spark()
        
        processed_path = f"{self.output_dir}/features_engineered"
        df = spark.read.csv(processed_path, header=True, inferSchema=True)
        
        export_path = f"{self.output_dir}/export_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        if output_format == "parquet":
            df.write.mode("overwrite").parquet(export_path)
        elif output_format == "csv":
            df.coalesce(1).write.mode("overwrite").csv(export_path, header=True)
        elif output_format == "json":
            df.write.mode("overwrite").json(export_path)
        else:
            raise ValueError(f"Unsupported format: {output_format}")
        
        logger.info(f"[SPARK_SERVICE] Exported to {export_path}")
        return export_path


# Global service instance
_spark_service: Optional[SparkService] = None


def get_spark_service() -> SparkService:
    """Dependency injection for Spark service."""
    global _spark_service
    if _spark_service is None:
        _spark_service = SparkService(use_spark_submit=False)
    return _spark_service
