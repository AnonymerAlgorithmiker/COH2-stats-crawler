import argparse
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests
from db import init_db, insert_match, insert_match_players, get_match_count

# Human-friendly labels for Relic's matchtype_id codes (observed mapping)
MATCH_TYPE_MAP = {
    0: "mixed/custom",
    1: "1v1",
    2: "2v2",
    3: "3v3",
    4: "4v4",
    22: "automatch/custom",
}


def match_type_label(matchtype_id: Optional[int]) -> str:
    if matchtype_id is None:
        return "unknown"
    return MATCH_TYPE_MAP.get(matchtype_id, f"unknown({matchtype_id})")


RELIC_API_BASE_URL = "https://coh2-api.reliclink.com"


def fetch_json(url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    response = requests.get(url, params=params, timeout=15)
    response.raise_for_status()
    return response.json()


def resolve_relic_profile_id_from_steam(steam_id: str) -> int:
    url = f"{RELIC_API_BASE_URL}/community/leaderboard/getRecentMatchHistory"
    profile_name = f"/steam/{steam_id}"
    params = {
        "title": "coh2",
        "profile_names": json.dumps([profile_name]),
    }
    data = fetch_json(url, params=params)

    if data.get("result", {}).get("message") != "SUCCESS":
        raise RuntimeError(f"Failed to resolve Relic profile for Steam ID {steam_id}: {data.get('result')}" )

    profiles = data.get("profiles")
    if not profiles:
        raise RuntimeError(f"No profiles returned for Steam ID {steam_id}")

    return profiles[0]["profile_id"]


def fetch_match_history_by_relic_id(relic_profile_id: int) -> Dict[str, Any]:
    url = f"{RELIC_API_BASE_URL}/community/leaderboard/getRecentMatchHistoryByProfileId"
    params = {
        "title": "coh2",
        "profile_id": relic_profile_id,
    }
    data = fetch_json(url, params=params)

    if data.get("result", {}).get("message") != "SUCCESS":
        raise RuntimeError(f"Failed to fetch match history for Relic profile {relic_profile_id}: {data.get('result')}" )

    data.pop("result", None)
    return data


def format_datetime(timestamp: Optional[int]) -> str:
    if not timestamp:
        return "unknown"
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat()


def build_profile_map(profiles: List[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
    return {p["profile_id"]: p for p in profiles}


def print_match_summary(match: Dict[str, Any], index: int) -> None:
    started = format_datetime(match.get("startgametime"))
    mtype = match_type_label(match.get('matchtype_id'))
    print(f"[{index}] Match ID: {match.get('id')} | Map: {match.get('mapname')} | Type: {match.get('matchtype_id')} ({mtype}) | Started: {started} | Players: {len(match.get('matchhistoryreportresults', []))}")


def print_match_details(match: Dict[str, Any], profile_map: Dict[int, Dict[str, Any]]) -> None:
    print("\n=== Match Details ===")
    print(f"Match ID: {match.get('id')}")
    print(f"Map: {match.get('mapname')}")
    print(f"Type ID: {match.get('matchtype_id')} ({match_type_label(match.get('matchtype_id'))})")
    print(f"Started: {format_datetime(match.get('startgametime'))}")
    print(f"Completed: {format_datetime(match.get('completiontime'))}")
    print(f"Players: {len(match.get('matchhistoryreportresults', []))}")

    # Extract final VP for each team
    team_vps = {}
    for player in match.get("matchhistoryreportresults", []):
        teamid = player.get("teamid")
        counters_str = player.get("counters", "{}")
        try:
            counters = json.loads(counters_str)
            vp0 = counters.get("vp0")
            vp1 = counters.get("vp1")
            if teamid not in team_vps:
                team_vps[teamid] = {"vp0": vp0, "vp1": vp1}
        except json.JSONDecodeError:
            pass

    # Display victory points
    if team_vps:
        print("\n--- Final Victory Points ---")
        print(f"Team 0 VP: {team_vps.get(0, {}).get('vp0', 'N/A')}")
        print(f"Team 1 VP: {team_vps.get(1, {}).get('vp1', 'N/A')}")

    print("\n--- Players ---")
    for player in match.get("matchhistoryreportresults", []):
        profile_id = player.get("profile_id")
        profile = profile_map.get(profile_id, {})
        steam_name = profile.get("name", "")
        alias = profile.get("alias", "")
        print("-", steam_name or alias or f"profile_id={profile_id}")
        print(f"    profile_id: {profile_id}")
        print(f"    alias: {alias}")
        print(f"    team_id: {player.get('teamid')}")
        print(f"    result_type: {player.get('resulttype')}")
        print(f"    outcome: {player.get('outcome')}")
        print(f"    race_id: {player.get('race_id')}")
        print(f"    xp_gained: {player.get('xpgained')}")
        print(f"    old_rating: {player.get('oldrating')} -> new_rating: {player.get('newrating')}")


def main() -> None:
    parser = argparse.ArgumentParser(description="COH2 match history crawler for a Steam or Relic profile.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--steam", help="Steam numerical ID, e.g. 76561198047485546")
    group.add_argument("--relic", type=int, help="Relic profile ID")
    parser.add_argument("--show-details", action="store_true", help="Print full player details for each returned match")
    parser.add_argument("--limit", type=int, default=10, help="Maximum number of matches to list")
    parser.add_argument("--no-db", action="store_true", help="Don't store matches in the database")
    args = parser.parse_args()
    print("Updating DB")
    # Initialize database
    if not args.no_db:
        init_db()

    if args.steam:
        print(f"Resolving Relic profile for Steam ID {args.steam}...")
        relic_profile_id = resolve_relic_profile_id_from_steam(args.steam)
        print(f"Resolved Relic profile ID: {relic_profile_id}")
    else:
        relic_profile_id = args.relic  # type: ignore

    print(f"Fetching match history for Relic profile {relic_profile_id}...")
    data = fetch_match_history_by_relic_id(relic_profile_id)
    matches = data.get("matchHistoryStats", [])
    profiles = build_profile_map(data.get("profiles", []))

    if not matches:
        print("No matches returned by the COH2 API.")
        return

    sorted_matches = sorted(matches, key=lambda m: m.get("startgametime") or 0, reverse=True)
    print(f"Returned {len(sorted_matches)} matches from the API. Showing up to {args.limit}.")

    # Store matches to database
    stored_count = 0
    if not args.no_db:
        print("Storing matches to database...")
        for match in sorted_matches:
            try:
                insert_match(match)
                insert_match_players(match.get("id"), match.get("matchhistoryreportresults", []))
                stored_count += 1
            except Exception as e:
                print(f"Error storing match {match.get('id')}: {e}")

    # Always print details of the newest match
    newest_match = sorted_matches[0]
    # print("\n" + "=" * 80)
    # print_match_details(newest_match, profiles)
    # print("=" * 80)

    # Then print summaries of remaining matches
    # print("\nRecent Matches:")
    # for index, match in enumerate(sorted_matches[: args.limit], start=1):
    #     print_match_summary(match, index)
    #     if args.show_details:
    #         print_match_details(match, profiles)

    # Summary
    if not args.no_db:
        total_db_matches = get_match_count()
        print(f"\n[OK] Stored {stored_count} matches. Total in database: {total_db_matches}")
    
    if not args.show_details and args.limit > 1:
        print("\nUse --show-details to print player details for each returned match.")


if __name__ == "__main__":
    main()
