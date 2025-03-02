# IdleBank-Alpha
Opened source of the game IdleBank Alpha, available as a telegram bot at [IdleBank_alphabot.t.me](https://IdleBank_alphabot.t.me)

The changelog is available here: [IdleBank Alpha Changelog](https://telegra.ph/Idle-Bank-Alpha-Changelog-10-11)

The full list of features is found here: [Feature Tree and Upcoming Changes](https://github.com/DeRobyJ/IdleBank-Factbook/blob/main/Feature_Tree_and_Upcoming_Changes.md)

## Usage and deployment
The game is designed to work on the AWS platform, using Lambda and DynamoDB. The main.py and dynamodb_interface.py sources can be changed to use different platforms than AWS and Telegram.

To deploy, the [Python Telegram Bot](https://pypi.org/project/python-telegram-bot/) library is required. Version 13.3 is currently being used. The library can be uploaded to AWS as a Lambda Layer.

## Brief history
The project started in April 2021, during COVID-19 lockdowns. It launched on the 29th of April with a post on the incremental_games subreddit. Initially, the game only offered the progression system and a very manual market made of individual block requests, and it only featured 3 factions: Federal Reserve, European Central Bank and People's Bank of China.

### Main updates

In May 2021, the game received localisation support, featuring English and Italian, a leaderboard and nicknames.

In June 2021, the first three minigames were added: Daily News, Ore Miner and Investment Plan. A tutorial phase was added for new players.

In July 2021, the prestige system known as "Gear System" was added. Gearing up makes the player decrease their production level, acquiring a "Badge" to commemorate their investment.

In September 2021, the simulated market was introduced, replacing block requests. This system received various iterations and tweaks ever since its introduction.

In December 2021, "The Big Update" introduced 4 more factions (Central Bank of Brazil, Reserve Bank of Australia, Reserve Bank of India and African Central Bank), and 2 new minigames (Coinopoly and Global Steel Road), among many tweaks, including a new progression formula.

In April 2022, many changes were introduced to the game, the most notable being a new version of the Investment Plan minigame

In June 2022, the Global Steel Road minigame received a second side with new mechanincs, which is effectively another minigame.

In August 2022, the Mysterious Item was introduced, which functions as a lootbox obtained as reward for various action.

In September 2022, game version 1.0 was reached, introducing Seasons and the seasonal faction challenge. It also introduced variations: every season the game automatically receives some tweaks.

In November 2022, monthly variations for minigames were introduced.

In March 2023, the Flea market was introduced, where players can exchange items coming from different minigames, and blocks.

In September 2023, a new minigame was introduced, Shop Chain.

In November 2023, a "squash" was introduced to soft-reset players' items at the start of every Season.

In April 2024, a partner feature for groups of 2 or 3 players was introduced inside the Daily News minigame.

The game was released as open source on the 28th of April 2024

In February 2025, the top players and the admin decided to reset the game. All pioneers, with at least a gear on the first game, received a special symbol for the new game, and the admin took the chance to completely review the game economy and to switch to just one AWS dynamoDB table.
