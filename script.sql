CREATE TABLE IF NOT EXISTS
servers(
    guildID bigint,
    bot_vc_id bigint,
    user_vc_id bigint,
    total_id bigint,
    listen boolean
);
-- FOR STATUSROLE
CREATE TABLE IF NOT EXISTS
statusrole(
    guildID bigint,
    channelID bigint,
    listen boolean,
    roleID bigint,
    statustext text
);