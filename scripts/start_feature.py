#!/usr/bin/env python3
"""
Feature Generator Script
Creates a complete feature structure with boilerplate code

Usage:
    python scripts/generate_feature.py feature_name [--with-celery] [--with-templates]

Example:
    python scripts/generate_feature.py notifications --with-celery
"""

import argparse
import sys
from pathlib import Path


def to_snake_case(name: str) -> str:
    """Convert string to snake_case"""
    return name.lower().replace("-", "_").replace(" ", "_")


def to_pascal_case(name: str) -> str:
    """Convert string to PascalCase"""
    return "".join(
        word.capitalize() for word in name.replace("-", "_").replace(" ", "_").split("_")
    )


def to_title_case(name: str) -> str:
    """Convert string to Title Case"""
    return " ".join(word.capitalize() for word in name.replace("-", " ").replace("_", " ").split())


class FeatureGenerator:
    def __init__(self, feature_name: str, with_celery: bool = False):
        self.feature_name = to_snake_case(feature_name)
        self.feature_pascal = to_pascal_case(feature_name)
        self.feature_title = to_title_case(feature_name)
        self.with_celery = with_celery

        # Base paths
        self.base_path = Path(f"app/features/{self.feature_name}")
        self.models_path = self.base_path / "models"
        self.routes_path = self.base_path / "routes"
        self.schemas_path = self.base_path / "schemas"
        self.services_path = self.base_path / "services"
        self.utils_path = self.base_path / "utils"

        if with_celery:
            self.workers_path = self.base_path / "workers"

    def create_directories(self):
        """Create all necessary directories"""
        print(f"📁 Creating directory structure for '{self.feature_name}'...")

        directories = [
            self.base_path,
            self.models_path,
            self.routes_path,
            self.schemas_path,
            self.services_path,
            self.utils_path,
        ]

        if self.with_celery:
            directories.append(self.workers_path)

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            print(f"  ✓ Created {directory}")

    def create_init_files(self):
        """Create __init__.py files"""
        print("\n📝 Creating __init__.py files...")

        init_files = [
            self.base_path / "__init__.py",
            self.models_path / "__init__.py",
            self.routes_path / "__init__.py",
            self.schemas_path / "__init__.py",
            self.services_path / "__init__.py",
            self.utils_path / "__init__.py",
        ]

        if self.with_celery:
            init_files.append(self.workers_path / "__init__.py")

        for init_file in init_files:
            init_file.write_text('"""' + f"{init_file.parent.name.capitalize()} module" + '"""\n')
            print(f"  ✓ Created {init_file}")

    def generate(self):
        """Generate all feature files"""
        if self.base_path.exists():
            print(f"❌ Error: Feature '{self.feature_name}' already exists at {self.base_path}")
            sys.exit(1)

        print(f"\n🚀 Generating feature: {self.feature_name}")
        print("=" * 60)

        self.create_directories()
        self.create_init_files()

        print("\n" + "=" * 60)
        print(f"✅ Feature '{self.feature_name}' generated successfully!")
        print(f"\n📂 Location: {self.base_path}")
        print("\n📋 Next steps:")
        print("   1. Review the generated files")
        print("   2. Customize the models, schemas, and services")
        print("   3. Create and run the migration")
        print("   4. Register the routes in v1.py")
        print("   5. Register the models in alembic")
        print("=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Generate a complete FastAPI feature with boilerplate code"
    )
    parser.add_argument(
        "feature_name", type=str, help="Name of the feature (e.g., notifications, products, orders)"
    )
    parser.add_argument("--with-celery", action="store_true", help="Include Celery worker files")

    args = parser.parse_args()

    if not Path("app").exists():
        print("❌ Error: Must run from project root directory (where 'app' folder exists)")
        sys.exit(1)

    generator = FeatureGenerator(
        feature_name=args.feature_name,
        with_celery=args.with_celery,
    )

    generator.generate()


if __name__ == "__main__":
    main()
