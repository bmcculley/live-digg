CREATE TABLE IF NOT EXISTS `stories` (
  `id` int(11) NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `date_added` DATE NOT NULL,
  `title` varchar(500) NOT NULL,
  `description` text NOT NULL,
  `link` varchar(200) NOT NULL,
  `digg_link` varchar(200) NOT NULL
)ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=latin1;

CREATE TABLE IF NOT EXISTS `users` (
  `id` int(11) NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `email` varchar(100) NOT NULL UNIQUE KEY,
  `name` varchar(100) NOT NULL,
  `hashed_password` varchar(100) NOT NULL
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=latin1;