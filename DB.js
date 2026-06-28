
import {DatabaseSync}  from 'node:sqlite';
import { spawn } from 'child_process';



export class Database {
    constructor(db) {
        this.db = new DatabaseSync('coh2_matches.db');
        this.out = '';
    }

// Reads 
    fetchMatchesCodeBlock(amount){
        const sqlStatement = `SELECT * FROM Matches order by startgametime desc`;
        const matchquery = this.db.prepare(sqlStatement);
        const matches = matchquery.all();
        const colWidth = 30;
        let out = '';

        for (let i = 0; i < Math.min(amount, matches.length); i++) {
            const match = matches[i];
            const playerStmt = this.fetchPlayers(match);
            const players = playerStmt.all();

            out += `Map: ${match.mapname}\n`;

            const headerLeft = `Team 1 (VP ${match.team0_vp})`;
            const headerRight = `Team 2 (VP ${match.team1_vp})`;
            out += headerLeft.padEnd(colWidth) + ' | ' + headerRight + "\n";

            out += '-'.repeat(colWidth) + ' | ' + '-'.repeat(colWidth - 3) + "\n";

            const team0 = players.filter(p => p.teamid == 0);
            const team1 = players.filter(p => p.teamid == 1);
            const rows = Math.max(team0.length, team1.length);

            for (let r = 0; r < rows; r++) {
                const left = team0[r] ? team0[r].profile_name : '';
                const right = team1[r] ? team1[r].profile_name : '';
                out += left.padEnd(colWidth) + ' | ' + right.padEnd(colWidth) + "\n";
            }

            out += "\n";
        }

        // wrap in a code block for Discord
        return "```text\n" + out + "```";
    }

    fetchNewestData(){

        const pythonProcess = spawn('python', ['coh2_stats_crawler.py', "--relic", "961334", "--show-details"]);
        // const pythonProcess = spawn('python', ['test.py']);

        pythonProcess.stdout.on('data', (data) => {
            console.log(`stdout: ${data}`);
        });
        pythonProcess.stderr.on('data', (data) => {
            console.error(`stderr: ${data}`);
        });

        pythonProcess.on('exit', (data) => {
            if(data == 0){
                console.log("No new matches added to the database.");
            }else {
                console.log(`Added ${data} new matches to the database.`);
                return this.fetchMatchesCodeBlock(data);
            }
        });
    }

    fetchPlayers(Match){
        const sqlStatement = `SELECT * FROM match_players WHERE match_id = ${Match.id} order by teamid desc`;
        return this.db.prepare(sqlStatement);
    }
}