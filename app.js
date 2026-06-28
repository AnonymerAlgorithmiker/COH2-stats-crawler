import 'dotenv/config';
import express from 'express';
import sqlite3 from 'sqlite3';
import {
  ButtonStyleTypes,
  InteractionResponseFlags,
  InteractionResponseType,
  InteractionType,
  MessageComponentTypes,
  verifyKeyMiddleware,
} from 'discord-interactions';
import { DiscordRequest } from './utils.js';
import {Database} from './DB.js';
import cron from 'node-cron';
import fetch from 'node-fetch';
import { Client, Events, GatewayIntentBits } from 'discord.js';

// Create an express app
const app = express();
// Get port, or default to 3000
const PORT = process.env.PORT || 3000;
const database = new Database();
const webhookUrls = {"1514343022169690305": process.env.WebHook_URL1,"1520761872520052736": process.env.WebHook_URL2, "1520778924320358550": process.env.WebHook_URL3}

app.post('/interactions', verifyKeyMiddleware(process.env.PUBLIC_KEY), async function (req, res) {
  // Interaction id, type and data
  const { id, type, data } = req.body;
  /**
   * Handle verification requests
   */
  if (type === InteractionType.PING) {
    return res.send({ type: InteractionResponseType.PONG });
  }

  /**
   * Handle slash command requests
   * See https://discord.com/developers/docs/interactions/application-commands#slash-commands
   */
  if (type === InteractionType.APPLICATION_COMMAND) {
    const { name } = data;

    // "test" command
    if (name === 'test') {
      // Send a message into the channel where command was triggered from
      return res.send({
        type: InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE,
        data: {
          content: 'Loading ...',
        },
      });
    }
    const ChannelID = req.body.channel_id;
    if (name == 'fetch'){
      const amount = data.options[0].value;
      database.fetchNewestData();
      const codeBlock = database.fetchMatchesCodeBlock(amount, true);
      sendMessage(codeBlock,webhookUrls[ChannelID]);
      return res.send({
        type: InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE,
        data: {
          content: 'Loading ...'
        }
      });
    }

    console.error(`unknown command: ${name}`);
    return res.status(400).json({ error: 'unknown command' });
  }

  console.error('unknown interaction type', type);
  return res.status(400).json({ error: 'unknown interaction type' });
});

app.listen(PORT, () => {
  console.log('Listening on port', PORT);
});

cron.schedule(" * * * * *", function() {
    console.log("crawling");
    for (const [ChannelID, URL] of Object.entries(webhookUrls)) {
      sendMessage(database.fetchNewestData(),URL);
    }
});


function sendMessage(message, URL) {
   fetch(URL, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({"username": "CoH Bot", "content": message})
    });
}

// const amount = 10;
// database.fetchNewestData();
// const codeBlock = database.fetchMatchesCodeBlock(amount);
// sendMessage(codeBlock);