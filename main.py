"""
Dealbaku Supplier Finder.

    python main.py --product "dog beds" --location "Guangdong" --moq 500 \
        --platform gold_supplier --1688-key sk_1688_xxx --nvidia-key nvapi_xxx

Keys can also come from .env (ALIBABA_1688_API_KEY, NVIDIA_API_KEY).
If the 1688 API fails you are prompted for a JSON/CSV export instead;
--suppliers-file skips the API and uses that file directly.
"""

import argparse
import logging
import sys
from datetime import date

from reports.generator import generate_report
from suppliers.analysis import analyze_with_glm5
from suppliers.distribution import analyze_distribution, format_distribution
from suppliers.extraction import extract_complete_contact_data
from suppliers.ranking import rank_suppliers_by_percentile
from suppliers.search_1688 import (NoSuppliersFound, SearchAPIError, filter_raw_records,
                                   load_suppliers_file, search_1688_with_constraints)
from utils import config

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("dealbaku")


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Dealbaku Supplier Finder (1688 + GLM-5.3)")
    p.add_argument("--product", required=True, help='Product category, e.g. "dog beds"')
    p.add_argument("--location", required=True, help='Province or city, e.g. "Guangdong"')
    p.add_argument("--moq", type=int, required=True, help="Maximum acceptable MOQ (units)")
    p.add_argument("--platform", default="any",
                   help="gold_supplier | verified_badge | any (default: any)")
    p.add_argument("--1688-key", dest="alibaba_key", help="1688 API key (or ALIBABA_1688_API_KEY)")
    p.add_argument("--nvidia-key", dest="nvidia_key", help="NVIDIA API key (or NVIDIA_API_KEY)")
    p.add_argument("--suppliers-file",
                   help="Skip the 1688 API and load suppliers from this JSON/CSV file")
    p.add_argument("--output-dir", default=".", help="Where to save the report (default: .)")
    p.add_argument("--no-scrape", action="store_true",
                   help="Don't fetch store pages to fill missing contact details")
    p.add_argument("--skip-glm", action="store_true", help="Skip the GLM-5.3 analysis step")
    p.add_argument("-v", "--verbose", action="store_true", help="Debug logging")
    args = p.parse_args(argv)
    if args.moq <= 0:
        p.error("--moq must be a positive number of units")
    try:
        args.platform = config.normalize_platform_req(args.platform)
    except ValueError as exc:
        p.error(str(exc))
    return args


def manual_fallback(args):
    """Ask for a supplier export when the API is unavailable."""
    print("\nManual fallback: export suppliers from 1688 (JSON or CSV) and give the path.")
    if not sys.stdin.isatty():
        print("Not running interactively. Re-run with --suppliers-file <path>.")
        return None
    path = input("Path to supplier file (blank to quit): ").strip()
    if not path:
        return None
    return filter_raw_records(load_suppliers_file(path), args.location, args.moq,
                              args.platform), path


def find_suppliers(args, alibaba_key):
    """Return (suppliers, data_source) or (None, None) if the user gave up."""
    if args.suppliers_file:
        print(f"Loading suppliers from {args.suppliers_file} (1688 API skipped)")
        raw = load_suppliers_file(args.suppliers_file)
        return filter_raw_records(raw, args.location, args.moq, args.platform), \
            f"file: {args.suppliers_file}"
    try:
        return search_1688_with_constraints(args.product, args.location, args.moq,
                                            args.platform, alibaba_key), "1688 API"
    except SearchAPIError:
        fallback = manual_fallback(args)
        if fallback is None:
            return None, None
        suppliers, path = fallback
        return suppliers, f"file: {path}"


def run(argv=None) -> int:
    args = parse_args(argv)
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    keys = config.resolve_api_keys(args.alibaba_key, args.nvidia_key)
    if not args.skip_glm and not keys.nvidia:
        print("Missing NVIDIA API key: pass --nvidia-key, set NVIDIA_API_KEY, or use --skip-glm.")
        return 2

    # STEP 1
    try:
        suppliers, data_source = find_suppliers(args, keys.alibaba_1688)
    except NoSuppliersFound as exc:
        logger.info("%s", exc)
        return 1
    except (FileNotFoundError, ValueError) as exc:
        print(f"✗ {exc}")
        return 1
    if suppliers is None:
        return 1

    # STEP 2
    print("\nAnalyzing distribution...")
    distribution = analyze_distribution(suppliers)
    print(format_distribution(distribution))

    # STEP 3
    print("\nRanking by percentile...")
    top_10 = rank_suppliers_by_percentile(suppliers, distribution)
    print(f"Top {len(top_10)} ranked suppliers identified")

    # STEP 4
    print("\nExtracting contact data...")
    top_10 = extract_complete_contact_data(top_10, scrape=not args.no_scrape)

    # STEP 5
    top_5 = top_10[:config.TOP_ANALYZED]
    print()
    if args.skip_glm:
        print("Skipping GLM-5.3 analysis (--skip-glm)")
    else:
        analyze_with_glm5(top_5, args.product, keys.nvidia)

    # STEP 6
    print("\nGenerating report...")
    all_ranked = sorted(suppliers, key=lambda s: s["rank"])
    generate_report(
        top_5, distribution, suppliers.total_found,
        context={"product": args.product, "location": args.location, "moq": args.moq,
                 "platform": args.platform, "search_date": date.today().isoformat(),
                 "data_source": data_source},
        top_10=top_10, all_suppliers=all_ranked, output_dir=args.output_dir,
    )
    return 0


if __name__ == "__main__":
    sys.exit(run())
