
import asyncio
from pprint import pprint

from app.collectors.prometheus.collector import PrometheusCollector


async def main():
    collector = PrometheusCollector()

    evidence = await collector.collect()

    print("\n========== CPU METRICS ==========")
    pprint(evidence["metrics"]["cpu"])

    print("\n========== MEMORY METRICS ==========")
    pprint(evidence["metrics"]["memory"])


if __name__ == "__main__":
    asyncio.run(main())
