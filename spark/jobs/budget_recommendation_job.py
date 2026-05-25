from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window


def build_spark() -> SparkSession:
    return (
        SparkSession.builder.appName("budget-recommendation-job")
        .config("spark.sql.session.timeZone", "UTC")
        .getOrCreate()
    )


def minmax_normalize(col_name: str, min_col: str, max_col: str):
    return F.when(F.col(max_col) > F.col(min_col), 
                  (F.col(col_name) - F.col(min_col)) / (F.col(max_col) 
                                                        - F.col(min_col))).otherwise(F.lit(0.5))

def _canonicalize_columns(df):
    if "campaign_id" not in df.columns:
        df = df.withColumn("campaign_id", F.lit(""))
    if "age_group" not in df.columns:
        df = df.withColumn("age_group", F.lit("unknown"))
    if "spend" not in df.columns:
        df = df.withColumn("spend", F.lit(0.0))
    if "conversions" not in df.columns:
        df = df.withColumn("conversions", F.lit(0.0))
    if "ctr" not in df.columns:
        df = df.withColumn("ctr", F.lit(0.0))
    if "cvr" not in df.columns:
        df = df.withColumn("cvr", F.lit(0.0))
    if "cpa" not in df.columns:
        df = df.withColumn("cpa", F.lit(0.0))
    if "quality_label" not in df.columns:
        df = df.withColumn("quality_label", F.lit("average"))
    return df

def main() -> None:
    spark = build_spark()

    input_path = "data/processed/ad_quality/*.csv"
    output_path = "data/curated/budget_recommendations"

    scored_df = (
        spark.read.option("header", True)
        .option("inferSchema", True)
        .csv(input_path)
        .transform(_canonicalize_columns)
        .withColumn("campaign_id", F.col("campaign_id").cast("string"))
        .withColumn("age_group", F.col("age_group").cast("string"))
        .withColumn("spend", F.col("spend").cast("double"))
        .withColumn("conversions", F.col("conversions").cast("double"))
        .withColumn("ctr", F.col("ctr").cast("double"))
        .withColumn("cvr", F.col("cvr").cast("double"))
        .withColumn("cpa", F.col("cpa").cast("double"))
        .withColumn(
            "age_segment",
            F.when(F.length(F.trim(F.col("age_group").cast("string"))) > 0, F.col("age_group").cast("string")).otherwise(F.lit("unknown")),
        )
        .where((F.length(F.trim(F.col("campaign_id").cast("string"))) > 0) & (F.col("age_segment") != F.lit("unknown")))
    )

    aggregated_df = (
        scored_df.groupBy("campaign_id", "age_segment")
        .agg(
            F.count("*").alias("ads_count"),
            F.sum("spend").alias("total_spent"),
            F.sum("conversions").alias("total_conversions"),
            F.avg("ctr").alias("avg_ctr"),
            F.avg("cvr").alias("avg_cvr"),
            F.avg("cpa").alias("avg_cpa"),
            F.avg(F.when(F.col("quality_label") == "good", F.lit(1.0)).otherwise(F.lit(0.0))).alias("good_ratio"),
        )
        .withColumn(
            "conversion_per_spend",
            F.when(F.col("total_spent") > 0, F.col("total_conversions") / F.col("total_spent")).otherwise(F.lit(0.0)),
        )
        .withColumn("cpa_inverse", F.when(F.col("avg_cpa") > 0, F.lit(1.0) / F.col("avg_cpa")).otherwise(F.lit(0.0)))
    )

    stat_window = Window.partitionBy()

    scored_segment_df = (
        aggregated_df.withColumn("min_avg_ctr", F.min("avg_ctr").over(stat_window))
        .withColumn("max_avg_ctr", F.max("avg_ctr").over(stat_window))
        .withColumn("min_avg_cvr", F.min("avg_cvr").over(stat_window))
        .withColumn("max_avg_cvr", F.max("avg_cvr").over(stat_window))
        .withColumn("min_conversion_per_spend", F.min("conversion_per_spend").over(stat_window))
        .withColumn("max_conversion_per_spend", F.max("conversion_per_spend").over(stat_window))
        .withColumn("min_good_ratio", F.min("good_ratio").over(stat_window))
        .withColumn("max_good_ratio", F.max("good_ratio").over(stat_window))
        .withColumn("min_cpa_inverse", F.min("cpa_inverse").over(stat_window))
        .withColumn("max_cpa_inverse", F.max("cpa_inverse").over(stat_window))
        .withColumn("norm_ctr", minmax_normalize("avg_ctr", "min_avg_ctr", "max_avg_ctr"))
        .withColumn("norm_cvr", minmax_normalize("avg_cvr", "min_avg_cvr", "max_avg_cvr"))
        .withColumn(
            "norm_conversion_per_spend",
            minmax_normalize("conversion_per_spend", "min_conversion_per_spend", "max_conversion_per_spend"),
        )
        .withColumn("norm_good_ratio", minmax_normalize("good_ratio", "min_good_ratio", "max_good_ratio"))
        .withColumn("norm_cpa_inverse", minmax_normalize("cpa_inverse", "min_cpa_inverse", "max_cpa_inverse"))
        .withColumn(
            "recommendation_score",
            F.round(
                F.col("norm_ctr") * F.lit(0.2)
                + F.col("norm_cvr") * F.lit(0.3)
                + F.col("norm_conversion_per_spend") * F.lit(0.25)
                + F.col("norm_good_ratio") * F.lit(0.15)
                + F.col("norm_cpa_inverse") * F.lit(0.1),
                6,
            ),
        )
        .withColumn(
            "suggested_action",
            F.when(F.col("recommendation_score") >= F.lit(0.7), F.lit("increase_budget"))
            .when(F.col("recommendation_score") >= F.lit(0.45), F.lit("keep_and_test"))
            .otherwise(F.lit("reduce_budget")),
        )
    )

    allocation_window = Window.partitionBy()
    total_score_col = F.sum("recommendation_score").over(allocation_window)

    final_df = (
        scored_segment_df.withColumn(
            "recommended_weight",
            F.when(total_score_col > 0, F.col("recommendation_score") / total_score_col).otherwise(F.lit(0.0)),
        )
        .withColumn("segment_id", F.concat_ws("|", F.col("campaign_id"), F.col("age_segment")))
        .select(
            "segment_id",
            "campaign_id",
            F.col("age_segment").alias("age_group"),
            "ads_count",
            F.round("total_spent", 4).alias("total_spent"),
            F.round("total_conversions", 4).alias("total_conversions"),
            F.round("avg_ctr", 6).alias("avg_ctr"),
            F.round("avg_cvr", 6).alias("avg_cvr"),
            F.round("avg_cpa", 6).alias("avg_cpa"),
            F.round("good_ratio", 6).alias("good_ratio"),
            F.round("conversion_per_spend", 6).alias("conversion_per_spend"),
            "recommendation_score",
            F.round("recommended_weight", 6).alias("recommended_weight"),
            "suggested_action",
        )
        .orderBy(F.col("recommendation_score").desc())
    )

    final_df.write.mode("overwrite").option("header", True).csv(output_path)

    spark.stop()


if __name__ == "__main__":
    main()
