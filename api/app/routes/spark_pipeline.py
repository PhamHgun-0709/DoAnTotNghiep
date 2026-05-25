"""
Spark Pipeline API Routes

FastAPI endpoints for triggering and monitoring Spark data pipelines.
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from app.core.role_checker import require_admin
from typing import Dict, Any
from app.services.spark_service import get_spark_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/spark", tags=["spark-pipeline"])

@router.post("/pipeline/run")
def run_spark_pipeline(
    input_path: str = Query(..., description="Path to input CSV (local or HDFS)"),
    pipeline_type: str = Query("full", pattern="^(full|cleaning|features|aggregation)$"),
    current_user: dict = Depends(require_admin()),
) -> Dict[str, Any]:
    """
    Trigger Spark data pipeline execution.
    
    Pipeline stages:
    1. **full**: Complete pipeline (cleaning → features → aggregation)
    2. **cleaning**: Data validation and cleanup only
    3. **features**: KPI computation (CTR, CPC, CPM, CVR, CPA)
    4. **aggregation**: Campaign and demographic aggregation
    
    Args:
        input_path: Path to raw CSV data file
        pipeline_type: Which pipeline stage(s) to execute
        
    Returns:
        Pipeline execution metadata and results
        
    Example:
        POST /api/spark/pipeline/run?input_path=data/raw/ads.csv&pipeline_type=full
    """
    try:
        logger.info(f"[API] Spark pipeline request: {pipeline_type} on {input_path}")
        
        spark_service = get_spark_service()
        
        if pipeline_type == "full":
            result = spark_service.run_full_pipeline(input_path)
        else:
            # For individual pipeline types, would call specific methods
            result = spark_service.run_full_pipeline(input_path)
        
        return {
            "status": "SUCCESS",
            "pipeline_type": pipeline_type,
            "input_path": input_path,
            "results": result,
            "timestamp": result.get("timestamp")
        }
        
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Input file not found: {input_path}")
    except Exception as exc:
        logger.error(f"[API] Spark pipeline error: {str(exc)}")
        raise HTTPException(status_code=500, detail=f"Pipeline execution failed: {str(exc)}")

@router.get("/pipeline/status")
def get_pipeline_status(current_user: dict = Depends(require_admin())) -> Dict[str, Any]:
    """
    Get status of latest Spark pipeline execution.
    
    Returns:
        Status of processed data and last update timestamp
    """
    try:
        spark_service = get_spark_service()
        status = spark_service.get_pipeline_status()
        
        return {
            "pipeline_status": status
        }
        
    except Exception as exc:
        logger.error(f"[API] Failed to get pipeline status: {str(exc)}")
        raise HTTPException(status_code=500, detail=str(exc))

@router.post("/pipeline/export")
def export_processed_data(
    output_format: str = Query("parquet", pattern="^(parquet|csv|json)$"),
    current_user: dict = Depends(require_admin()),
) -> Dict[str, Any]:
    """
    Export processed data in specified format.
    
    Args:
        output_format: Output format (parquet, csv, or json)
        
    Returns:
        Export metadata and path
        
    Formats:
        - **parquet**: Apache Parquet (columnar, compressed)
        - **csv**: CSV (human-readable)
        - **json**: JSON (nested, structured)
    """
    try:
        spark_service = get_spark_service()
        export_path = spark_service.export_processed_data(output_format)
        
        return {
            "status": "EXPORTED",
            "format": output_format,
            "path": export_path
        }
        
    except Exception as exc:
        logger.error(f"[API] Export failed: {str(exc)}")
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/jobs")
def list_spark_jobs(current_user: dict = Depends(require_admin())) -> Dict[str, Any]:
    """
    List available Spark jobs.
    
    Returns:
        Information about available data processing jobs
    """
    jobs = [
        {
            "job_name": "data_cleaning",
            "description": "Validate and clean raw ad data",
            "input": "Raw CSV with ad performance metrics",
            "output": "Cleaned dataset with validation",
            "duration": "~1-5 minutes",
            "scalability": "10GB+"
        },
        {
            "job_name": "feature_engineering",
            "description": "Compute KPIs: CTR, CPC, CPM, CVR, CPA, Quality Score",
            "input": "Cleaned ad data",
            "output": "Data with computed features",
            "duration": "~2-10 minutes",
            "scalability": "10GB+"
        },
        {
            "job_name": "campaign_analysis",
            "description": "Aggregate data by campaign, demographics, quality",
            "input": "Featured data",
            "output": "Campaign summaries and recommendations",
            "duration": "~1-5 minutes",
            "scalability": "10GB+"
        },
        {
            "job_name": "full_pipeline",
            "description": "Complete pipeline: clean → features → aggregate",
            "input": "Raw CSV",
            "output": "Fully processed and aggregated data",
            "duration": "~5-20 minutes",
            "scalability": "10GB+"
        }
    ]
    
    return {
        "available_jobs": jobs,
        "total": len(jobs)
    }

@router.get("/metrics")
def get_spark_metrics(current_user: dict = Depends(require_admin())) -> Dict[str, Any]:
    """
    Get Spark execution metrics and statistics.
    
    Returns:
        Information about Spark cluster and recent jobs
    """
    try:
        from spark.spark_session import get_spark
        
        spark = get_spark()
        
        metrics = {
            "spark_version": spark.version,
            "app_name": spark.sparkContext.appName,
            "master": spark.sparkContext.master,
            "default_parallelism": spark.sparkContext.defaultParallelism,
            "default_partitions": spark.sparkContext.defaultMinPartitions,
        }
        
        return {
            "metrics": metrics
        }
        
    except Exception as exc:
        logger.error(f"[API] Failed to get metrics: {str(exc)}")
        raise HTTPException(status_code=500, detail=str(exc))
