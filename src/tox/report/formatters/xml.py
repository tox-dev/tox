"""XML report formatter (JUnit XML style)."""

from __future__ import annotations

import locale
from pathlib import Path
from typing import TYPE_CHECKING
from xml.etree import ElementTree as ET

from tox.report.formatter import ReportFormatter

if TYPE_CHECKING:
    from tox.journal.main import Journal


class XmlFormatter(ReportFormatter):
    """JUnit XML format report formatter."""

    @property
    def name(self) -> str:
        return "xml"

    @property
    def file_extension(self) -> str:
        return ".xml"

    def format(self, journal: Journal, output_path: Path | None = None) -> str | None:
        content = journal.content

        # Create root testsuites element
        testsuites = ET.Element("testsuites")

        # Add metadata
        if "toxversion" in content:
            testsuites.set("toxversion", str(content["toxversion"]))
        if "platform" in content:
            testsuites.set("platform", str(content["platform"]))
        if "host" in content:
            testsuites.set("host", str(content["host"]))

        total_tests = 0
        total_failures = 0
        total_errors = 0
        total_time = 0.0

        # Process each test environment
        testenvs = content.get("testenvs", {})
        for env_name, env_data in testenvs.items():
            testsuite = ET.SubElement(testsuites, "testsuite")
            testsuite.set("name", env_name)

            env_tests = 0
            env_failures = 0
            env_errors = 0
            env_time = 0.0

            # Process test results from journal
            test_results = env_data.get("test", [])
            setup_results = env_data.get("setup", [])

            # Process setup commands
            for setup in setup_results:
                testcase = ET.SubElement(testsuite, "testcase")
                testcase.set("classname", env_name)
                testcase.set("name", f"setup:{setup.get('run_id', 'unknown')}")
                elapsed = float(setup.get("elapsed", 0.0))
                testcase.set("time", f"{elapsed:.3f}")
                env_time += elapsed
                env_tests += 1

                if setup.get("retcode", 0) != 0:
                    failure = ET.SubElement(testcase, "failure")
                    failure.set("message", f"Setup command failed with exit code {setup.get('retcode')}")
                    failure.text = setup.get("err", "")
                    env_errors += 1

            # Process test commands
            for test in test_results:
                testcase = ET.SubElement(testsuite, "testcase")
                testcase.set("classname", env_name)
                testcase.set("name", test.get("command", test.get("run_id", "unknown")))
                elapsed = float(test.get("elapsed", 0.0))
                testcase.set("time", f"{elapsed:.3f}")
                env_time += elapsed
                env_tests += 1

                retcode = test.get("retcode", 0)
                if retcode != 0:
                    failure = ET.SubElement(testcase, "failure")
                    failure.set("message", f"Test command failed with exit code {retcode}")
                    failure.text = test.get("err", test.get("output", ""))
                    env_failures += 1

            # Check result from journal
            result = env_data.get("result", {})
            if not result.get("success", True) and env_failures == 0:
                # If marked as failed but no failures tracked, add error
                env_errors += 1

            testsuite.set("tests", str(env_tests))
            testsuite.set("failures", str(env_failures))
            testsuite.set("errors", str(env_errors))
            testsuite.set("time", f"{env_time:.3f}")

            total_tests += env_tests
            total_failures += env_failures
            total_errors += env_errors
            total_time += env_time

        testsuites.set("tests", str(total_tests))
        testsuites.set("failures", str(total_failures))
        testsuites.set("errors", str(total_errors))
        testsuites.set("time", f"{total_time:.3f}")

        # Convert to XML string
        try:
            ET.indent(testsuites, space="  ")  # Python 3.9+
        except AttributeError:
            pass  # ElementTree.indent not available in older Python versions
        xml_content = ET.tostring(testsuites, encoding="unicode", xml_declaration=True)

        if output_path is not None:
            with Path(output_path).open("w", encoding=locale.getpreferredencoding(do_setlocale=False)) as file_handler:
                file_handler.write(xml_content)
            return None

        return xml_content


__all__ = ("XmlFormatter",)
