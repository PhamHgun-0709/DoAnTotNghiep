"""
Spark Session Management and Configuration

Centralizes Spark session creation and configuration for all jobs.
Enables easy switching between local, YARN, and cloud deployments.
"""

import os
import logging
from pyspark.sql import SparkSession
from pyspark.conf import SparkConf
from typing import Optional

logger = logging.getLogger(__name__)


class SparkSessionManager:
    """
    Singleton Spark Session manager.
    
    Ensures consistent Spark configuration across all jobs and prevents
    multiple session creation.
    """
    
    _instance: Optional[SparkSession] = None
    
    @staticmethod
    def get_session(app_name: str = "AdCampaignAnalysis") -> SparkSession:
        """
        Get or create Spark session.
        
        Args:
            app_name: Application name for Spark
            
        Returns:
            SparkSession configured for Big Data processing
        """
        if SparkSessionManager._instance is None:
            SparkSessionManager._instance = SparkSessionManager._create_session(app_name)
        return SparkSessionManager._instance
    
    @staticmethod
    def _create_session(app_name: str) -> SparkSession:
        """Create configured Spark session."""
        
        # Determine execution mode
        master_url = os.getenv("SPARK_MASTER", "local[*]")  # local[*] for dev, yarn for prod
        
        conf = SparkConf()
        conf.setAppName(app_name)
        conf.setMaster(master_url)
        
        # Performance tuning
        conf.set("spark.sql.shuffle.partitions", "200")
        conf.set("spark.sql.adaptive.enabled", "true")
        conf.set("spark.sql.adaptive.coalescePartitions.enabled", "true")
        
        # Memory configuration
        conf.set("spark.driver.memory", "4g")
        conf.set("spark.executor.memory", "4g")
        conf.set("spark.executor.cores", "4")
        
        # Hadoop integration
        conf.set("spark.hadoop.fs.defaultFS", os.getenv("HDFS_NAMENODE", "hdfs://localhost:9000"))
        
        # Create session
        spark = SparkSession.builder.config(conf=conf).getOrCreate()
        
        # Log configuration
        logger.info(f"✅ Spark session created: {app_name}")
        logger.info(f"🖥️  Master URL: {master_url}")
        logger.info(f"⚙️  Default parallelism: {spark.sparkContext.defaultParallelism}")
        
        return spark
    
    @staticmethod
    def stop_session():
        """Gracefully stop Spark session."""
        if SparkSessionManager._instance is not None:
            SparkSessionManager._instance.stop()
            SparkSessionManager._instance = None
            logger.info("🛑 Spark session stopped")


def get_spark() -> SparkSession:
    """Convenience function for getting Spark session."""
    return SparkSessionManager.get_session()
