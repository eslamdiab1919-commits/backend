import json
import asyncio
import os
from datetime import datetime
from eval.evaluator import evaluate_query

async def main():
    print("Starting AI Evaluation Framework...")
    dataset_path = os.path.join(os.path.dirname(__file__), "dataset.json")
    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)
        
    print(f"Loaded {len(dataset)} queries. Running evaluation...")
    
    results = []
    for item in dataset:
        print(f"Evaluating [{item['id']}]: {item['query']}")
        res = await evaluate_query(item)
        if "error" in res:
            print(f"Error evaluating {item['id']}: {res['error']}")
            # Mock failed result for aggregation
            res = {
                "id": item["id"],
                "category": item.get("category", "unknown"),
                "passed": False,
                "judge_reason": f"System Error: {res['error']}"
            }
        results.append(res)
        await asyncio.sleep(1) # avoid rate limits
        
    # Aggregate Metrics
    passed = sum(1 for r in results if r.get("passed", False))
    total_cost = sum(r.get("cost_usd", 0) for r in results)
    
    ttft_values = [r.get("ttft_sec", 0) for r in results if "ttft_sec" in r]
    avg_ttft = sum(ttft_values) / len(ttft_values) if ttft_values else 0
    
    latency_values = [r.get("latency_sec", 0) for r in results if "latency_sec" in r]
    avg_latency = sum(latency_values) / len(latency_values) if latency_values else 0
    
    # Check Regression
    report_json_path = os.path.join(os.path.dirname(__file__), "eval_report.json")
    previous_passed = None
    if os.path.exists(report_json_path):
        with open(report_json_path, "r", encoding="utf-8") as f:
            prev_data = json.load(f)
            previous_passed = prev_data.get("summary", {}).get("passed")
            
    regression_msg = ""
    if previous_passed is not None:
        if passed < previous_passed:
            regression_msg = f"⚠️ REGRESSION DETECTED: Pass rate dropped from {previous_passed} to {passed}."
        elif passed > previous_passed:
            regression_msg = f"✅ IMPROVEMENT: Pass rate increased from {previous_passed} to {passed}."
        else:
            regression_msg = "No change in pass rate."
    else:
        regression_msg = "First run. Baseline established."
            
    summary = {
        "timestamp": datetime.now().isoformat(),
        "total": len(dataset),
        "passed": passed,
        "pass_rate": f"{passed/len(dataset)*100:.1f}%" if len(dataset) > 0 else "0%",
        "avg_ttft_sec": round(avg_ttft, 2),
        "avg_latency_sec": round(avg_latency, 2),
        "total_cost_usd": round(total_cost, 6),
        "regression": regression_msg
    }
    
    report = {
        "summary": summary,
        "results": results
    }
    
    with open(report_json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        
    # Markdown Report
    report_md_path = os.path.join(os.path.dirname(__file__), "eval_report.md")
    with open(report_md_path, "w", encoding="utf-8") as f:
        f.write("# AI Evaluation Report\n\n")
        f.write(f"**Date:** {summary['timestamp']}\n\n")
        f.write("## Summary Metrics\n")
        f.write(f"- **Pass Rate:** {summary['pass_rate']} ({passed}/{len(dataset)})\n")
        f.write(f"- **Avg TTFT:** {summary['avg_ttft_sec']}s\n")
        f.write(f"- **Avg Latency:** {summary['avg_latency_sec']}s\n")
        f.write(f"- **Total Estimated Cost:** ${summary['total_cost_usd']}\n")
        f.write(f"- **Regression Status:** {regression_msg}\n\n")
        
        f.write("## Detailed Results\n")
        for r in results:
            status = "✅ PASS" if r.get("passed") else "❌ FAIL"
            f.write(f"### {r.get('id')} - {r.get('category')} - {status}\n")
            if "error" in r:
                f.write(f"**Error:** {r.get('error')}\n\n---\n")
                continue
                
            f.write(f"**Query:** {r.get('query')}\n\n")
            f.write(f"**Response:** {r.get('response')}\n\n")
            f.write(f"**Judge Reason:** {r.get('judge_reason')}\n\n")
            f.write(f"- TTFT: {r.get('ttft_sec')}s | Cost: ${r.get('cost_usd'):.6f} | Citations: {r.get('has_citations')}\n\n")
            f.write("---\n")
            
    print(f"\nEvaluation complete: {passed}/{len(dataset)} passed.")
    print(f"Reports saved to eval_report.json and eval_report.md.")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(main())
