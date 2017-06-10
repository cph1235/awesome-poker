create table user (
    userId integer primary key autoincrement,
    username varchar(200) not null,
    password varchar(200) not null,
    chip integer not null default 0
);

create table table (
    tableId integer primary key autoincrement,
    tableName varchar(50) not null,
    board: varchar(200),
    pot: integer not null default 0,
    stage: varchar(50) not null
);

create table seat (
    seatId integer primary key autoincrement,
    userId integer not null,
    tableId integer not null,
    seat integer not null,
    chip integer not null default 0,
    hand varchar(50),
    status varchar(50)
);