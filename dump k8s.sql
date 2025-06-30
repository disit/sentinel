CREATE DATABASE  IF NOT EXISTS `checker`;
USE `checker`;

DROP TABLE IF EXISTS `asking_containers`;
CREATE TABLE `asking_containers` (
  `id` int NOT NULL AUTO_INCREMENT,
  `date` text DEFAULT NULL,
  `log` text DEFAULT NULL,
  `perpetrator` varchar(45) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=0 DEFAULT CHARSET=utf8mb4;



DROP TABLE IF EXISTS `container_data`;
CREATE TABLE `container_data` (
  `id` int NOT NULL AUTO_INCREMENT,
  `containers` json NOT NULL,
  `sampled_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=0 DEFAULT CHARSET=utf8mb4;


DROP TABLE IF EXISTS `categories`;
CREATE TABLE `categories` (
  `idcategories` int(11) NOT NULL AUTO_INCREMENT,
  `category` varchar(45) NOT NULL,
  PRIMARY KEY (`idcategories`)
) ENGINE=InnoDB AUTO_INCREMENT=0 DEFAULT CHARSET=utf8mb4;
LOCK TABLES `categories` WRITE;
INSERT INTO `categories` VALUES (1,'Dashboard'),
(2,'Authorization and Authentication'),
(3,'HLT'),
(4,'Knowledge Base'),
(5,'Process Logic'),
(6,'Real Time Dash'),
(7,'Broker'),
(8,'Data Storage'),
(9,'System');
UNLOCK TABLES;

DROP TABLE IF EXISTS `category_test`;
CREATE TABLE `category_test` (
  `test` int(11) NOT NULL,
  `category` int(11) NOT NULL,
  PRIMARY KEY (`test`,`category`),
  KEY `category_foreign_key_idx` (`category`),
  CONSTRAINT `category_foreign_key` FOREIGN KEY (`category`) REFERENCES `categories` (`idcategories`),
  CONSTRAINT `test_foreign_key` FOREIGN KEY (`test`) REFERENCES `complex_tests` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
LOCK TABLES `category_test` WRITE;
INSERT INTO `category_test` VALUES (5,2),
(8,2);
UNLOCK TABLES;

DROP TABLE IF EXISTS `complex_tests`;
CREATE TABLE `complex_tests` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name_of_test` varchar(100) DEFAULT NULL,
  `command` varchar(200) DEFAULT NULL,
  `extraparameters` varchar(200) DEFAULT NULL,
  `button_color` varchar(7) DEFAULT '#ffffff',
  `explanation` tinytext DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name_of_test_UNIQUE` (`name_of_test`)
) ENGINE=InnoDB AUTO_INCREMENT=0 DEFAULT CHARSET=utf8mb4;
LOCK TABLES `complex_tests` WRITE;
INSERT INTO `complex_tests` VALUES (4,'Check iotapps','bash scripts/check_iotapps.sh',NULL,'#20ff14','Check all iotapps, no matter how many they are'),
(5,'Add Device','bash scripts/add_device.sh',NULL,'#ff7f00','Calls the test for adding a new device, then adds some test data');
UNLOCK TABLES;

DROP TABLE IF EXISTS `component_to_category`;
CREATE TABLE `component_to_category` (
  `component` varchar(50) NOT NULL,
  `category` varchar(50) NOT NULL,
  `references` varchar(200) NOT NULL DEFAULT 'Contact information not set',
  PRIMARY KEY (`component`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
LOCK TABLES `component_to_category` WRITE;
INSERT INTO `component_to_category` VALUES ('certbot','Authorization and Authentication','Contact information not set'),
('dashboard-backend','Dashboard','Contact information not set'),
('dashboard-builder','Dashboard','Contact information not set'),
('dashboard-cron','Dashboard','Contact information not set'),
('dashboarddb','Data Storage','Contact information not set'),
('geoserver','HLT','Contact information not set'),
('geoserver-db','Knowledge Base','Contact information not set'),
('heatmap-api','HLT','Contact information not set'),
('heatmap2geosrv','HLT','Contact information not set'),
('iot-discovery','Dashboard','Contact information not set'),
('iot-fiware-api','Dashboard','Contact information not set'),
('iot-fiware-harvester','Dashboard','Contact information not set'),
('iotapp-*','Process Logic','Contact information not set'),
('kafka','Real Time Dash','Contact information not set'),
('keycloak','Authorization and Authentication','Contact information not set'),
('ldap-server','Authorization and Authentication','Contact information not set'),
('myldap','Authorization and Authentication','Contact information not set'),
('nifi','Data Storage','Contact information not set'),
('od-build-api','HLT','Contact information not set'),
('od-get-api','HLT','Contact information not set'),
('od-insert-api','HLT','Contact information not set'),
('od-postgis','Knowledge Base','Contact information not set'),
('opensearch-dashboards','Data Storage','Contact information not set'),
('orion-*','Broker','Contact information not set'),
('orionbrokerfilter-*','Broker','Contact information not set'),
('personaldata','Dashboard','Contact information not set'),
('proxy','System','Contact information not set'),
('servicemap','Knowledge Base','Contact information not set'),
('solr-kb','Knowledge Base','Contact information not set'),
('synoptics','Real Time Dash','Contact information not set'),
('varnish','Data Storage','Contact information not set'),
('virtuoso-kb','Knowledge Base','Contact information not set'),
('wsserver','Real Time Dash','Contact information not set'),
('zookeeper','Real Time Dash','Contact information not set');
UNLOCK TABLES;

DROP TABLE IF EXISTS `extra_resources`;
CREATE TABLE `extra_resources` (
  `id_category` int(11) NOT NULL AUTO_INCREMENT,
  `resource_address` varchar(45) NOT NULL,
  `resource_information` varchar(100) NOT NULL,
  `resource_description` varchar(45) NOT NULL,
  PRIMARY KEY (`id_category`,`resource_address`),
  CONSTRAINT `category_fk` FOREIGN KEY (`id_category`) REFERENCES `categories` (`idcategories`)
) ENGINE=InnoDB AUTO_INCREMENT=0 DEFAULT CHARSET=utf8mb4;
LOCK TABLES `extra_resources` WRITE;
UNLOCK TABLES;
DROP TABLE IF EXISTS `getting_tests`;
CREATE TABLE `getting_tests` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `datetime` text DEFAULT NULL,
  `log` text DEFAULT NULL,
  `perpetrator` varchar(45) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=0 DEFAULT CHARSET=utf8mb4;
DROP TABLE IF EXISTS `rebooting_containers`;
CREATE TABLE `rebooting_containers` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `datetime` text DEFAULT NULL,
  `log` text DEFAULT NULL,
  `perpetrator` varchar(45) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=0 DEFAULT CHARSET=utf8mb4;
DROP TABLE IF EXISTS `summary_status`;
CREATE TABLE `summary_status` (
  `category` varchar(50) NOT NULL,
  `status` varchar(200) NOT NULL,
  PRIMARY KEY (`category`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
LOCK TABLES `summary_status` WRITE;
INSERT INTO `summary_status` VALUES ('Authorization and Authentication',''),
('Broker','<svg width="12" height="12" style="vertical-align: middle;"><circle cx="6" cy="6" r="6" fill="green"/></svg>'),
('Dashboard','<svg width="12" height="12" style="vertical-align: middle;"><circle cx="6" cy="6" r="6" fill="green"/></svg>'),
('Data Storage','<svg width="12" height="12" style="vertical-align: middle;"><circle cx="6" cy="6" r="6" fill="green"/></svg>'),
('HLT','<svg width="12" height="12" style="vertical-align: middle;"><circle cx="6" cy="6" r="6" fill="green"/></svg>'),
('Knowledge Base','<svg width="12" height="12" style="vertical-align: middle;"><circle cx="6" cy="6" r="6" fill="green"/></svg>'),
('Process Logic','<svg width="12" height="12" style="vertical-align: middle;"><circle cx="6" cy="6" r="6" fill="green"/></svg>'),
('Real Time Dash','<svg width="12" height="12" style="vertical-align: middle;"><circle cx="6" cy="6" r="6" fill="green"/></svg>'),
('System','<svg width="12" height="12" style="vertical-align: middle;"><circle cx="6" cy="6" r="6" fill="green"/></svg>');
UNLOCK TABLES;

DROP TABLE IF EXISTS `test_ran`;
CREATE TABLE `test_ran` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `test` varchar(200) DEFAULT NULL,
  `log` text DEFAULT NULL,
  `datetime` varchar(45) DEFAULT NULL,
  `perpetrator` varchar(45) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=0 DEFAULT CHARSET=utf8mb4;
DROP TABLE IF EXISTS `tests_results`;
CREATE TABLE `tests_results` (
  `id_test` int(11) NOT NULL AUTO_INCREMENT,
  `datetime` text DEFAULT NULL,
  `result` text DEFAULT NULL,
  `container` text DEFAULT NULL,
  `command` text DEFAULT NULL,
  PRIMARY KEY (`id_test`)
) ENGINE=InnoDB AUTO_INCREMENT=0 DEFAULT CHARSET=utf8mb4;
DROP TABLE IF EXISTS `tests_table`;
CREATE TABLE `tests_table` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `container_name` varchar(45) DEFAULT NULL,
  `command` varchar(500) DEFAULT NULL,
  `command_explained` varchar(500) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=0 DEFAULT CHARSET=utf8mb4;


DROP TABLE IF EXISTS `ip_table`;
CREATE TABLE `ip_table` (
  `ip` varchar(45) NOT NULL,
  `hostname` varchar(45) NOT NULL,
  PRIMARY KEY (`ip`,`hostname`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

LOCK TABLES `tests_table` WRITE;
INSERT INTO `tests_table` VALUES (2,'opensearch-dashboards','curl -I -s http://opensearch-dashboards:5601/kibana/ | awk \'NR==1{print $2}\' | ( read code && [ \"$code\" -eq 302 ] && echo \'Success <svg width="12" height="12" style="vertical-align: middle;"><circle cx="6" cy="6" r="6" fill="green"/></svg>\' || echo \'Failure <svg width="12" height="12" style="vertical-align: middle;"><circle cx="6" cy="6" r="6" fill="red"/></svg>\' ); date "+%F at %H:%M:%S"','curl -I -s http://opensearch-dashboards:5601/'),
(3,'proxy','curl -I -s http://proxy | awk \'NR==1{print $2}\' | ( read code && [ \"$code\" -eq 301 ] && echo \'Success <svg width="12" height="12" style="vertical-align: middle;"><circle cx="6" cy="6" r="6" fill="green"/></svg>\' || echo \'Failure <svg width="12" height="12" style="vertical-align: middle;"><circle cx="6" cy="6" r="6" fill="red"/></svg>\' ); date "+%F at %H:%M:%S"','curl -I -s http://proxy/dashboardSmartCity/'),
(4,'certbot','echo Not meant to be running nor tested','echo Not meant to be running nor tested'),
(5,'dashboard-backend','echo Not meant to be tested','echo Not meant to be tested'),
(6,'dashboard-builder','curl -I -s http://dashboard-builder/dashboardSmartCity/ | awk \'NR==1{print $2}\' | ( read code && [ \"$code\" -eq 302 ] && echo \'Success <svg width="12" height="12" style="vertical-align: middle;"><circle cx="6" cy="6" r="6" fill="green"/></svg>\' || echo \'Failure <svg width="12" height="12" style="vertical-align: middle;"><circle cx="6" cy="6" r="6" fill="red"/></svg>\' ); date "+%F at %H:%M:%S"','curl -I -s http://dashboard-builder/dashboardSmartCity/'),
(7,'dashboard-cron','echo Not meant to be tested','echo Not meant to be tested'),
(8,'dashboarddb','if nc -z dashboarddb 3306; then echo \'Success <svg width="12" height="12" style="vertical-align: middle;"><circle cx="6" cy="6" r="6" fill="green"/></svg>\'; else echo \'Failure <svg width="12" height="12" style="vertical-align: middle;"><circle cx="6" cy="6" r="6" fill="red"/></svg>\'; fi; date "+%F at %H:%M:%S"','nc -z -v dashboarddb 3306'),
(9,'geoserver','curl -I -s http://geoserver:8080/geoserver/ | awk \'NR==1{print $2}\' | ( read code && [ \"$code\" -eq 302 ] && echo \'Success <svg width="12" height="12" style="vertical-align: middle;"><circle cx="6" cy="6" r="6" fill="green"/></svg>\' || echo \'Failure <svg width="12" height="12" style="vertical-align: middle;"><circle cx="6" cy="6" r="6" fill="red"/></svg>\'; date "+%F at %H:%M:%S" )','curl -I -s http://geoserver:8080/geoserver/'),
(10,'geoserver-db','if nc -z geoserver-db 5432; then echo \'Success <svg width="12" height="12" style="vertical-align: middle;"><circle cx="6" cy="6" r="6" fill="green"/></svg>\'; else echo \'Failure <svg width="12" height="12" style="vertical-align: middle;"><circle cx="6" cy="6" r="6" fill="red"/></svg>\'; fi; date "+%F at %H:%M:%S"','nc -v -z geoserver-db 5432'),
(11,'heatmap-api','echo Not meant to be tested','echo Not meant to be tested'),
(12,'heatmap2geosrv','echo Not meant to be tested','echo Not meant to be tested'),
(14,'iot-fiware-api','curl -I -s http://dashboard-builder/iot-directory/ | awk \'NR==1{print $2}\' | ( read code && [ \"$code\" -eq 302 ] && echo \'Success <svg width="12" height="12" style="vertical-align: middle;"><circle cx="6" cy="6" r="6" fill="green"/></svg>\' || echo \'Failure <svg width="12" height="12" style="vertical-align: middle;"><circle cx="6" cy="6" r="6" fill="red"/></svg>\' ); date "+%F at %H:%M:%S"','curl -I -s http://dashboard-builder/iot-directory/'),
(15,'iot-fiware-harvester','echo Not meant to be tested','echo Not meant to be tested'),
(19,'kafka','if nc -z kafka 9000; then echo \'Success <svg width="12" height="12" style="vertical-align: middle;"><circle cx="6" cy="6" r="6" fill="green"/></svg>\'; else echo \'Failure <svg width="12" height="12" style="vertical-align: middle;"><circle cx="6" cy="6" r="6" fill="red"/></svg>\'; fi; date "+%F at %H:%M:%S"','nc -v -z kafka 9000'),
(20,'keycloak','curl -I -s http://keycloak:8080/auth/ | awk \'NR==1{print $2}\' | ( read code && [ \"$code\" -eq 200 ] && echo \'Success <svg width="12" height="12" style="vertical-align: middle;"><circle cx="6" cy="6" r="6" fill="green"/></svg>\' || echo \'Failure <svg width="12" height="12" style="vertical-align: middle;"><circle cx="6" cy="6" r="6" fill="red"/></svg>\' ); date "+%F at %H:%M:%S"','curl -I -s http://keycloak/auth/'),
(21,'ldap-server','if nc -z ldap-server 389; then echo \'Success <svg width="12" height="12" style="vertical-align: middle;"><circle cx="6" cy="6" r="6" fill="green"/></svg>\'; else echo \'Failure <svg width="12" height="12" style="vertical-align: middle;"><circle cx="6" cy="6" r="6" fill="red"/></svg>\'; fi; date "+%F at %H:%M:%S"','nc -v -z ldap-server 389'),
(23,'myldap','curl -I -s https://myldap:443/phpldapadmin/cmd.php | awk \'NR==1{print $2}\' | ( read code && [ \"$code\" -eq 302 ] && echo \'Success <svg width="12" height="12" style="vertical-align: middle;"><circle cx="6" cy="6" r="6" fill="green"/></svg>\' || echo \'Failure <svg width="12" height="12" style="vertical-align: middle;"><circle cx="6" cy="6" r="6" fill="red"/></svg>\' ); date "+%F at %H:%M:%S"','curl -I -s https://myldap:443/phpldapadmin/cmd.php'),
(24,'nifi','curl -I -s --insecure https://nifi:9090 | awk \'NR==1{print $2}\' | ( read code && [ \"$code\" -eq 200 ] && echo \'Success <svg width="12" height="12" style="vertical-align: middle;"><circle cx="6" cy="6" r="6" fill="green"/></svg>\' || echo \'Failure <svg width="12" height="12" style="vertical-align: middle;"><circle cx="6" cy="6" r="6" fill="red"/></svg>\'); date "+%F at %H:%M:%S"','curl -I -s --insecure https://nifi:9090'),
(25,'od-build-api','curl -I -s http://od-build-api:3000/odmm-build/api | grep -q \'NOT FOUND\' && echo \'Success <svg width="12" height="12" style="vertical-align: middle;"><circle cx="6" cy="6" r="6" fill="green"/></svg>\' || echo \'Failure <svg width="12" height="12" style="vertical-align: middle;"><circle cx="6" cy="6" r="6" fill="red"/></svg>\'; date "+%F at %H:%M:%S"','curl -I -s http://od-build-api:3100/odmm-build/api'),
(26,'od-get-api','curl -I -s http://od-insert-api:3100/odmm/api | grep -q \'NOT FOUND\' && echo \'Success <svg width="12" height="12" style="vertical-align: middle;"><circle cx="6" cy="6" r="6" fill="green"/></svg>\' || echo \'Failure <svg width="12" height="12" style="vertical-align: middle;"><circle cx="6" cy="6" r="6" fill="red"/></svg>\'; date "+%F at %H:%M:%S"','curl -I -s http://od-insert-api:3100/odmm/api'),
(27,'od-insert-api','curl -I -s http://od-insert-api:3100/odmm-insert/api | grep -q \'NOT FOUND\' && echo \'Success <svg width="12" height="12" style="vertical-align: middle;"><circle cx="6" cy="6" r="6" fill="green"/></svg>\' || echo \'Failure <svg width="12" height="12" style="vertical-align: middle;"><circle cx="6" cy="6" r="6" fill="red"/></svg>\'; date "+%F at %H:%M:%S"','curl -I -s http://od-insert-api:3100/odmm-insert/api'),
(28,'od-postgis','if nc -z od-postgis 5432; then echo \'Success <svg width="12" height="12" style="vertical-align: middle;"><circle cx="6" cy="6" r="6" fill="green"/></svg>\'; else echo \'Failure <svg width="12" height="12" style="vertical-align: middle;"><circle cx="6" cy="6" r="6" fill="red"/></svg>\'; fi; date "+%F at %H:%M:%S"','nc -v -z od-postgis 5432'),
(33,'personaldata','curl -I -s http://personaldata:8080/datamanager/ | awk \'NR==1{print $2}\' | ( read code && [ \"$code\" -eq 200 ] && echo \'Success <svg width="12" height="12" style="vertical-align: middle;"><circle cx="6" cy="6" r="6" fill="green"/></svg>\' || echo \'Failure <svg width="12" height="12" style="vertical-align: middle;"><circle cx="6" cy="6" r="6" fill="red"/></svg>\' ); date "+%F at %H:%M:%S"','curl -I -s http://dashboard-builder/datamanager/'),
(34,'servicemap','curl -I -s http://servicemap:8080/ServiceMap/ | awk \'NR==1{print $2}\' | ( read code && [ \"$code\" -eq 200 ] && echo \'Success <svg width="12" height="12" style="vertical-align: middle;"><circle cx="6" cy="6" r="6" fill="green"/></svg>\' || echo \'Failure <svg width="12" height="12" style="vertical-align: middle;"><circle cx="6" cy="6" r="6" fill="red"/></svg>\' ); date "+%F at %H:%M:%S"','curl -I -s http://dashboard-builder/ServiceMap/'),
(35,'solr-kb','curl -I -s http://solr:8983/solr/ | awk \'NR==1{print $2}\' | ( read code && [ \"$code\" -eq 200 ] && echo \'Success <svg width="12" height="12" style="vertical-align: middle;"><circle cx="6" cy="6" r="6" fill="green"/></svg>\' || echo \'Failure <svg width="12" height="12" style="vertical-align: middle;"><circle cx="6" cy="6" r="6" fill="red"/></svg>\' ); date "+%F at %H:%M:%S"','curl -I -s http://solr-kb:8983/solr/'),
(36,'synoptics','curl -I -s http://synoptics:3002/synoptics/ | awk \'NR==1{print $2}\' | ( read code && [ \"$code\" -eq 200 ] && echo \'Success <svg width="12" height="12" style="vertical-align: middle;"><circle cx="6" cy="6" r="6" fill="green"/></svg>\' || echo \'Failure <svg width="12" height="12" style="vertical-align: middle;"><circle cx="6" cy="6" r="6" fill="red"/></svg>\' ); date "+%F at %H:%M:%S"','curl -I -s http://dashboard-builder/synoptics/'),
(37,'varnish','curl -I -s http://varnish:6081/ | awk \'NR==1{print $2}\' | ( read code && [ \"$code\" -eq 403 ] && echo \'Success <svg width="12" height="12" style="vertical-align: middle;"><circle cx="6" cy="6" r="6" fill="green"/></svg>\' || echo \'Failure <svg width="12" height="12" style="vertical-align: middle;"><circle cx="6" cy="6" r="6" fill="red"/></svg>\' ); date "+%F at %H:%M:%S"','curl -I -s http://varnish:6081/'),
(38,'virtuoso-kb','curl -I -s http://virtuoso-kb:8890/ | awk \'NR==1{print $2}\' | ( read code && [ \"$code\" -eq 200 ] && echo \'Success <svg width="12" height="12" style="vertical-align: middle;"><circle cx="6" cy="6" r="6" fill="green"/></svg>\' || echo \'Failure <svg width="12" height="12" style="vertical-align: middle;"><circle cx="6" cy="6" r="6" fill="red"/></svg>\' ); date "+%F at %H:%M:%S"','curl -I -s http://virtuoso-kb:8890/'),
(39,'wsserver','curl -I -s http://wsserver:8000/wsserver/ | awk \'NR==1{print $2}\' | ( read code && [ \"$code\" -eq 400 ] && echo \'Success <svg width="12" height="12" style="vertical-align: middle;"><circle cx="6" cy="6" r="6" fill="green"/></svg>\' || echo \'Failure <svg width="12" height="12" style="vertical-align: middle;"><circle cx="6" cy="6" r="6" fill="red"/></svg>\' ); date "+%F at %H:%M:%S"','curl -I -s http://wsserver:8000/wsserver');
UNLOCK TABLES;

CREATE TABLE `telegram_alert_pauses` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `component` varchar(200) NOT NULL,
  `until` datetime NOT NULL,
  `issued` datetime NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;


DELIMITER ;;
CREATE DEFINER=`root`@`localhost` FUNCTION `GetHighContrastColor`(hexColor CHAR(7)) RETURNS char(7) CHARSET utf8mb4 
    DETERMINISTIC
BEGIN
  DECLARE colorR INT;
  DECLARE colorG INT;
  DECLARE colorB INT;
  DECLARE colorLuminance DECIMAL(10, 2);
  DECLARE contrastColor CHAR(7);
  DECLARE contrastThreshold INT;
  SET colorR = CAST(CONV(SUBSTRING(hexColor, 2, 2), 16, 10) AS UNSIGNED);
  SET colorG = CAST(CONV(SUBSTRING(hexColor, 4, 2), 16, 10) AS UNSIGNED);
  SET colorB = CAST(CONV(SUBSTRING(hexColor, 6, 2), 16, 10) AS UNSIGNED);
  SET contrastThreshold = 128;
  SET colorLuminance = 0.2126 * colorR + 0.7152 * colorG + 0.0722 * colorB;
  IF colorLuminance > contrastThreshold THEN
    SET contrastColor = '#000000';
  ELSE
    SET contrastColor = '#ffffff';
  END IF;

  RETURN contrastColor;
END ;;
DELIMITER ;


CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`%` SQL SECURITY DEFINER VIEW `all_logs` AS (select `test_ran`.`datetime` AS `datetime`,`test_ran`.`log` AS `log`,`test_ran`.`perpetrator` AS `perpetrator` from `test_ran`) union (select `rebooting_containers`.`datetime` AS `datetime`,`rebooting_containers`.`log` AS `log`,`rebooting_containers`.`perpetrator` AS `perpetrator` from `rebooting_containers`) union (select `telegram_alert_pauses`.`issued` AS `datetime`,concat('Paused ',`telegram_alert_pauses`.`component`,' until ',`telegram_alert_pauses`.`until`) AS `log`,'admin' AS `log` from `telegram_alert_pauses`) order by `datetime` desc;
