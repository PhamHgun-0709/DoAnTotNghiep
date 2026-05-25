"""
Spark Job Orchestrator

Manages execution of Spark jobs, data pipeline orchestration,
and output coordination with ML and API layers.
"""

import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from pyspark.sql import functions as F
from pyspark.sql import SparkSession, DataFrame
from spark.spark_session import get_spark
import json

logger = logging.getLogger(__name__)


def _canonicalize_columns(df: DataFrame) -> DataFrame:
    if "ad_id" not in df.columns:
        df = df.withColumn("ad_id", F.monotonically_increasing_id() + F.lit(1))
    if "campaign_id" not in df.columns:
        df = df.withColumn("campaign_id", F.lit(""))
    if "date" not in df.columns:
        df = df.withColumn("date", F.lit(""))
    if "platform" not in df.columns:
        df = df.withColumn("platform", F.lit("unknown"))
    if "spend" not in df.columns:
        df = df.withColumn("spend", F.lit(0.0))
    if "conversions" not in df.columns:
        df = df.withColumn("conversions", F.lit(0.0))
    if "age_group" not in df.columns:
        df = df.withColumn("age_group", F.lit("unknown"))
    if "impressions" not in df.columns:
        df = df.withColumn("impressions", F.lit(0.0))
    if "clicks" not in df.columns:
        df = df.withColumn("clicks", F.lit(0.0))
    if "revenue" not in df.columns:
        df = df.withColumn("revenue", F.lit(0.0))
    return df


