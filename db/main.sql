CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(250) NOT NULL UNIQUE,
    password VARCHAR(250) NOT NULL
);

CREATE TABLE players (
    id INT AUTO_INCREMENT PRIMARY KEY,
    player_name VARCHAR(250) NOT NULL,
    player_firstname VARCHAR(250) NOT NULL,
    player_identifier VARCHAR(250) NOT NULL
);

CREATE TABLE coaches (
    id INT AUTO_INCREMENT PRIMARY KEY,
    coach_name VARCHAR(250) NOT NULL,
    coach_firstname VARCHAR(250) NOT NULL
);

CREATE TABLE clubs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    club_name VARCHAR(250) NOT NULL
);

CREATE TABLE titles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title_name VARCHAR(250) NOT NULL
);

CREATE TABLE players_by_club (
    id INT AUTO_INCREMENT PRIMARY KEY,
    club_id INT NOT NULL,
    player_id INT NOT NULL,
    FOREIGN KEY (club_id) REFERENCES clubs(id),
    FOREIGN KEY (player_id) REFERENCES players(id)
);

CREATE TABLE titles_per_club (
    id INT AUTO_INCREMENT PRIMARY KEY,
    year_ YEAR NOT NULL,
    title_id INT NOT NULL,
    club_id INT NOT NULL,
    FOREIGN KEY (title_id) REFERENCES titles(id),
    FOREIGN KEY (club_id) REFERENCES clubs(id)
);
