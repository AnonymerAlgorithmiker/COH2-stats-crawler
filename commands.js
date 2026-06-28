import 'dotenv/config';
// import { getRPSChoices } from './game.js';
import { InstallGlobalCommands } from './utils.js';

// Simple test command
const TEST_COMMAND = {
  name: 'test',
  description: 'Basic command',
  type: 1,
  integration_types: [0, 1],
  contexts: [0, 1, 2],
};

const FETCH_COMMAND = {
  name: 'fetch',
  description: 'Fetch Coh2 Stats Data',
  type: 1,
  options: [{
    type: 4,
    name: 'amount',
    description: 'Amount of matches to fetch',
    required: true,
  } ],
  integration_types: [0, 1],
  contexts: [0, 1, 2],
};


const ALL_COMMANDS = [TEST_COMMAND, FETCH_COMMAND];

await InstallGlobalCommands(process.env.APP_ID, ALL_COMMANDS);
