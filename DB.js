
import {DatabaseSync}  from 'node:sqlite';
import { spawn } from 'child_process';



export class Database {
    constructor(db) {
        this.db = new DatabaseSync('coh2_matches.db');
        this.out = '';
    }
    fetchMatches(amount){
        const sqlStatement = `SELECT * FROM Matches order by startgametime desc`;
        const matchquery = this.db.prepare(sqlStatement);
        for (let i = 0; i < amount; i++) {
            const match = matchquery.get();
            const playerQuery = this.fetchPlayers(match);
            playerQuery.get();
            this.out += matchquery.all()[i]["mapname"] + "\n";
            // console.log(playerQuery.all());
            let team1Announced = false;
            let team2Announced = false;
            for(let j = 0; j < playerQuery.all().length; j++){
                if(playerQuery.all()[j]["teamid"] == 0 && !team1Announced){
                    this.out += "Team 1:\n";
                    this.out += matchquery.all()[i]["team0_vp"] + "\n";
                    team1Announced = true;
                }
                if(playerQuery.all()[j]["teamid"] == 1 && !team2Announced){
                    this.out += "Team 2:\n";
                    this.out += matchquery.all()[i]["team1_vp"] + "\n";
                    team2Announced = true;
                }
                this.out += playerQuery.all()[j]["profile_name"] + "\n";
            }
        }
        return this.out;
    }

    fetchPlayers(Match){
        const sqlStatement = `SELECT * FROM match_players WHERE match_id = ${Match.id} order by teamid desc`;
        return this.db.prepare(sqlStatement);
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
                fetchMatches(data);
            }
        });
    }
}

// const DB = new Database();
// DB.fetchNewestData();
// console.log(Database.fetchMatches(1));

// module.exports = Database;