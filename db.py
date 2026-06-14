import sqlite3
import json
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from pathlib import Path

DB_PATH = Path(__file__).parent / "coh2_matches.db"


def init_db() -> None:
    """Initialize the database with required tables."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create matches table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY,
            creator_profile_id INTEGER NOT NULL,
            mapname TEXT,
            matchtype_label TEXT,
            startgametime TEXT,
            gamelaenge TEXT,
            team0_vp INTEGER,
            team1_vp INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create match_players table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS match_players (
            match_id INTEGER NOT NULL,
            profile_id INTEGER NOT NULL,
            profile_name TEXT,
            teamid INTEGER,
            race_id TEXT,
            resulttype TEXT,
            counters TEXT,
            PRIMARY KEY (match_id, profile_id),
            FOREIGN KEY (match_id) REFERENCES matches(id)
        )
    """)

    # Create indexes for faster queries
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_matches_starttime
        ON matches(startgametime DESC)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_match_players_profile
        ON match_players(profile_id)
    """)

    conn.commit()
    conn.close()


def insert_match(match: Dict[str, Any]) -> int:
    """Insert a match into the database. Returns the match ID."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Extract team victory points
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

    team0_vp = team_vps.get(0, {}).get("vp0")
    team1_vp = team_vps.get(1, {}).get("vp1")

    # Convert Unix timestamps to readable datetime format
    def format_timestamp(timestamp: Optional[int]) -> Optional[str]:
        if not timestamp:
            return None
        try:
            return datetime.fromtimestamp(timestamp, timezone.utc).isoformat()
        except (ValueError, OSError):
            return None

    # startgametime_str = format_timestamp(match.get("startgametime"))
    # gamelaenge_str = format_timestamp(match.get("completiontime") - match.get("startgametime")) if match.get("completiontime") and match.get("startgametime") else None
    matchtype_label = matchtypeIDtoText(match.get("matchtype_id"))

    start_iso = format_timestamp(match.get("startgametime")) if match.get("startgametime") else None
    end_iso   = format_timestamp(match.get("completiontime")) if match.get("completiontime") else None
    if start_iso and end_iso:
        start_dt = datetime.fromisoformat(start_iso)
        end_dt   = datetime.fromisoformat(end_iso)
        length_seconds = int((end_dt - start_dt).total_seconds())
        length_str = str(timedelta(seconds=length_seconds))

    cursor.execute("""
        INSERT OR IGNORE INTO matches 
        (id, creator_profile_id, mapname, matchtype_label, startgametime, gamelaenge, team0_vp, team1_vp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        match.get("id"),
        match.get("creator_profile_id"),
        match.get("mapname"),
        matchtype_label,
        start_iso,
        length_str,
        team0_vp,
        team1_vp,
    ))

    conn.commit()

    # Return the match ID (either newly inserted or existing)
    match_id = match.get("id")
    conn.close()
    return match_id

def matchtypeIDtoText(matchtype_id: int) -> str:
    """Convert match type ID to human-readable text."""
    mapping = {
        0: "Custom",
        1: "1v1",
        2: "2v2",
        3: "3v3",
        4: "4v4",
        22: "Automatch",
        # Add more mappings as needed
    }
    return mapping.get(matchtype_id, f"Unknown ({matchtype_id})")

def playerIDtoText(player_id: int) -> str:
    """Convert player ID to human-readable text."""
    mapping = {
        961334: "Schoko Knusper Müsli Mann",
        6738995: "Joooooordi",
        3921193: "Will Shakes Beer",
        5407006: "Foooolix",
        6738994: "GeGeGerrit",
        1577976: "Der G",
        6802047: "Paul der Befreier"
    }
    return mapping.get(player_id, "Unknown Player")

def raceIdtoText(race_id: int) -> str:
    """Convert race ID to human-readable text."""
    mapping = {
        0: "Wehrmacht",
        1: "Soviet",
        2: "Oberkomandant West",
        3: "Amerikaner",
        4: "Brite",
    }
    return mapping.get(race_id, "Unknown Race")

def resulttypeIDtoText(resulttype_id: int) -> str:
    """Convert result type ID to human-readable text."""
    mapping = {
        0: "Loss",
        1: "Win",
    }
    return mapping.get(resulttype_id, f"Unknown ({resulttype_id})")


def insert_match_players(match_id: int, players: List[Dict[str, Any]]) -> None:
    """Insert player data for a match into the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for player in players:
        # Resolve values safely. Use provided name if available, else fallback to mapping.
        profile_id = player.get("profile_id")
        profile_name = player.get("profile_name") or playerIDtoText(profile_id)
        teamid = player.get("teamid")
        # Store a human-readable race name (schema uses TEXT for race_id)
        race_text = raceIdtoText(player.get("race_id")) if player.get("race_id") is not None else None
        result_text = resulttypeIDtoText(player.get("resulttype")) if player.get("resulttype") is not None else None
        counters = player.get("counters")

        cursor.execute("""
            INSERT OR IGNORE INTO match_players
            (match_id, profile_id, profile_name, teamid, race_id, resulttype, counters)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            match_id,
            profile_id,
            profile_name,
            teamid,
            race_text,
            result_text,
            counters,
        ))

    conn.commit()
    conn.close()


def get_match_count() -> int:
    """Get total number of matches in the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM matches")
    count = cursor.fetchone()[0]
    conn.close()
    return count


def get_recent_matches(limit: int = 10) -> List[Dict[str, Any]]:
    """Get recent matches from the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, mapname, matchtype_label, startgametime, gamelaenge, team0_vp, team1_vp
        FROM matches
        ORDER BY startgametime DESC
        LIMIT ?
    """, (limit,))
    
    matches = []
    for row in cursor.fetchall():
        matches.append({
            "id": row[0],
            "mapname": row[1],
            "matchtype_label": row[2],
            "startgametime": row[3],
            "gamelaenge": row[4],
            "team0_vp": row[5],
            "team1_vp": row[6],
        })
    
    conn.close()
    return matches


def get_player_matches(profile_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """Get matches for a specific player from the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT m.id, m.mapname, m.matchtype_label, m.startgametime, m.team0_vp, m.team1_vp,
               mp.teamid, mp.resulttype, mp.counters
        FROM matches m
        JOIN match_players mp ON m.id = mp.match_id
        WHERE mp.profile_id = ?
        ORDER BY m.startgametime DESC
        LIMIT ?
    """, (profile_id, limit))
    
    matches = []
    for row in cursor.fetchall():
        matches.append({
            "id": row[0],
            "mapname": row[1],
            "matchtype_label": row[2],
            "startgametime": row[3],
            "team0_vp": row[4],
            "team1_vp": row[5],
            "teamid": row[6],
            "resulttype": row[7],
            "counters": row[8],
        })
    
    conn.close()
    return matches
