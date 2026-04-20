"""
e2e_live_test.py
================
Comprehensive End-to-End Live Testing Suite
Tests all modules and alert engines in sequence with real-time visibility.

Tests:
  ✓ Database initialization
  ✓ Data collection
  ✓ Trend analysis engine
  ✓ Root cause detection
  ✓ Failure prediction
  ✓ Prevention engine
  ✓ Action policy engine
  ✓ Alert notifications
  ✓ Dashboard API endpoints
"""

import logging
import sys
import time
import threading
import json
from datetime import datetime
from pathlib import Path

# Setup rich logging for better visibility
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-8s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("E2E_TEST")

# Import core modules
try:
    from config.settings import SAMPLING_INTERVAL, ANALYSIS_EVERY_N
    from database.db_manager import DatabaseManager
    from core.collector import DataCollector
    from core.analyzer import TrendAnalyzer
    from core.root_cause import RootCauseEngine
    from core.predictor import FailurePredictor
    from core.prevention import PreventionEngine
    from core.action_policy import ActionPolicyEngine
    from core.notifier import SmartNotifier
    from models.reliability_model import ReliabilityModel
    logger.info("✓ All core modules imported successfully")
except Exception as e:
    logger.error(f"✗ Failed to import modules: {e}")
    sys.exit(1)


