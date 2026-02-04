CREATE DATABASE  IF NOT EXISTS `checker`
USE `checker`;
-- MySQL dump 10.13  Distrib 8.0.38, for Win64 (x86_64)
--
-- Host: 192.168.0.33    Database: checker
-- ------------------------------------------------------
-- Server version	5.5.5-10.3.39-MariaDB-1:10.3.39+maria~ubu2004

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Temporary view structure for view `all_logs`
--

DROP TABLE IF EXISTS `all_logs`;
/*!50001 DROP VIEW IF EXISTS `all_logs`*/;
SET @saved_cs_client     = @@character_set_client;
/*!50503 SET character_set_client = utf8mb4 */;
/*!50001 CREATE VIEW `all_logs` AS SELECT 
 1 AS `datetime`,
 1 AS `log`,
 1 AS `perpetrator`*/;
SET character_set_client = @saved_cs_client;

--
-- Table structure for table `asking_containers`
--

DROP TABLE IF EXISTS `asking_containers`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `asking_containers` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `date` text DEFAULT NULL,
  `log` text DEFAULT NULL,
  `perpetrator` varchar(45) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `categories`
--

DROP TABLE IF EXISTS `categories`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `categories` (
  `idcategories` int(11) NOT NULL AUTO_INCREMENT,
  `category` varchar(45) NOT NULL,
  PRIMARY KEY (`idcategories`)
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `category_test`
--

DROP TABLE IF EXISTS `category_test`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `category_test` (
  `test` int(11) NOT NULL,
  `category` int(11) NOT NULL,
  PRIMARY KEY (`test`,`category`),
  KEY `category_foreign_key_idx` (`category`),
  CONSTRAINT `category_foreign_key` FOREIGN KEY (`category`) REFERENCES `categories` (`idcategories`),
  CONSTRAINT `test_foreign_key` FOREIGN KEY (`test`) REFERENCES `complex_tests` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `complex_tests`
--

DROP TABLE IF EXISTS `complex_tests`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `complex_tests` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name_of_test` varchar(100) DEFAULT NULL,
  `command` varchar(200) DEFAULT NULL,
  `extraparameters` varchar(200) DEFAULT NULL,
  `button_color` varchar(7) DEFAULT '#ffffff',
  `explanation` tinytext DEFAULT NULL,
  `category_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name_of_test_UNIQUE` (`name_of_test`),
  KEY `fk_idx` (`category_id`),
  CONSTRAINT `fk` FOREIGN KEY (`category_id`) REFERENCES `categories` (`idcategories`) ON DELETE NO ACTION ON UPDATE NO ACTION
) ENGINE=InnoDB AUTO_INCREMENT=12 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `component_to_category`
--

DROP TABLE IF EXISTS `component_to_category`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `component_to_category` (
  `component` varchar(50) NOT NULL,
  `category` varchar(50) NOT NULL,
  `references` varchar(200) NOT NULL DEFAULT 'Contact information not set',
  `position` varchar(45) NOT NULL DEFAULT 'localhost',
  `kind` set('kubernetes','docker') NOT NULL DEFAULT 'docker',
  PRIMARY KEY (`component`,`position`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `container_data`
--

DROP TABLE IF EXISTS `container_data`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `container_data` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `containers` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
  `sampled_at` timestamp NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=5177 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `cronjob_history`
--

DROP TABLE IF EXISTS `cronjob_history`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cronjob_history` (
  `idcronjob_history` int(11) NOT NULL AUTO_INCREMENT,
  `datetime` datetime NOT NULL DEFAULT current_timestamp(),
  `result` mediumtext NOT NULL,
  `id_cronjob` int(11) NOT NULL,
  `errors` mediumtext DEFAULT NULL,
  PRIMARY KEY (`idcronjob_history`),
  KEY `cronjobid` (`id_cronjob`),
  CONSTRAINT `cronjobid` FOREIGN KEY (`id_cronjob`) REFERENCES `cronjobs` (`idcronjobs`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=222190 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `cronjobs`
--

DROP TABLE IF EXISTS `cronjobs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cronjobs` (
  `idcronjobs` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `command` varchar(400) NOT NULL,
  `category` int(11) NOT NULL,
  `where_to_run` varchar(45) DEFAULT NULL,
  `disabled` tinyint(4) NOT NULL DEFAULT 0,
  `restart_logic` varchar(200) DEFAULT NULL,
  `description` varchar(400) DEFAULT NULL,
  PRIMARY KEY (`idcronjobs`),
  KEY `category` (`category`),
  KEY `where_to_run` (`where_to_run`),
  CONSTRAINT `category` FOREIGN KEY (`category`) REFERENCES `categories` (`idcategories`) ON DELETE NO ACTION ON UPDATE NO ACTION,
  CONSTRAINT `where_to_run` FOREIGN KEY (`where_to_run`) REFERENCES `ip_table` (`hostname`) ON DELETE NO ACTION ON UPDATE NO ACTION
) ENGINE=InnoDB AUTO_INCREMENT=45 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `extra_resources`
--

DROP TABLE IF EXISTS `extra_resources`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `extra_resources` (
  `id_category` int(11) NOT NULL AUTO_INCREMENT,
  `resource_address` varchar(45) NOT NULL,
  `resource_information` varchar(100) NOT NULL,
  `resource_description` varchar(45) NOT NULL,
  PRIMARY KEY (`id_category`,`resource_address`),
  CONSTRAINT `category_fk` FOREIGN KEY (`id_category`) REFERENCES `categories` (`idcategories`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `getting_tests`
--

DROP TABLE IF EXISTS `getting_tests`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `getting_tests` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `datetime` text DEFAULT NULL,
  `log` text DEFAULT NULL,
  `perpetrator` varchar(45) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=14674 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `host`
--

DROP TABLE IF EXISTS `host`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `host` (
  `host` varchar(100) NOT NULL,
  `user` varchar(45) NOT NULL,
  `description` varchar(200) DEFAULT NULL,
  `threshold_cpu` float DEFAULT 1,
  `threshold_mem` float DEFAULT 0.8,
  PRIMARY KEY (`host`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `host_data`
--

DROP TABLE IF EXISTS `host_data`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `host_data` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `host` varchar(100) NOT NULL,
  `sampled_at` datetime NOT NULL DEFAULT current_timestamp(),
  `data` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `errors` mediumtext DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `host_key` (`host`),
  CONSTRAINT `host_key` FOREIGN KEY (`host`) REFERENCES `host` (`host`) ON DELETE NO ACTION ON UPDATE NO ACTION
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `ip_table`
--

DROP TABLE IF EXISTS `ip_table`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `ip_table` (
  `ip` varchar(45) NOT NULL,
  `hostname` varchar(45) NOT NULL,
  PRIMARY KEY (`ip`,`hostname`),
  KEY `idx_hostname` (`hostname`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `rebooting_containers`
--

DROP TABLE IF EXISTS `rebooting_containers`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `rebooting_containers` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `datetime` text DEFAULT NULL,
  `log` text DEFAULT NULL,
  `perpetrator` varchar(45) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=16 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `rebooting_cronjobs`
--

DROP TABLE IF EXISTS `rebooting_cronjobs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `rebooting_cronjobs` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `datetime` text DEFAULT current_timestamp(),
  `cronjob_id` int(11) NOT NULL,
  `perpetrator` varchar(45) NOT NULL,
  `result` varchar(300) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `cronjob_fk` (`cronjob_id`),
  CONSTRAINT `cronjob_fk` FOREIGN KEY (`cronjob_id`) REFERENCES `cronjobs` (`idcronjobs`) ON DELETE CASCADE ON UPDATE NO ACTION
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;


CREATE TABLE `sent_notification` (
  `idsent_notification` int(11) NOT NULL AUTO_INCREMENT,
  `hash` varchar(32) NOT NULL,
  `sent_when` varchar(45) NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`idsent_notification`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Table structure for table `snmp_data`
--

DROP TABLE IF EXISTS `snmp_data`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `snmp_data` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `host` varchar(100) NOT NULL,
  `sampled_at` datetime NOT NULL DEFAULT current_timestamp(),
  `data` longtext NOT NULL,
  PRIMARY KEY (`id`),
  KEY `snmp_host_key` (`host`),
  CONSTRAINT `snmp_host_key` FOREIGN KEY (`host`) REFERENCES `snmp_host` (`host`) ON DELETE NO ACTION ON UPDATE NO ACTION
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `snmp_host`
--

DROP TABLE IF EXISTS `snmp_host`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `snmp_host` (
  `protocol` varchar(20) NOT NULL,
  `host` varchar(100) NOT NULL,
  `user` varchar(45) NOT NULL,
  `description` varchar(200) DEFAULT NULL,
  `threshold_cpu` float DEFAULT NULL,
  `details` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `threshold_mem` float DEFAULT NULL,
  PRIMARY KEY (`host`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `summary_status`
--

DROP TABLE IF EXISTS `summary_status`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `summary_status` (
  `category` varchar(50) NOT NULL,
  `status` varchar(200) NOT NULL,
  PRIMARY KEY (`category`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `telegram_alert_pauses`
--

DROP TABLE IF EXISTS `telegram_alert_pauses`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `telegram_alert_pauses` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `component` varchar(200) NOT NULL,
  `until` datetime NOT NULL,
  `issued` datetime NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `test_ran`
--

DROP TABLE IF EXISTS `test_ran`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `test_ran` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `test` varchar(200) DEFAULT NULL,
  `log` text DEFAULT NULL,
  `datetime` varchar(45) DEFAULT NULL,
  `perpetrator` varchar(45) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=39 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tests_results`
--

DROP TABLE IF EXISTS `tests_results`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `tests_results` (
  `id_test` int(11) NOT NULL AUTO_INCREMENT,
  `datetime` text DEFAULT NULL,
  `result` text DEFAULT NULL,
  `container` text DEFAULT NULL,
  `command` text DEFAULT NULL,
  PRIMARY KEY (`id_test`)
) ENGINE=InnoDB AUTO_INCREMENT=12778 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci MAX_ROWS=200000;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tests_table`
--

DROP TABLE IF EXISTS `tests_table`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `tests_table` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `container_name` varchar(45) DEFAULT NULL,
  `command` varchar(500) DEFAULT NULL,
  `command_explained` varchar(500) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping events for database 'checker'
--

--
-- Dumping routines for database 'checker'
--
/*!50003 DROP FUNCTION IF EXISTS `GetHighContrastColor` */;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = utf8 */ ;
/*!50003 SET character_set_results = utf8 */ ;
/*!50003 SET collation_connection  = utf8_general_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = 'STRICT_TRANS_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION' */ ;
DELIMITER ;;
CREATE DEFINER=`root`@`localhost` FUNCTION `GetHighContrastColor`(hexColor CHAR(7)) RETURNS char(7) CHARSET utf8mb4 COLLATE utf8mb4_general_ci
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
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;

--
-- Final view structure for view `all_logs`
--

/*!50001 DROP VIEW IF EXISTS `all_logs`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8 */;
/*!50001 SET character_set_results     = utf8 */;
/*!50001 SET collation_connection      = utf8_general_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`root`@`%` SQL SECURITY DEFINER */
/*!50001 VIEW `all_logs` AS (select `test_ran`.`datetime` AS `datetime`,`test_ran`.`log` AS `log`,`test_ran`.`perpetrator` AS `perpetrator` from `test_ran`) union (select `rebooting_containers`.`datetime` AS `datetime`,`rebooting_containers`.`log` AS `log`,`rebooting_containers`.`perpetrator` AS `perpetrator` from `rebooting_containers`) union (select `telegram_alert_pauses`.`issued` AS `datetime`,concat('Paused ',`telegram_alert_pauses`.`component`,' until ',`telegram_alert_pauses`.`until`) AS `log`,'admin' AS `log` from `telegram_alert_pauses`) order by `datetime` desc */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-02-02 15:26:32
