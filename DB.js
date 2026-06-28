
import {DatabaseSync}  from 'node:sqlite';
import { spawn } from 'child_process';
import { profile } from 'console';
import { sendMessage } from './app.js';

const webhookUrls = {"1514343022169690305": process.env.WebHook_URL1,"1520761872520052736": process.env.WebHook_URL2, "1520778924320358550": process.env.WebHook_URL3}


export class Database {
    constructor(db) {
        this.db = new DatabaseSync('coh2_matches.db');
        this.out = '';
    }

// Reads 
    fetchMatchesCodeBlock(amount, bots){
        const sqlStatement = `SELECT * FROM Matches order by startgametime desc`;
        const matchquery = this.db.prepare(sqlStatement);
        const matches = matchquery.all();
        const colWidth = 30;
        let out = '';

        for (let i = 0; i < Math.min(amount, matches.length); i++) {
            const match = matches[i];
            const playerStmt = this.fetchPlayers(match);
            const players = playerStmt.all();
            const team0 = players.filter(p => p.teamid == 0);
            const team1 = players.filter(p => p.teamid == 1);
            if (bots && !(team0.length == team1.length)){
                if(team0.length < team1.length){
                    team0.push({profile_name: 'CPU',teamid: 0})
                }else{
                    team1.push({profile_name: 'CPU',teamid: 1})
                }
            }

            out += `Map: ${match.mapname}\n`;

            const headerLeft = `Team 1 (VP ${match.team0_vp})`;
            const headerRight = `Team 2 (VP ${match.team1_vp})`;
            out += headerLeft.padEnd(colWidth) + ' | ' + headerRight + "\n";

            out += '-'.repeat(colWidth) + ' | ' + '-'.repeat(colWidth - 3) + "\n";

            const rows = Math.max(team0.length, team1.length);

            for (let r = 0; r < rows; r++) {
                const left = team0[r] ? team0[r].profile_name : '';
                const right = team1[r] ? team1[r].profile_name : '';
                out += left.padEnd(colWidth) + ' | ' + right.padEnd(colWidth) + "\n";
            }

            out += "\n";
        }

        // wrap in a code block for Discord
        return "```Dies ist kein Bug gehen sie weiter\n" + out + "```";
    }

    fetchNewestData(send){

        const pythonProcess = spawn('python', ['coh2_stats_crawler.py', "--relic", "961334", "--show-details"]);
        // const pythonProcess = spawn('python', ['test.py']);

        pythonProcess.stdout.on('data', (data) => {
            console.log(`${data}`);
        });
        pythonProcess.stderr.on('data', (data) => {
            console.error(`${data}`);
        });

        pythonProcess.on('exit', (data) => {
            if(data == 0){
                console.log("No new matches added to the database.");
            }else {
                console.log(`Added ${data} new matches to the database.`);
                if(send){
                    const codeblock = this.fetchMatchesCodeBlock(data,true);
                    for (const [ChannelID, URL] of Object.entries(webhookUrls)) {
                        sendMessage(codeblock,URL);
                    }
                }
            }
        });
    }

    fetchPlayers(Match){
        const sqlStatement = `SELECT * FROM match_players WHERE match_id = ${Match.id} order by teamid desc`;
        return this.db.prepare(sqlStatement);
    }
}