class SparkJobOrchestrator:
    """
    Orchestrates Spark job execution and data pipeline coordination.
    
    Responsibilities:
    - Execute Spark transformations on HDFS/local data
    - Manage data output to processed directory
    - Track job execution metadata
    - Coordinate with ML and API layers
    """
    
    def __init__(self, jobs_dir: str = "spark/jobs"):
        self.spark = get_spark()
        self.jobs_dir = jobs_dir
        self.output_dir = "data/processed"
        self.metadata_dir = "data/metadata"
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Create necessary output directories."""
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        Path(self.metadata_dir).mkdir(parents=True, exist_ok=True)
    
    def run_data_cleaning_pipeline(self, input_path: str) -> Dict[str, Any]:
        """
        Execute data cleaning and validation job.
        
        Args:
            input_path: Path to raw CSV data (local or HDFS)
            
        Returns:
            Pipeline execution metadata
        """
        logger.info(f"🔍 Starting data cleaning pipeline: {input_path}")
        
        df = self.spark.read.csv(input_path, header=True, inferSchema=True)
        df = _canonicalize_columns(df)
        
        initial_count = df.count()
        logger.info(f"📥 Loaded {initial_count:,} raw records from {input_path}")
        
        # Validate required columns
        required_cols = [
            "ad_id", "campaign_id", "impressions", "clicks",
            "spend", "conversions"
        ]
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        # Remove null values
        df_clean = df.dropna(subset=required_cols)
        clean_count = df_clean.count()
        
        logger.info(f"✅ After cleaning: {clean_count:,} records")
        logger.info(f"🗑️  Removed {initial_count - clean_count:,} invalid rows")
        
        # Save cleaned data (10-column schema only)
        output_path = f"{self.output_dir}/cleaned_data"
        cleaned_output = df_clean.select(
            "ad_id",
            "campaign_id",
            "date",
            "platform",
            "age_group",
            "impressions",
            "clicks",
            "conversions",
            "spend",
            "revenue",
        )
        cleaned_output.coalesce(1).write.mode("overwrite").csv(output_path, header=True)
        
        metadata = {
            "stage": "data_cleaning",
            "input_path": input_path,
            "output_path": output_path,
            "timestamp": datetime.now().isoformat(),
            "initial_count": initial_count,
            "final_count": clean_count,
            "removed_rows": initial_count - clean_count,
            "status": "SUCCESS"
        }
        
        self._save_metadata("data_cleaning", metadata)
        return metadata
    
    def run_feature_engineering_pipeline(self, input_path: str) -> Dict[str, Any]:
        """
        Execute feature engineering job (KPI calculations).
        
        Computes:
        - CTR (Click-Through Rate)
        - CPC (Cost Per Click)
        - CPM (Cost Per Mille)
        - CVR (Conversion Rate)
        - CPA (Cost Per Action)
        - Quality scores
        
        Args:
            input_path: Path to cleaned data
            
        Returns:
            Pipeline execution metadata
        """
        logger.info(f"⚙️  Starting feature engineering pipeline: {input_path}")
        
        from pyspark.sql import functions as F
        
        df = self.spark.read.csv(input_path, header=True, inferSchema=True)
        df = _canonicalize_columns(df)
        
        # Compute KPI features
        df_features = df.withColumn("ctr", 
            F.when(F.col("impressions") > 0, F.col("clicks") / F.col("impressions"))
            .otherwise(F.lit(0.0))
        ).withColumn("cpc",
            F.when(F.col("clicks") > 0, F.col("spend") / F.col("clicks"))
            .otherwise(F.lit(0.0))
        ).withColumn("cpm",
            F.when(F.col("impressions") > 0, (F.col("spend") / F.col("impressions")) * 1000)
            .otherwise(F.lit(0.0))
        ).withColumn("cvr",
            F.when(F.col("clicks") > 0, F.col("conversions") / F.col("clicks"))
            .otherwise(F.lit(0.0))
        ).withColumn("cpa",
            F.when(F.col("conversions") > 0, F.col("spend") / F.col("conversions"))
            .otherwise(F.lit(None).cast("double"))
        )
        
        # Quality scoring
        cpa_median = df_features.selectExpr("percentile_approx(cpa, 0.5)").collect()[0][0]
        
        df_features = df_features.withColumn("quality_score",
            F.when(
                (F.col("ctr") >= 0.01) & 
                (F.col("cvr") >= 0.02) & 
                (F.col("cpa") <= cpa_median),
                F.lit(3.0)
            ).when(
                (F.col("ctr") >= 0.01) | 
                (F.col("cvr") >= 0.02) | 
                (F.col("cpa") <= cpa_median),
                F.lit(2.0)
            ).otherwise(F.lit(1.0))
        ).withColumn("quality_label",
            F.when(F.col("quality_score") == 3.0, F.lit("good"))
            .when(F.col("quality_score") == 2.0, F.lit("average"))
            .otherwise(F.lit("bad"))
        )
        
        output_path = f"{self.output_dir}/features_engineered"
        feature_output = df_features.select(
            "ad_id",
            "campaign_id",
            "date",
            "platform",
            "age_group",
            "impressions",
            "clicks",
            "conversions",
            "spend",
            "revenue",
            "ctr",
            "cpc",
            "cpm",
            "cvr",
            "cpa",
            "quality_score",
            "quality_label",
        )
        feature_output.coalesce(1).write.mode("overwrite").csv(output_path, header=True)
        
        feature_count = df_features.count()
        
        metadata = {
            "stage": "feature_engineering",
            "input_path": input_path,
            "output_path": output_path,
            "timestamp": datetime.now().isoformat(),
            "features_added": ["ctr", "cpc", "cpm", "cvr", "cpa", "quality_score", "quality_label"],
            "total_records": feature_count,
            "cpa_median": float(cpa_median) if cpa_median else 0,
            "status": "SUCCESS"
        }
        
        self._save_metadata("feature_engineering", metadata)
        return metadata
    
    def run_aggregation_pipeline(self, input_path: str) -> Dict[str, Any]:
        """
        Execute aggregation job for campaign-level analytics.
        
        Creates:
        - Campaign summary statistics
        - Demographic breakdowns
        - Performance benchmarks
        
        Args:
            input_path: Path to feature-engineered data
            
        Returns:
            Pipeline execution metadata
        """
        logger.info(f"📊 Starting aggregation pipeline: {input_path}")
        
        from pyspark.sql import functions as F
        
        df = self.spark.read.csv(input_path, header=True, inferSchema=True)
        
        # Campaign-level aggregation
        campaign_agg = df.groupBy("campaign_id").agg(
            F.count("ad_id").alias("ad_count"),
            F.sum("impressions").alias("total_impressions"),
            F.sum("clicks").alias("total_clicks"),
            F.sum("spend").alias("total_spend"),
            F.sum("conversions").alias("total_conversions"),
            F.avg("ctr").alias("avg_ctr"),
            F.avg("cpc").alias("avg_cpc"),
            F.avg("cpm").alias("avg_cpm"),
            F.avg("cvr").alias("avg_cvr"),
            F.avg("cpa").alias("avg_cpa"),
            F.avg("quality_score").alias("avg_quality_score"),
            F.countIf(F.col("quality_label") == "good").alias("good_count"),
            F.countIf(F.col("quality_label") == "average").alias("average_count"),
            F.countIf(F.col("quality_label") == "bad").alias("bad_count")
        ).orderBy(F.col("total_conversions").desc())
        
        campaign_output = f"{self.output_dir}/campaign_aggregation"
        campaign_agg.coalesce(1).write.mode("overwrite").csv(campaign_output, header=True)
        
        # Age demographic aggregation
        age_agg = df.filter(F.col("age_group").isNotNull()).groupBy("age_group").agg(
            F.count("ad_id").alias("ad_count"),
            F.avg("ctr").alias("avg_ctr"),
            F.avg("cpc").alias("avg_cpc"),
            F.avg("cpm").alias("avg_cpm"),
            F.avg("cvr").alias("avg_cvr"),
            F.avg("cpa").alias("avg_cpa")
        )
        
        age_output = f"{self.output_dir}/age_aggregation"
        age_agg.coalesce(1).write.mode("overwrite").csv(age_output, header=True)
        
        metadata = {
            "stage": "aggregation",
            "input_path": input_path,
            "campaign_output": campaign_output,
            "age_output": age_output,
            "timestamp": datetime.now().isoformat(),
            "campaign_count": campaign_agg.count(),
            "age_groups": age_agg.count(),
            "status": "SUCCESS"
        }
        
        self._save_metadata("aggregation", metadata)
        return metadata
    
    def run_full_pipeline(self, input_path: str) -> Dict[str, Any]:
        """
        Execute complete data pipeline from raw to aggregated.
        
        Pipeline stages:
        1. Data Cleaning & Validation
        2. Feature Engineering (KPI computation)
        3. Aggregation (Campaign, demographic)
        
        Args:
            input_path: Path to raw data
            
        Returns:
            Complete pipeline execution report
        """
        logger.info("🚀 Starting full data pipeline...")
        
        try:
            # Stage 1: Clean
            clean_meta = self.run_data_cleaning_pipeline(input_path)
            
            # Stage 2: Features
            features_meta = self.run_feature_engineering_pipeline(clean_meta["output_path"])
            
            # Stage 3: Aggregate
            agg_meta = self.run_aggregation_pipeline(features_meta["output_path"])
            
            full_report = {
                "pipeline_status": "SUCCESS",
                "total_stages": 3,
                "stages": {
                    "data_cleaning": clean_meta,
                    "feature_engineering": features_meta,
                    "aggregation": agg_meta
                },
                "timestamp": datetime.now().isoformat(),
                "total_processing_time": "See individual stages"
            }
            
            logger.info("✅ Pipeline completed successfully!")
            self._save_metadata("full_pipeline", full_report)
            
            return full_report
            
        except Exception as e:
            error_report = {
                "pipeline_status": "FAILED",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            self._save_metadata("pipeline_error", error_report)
            raise
    
    def _save_metadata(self, job_name: str, metadata: Dict[str, Any]):
        """Save job metadata for tracking and auditing."""
        metadata_path = f"{self.metadata_dir}/{job_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)
        logger.info(f"💾 Metadata saved to {metadata_path}")


def run_spark_pipeline(input_path: str, pipeline_type: str = "full") -> Dict[str, Any]:
    """
    Convenience function to run Spark pipeline.
    
    Args:
        input_path: Path to input data
        pipeline_type: "full", "cleaning", "features", or "aggregation"
        
    Returns:
        Pipeline execution results
    """
    orchestrator = SparkJobOrchestrator()
    
    if pipeline_type == "full":
        return orchestrator.run_full_pipeline(input_path)
    elif pipeline_type == "cleaning":
        return orchestrator.run_data_cleaning_pipeline(input_path)
    elif pipeline_type == "features":
        return orchestrator.run_feature_engineering_pipeline(input_path)
    elif pipeline_type == "aggregation":
        return orchestrator.run_aggregation_pipeline(input_path)
    else:
        raise ValueError(f"Unknown pipeline type: {pipeline_type}")
