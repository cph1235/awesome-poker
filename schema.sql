create table user (
    userId integer primary key autoincrement,
    username varchar(200) not null,
    password varchar(200) not null,
    stackSize integer not null default 0
);

create table game (
    gameId integer primary key autoincrement,
    gameName varchar(50) not null,
    board varchar(200),
    stage varchar(50) not null
    buttonSeatId integer
);

create table seat (
    seatId integer primary key autoincrement,
    userId integer not null,
    username varchar(200) not null,
    gameId integer not null,
    seatNumber integer not null,
    stackSize integer not null default 0,
    hand varchar(50),
    action varchar(20), /* acting, waiting, fold, all in */
    betSize integer not null default 0
);

create table pot(
    potId integer primary key autoincrement,
    seatIds varchar(200) not null, 
    gameid integer not null,
    currentBetSize integer not null default 0,
    potSize integer not null default 0,
    rank integer not null default 0,
)