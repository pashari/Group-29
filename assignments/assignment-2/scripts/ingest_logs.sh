#!/bin/bash
# usage: ./ingest_logs.sh YYYY-MM-DD

if [ $# -ne 1 ]; then
  echo "Usage: $0 YYYY-MM-DD"
  exit 1
fi

DATE=$1
YEAR=$(echo $DATE | cut -d- -f1)
MONTH=$(echo $DATE | cut -d- -f2)
DAY=$(echo $DATE | cut -d- -f3)

LOGS_HDFS="/raw/logs/$YEAR/$MONTH/$DAY"
META_HDFS="/raw/metadata/$YEAR/$MONTH/$DAY"

# 1) make sure the HDFS dirs exist
hdfs dfs -mkdir -p $LOGS_HDFS
hdfs dfs -mkdir -p $META_HDFS

# 2) push your CSVs up to HDFS
hdfs dfs -put -f rawdata/User_Activity_Logs.csv $LOGS_HDFS/
hdfs dfs -put -f rawdata/Content_Metadata.csv    $META_HDFS/

echo "✔ Ingested User_Activity_Logs.csv → $LOGS_HDFS"
echo "✔ Ingested Content_Metadata.csv    → $META_HDFS"
