#!/usr/bin/env python3
import os
import time
import argparse
from dotenv import load_dotenv
from pathlib import Path
from requests import HTTPError

# load .env from likely locations
repo_root = Path(__file__).resolve().parents[1]
env_candidates = [repo_root / "backend" / ".env", repo_root / ".env", repo_root / "backend" / "app" / ".env"]
for p in env_candidates:
    if p.exists():
        load_dotenv(p)
        print("Loaded env from", p)
        break

API_KEY = os.getenv("LANGSMITH_API_KEY")
if not API_KEY:
    raise SystemExit("LANGSMITH_API_KEY missing in backend/.env or environment")

# import client after loading key
try:
    from langsmith import Client
except Exception as e:
    print("Failed to import langsmith Client:", e)
    raise

client = Client(api_key=API_KEY)

def try_list_runs(limit=50):
    """
    Try multiple list-like APIs depending on SDK shape.
    Some SDKs call a query endpoint that requires filters; catch that and let caller decide next steps.
    """
    # try common list variants
    try:
        runs = client.runs.list(limit=limit)
        print("Used client.runs.list")
        return list(runs)
    except Exception as e:
        # if we got a 400 complaining about missing filters, bubble that up
        errtxt = str(e)
        if "At least one of" in errtxt or "must be specified" in errtxt:
            raise
    try:
        if hasattr(client, "list_runs"):
            runs = client.list_runs(limit=limit)
            print("Used client.list_runs")
            return list(runs)
    except Exception:
        pass
    try:
        # some versions expose runs as a callable
        if hasattr(client, "runs") and callable(client.runs):
            runs = client.runs(limit=limit)
            print("Used client.runs(...) callable")
            return list(runs)
    except Exception:
        pass
    # fallback: try scanning attributes for something run-related
    for name in dir(client):
        if "run" in name.lower() and callable(getattr(client, name)):
            try:
                fn = getattr(client, name)
                runs = fn(limit=limit)
                print(f"Used client.{name} as fallback")
                return list(runs)
            except Exception:
                continue
    raise RuntimeError("No compatible list method found on langsmith Client. Client attrs: " + ", ".join([a for a in dir(client) if not a.startswith("_")]))

def try_query_runs_by_session_or_id(substr, limit=100):
    """
    Use runs.query(session=...) or similar if the SDK exposes it.
    """
    # prefer client.runs.query
    if hasattr(client, "runs") and hasattr(client.runs, "query"):
        try:
            # many SDKs accept session= or id=; we try both
            try:
                results = client.runs.query(session=substr, limit=limit)
                print("Used client.runs.query(session=...)")
                return list(results)
            except HTTPError as he:
                # if server rejected session= we try id=
                pass
            results = client.runs.query(id=substr, limit=limit)
            print("Used client.runs.query(id=...)")
            return list(results)
        except Exception as e:
            print("client.runs.query raised:", e)
            raise

    # fallback: client.get_run / client.get_runs / client.find_run variants
    if hasattr(client, "get_run"):
        try:
            r = client.get_run(substr)
            return [r]
        except Exception:
            pass
    # last resort: try listing then filtering locally
    try:
        runs = try_list_runs(limit=200)
        filtered = []
        for r in runs:
            name = getattr(r, "name", None) or (r.get("name") if isinstance(r, dict) else None) or getattr(r, "id", "")
            if substr in str(name) or substr in str(getattr(r, "id", "")):
                filtered.append(r)
        return filtered
    except Exception:
        pass

    return []

def find_run(substr, tries=6, wait=5):
    for i in range(tries):
        try:
            runs = try_list_runs(limit=100)
        except Exception as e:
            # if the list call failed because the server expects filters, fallback to query-based approach
            print("List method failed or returned 400 requiring filters; will try query by session/id. Error:", e)
            runs = try_query_runs_by_session_or_id(substr, limit=200)
            if not runs:
                print(f"Attempt {i+1}/{tries}: no runs found by query yet; sleeping {wait}s...")
                time.sleep(wait)
                continue
        # runs now contains objects or dicts
        for r in runs:
            name = getattr(r, "name", None) or (r.get("name") if isinstance(r, dict) else None)
            rid = getattr(r, "id", None) or (r.get("id") if isinstance(r, dict) else None)
            if (name and substr in str(name)) or (rid and substr in str(rid)):
                return r
        print(f"Attempt {i+1}/{tries}: run not found by name/id; sleeping {wait}s...")
        time.sleep(wait)
    return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--substr", "-s", required=True, help="substring of session/run name to search")
    parser.add_argument("--tries", "-t", type=int, default=6)
    args = parser.parse_args()

    print("Searching for runs matching:", args.substr)
    run = find_run(args.substr, tries=args.tries)
    if not run:
        print("No run found matching:", args.substr)
        # Print some client introspection to help debug
        print("Client attributes (sample):", [a for a in dir(client) if not a.startswith("_")][:200])
        raise SystemExit(1)

    print("Found run:", getattr(run, "id", None), getattr(run, "name", None))
    # try to fetch details if possible
    try:
        if hasattr(client, "runs") and hasattr(client.runs, "get"):
            full = client.runs.get(getattr(run, "id", getattr(run, "runId", None)))
            print("Fetched full run via client.runs.get()")
            print(full)
        elif hasattr(client, "get_run"):
            full = client.get_run(getattr(run, "id", getattr(run, "runId", None)))
            print("Fetched full run via client.get_run()")
            print(full)
        else:
            print("Run object (no get method available):", run)
    except Exception as e:
        print("Failed to fetch full run details:", e)
        print("Run object:", run)

    print("Done.")
