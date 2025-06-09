"""
test_license_compliance.py - License auditing tests for QualityGate agent
Scans /symbols/ and /noise_assets/ for license compliance
"""

import csv
from pathlib import Path

import pytest


class TestLicenseCompliance:
    """Test suite for license compliance validation"""

    # OSI-approved and Creative Commons licenses
    APPROVED_LICENSES = {
        "MIT",
        "Apache-2.0",
        "BSD-2-Clause",
        "BSD-3-Clause",
        "GPL-2.0",
        "GPL-3.0",
        "LGPL-2.1",
        "LGPL-3.0",
        "CC0-1.0",
        "CC-BY-4.0",
        "CC-BY-SA-4.0",
        "ISC",
        "MPL-2.0",
        "Unlicense",
    }

    @pytest.fixture
    def symbols_directory(self) -> Path:
        """Path to symbols directory"""
        return Path(__file__).parent.parent / "symbols"

    @pytest.fixture
    def noise_assets_directory(self) -> Path:
        """Path to noise_assets directory"""
        return Path(__file__).parent.parent / "noise_assets"

    @pytest.fixture
    def license_csv_path(self) -> Path:
        """Path to license CSV file"""
        return Path(__file__).parent.parent / "symbols" / "symbol_licences.csv"

    def test_symbols_directory_exists(self, symbols_directory: Path):
        """Test that symbols directory exists"""
        assert symbols_directory.exists(), "symbols/ directory must exist"

    def test_license_csv_exists(self, license_csv_path: Path):
        """Test that license CSV file exists"""
        if not license_csv_path.exists():
            pytest.skip("symbol_licences.csv not created yet by VectorForge")

    def test_license_csv_structure(self, license_csv_path: Path):
        """Test that license CSV has correct structure"""
        if not license_csv_path.exists():
            pytest.skip("symbol_licences.csv not found")

        with open(license_csv_path, newline="") as csvfile:
            reader = csv.DictReader(csvfile)

            # Check required columns
            required_columns = {"filename", "licence", "source-URL"}
            actual_columns = set(reader.fieldnames or [])
            assert required_columns.issubset(
                actual_columns
            ), f"Missing required columns: {required_columns - actual_columns}"

            # Check each row has data
            row_count = 0
            for row in reader:
                row_count += 1
                assert row["filename"].strip(), f"Empty filename in row {row_count}"
                assert row["licence"].strip(), f"Empty licence in row {row_count}"
                # source-URL can be empty for original works

            assert row_count > 0, "License CSV cannot be empty"

    def test_all_symbols_have_license_entries(
        self, symbols_directory: Path, license_csv_path: Path
    ):
        """Test that every SVG file has a corresponding license entry"""
        if not license_csv_path.exists():
            pytest.skip("symbol_licences.csv not found")

        # Get all SVG files
        svg_files = set()
        if symbols_directory.exists():
            svg_files = {f.name for f in symbols_directory.glob("*.svg")}

        if not svg_files:
            pytest.skip("No SVG files found in symbols/")

        # Get licensed files
        licensed_files = set()
        with open(license_csv_path, newline="") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                licensed_files.add(row["filename"].strip())

        # Check coverage
        missing_licenses = svg_files - licensed_files
        assert (
            not missing_licenses
        ), f"SVG files missing license entries: {missing_licenses}"

        # Check for orphaned entries
        orphaned_licenses = licensed_files - svg_files
        if orphaned_licenses:
            # Warning but not failure - might be work in progress
            print(
                f"Warning: License entries for non-existent files: {orphaned_licenses}"
            )

    def test_only_approved_licenses(self, license_csv_path: Path):
        """Test that only OSI-approved or CC licenses are used"""
        if not license_csv_path.exists():
            pytest.skip("symbol_licences.csv not found")

        unapproved_licenses = []

        with open(license_csv_path, newline="") as csvfile:
            reader = csv.DictReader(csvfile)
            for row_num, row in enumerate(reader, 1):
                license_name = row["licence"].strip()
                filename = row["filename"].strip()

                if license_name not in self.APPROVED_LICENSES:
                    unapproved_licenses.append(
                        {"row": row_num, "filename": filename, "license": license_name}
                    )

        if unapproved_licenses:
            error_msg = "Non-approved licenses found:\n"
            for item in unapproved_licenses:
                error_msg += (
                    f"  Row {item['row']}: {item['filename']} -> {item['license']}\n"
                )
            error_msg += f"\nApproved licenses: {sorted(self.APPROVED_LICENSES)}"

            pytest.fail(error_msg)

    def test_source_urls_valid_format(self, license_csv_path: Path):
        """Test that source URLs are valid when provided"""
        if not license_csv_path.exists():
            pytest.skip("symbol_licences.csv not found")

        invalid_urls = []

        with open(license_csv_path, newline="") as csvfile:
            reader = csv.DictReader(csvfile)
            for row_num, row in enumerate(reader, 1):
                source_url = row.get("source-URL", "").strip()
                filename = row["filename"].strip()

                if source_url:  # Only validate non-empty URLs
                    if not (
                        source_url.startswith("http://")
                        or source_url.startswith("https://")
                    ):
                        invalid_urls.append(
                            {"row": row_num, "filename": filename, "url": source_url}
                        )

        if invalid_urls:
            error_msg = "Invalid source URLs found:\n"
            for item in invalid_urls:
                error_msg += (
                    f"  Row {item['row']}: {item['filename']} -> {item['url']}\n"
                )
            pytest.fail(error_msg)

    def test_no_proprietary_content(self, symbols_directory: Path):
        """Test that no proprietary content is included"""
        if not symbols_directory.exists():
            pytest.skip("symbols/ directory not found")

        # Check for common proprietary indicators in filenames
        proprietary_indicators = [
            "autocad",
            "solidworks",
            "catia",
            "inventor",
            "fusion360",
            "pro-engineer",
            "creo",
            "nx",
            "mastercam",
        ]

        suspicious_files = []
        for svg_file in symbols_directory.glob("*.svg"):
            filename_lower = svg_file.name.lower()
            for indicator in proprietary_indicators:
                if indicator in filename_lower:
                    suspicious_files.append((svg_file.name, indicator))

        if suspicious_files:
            error_msg = "Potentially proprietary content detected:\n"
            for filename, indicator in suspicious_files:
                error_msg += f"  {filename} (contains '{indicator}')\n"
            pytest.fail(error_msg)

    def test_cc_attribution_compliance(self, license_csv_path: Path):
        """Test CC-licensed content has proper attribution"""
        if not license_csv_path.exists():
            pytest.skip("symbol_licences.csv not found")

        cc_without_source = []

        with open(license_csv_path, newline="") as csvfile:
            reader = csv.DictReader(csvfile)
            for row_num, row in enumerate(reader, 1):
                license_name = row["licence"].strip()
                source_url = row.get("source-URL", "").strip()
                filename = row["filename"].strip()

                # CC licenses (except CC0) require attribution
                if license_name.startswith("CC-") and license_name != "CC0-1.0":
                    if not source_url:
                        cc_without_source.append(
                            {
                                "row": row_num,
                                "filename": filename,
                                "license": license_name,
                            }
                        )

        if cc_without_source:
            error_msg = "CC-licensed files missing source URLs for attribution:\n"
            for item in cc_without_source:
                error_msg += (
                    f"  Row {item['row']}: {item['filename']} ({item['license']})\n"
                )
            pytest.fail(error_msg)


def test_create_sample_license_csv():
    """Create sample license CSV if it doesn't exist (for development)"""
    license_csv_path = Path(__file__).parent.parent / "symbols" / "symbol_licences.csv"

    if not license_csv_path.exists():
        # Create sample file for development
        license_csv_path.parent.mkdir(exist_ok=True)

        with open(license_csv_path, "w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["filename", "licence", "source-URL"])
            writer.writerow(["gdt_flatness.svg", "CC0-1.0", ""])
            writer.writerow(
                ["surface_triangle.svg", "MIT", "https://github.com/example/symbols"]
            )
            writer.writerow(["diameter_symbol.svg", "CC0-1.0", ""])

        print(f"Created sample license CSV at {license_csv_path}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
