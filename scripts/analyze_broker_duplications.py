#!/usr/bin/env python3
"""
Migration script to refactor Alpaca broker code and remove duplications
This script performs the cleanup and reorganization safely
"""

import shutil
from pathlib import Path
from typing import List, Dict
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


class BrokerCodeRefactorMigration:
    """Handles the refactoring of broker code to remove duplications"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.alpaca_path = project_root / "src" / "brokers" / "alpaca"
        self.backup_path = project_root / "backup_before_refactor"

    def create_backup(self):
        """Create backup of current alpaca broker code"""
        logger.info("Creating backup of current Alpaca broker code...")

        if self.backup_path.exists():
            shutil.rmtree(self.backup_path)

        shutil.copytree(self.alpaca_path, self.backup_path / "alpaca")
        logger.info(f"Backup created at: {self.backup_path}")

    def analyze_duplications(self) -> Dict[str, List[str]]:
        """Analyze and report code duplications"""
        logger.info("Analyzing code duplications...")

        duplications = {
            "http_requests": [],
            "model_conversions": [],
            "error_handling": [],
            "data_structures": [],
            "utility_functions": [],
        }

        # Find files with HTTP request patterns
        for py_file in self.alpaca_path.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8")

            if "from ..http.requests import Requests" in content:
                duplications["http_requests"].append(
                    str(py_file.relative_to(self.project_root))
                )

            if "class_from_dict" in content:
                duplications["model_conversions"].append(
                    str(py_file.relative_to(self.project_root))
                )

            if "Exception" in content and "raise" in content:
                duplications["error_handling"].append(
                    str(py_file.relative_to(self.project_root))
                )

            if "@dataclass" in content:
                duplications["data_structures"].append(
                    str(py_file.relative_to(self.project_root))
                )

        # Report findings
        logger.info("Duplication Analysis Results:")
        for category, files in duplications.items():
            if files:
                logger.info(f"  {category}: {len(files)} files")
                for file in files[:3]:  # Show first 3 files
                    logger.info(f"    - {file}")
                if len(files) > 3:
                    logger.info(f"    ... and {len(files) - 3} more")

        return duplications

    def identify_movable_code(self) -> Dict[str, List[str]]:
        """Identify code that can be moved out of broker-specific folder"""
        logger.info("Identifying code that can be moved to common infrastructure...")

        movable = {
            "http_client": [
                "src/brokers/alpaca/api/http/requests.py",
                "src/brokers/alpaca/api/utils/session.py",
            ],
            "model_utilities": ["src/brokers/alpaca/api/models/model_utils.py"],
            "common_patterns": [
                # Error handling patterns
                # Data conversion patterns
                # Authentication patterns
            ],
            "data_fetching": [
                "src/brokers/alpaca/api/stock/screener.py",  # Has generic screening logic
                "src/brokers/alpaca/api/stock/predictor.py",  # Has generic prediction logic
            ],
            "testing_utilities": [
                # Common test patterns that could be reused
            ],
        }

        return movable

    def generate_refactor_plan(self) -> Dict[str, any]:
        """Generate detailed refactoring plan"""
        logger.info("Generating refactoring plan...")

        plan = {
            "phase_1_infrastructure": {
                "description": "Move common infrastructure to shared modules",
                "actions": [
                    "Move HTTP client logic to src/infra/http_client.py ✓",
                    "Move model utilities to src/infra/model_utils.py ✓",
                    "Create common broker utilities in src/brokers/common/ ✓",
                    "Update import statements in affected files",
                ],
            },
            "phase_2_simplify_alpaca": {
                "description": "Simplify Alpaca broker implementation",
                "actions": [
                    "Remove duplicated HTTP request code",
                    "Use common model conversion utilities",
                    "Simplify model classes to use common patterns",
                    "Remove redundant error handling",
                ],
            },
            "phase_3_generic_extraction": {
                "description": "Extract generic functionality",
                "actions": [
                    "Move stock screening logic to core/",
                    "Move prediction logic to ml/",
                    "Create generic data fetching interfaces",
                    "Standardize response formats",
                ],
            },
            "phase_4_cleanup": {
                "description": "Clean up and optimize",
                "actions": [
                    "Remove unused imports",
                    "Consolidate similar functions",
                    "Update tests to use new structure",
                    "Update documentation",
                ],
            },
        }

        return plan

    def calculate_reduction_potential(self) -> Dict[str, int]:
        """Calculate potential code reduction"""
        logger.info("Calculating potential code reduction...")

        # Count lines in various categories
        current_lines = self._count_lines_in_directory(self.alpaca_path)

        estimated_reduction = {
            "http_requests": 150,  # Requests class + duplicated patterns
            "model_conversions": 200,  # Repeated conversion logic
            "error_handling": 100,  # Duplicated error handling
            "utility_functions": 50,  # Scattered utility functions
            "redundant_imports": 30,  # Cleanup of imports
        }

        total_current = current_lines
        total_reduction = sum(estimated_reduction.values())
        percentage_reduction = (total_reduction / total_current) * 100

        logger.info(f"Current Alpaca broker code: {total_current} lines")
        logger.info(
            f"Estimated reduction: {total_reduction} lines ({percentage_reduction:.1f}%)"
        )

        return {
            "current_lines": total_current,
            "potential_reduction": total_reduction,
            "percentage_reduction": percentage_reduction,
            "breakdown": estimated_reduction,
        }

    def _count_lines_in_directory(self, directory: Path) -> int:
        """Count total lines of Python code in directory"""
        total_lines = 0
        for py_file in directory.rglob("*.py"):
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    lines = len(
                        [
                            line
                            for line in f
                            if line.strip() and not line.strip().startswith("#")
                        ]
                    )
                    total_lines += lines
            except Exception as e:
                logger.warning(f"Could not read {py_file}: {e}")
        return total_lines

    def suggest_new_structure(self) -> Dict[str, List[str]]:
        """Suggest new, cleaner structure"""
        logger.info("Suggesting new structure...")

        new_structure = {
            "src/infra/": [
                "http_client.py - Common HTTP client with retry logic ✓",
                "model_utils.py - Common data model utilities ✓",
                "broker_utils.py - Common broker utilities",
                "data_validators.py - Common validation logic",
            ],
            "src/brokers/common/": [
                "__init__.py - Enhanced broker interfaces ✓",
                "mixins.py - Common functionality mixins",
                "exceptions.py - Common broker exceptions",
                "protocols.py - Broker capability protocols",
            ],
            "src/brokers/alpaca/": [
                "adapter.py - Simplified main adapter",
                "models.py - Alpaca-specific models only",
                "endpoints.py - Alpaca API endpoints",
                "config.yaml - Alpaca configuration",
            ],
            "src/core/data_sources/": [
                "base.py - Abstract data source",
                "stock_screener.py - Generic screening (moved from broker)",
                "market_data.py - Generic market data fetching",
            ],
            "src/ml/predictors/": [
                "base.py - Abstract predictor interface",
                "technical_analysis.py - TA predictions (extracted from broker)",
            ],
        }

        return new_structure

    def run_analysis(self):
        """Run complete analysis and generate report"""
        logger.info("=" * 60)
        logger.info("ALPACA BROKER CODE ANALYSIS & REFACTORING PLAN")
        logger.info("=" * 60)

        # Create backup
        self.create_backup()

        # Analyze duplications
        duplications = self.analyze_duplications()

        # Identify movable code
        movable = self.identify_movable_code()

        # Generate plan
        plan = self.generate_refactor_plan()

        # Calculate reduction
        reduction = self.calculate_reduction_potential()

        # Suggest structure
        new_structure = self.suggest_new_structure()

        # Generate summary report
        self._generate_report(duplications, movable, plan, reduction, new_structure)

    def _generate_report(self, duplications, movable, plan, reduction, new_structure):
        """Generate comprehensive report"""

        report_file = self.project_root / "BROKER_REFACTOR_ANALYSIS.md"

        with open(report_file, "w", encoding="utf-8") as f:
            f.write("# Alpaca Broker Code Refactoring Analysis\n\n")

            f.write("## 📊 Current State Analysis\n\n")
            f.write(f"- **Total lines of code**: {reduction['current_lines']}\n")
            f.write(
                f"- **Potential reduction**: {reduction['potential_reduction']} lines ({reduction['percentage_reduction']:.1f}%)\n\n"
            )

            f.write("## 🔍 Identified Duplications\n\n")
            for category, files in duplications.items():
                if files:
                    f.write(f"### {category.replace('_', ' ').title()}\n")
                    f.write(f"Found in {len(files)} files:\n")
                    for file in files:
                        f.write(f"- {file}\n")
                    f.write("\n")

            f.write("## 🎯 Refactoring Plan\n\n")
            for phase, details in plan.items():
                f.write(f"### {phase.replace('_', ' ').title()}\n")
                f.write(f"{details['description']}\n\n")
                for action in details["actions"]:
                    status = "✅" if "✓" in action else "⏳"
                    f.write(f"{status} {action}\n")
                f.write("\n")

            f.write("## 🏗️ Proposed New Structure\n\n")
            for directory, files in new_structure.items():
                f.write(f"### {directory}\n")
                for file in files:
                    status = "✅" if "✓" in file else "📝"
                    f.write(f"{status} {file}\n")
                f.write("\n")

            f.write("## 🎉 Expected Benefits\n\n")
            f.write("- **Reduced code duplication** - Eliminate repetitive patterns\n")
            f.write(
                "- **Improved maintainability** - Common utilities in shared modules\n"
            )
            f.write("- **Better testability** - Isolated, focused components\n")
            f.write(
                "- **Enhanced reusability** - Common code can be used by other brokers\n"
            )
            f.write("- **Cleaner architecture** - Separation of concerns\n")
            f.write(
                "- **Easier onboarding** - New broker implementations are simpler\n\n"
            )

            f.write("## 🚀 Next Steps\n\n")
            f.write("1. **Phase 1** ✅ - Infrastructure setup (completed)\n")
            f.write(
                "2. **Phase 2** - Refactor Alpaca adapter to use common utilities\n"
            )
            f.write("3. **Phase 3** - Extract generic functionality to core modules\n")
            f.write("4. **Phase 4** - Final cleanup and optimization\n")
            f.write("5. **Testing** - Comprehensive testing of refactored code\n")
            f.write("6. **Documentation** - Update documentation for new structure\n")

        logger.info(f"Report generated: {report_file}")
        logger.info(
            "Analysis complete! Review the report and backup before proceeding."
        )


def main():
    """Main entry point"""
    # Get project root
    script_path = Path(__file__)
    project_root = script_path.parent.parent

    # Run analysis
    migration = BrokerCodeRefactorMigration(project_root)
    migration.run_analysis()


if __name__ == "__main__":
    main()
