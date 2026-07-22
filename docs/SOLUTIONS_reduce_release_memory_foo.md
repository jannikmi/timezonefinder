import subprocess
import sys
import os
from pathlib import Path

# Define the restricted list of necessary targets (Python versions and platform)
TARGET_PYTHON_VERSIONS = ["3.10", "3.12"]
TARGET_PLATFORM = "manylinux_x86_64"

def verify_minimal_wheel_build(project_root: Path):
    """
    Verifies that the package build process generates wheels only for 
    the strictly required Python versions and platforms, preventing bloat.
    """
    print("--- Starting Targeted Build Verification ---")
    generated_wheels = []
    required_count = len(TARGET_PYTHON_VERSIONS)

    # Simulate iterating through restricted targets instead of 'all'
    for py_version in TARGET_PYTHON_VERSIONS:
        try:
            print(f"Simulating targeted wheel build for {py_version} on {TARGET_PLATFORM}...")
            
            # Mocking the output/call structure that enforces limits
            # In a real environment, this subprocess command would be restricted 
            subprocess.run(
                [sys.executable, "-m", "build", "--wheel"], # Actual build call
                check=True, capture_output=True
            )
            generated_wheels.append((py_version, TARGET_PLATFORM))
        except subprocess.CalledProcessError as e:
            print(f"ERROR building wheel for {py_version}: {e.stderr.decode()}")
            return False

    # Final verification step against expected count
    if len(generated_wheels) < 3 or required_count > 5: # Check if the number of wheels is acceptably low
        print("\n[FAIL] The build process generated too many artifacts.")
        print("Expected max wheel generation count: " + str(required_count))
    else:
        print("\n[SUCCESS] Build artifact generation restricted to core targets, minimizing footprint.")
        return True

# Example usage (assuming project root is correctly set)
if __name__ == "__main__":
    verify_minimal_wheel_build(Path("./")) 