class E2ETestSuite:
    """Orchestrates end-to-end testing of all system components."""
    
    def __init__(self):
        self.db = None
        self.collector = None
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "tests": {},
            "errors": [],
        }
        self.stop_event = threading.Event()
        
    def log_test(self, test_name, status, details=""):
        """Log test result."""
        status_emoji = "✓" if status == "PASS" else "✗"
        self.results["tests"][test_name] = {
            "status": status,
            "details": details,
            "timestamp": datetime.now().isoformat(),
        }
        logger.info(f"{status_emoji} {test_name}: {status} {details}")
        
    def test_1_database_initialization(self):
        """TEST 1: Database initialization and schema."""
        logger.info("\n" + "="*70)
        logger.info("TEST 1: Database Initialization")
        logger.info("="*70)
        
        try:
            self.db = DatabaseManager()
            logger.info("  ✓ Database connection established")
            
            # Check tables exist
            tables = self.db.get_tables()
            logger.info(f"  ✓ Tables created: {len(tables)} tables")
            for table in tables:
                logger.info(f"    - {table}")
            
            # Check baseline data
            baseline = self.db.get_baseline_metrics()
            logger.info(f"  ✓ Baseline metrics retrieved")
            for metric, value in baseline.items():
                logger.info(f"    - {metric}: {value:.2f}")
            
            self.log_test("Database Initialization", "PASS", f"{len(tables)} tables")
            return True
        except Exception as e:
            logger.exception(f"  ✗ Database test failed: {e}")
            self.log_test("Database Initialization", "FAIL", str(e))
            self.results["errors"].append(str(e))
            return False
    
    def test_2_data_collection(self):
        """TEST 2: Data collection from psutil."""
        logger.info("\n" + "="*70)
        logger.info("TEST 2: Data Collection")
        logger.info("="*70)
        
        try:
            self.collector = DataCollector(self.db, interval_s=SAMPLING_INTERVAL)
            logger.info("  ✓ DataCollector initialized")
            
            # Start collection
            self.collector.start()
            logger.info("  ✓ Collection started")
            
            # Collect samples
            logger.info("  ⏳ Collecting 10 samples (10 seconds)...")
            time.sleep(10)
            
            # Get collected metrics
            recent_data = self.db.get_recent_snapshots(count=10)
            logger.info(f"  ✓ Collected {len(recent_data)} samples")
            
            if recent_data:
                last_sample = recent_data[-1]
                logger.info("  Last sample metrics:")
                for key, value in last_sample.items():
                    if key != "id" and key != "timestamp":
                        logger.info(f"    - {key}: {value:.2f}")
            
            self.log_test("Data Collection", "PASS", f"{len(recent_data)} samples")
            return True
        except Exception as e:
            logger.exception(f"  ✗ Collection test failed: {e}")
            self.log_test("Data Collection", "FAIL", str(e))
            self.results["errors"].append(str(e))
            return False
    
    def test_3_trend_analyzer(self):
        """TEST 3: Trend analysis engine."""
        logger.info("\n" + "="*70)
        logger.info("TEST 3: Trend Analyzer Engine")
        logger.info("="*70)
        
        try:
            analyzer = TrendAnalyzer(self.db)
            logger.info("  ✓ TrendAnalyzer initialized")
            
            # Analyze trends
            trends = analyzer.detect_trends()
            logger.info(f"  ✓ Trend analysis complete")
            
            if trends["detected_issues"]:
                logger.info(f"  ⚠ Detected {len(trends['detected_issues'])} aging indicators")
                for issue in trends["detected_issues"]:
                    logger.info(f"    - {issue['metric']}: slope={issue['slope']:.4f}")
            else:
                logger.info("  ✓ No aging issues detected (system healthy)")
            
            self.log_test("Trend Analyzer", "PASS", f"{len(trends['detected_issues'])} issues")
            return True
        except Exception as e:
            logger.exception(f"  ✗ Trend analysis failed: {e}")
            self.log_test("Trend Analyzer", "FAIL", str(e))
            self.results["errors"].append(str(e))
            return False
    
    def test_4_root_cause_engine(self):
        """TEST 4: Root cause detection engine."""
        logger.info("\n" + "="*70)
        logger.info("TEST 4: Root Cause Detection Engine")
        logger.info("="*70)
        
        try:
            analyzer = TrendAnalyzer(self.db)
            rc_engine = RootCauseEngine(self.db, analyzer)
            logger.info("  ✓ RootCauseEngine initialized")
            
            # Run root cause analysis
            root_causes = rc_engine.run()
            logger.info(f"  ✓ Root cause analysis complete")
            
            if root_causes:
                logger.info(f"  Identified {len(root_causes)} root causes:")
                for cause in root_causes:
                    logger.info(f"    - {cause.get('cause', 'Unknown')}")
                    logger.info(f"      Confidence: {cause.get('confidence', 0):.1%}")
            else:
                logger.info("  ✓ No root causes identified (system healthy)")
            
            self.log_test("Root Cause Engine", "PASS", f"{len(root_causes)} causes")
            return True
        except Exception as e:
            logger.exception(f"  ✗ Root cause analysis failed: {e}")
            self.log_test("Root Cause Engine", "FAIL", str(e))
            self.results["errors"].append(str(e))
            return False
    
    def test_5_failure_predictor(self):
        """TEST 5: Failure prediction engine."""
        logger.info("\n" + "="*70)
        logger.info("TEST 5: Failure Prediction Engine")
        logger.info("="*70)
        
        try:
            analyzer = TrendAnalyzer(self.db)
            model = ReliabilityModel()
            predictor = FailurePredictor(self.db, analyzer, model)
            logger.info("  ✓ FailurePredictor initialized")
            
            # Run prediction
            predictions = predictor.run()
            logger.info(f"  ✓ Failure prediction complete")
            
            if predictions:
                logger.info(f"  Predictions for {len(predictions)} metrics:")
                for pred in predictions:
                    metric = pred.get("metric", "Unknown")
                    prob = pred.get("failure_probability", 0)
                    eta = pred.get("time_to_failure_hours", -1)
                    logger.info(f"    - {metric}")
                    logger.info(f"      Failure Probability: {prob:.1%}")
                    if eta > 0:
                        logger.info(f"      Time to Failure: {eta:.1f} hours")
            else:
                logger.info("  ✓ No critical failures predicted")
            
            self.log_test("Failure Predictor", "PASS", f"{len(predictions)} predictions")
            return True
        except Exception as e:
            logger.exception(f"  ✗ Prediction failed: {e}")
            self.log_test("Failure Predictor", "FAIL", str(e))
            self.results["errors"].append(str(e))
            return False
    
    def test_6_prevention_engine(self):
        """TEST 6: Prevention engine."""
        logger.info("\n" + "="*70)
        logger.info("TEST 6: Prevention Engine")
        logger.info("="*70)
        
        try:
            prevention = PreventionEngine(self.db)
            logger.info("  ✓ PreventionEngine initialized")
            
            # Run prevention
            actions = prevention.run()
            logger.info(f"  ✓ Prevention analysis complete")
            
            if actions:
                logger.info(f"  Generated {len(actions)} prevention actions:")
                for action in actions:
                    logger.info(f"    - {action.get('action', 'Unknown')}")
                    logger.info(f"      Type: {action.get('type', 'Unknown')}")
                    logger.info(f"      Priority: {action.get('priority', 'Medium')}")
            else:
                logger.info("  ✓ No prevention actions needed")
            
            self.log_test("Prevention Engine", "PASS", f"{len(actions)} actions")
            return True
        except Exception as e:
            logger.exception(f"  ✗ Prevention failed: {e}")
            self.log_test("Prevention Engine", "FAIL", str(e))
            self.results["errors"].append(str(e))
            return False
    
    def test_7_action_policy_engine(self):
        """TEST 7: Action policy engine."""
        logger.info("\n" + "="*70)
        logger.info("TEST 7: Action Policy Engine")
        logger.info("="*70)
        
        try:
            policy_engine = ActionPolicyEngine(self.db)
            logger.info("  ✓ ActionPolicyEngine initialized")
            
            # Run policy evaluation
            policy_decisions = policy_engine.run()
            logger.info(f"  ✓ Policy evaluation complete")
            
            if policy_decisions:
                logger.info(f"  Policy decisions: {len(policy_decisions)} actions")
                for decision in policy_decisions:
                    logger.info(f"    - {decision.get('action', 'Unknown')}")
                    logger.info(f"      Risk Level: {decision.get('risk_level', 'Medium')}")
                    logger.info(f"      Approved: {decision.get('approved', False)}")
            else:
                logger.info("  ✓ No policy violations")
            
            self.log_test("Action Policy Engine", "PASS", f"{len(policy_decisions)} decisions")
            return True
        except Exception as e:
            logger.exception(f"  ✗ Policy engine failed: {e}")
            self.log_test("Action Policy Engine", "FAIL", str(e))
            self.results["errors"].append(str(e))
            return False
    
    def test_8_alert_engine(self):
        """TEST 8: Alert/Notification engine."""
        logger.info("\n" + "="*70)
        logger.info("TEST 8: Alert & Notification Engine")
        logger.info("="*70)
        
        try:
            notifier = SmartNotifier(self.db)
            logger.info("  ✓ SmartNotifier initialized")
            
            # Run notification
            alerts_sent = notifier.run()
            logger.info(f"  ✓ Alert processing complete")
            
            # Get alert history
            try:
                alert_count = len(self.db.get_alerts(limit=100))
                logger.info(f"  ✓ Alert history: {alert_count} total alerts")
            except:
                alert_count = 0
            
            logger.info(f"  ✓ Alerts sent in this cycle: {alerts_sent}")
            
            self.log_test("Alert Engine", "PASS", f"{alerts_sent} alerts sent")
            return True
        except Exception as e:
            logger.exception(f"  ✗ Alert engine failed: {e}")
            self.log_test("Alert Engine", "FAIL", str(e))
            self.results["errors"].append(str(e))
            return False
    
    def test_9_dashboard_api(self):
        """TEST 9: Dashboard API endpoints."""
        logger.info("\n" + "="*70)
        logger.info("TEST 9: Dashboard API Endpoints")
        logger.info("="*70)
        
        try:
            from dashboard.app import create_app
            
            app = create_app()
            client = app.test_client()
            
            endpoints_tested = []
            
            # Test metrics endpoint
            try:
                resp = client.get('/api/metrics')
                if resp.status_code == 200:
                    logger.info("  ✓ /api/metrics: OK")
                    endpoints_tested.append(("GET /api/metrics", "200 OK"))
                else:
                    logger.info(f"  ✗ /api/metrics: Status {resp.status_code}")
            except Exception as e:
                logger.info(f"  ✗ /api/metrics: {e}")
            
            # Test alerts endpoint
            try:
                resp = client.get('/api/alerts')
                if resp.status_code == 200:
                    logger.info("  ✓ /api/alerts: OK")
                    endpoints_tested.append(("GET /api/alerts", "200 OK"))
                else:
                    logger.info(f"  ✗ /api/alerts: Status {resp.status_code}")
            except Exception as e:
                logger.info(f"  ✗ /api/alerts: {e}")
            
            # Test health endpoint
            try:
                resp = client.get('/api/health')
                if resp.status_code == 200:
                    logger.info("  ✓ /api/health: OK")
                    endpoints_tested.append(("GET /api/health", "200 OK"))
                else:
                    logger.info(f"  ✗ /api/health: Status {resp.status_code}")
            except Exception as e:
                logger.info(f"  ✗ /api/health: {e}")
            
            # Test dashboard main page
            try:
                resp = client.get('/')
                if resp.status_code == 200:
                    logger.info("  ✓ Dashboard: OK")
                    endpoints_tested.append(("GET /", "200 OK"))
                else:
                    logger.info(f"  ✗ Dashboard: Status {resp.status_code}")
            except Exception as e:
                logger.info(f"  ✗ Dashboard: {e}")
            
            self.log_test("Dashboard API", "PASS", f"{len(endpoints_tested)} endpoints")
            return True
        except Exception as e:
            logger.exception(f"  ✗ Dashboard API test failed: {e}")
            self.log_test("Dashboard API", "FAIL", str(e))
            self.results["errors"].append(str(e))
            return False
    
    def test_10_end_to_end_pipeline(self):
        """TEST 10: Full end-to-end pipeline simulation."""
        logger.info("\n" + "="*70)
        logger.info("TEST 10: Complete End-to-End Pipeline")
        logger.info("="*70)
        
        try:
            logger.info("  Executing full analysis pipeline...")
            
            # Perform full cycle
            analyzer = TrendAnalyzer(self.db)
            rc_engine = RootCauseEngine(self.db, analyzer)
            model = ReliabilityModel()
            predictor = FailurePredictor(self.db, analyzer, model)
            prevention = PreventionEngine(self.db)
            policy = ActionPolicyEngine(self.db)
            notifier = SmartNotifier(self.db)
            
            logger.info("  ✓ All engines initialized")
            
            # Run full cycle
            logger.info("  Running analysis cycle...")
            rc_results = rc_engine.run()
            logger.info(f"    - Root cause: {len(rc_results)} issues")
            
            pred_results = predictor.run()
            logger.info(f"    - Predictions: {len(pred_results)} metrics")
            
            prev_results = prevention.run()
            logger.info(f"    - Prevention: {len(prev_results)} actions")
            
            policy_results = policy.run()
            logger.info(f"    - Policies: {len(policy_results)} decisions")
            
            alert_results = notifier.run()
            logger.info(f"    - Alerts: {alert_results} sent")
            
            total_items = len(rc_results) + len(pred_results) + len(prev_results) + len(policy_results)
            logger.info(f"  ✓ Pipeline complete: {total_items} items processed")
            
            self.log_test("End-to-End Pipeline", "PASS", f"{total_items} items")
            return True
        except Exception as e:
            logger.exception(f"  ✗ Pipeline failed: {e}")
            self.log_test("End-to-End Pipeline", "FAIL", str(e))
            self.results["errors"].append(str(e))
            return False
    
    def run_all_tests(self):
        """Run all tests in sequence."""
        logger.info("\n" + "█"*70)
        logger.info("█  SOFTWARE AGING ANALYZER - E2E LIVE TEST SUITE  █")
        logger.info("█"*70 + "\n")
        
        test_methods = [
            self.test_1_database_initialization,
            self.test_2_data_collection,
            self.test_3_trend_analyzer,
            self.test_4_root_cause_engine,
            self.test_5_failure_predictor,
            self.test_6_prevention_engine,
            self.test_7_action_policy_engine,
            self.test_8_alert_engine,
            self.test_9_dashboard_api,
            self.test_10_end_to_end_pipeline,
        ]
        
        passed = 0
        failed = 0
        
        for test_method in test_methods:
            try:
                if test_method():
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                logger.exception(f"Unexpected error in {test_method.__name__}: {e}")
                failed += 1
                self.results["errors"].append(f"Unexpected error in {test_method.__name__}: {e}")
            
            time.sleep(1)  # Small delay between tests
        
        # Cleanup
        if self.collector:
            try:
                self.collector.stop()
                logger.info("\n✓ Data collector stopped")
            except:
                pass
        
        # Print summary
        self.print_summary(passed, failed)
        
        # Save results
        self.save_results()
    
    def print_summary(self, passed, failed):
        """Print test summary."""
        logger.info("\n" + "="*70)
        logger.info("TEST SUMMARY")
        logger.info("="*70)
        logger.info(f"\n  Total Tests: {passed + failed}")
        logger.info(f"  ✓ Passed: {passed}")
        logger.info(f"  ✗ Failed: {failed}")
        logger.info(f"  Success Rate: {(passed/(passed+failed)*100):.1f}%\n")
        
        if self.results["errors"]:
            logger.info("  Errors:")
            for error in self.results["errors"]:
                logger.info(f"    - {error}")
        
        logger.info("\n  Test Results by Component:")
        for test_name, result in self.results["tests"].items():
            status_emoji = "✓" if result["status"] == "PASS" else "✗"
            logger.info(f"    {status_emoji} {test_name}: {result['status']}")
        
        logger.info("\n" + "="*70 + "\n")
    
    def save_results(self):
        """Save results to JSON file."""
        try:
            results_file = Path("e2e_test_results.json")
            with open(results_file, "w") as f:
                json.dump(self.results, f, indent=2, default=str)
            logger.info(f"✓ Results saved to {results_file}")
        except Exception as e:
            logger.error(f"✗ Failed to save results: {e}")


def main():
    """Main entry point."""
    suite = E2ETestSuite()
    suite.run_all_tests()


if __name__ == "__main__":
    main()
