from pyspark.sql import SparkSession
from pyspark.sql import functions as F


def build_spark() -> SparkSession:
    return (
        SparkSession.builder.appName("ad-quality-job")
        .config("spark.sql.session.timeZone", "UTC")
        .getOrCreate()
    )


def safe_divide(numerator_col, denominator_col):
    return F.when(denominator_col > 0, numerator_col / denominator_col).otherwise(F.lit(0.0))


def main() -> None:
    spark = build_spark()

    input_path = "data/data_extended.csv"
    output_path = "data/processed/ad_quality"

    raw_df = (
        spark.read.option("header", True)
        .option("inferSchema", True)
        .csv(input_path)
    )

    typed_df = (
        raw_df.withColumn("impressions", F.col("impressions").cast("double"))
        .withColumn("clicks", F.col("clicks").cast("double"))
        .withColumn("spent", F.col("spent").cast("double"))
        .withColumn("approved_conversion", F.col("approved_conversion").cast("double"))
    )

    kpi_df = (
        typed_df.withColumn("ctr", safe_divide(F.col("clicks"), F.col("impressions")))
        .withColumn("cpc", safe_divide(F.col("spent"), F.col("clicks")))
        .withColumn("cvr", safe_divide(F.col("approved_conversion"), F.col("clicks")))
        .withColumn(
            "cpa",
            F.when(F.col("approved_conversion") > 0, F.col("spent") / F.col("approved_conversion")).otherwise(
                F.lit(None).cast("double")
            ),
        )
    )

    cpa_median = kpi_df.approxQuantile("cpa", [0.5], 0.01)[0]

    scored_df = (
        kpi_df.withColumn("rule_ctr", F.when(F.col("ctr") >= F.lit(0.01), F.lit(1)).otherwise(F.lit(0)))
        .withColumn("rule_cvr", F.when(F.col("cvr") >= F.lit(0.02), F.lit(1)).otherwise(F.lit(0)))
        .withColumn(
            "rule_cpa",
            F.when((F.col("approved_conversion") > 0) & (F.col("cpa") <= F.lit(cpa_median)), F.lit(1)).otherwise(
                F.lit(0)
            ),
        )
        .withColumn(
            "rule_conv",
            F.when(F.col("approved_conversion") >= F.lit(1.0), F.lit(1)).otherwise(F.lit(0)),
        )
        .withColumn(
            "quality_score",
            F.col("rule_ctr") + F.col("rule_cvr") + F.col("rule_cpa") + F.col("rule_conv"),
        )
        .withColumn(
            "quality_label",
            F.when(F.col("quality_score") >= 3, F.lit("good"))
            .when(F.col("quality_score") == 2, F.lit("average"))
            .otherwise(F.lit("bad")),
        )
    )

    final_df = scored_df.select(
        "ad_id",
        "campaign_id",
        "fb_campaign_id",
        "reporting_start",
        "reporting_end",
        "age",
        "gender",
        "impressions",
        "clicks",
        "spent",
        "approved_conversion",
        "ctr",
        "cpc",
        "cvr",
        "cpa",
        "quality_score",
        "quality_label",
    )

    final_df.write.mode("overwrite").option("header", True).csv(output_path)

    spark.stop()


if __name__ == "__main__":
    main()
