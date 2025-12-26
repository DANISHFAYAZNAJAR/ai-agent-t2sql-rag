"""
DeepEval evaluation script for agent performance
"""
import os
import sys
import django
import json
from datetime import datetime

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from deepeval.test_case import LLMTestCase
from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric
from deepeval import evaluate
from agent.graph import get_agent
from django.conf import settings


class AgentTestCase(LLMTestCase):
    """Test case for agent evaluation"""
    
    def __init__(self, input_query, expected_output, task_type, metrics=None):
        super().__init__(
            input=input_query,
            actual_output="",  # Will be set in run()
            expected_output=expected_output,
            metrics=metrics or [AnswerRelevancyMetric(threshold=0.7)]
        )
        # Store task_type as a class attribute (not a field)
        object.__setattr__(self, 'task_type', task_type)
    
    def run(self):
        """Run the agent and return output"""
        agent = get_agent()
        
        initial_state = {
            "query": self.input,
            "route": "unknown",
            "task_type": "unknown",
            "response": "",
            "result": {},
            "metadata": {},
            "error": ""
        }
        
        result = agent.invoke(initial_state)
        self.actual_output = result.get("response", "")
        return self.actual_output


def create_test_cases():
    """Create test cases for evaluation"""
    
    test_cases = [
        # T2SQL test cases
        AgentTestCase(
            input_query="How many leads are there?",
            expected_output="There should be 100 leads in the database",
            task_type="t2sql",
            metrics=[AnswerRelevancyMetric(threshold=0.7)]
        ),
        AgentTestCase(
            input_query="Show me all leads from Lumina Grand",
            expected_output="Should return leads where project_name is 'Lumina Grand'",
            task_type="t2sql",
            metrics=[AnswerRelevancyMetric(threshold=0.7)]
        ),
        AgentTestCase(
            input_query="Count leads by project name",
            expected_output="Should return a count grouped by project_name",
            task_type="t2sql",
            metrics=[AnswerRelevancyMetric(threshold=0.7)]
        ),
        AgentTestCase(
            input_query="Find leads with budget above 1 million",
            expected_output="Should return leads where min_budget or max_budget is above 1000000",
            task_type="t2sql",
            metrics=[AnswerRelevancyMetric(threshold=0.7)]
        ),
        
        # RAG test cases (if documents are ingested)
        AgentTestCase(
            input_query="What are the amenities in Lumina Grand?",
            expected_output="Should provide information about amenities from the brochure",
            task_type="rag",
            metrics=[AnswerRelevancyMetric(threshold=0.7), FaithfulnessMetric(threshold=0.7)]
        ),
        AgentTestCase(
            input_query="Tell me about the features of Sobha Crest",
            expected_output="Should provide information about property features from the brochure",
            task_type="rag",
            metrics=[AnswerRelevancyMetric(threshold=0.7), FaithfulnessMetric(threshold=0.7)]
        ),
    ]
    
    return test_cases


def run_evaluation():
    """Run DeepEval evaluation"""
    print("=" * 60)
    print("Running DeepEval Evaluation")
    print("=" * 60)
    
    if not settings.OPENAI_API_KEY:
        print("⚠️  WARNING: OPENAI_API_KEY not set. Evaluation may fail.")
        return
    
    # Create test cases
    test_cases = create_test_cases()
    print(f"\nCreated {len(test_cases)} test cases")
    
    # Run each test case to get actual output
    print("\nRunning test cases to generate actual outputs...")
    for i, test_case in enumerate(test_cases, 1):
        print(f"  Running test case {i}/{len(test_cases)}: {test_case.input[:50]}...")
        try:
            test_case.run()
            print(f"    ✓ Generated output: {len(test_case.actual_output)} characters")
        except Exception as e:
            print(f"    ✗ Error: {str(e)}")
            test_case.actual_output = f"Error: {str(e)}"
    
    # Extract all unique metrics from test cases
    all_metrics = []
    for test_case in test_cases:
        if hasattr(test_case, 'metrics') and test_case.metrics:
            for metric in test_case.metrics:
                # Create a new instance to avoid conflicts
                metric_class = metric.__class__
                metric_threshold = getattr(metric, 'threshold', 0.7)
                new_metric = metric_class(threshold=metric_threshold)
                if not any(m.__class__ == new_metric.__class__ for m in all_metrics):
                    all_metrics.append(new_metric)
    
    # If no metrics found, use default
    if not all_metrics:
        all_metrics = [AnswerRelevancyMetric(threshold=0.7)]
    
    print(f"\nUsing {len(all_metrics)} metric(s) for evaluation")
    
    # Run evaluation with explicit metrics
    try:
        print("\nRunning DeepEval evaluation...")
        evaluation_result = evaluate(test_cases, metrics=all_metrics)
        
        # Prepare results for JSON export
        evaluation_results = {
            "timestamp": datetime.now().isoformat(),
            "total_test_cases": len(test_cases),
            "results": []
        }
        
        # Extract results from EvaluationResult object
        # evaluation_result.test_results contains TestResult objects
        for i, (test_case, test_result) in enumerate(zip(test_cases, evaluation_result.test_results)):
            result_data = {
                "test_case": i + 1,
                "input": test_result.input or test_case.input,
                "actual_output": test_result.actual_output or getattr(test_case, 'actual_output', ''),
                "expected_output": test_case.expected_output,
                "task_type": test_case.task_type,
                "test_success": test_result.success,
                "metrics": []
            }
            
            # Extract metric results from TestResult.metrics_data
            if test_result.metrics_data:
                for metric_data in test_result.metrics_data:
                    # MetricData has: name, score, threshold, success, reason
                    metric_info = {
                        "name": metric_data.name,
                        "score": metric_data.score,
                        "threshold": metric_data.threshold,
                        "success": metric_data.success,
                        "reason": metric_data.reason
                    }
                    result_data["metrics"].append(metric_info)
            else:
                # Fallback: try to get from test_case.metrics if metrics_data is not available
                if hasattr(test_case, 'metrics') and test_case.metrics:
                    for metric in test_case.metrics:
                        score = getattr(metric, 'score', None) or getattr(metric, '_score', None)
                        threshold = getattr(metric, 'threshold', 0.7)
                        success = getattr(metric, 'success', None)
                        if success is None and score is not None:
                            success = score >= threshold
                        
                        metric_info = {
                            "name": metric.__class__.__name__,
                            "score": score,
                            "threshold": threshold,
                            "success": success,
                            "reason": getattr(metric, 'reason', None) or getattr(metric, '_reason', None)
                        }
                        result_data["metrics"].append(metric_info)
            
            evaluation_results["results"].append(result_data)
        
        # Save results to JSON file
        output_file = "agent_evaluation_scores.json"
        with open(output_file, 'w') as f:
            json.dump(evaluation_results, f, indent=2)
        
        print(f"\n✓ Evaluation completed")
        print(f"✓ Results saved to {output_file}")
        
        # Print summary
        print("\n" + "=" * 60)
        print("Evaluation Summary")
        print("=" * 60)
        for result in evaluation_results["results"]:
            print(f"\nTest Case {result['test_case']}: {result['input']}")
            print(f"  Task Type: {result['task_type']}")
            for metric in result['metrics']:
                score = metric.get('score', 'N/A')
                success = metric.get('success', 'N/A')
                print(f"  {metric['name']}: Score={score}, Success={success}")
        
        return evaluation_results
        
    except Exception as e:
        print(f"✗ Error during evaluation: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    results = run_evaluation()
    
    if results:
        print("\n🎉 Evaluation completed successfully!")
    else:
        print("\n⚠️  Evaluation encountered errors")

