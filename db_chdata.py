# This is a cache, to avoid reading from the db at each action
# This gets updated at every action, together with the db.
# It would be cool if we could update the db right before the instance is killed by aws
# but, to my understanding, we can't
active_users = {}
market_data = {}
global_production = {}
events_data = {}
leaderboard_data = {}
member_count = {}
multiplayer_info = {}
season_info = {}
mini_general = {}
mini_player = {}


''' tables  # might be a lil outdated
general_data
    currency: row
        name: S
        members: N
        hourly_production_rate: N
        leaderboard: NS
    multiplayer_info: dict
        players_activity: dict (chat_id : timestamp)
        top_gear: dict
            chat_id: N
            level: N
        top_production: dict
            chat_id: N
            level: N
    season_info: dict
        current_season: S       # made of 2 values: a number (1,2,3,4) for the
                                #  season, and the year (eg. 2022)
        faction: dict
            <every faction>: dict
                top_contributor: N
                blocks_used: N
                current_badge: S


user_data
    user: row
        chat_id: N
        account_status: S
        membership: S
        account_creation_timestamp: N
        last_login_timestamp: N
        production_level: N
        cur_Euro: N (deprecated)
        cur_Dollar: N (deprecated)
        cur_Yuan: N (deprecated)
        blocks_Euro: N
        blocks_Dollar: N
        blocks_Yuan: N
        blocks_AUDollar: N
        blocks_Real: N
        blocks_Rupee: N
        blocks_Afro: N
        saved_balance: N
        balance_timestamp: N
        language: S
        nickname: NS
        season_data: dict
            season: S
            blocks_contributed: N

market_data
    section: row
        type: S
        money: N
        blocks: N
        current_price_multiplier_pcent: N

events_data
    user: row
        chat_id: N
        <event name>: N

minigame tables: see game_minis.py
'''
