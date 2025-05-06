from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, to_timestamp, window, sum as spark_sum, avg as spark_avg, max as spark_max, min as spark_min
from pyspark.sql.types import StructType, StringType, IntegerType, FloatType
from prometheus_client import start_http_server, Gauge
import time


# 1. Start Prometheus HTTP Serve
start_http_server(8000)
print("Prometheus metrics HTTP server started on port 8000")


# 2. Define Prometheus Gauges (Using only sensor_id as label)
traffic_total_vehicle_count = Gauge(
    "total_vehicle_count",
    "Total Vehicle Count per sensor aggregated over a 5-minute window",
    ["sensor_id"]
)

avg_speed_gauge = Gauge(
    "avg_speed",
    "Average Speed per sensor aggregated over a 10-minute window",
    ["sensor_id"]
)

congestion_hotspot_gauge = Gauge(
    "congestion_hotspot",
    "Count of HIGH congestion records per sensor (5-minute window)",
    ["sensor_id"]
)

sudden_speed_drop_gauge = Gauge(
    "sudden_speed_drop",
    "Sudden speed drop (>=50%) per sensor (2-minute window) as drop percentage",
    ["sensor_id"]
)

busiest_sensor_gauge = Gauge(
    "busiest_sensor",
    "Total Vehicle Count per sensor aggregated over a 30-minute window",
    ["sensor_id"]
)

# 3. Create SparkSession with Kafka Support
spark = SparkSession.builder \
    .appName("KafkaStreamToPrometheus_Simplified") \
    .master("local[*]") \
    .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.3.2") \
    .getOrCreate()


# 4. Define Schema and Read from Kafka
schema = StructType() \
    .add("sensor_id", StringType()) \
    .add("timestamp", StringType()) \
    .add("vehicle_count", IntegerType()) \
    .add("average_speed", FloatType()) \
    .add("congestion_level", StringType())

raw_stream = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:9092") \
    .option("subscribe", "traffic_data") \
    .option("startingOffsets", "latest") \
    .option("failOnDataLoss", "false") \
    .load()

# Parse JSON and do data quality checks:
traffic_df = raw_stream.selectExpr("CAST(value AS STRING) as json_str") \
    .select(from_json(col("json_str"), schema).alias("data")) \
    .select("data.*") \
    .filter(col("sensor_id").isNotNull() & col("timestamp").isNotNull()) \
    .filter(col("vehicle_count") >= 0) \
    .filter(col("average_speed") > 0) \
    .dropDuplicates(["sensor_id", "timestamp"])

# Convert timestamp and set watermark
traffic_df = traffic_df.withColumn("event_time", to_timestamp(col("timestamp"), "yyyy-MM-dd'T'HH:mm:ss"))
traffic_df = traffic_df.withWatermark("event_time", "10 minutes")

# 5. Define Windowed Aggregations
# (A) Traffic Volume Over Time (5-minute window)
traffic_volume_df = traffic_df.groupBy(
    window(col("event_time"), "5 minutes"),
    col("sensor_id")
).agg(
    spark_sum("vehicle_count").alias("total_count")
)

# (B) Average Speed per Sensor (10-minute window)
avg_speed_df = traffic_df.groupBy(
    window(col("event_time"), "10 minutes"),
    col("sensor_id")
).agg(
    spark_avg("average_speed").alias("avg_speed")
)

# (C) Congestion Hotspots (5-minute window, count HIGH congestion events)
congestion_df = traffic_df.filter(col("congestion_level") == "HIGH").groupBy(
    window(col("event_time"), "5 minutes"),
    col("sensor_id")
).agg(
    spark_sum("vehicle_count").alias("high_count")
)

# (D) Sudden Speed Drops (2-minute window: compute drop percentage)
speed_drop_df = traffic_df.groupBy(
    window(col("event_time"), "2 minutes"),
    col("sensor_id")
).agg(
    spark_max("average_speed").alias("max_speed"),
    spark_min("average_speed").alias("min_speed")
)

