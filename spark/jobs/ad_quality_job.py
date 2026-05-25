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


def _canonicalize_columns(df):
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


def main() -> None:
    spark = build_spark()

    input_path = "data/data_100_campaigns_high_cvr.csv"
    output_path = "data/processed/ad_quality"

    raw_df = (
        spark.read.option("header", True)
        .option("inferSchema", True)
        .csv(input_path)
    )

    raw_df = _canonicalize_columns(raw_df)

    typed_df = (
        raw_df.withColumn("impressions", F.col("impressions").cast("double"))
        .withColumn("clicks", F.col("clicks").cast("double"))
        .withColumn("spend", F.col("spend").cast("double"))
        .withColumn("conversions", F.col("conversions").cast("double"))
    )

    kpi_df = (
        typed_df.withColumn("ctr", safe_divide(F.col("clicks"), F.col("impressions")))
        .withColumn("cpc", safe_divide(F.col("spend"), F.col("clicks")))
        .withColumn("cvr", safe_divide(F.col("conversions"), F.col("clicks")))
        .withColumn("cpm", F.when(F.col("impressions") > 0, (F.col("spend") / F.col("impressions")) * 1000).otherwise(F.lit(0.0)))
        .withColumn(
            "cpa",
            F.when(F.col("conversions") > 0, F.col("spend") / F.col("conversions")).otherwise(
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
            F.when((F.col("conversions") > 0) & (F.col("cpa") <= F.lit(cpa_median)), F.lit(1)).otherwise(
                F.lit(0)
            ),
        )
        .withColumn(
            "rule_conv",
            F.when(F.col("conversions") >= F.lit(1.0), F.lit(1)).otherwise(F.lit(0)),
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

    final_df.write.mode("overwrite").option("header", True).csv(output_path)

    spark.stop()


if __name__ == "__main__":
    main()
