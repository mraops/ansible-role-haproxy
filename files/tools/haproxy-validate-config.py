#!/usr/bin/env python3

import argparse
import os
import shutil
import subprocess
import sys
import tempfile


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate HAProxy main config together with conf.d directory."
    )
    parser.add_argument("--main-config", required=True, help="Path to main haproxy.cfg to validate.")
    parser.add_argument("--conf-dir", required=True, help="Existing conf.d directory path.")
    parser.add_argument(
        "--candidate-config",
        help="Temporary candidate config file that should replace one file in conf.d.",
    )
    parser.add_argument(
        "--candidate-name",
        help="Target filename inside conf.d for the candidate config.",
    )
    return parser.parse_args()


def copy_conf_tree(source_dir: str, target_dir: str, candidate_config: str, candidate_name: str) -> None:
    if os.path.isdir(source_dir):
        for entry in os.listdir(source_dir):
            source_path = os.path.join(source_dir, entry)
            if candidate_name and entry == candidate_name:
                continue
            if os.path.isfile(source_path):
                shutil.copy2(source_path, os.path.join(target_dir, entry))

    if candidate_config and candidate_name:
        shutil.copy2(candidate_config, os.path.join(target_dir, candidate_name))


def main() -> int:
    args = parse_args()

    if bool(args.candidate_config) != bool(args.candidate_name):
        print("ERROR: --candidate-config and --candidate-name must be used together", file=sys.stderr)
        return 1

    if not os.path.isfile(args.main_config):
        print(f"ERROR: main config not found: {args.main_config}", file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory(prefix="haproxy-conf-") as temp_dir:
        merged_conf_dir = os.path.join(temp_dir, "conf.d")
        os.makedirs(merged_conf_dir, exist_ok=True)
        copy_conf_tree(args.conf_dir, merged_conf_dir, args.candidate_config, args.candidate_name)

        result = subprocess.run(
            ["haproxy", "-f", args.main_config, "-f", merged_conf_dir, "-c"],
            check=False,
            capture_output=True,
            text=True,
        )

    if result.returncode != 0:
        sys.stderr.write(result.stdout)
        sys.stderr.write(result.stderr)

    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