# (E) Busiest Sensors (30-minute window)
busiest_df = traffic_df.groupBy(
    window(col("event_time"), "30 minutes"),
    col("sensor_id")
).agg(
    spark_sum("vehicle_count").alias("total_count")
)


# 6. Define Update Functions for Prometheus (Group by sensor_id only)
# For each update function, we select the most recent window (i.e. with the maximum window.end)
# from the batch for each sensor and update the corresponding gauge.

def update_by_sensor(batch_df, value_field, gauge, label_name):
    # Create a dict to store the most recent window's value for each sensor
    sensor_values = {}
    rows = batch_df.collect()
    for row in rows:
        sensor_id = row["sensor_id"]
        # Use window end time to determine recency
        current_window_end = row["window"]["end"]
        # If sensor not seen or this window is later, update
        if sensor_id not in sensor_values or current_window_end > sensor_values[sensor_id]["window_end"]:
            sensor_values[sensor_id] = {"value": row[value_field], "window_end": current_window_end}
    for sensor_id, data in sensor_values.items():
        gauge.labels(sensor_id).set(data["value"])
        print(f"[{label_name}] Sensor {sensor_id}: {data['value']}")

def update_total_vehicle_count(batch_df, batch_id):
    update_by_sensor(batch_df, "total_count", traffic_total_vehicle_count, "Volume")

def update_avg_speed(batch_df, batch_id):
    update_by_sensor(batch_df, "avg_speed", avg_speed_gauge, "AvgSpeed")

def update_congestion(batch_df, batch_id):
    update_by_sensor(batch_df, "high_count", congestion_hotspot_gauge, "Congestion")

def update_speed_drop(batch_df, batch_id):
    # For speed drop, calculate drop percentage first per row, then group by sensor.
    sensor_values = {}
    for row in batch_df.collect():
        sensor_id = row["sensor_id"]
        max_speed = row["max_speed"]
        min_speed = row["min_speed"]
        # Calculate drop percentage
        drop_percentage = ((max_speed - min_speed) / max_speed) if max_speed > 0 else 0
        # We only care if drop is >=50%
        value = drop_percentage if drop_percentage >= 0.5 else 0
        current_window_end = row["window"]["end"]
        if sensor_id not in sensor_values or current_window_end > sensor_values[sensor_id]["window_end"]:
            sensor_values[sensor_id] = {"value": value, "window_end": current_window_end}
    for sensor_id, data in sensor_values.items():
        sudden_speed_drop_gauge.labels(sensor_id).set(data["value"])
        if data["value"]:
            print(f"[SpeedDrop] Sensor {sensor_id}: Drop = {data['value']*100:.1f}%")

def update_busiest_sensor(batch_df, batch_id):
    update_by_sensor(batch_df, "total_count", busiest_sensor_gauge, "Busiest")

# 7. Start Streaming Queries (Each aggregation runs as a separate query)
query_volume = traffic_volume_df.writeStream \
    .foreachBatch(update_total_vehicle_count) \
    .outputMode("update") \
    .option("checkpointLocation", "/tmp/checkpoint_volume") \
    .start()

query_avg_speed = avg_speed_df.writeStream \
    .foreachBatch(update_avg_speed) \
    .outputMode("update") \
    .option("checkpointLocation", "/tmp/checkpoint_avg_speed") \
    .start()

query_congestion = congestion_df.writeStream \
    .foreachBatch(update_congestion) \
    .outputMode("update") \
    .option("checkpointLocation", "/tmp/checkpoint_congestion") \
    .start()

query_speed_drop = speed_drop_df.writeStream \
    .foreachBatch(update_speed_drop) \
    .outputMode("update") \
    .option("checkpointLocation", "/tmp/checkpoint_speed_drop") \
    .start()

query_busiest = busiest_df.writeStream \
    .foreachBatch(update_busiest_sensor) \
    .outputMode("update") \
    .option("checkpointLocation", "/tmp/checkpoint_busiest") \
    .start()

# 8. Await Termination (All queries run concurrently)
query_volume.awaitTermination()
