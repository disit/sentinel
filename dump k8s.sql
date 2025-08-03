-- MySQL dump 10.13  Distrib 8.0.33, for Linux (x86_64)
--
-- Host: 192.168.1.30    Database: checker
-- ------------------------------------------------------
-- Server version	5.5.5-10.3.39-MariaDB-1:10.3.39+maria~ubu2004

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Temporary view structure for view `all_logs`
--

USE checker;

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
-- Dumping data for table `asking_containers`
--

LOCK TABLES `asking_containers` WRITE;
/*!40000 ALTER TABLE `asking_containers` DISABLE KEYS */;
/*!40000 ALTER TABLE `asking_containers` ENABLE KEYS */;
UNLOCK TABLES;

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
-- Dumping data for table `categories`
--

LOCK TABLES `categories` WRITE;
/*!40000 ALTER TABLE `categories` DISABLE KEYS */;
INSERT INTO `categories` VALUES (1,'Dashboard'),(2,'Authorization and Authentication'),(3,'HLT'),(4,'Knowledge Base'),(5,'Process Logic'),(6,'Real Time Dash'),(7,'Broker'),(8,'Data Storage'),(9,'System');
/*!40000 ALTER TABLE `categories` ENABLE KEYS */;
UNLOCK TABLES;


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
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `complex_tests`
--

LOCK TABLES `complex_tests` WRITE;
/*!40000 ALTER TABLE `complex_tests` DISABLE KEYS */;
INSERT INTO `complex_tests` VALUES (4,'Check iotapps','bash scripts/check_iotapps.sh',NULL,'#20ff14','Check all iotapps, no matter how many they are',1),(5,'Add Device','bash scripts/add_device.sh',NULL,'#ff7f00','Calls the test for adding a new device, then adds some test data',2),(7,'Verify Authentication','bash scripts/get_token.sh',NULL,'#20ff14','Attempts to register as the operator to ensure the correct behavior of keycloak',1),(8,'Attempt new user registration','bash scripts/attempt-registration.sh',NULL,'#ffffff',NULL,2);
/*!40000 ALTER TABLE `complex_tests` ENABLE KEYS */;
UNLOCK TABLES;

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
  `position` varchar(45) NOT NULL DEFAULT '$#k8-namespace#$',
  PRIMARY KEY (`component`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `component_to_category`
--
LOCK TABLES `component_to_category` WRITE;
INSERT INTO `component_to_category` VALUES ('certbot-*','Authorization and Authentication','Contact information not set'),
('dashboard-backend-*','Dashboard','Contact information not set'),
('dashboard-builder-*','Dashboard','Contact information not set'),
('dashboard-cron-*','Dashboard','Contact information not set'),
('dashboarddb-*','Data Storage','Contact information not set'),
('geoserver-*','HLT','Contact information not set'),
('geoserver-db-*','Knowledge Base','Contact information not set'),
('heatmap-api-*','HLT','Contact information not set'),
('heatmap2geosrv-*','HLT','Contact information not set'),
('iot-discovery-*','Dashboard','Contact information not set'),
('iot-fiware-api-*','Dashboard','Contact information not set'),
('iot-fiware-harvester-*','Dashboard','Contact information not set'),
('iotapp-*','Process Logic','Contact information not set'),
('kafka-*','Real Time Dash','Contact information not set'),
('keycloak-*','Authorization and Authentication','Contact information not set'),
('ldap-server-*','Authorization and Authentication','Contact information not set'),
('myldap-*','Authorization and Authentication','Contact information not set'),
('nifi-*','Data Storage','Contact information not set'),
('od-build-api-*','HLT','Contact information not set'),
('od-get-api-*','HLT','Contact information not set'),
('od-insert-api-*','HLT','Contact information not set'),
('od-postgis-*','Knowledge Base','Contact information not set'),
('opensearch-dashboards-*','Data Storage','Contact information not set'),
('orion-*','Broker','Contact information not set'),
('orionbrokerfilter-*','Broker','Contact information not set'),
('personaldata-*','Dashboard','Contact information not set'),
('proxy-*','System','Contact information not set'),
('servicemap-*','Knowledge Base','Contact information not set'),
('solr-kb-*','Knowledge Base','Contact information not set'),
('synoptics-*','Real Time Dash','Contact information not set'),
('varnish-*','Data Storage','Contact information not set'),
('virtuoso-kb-*','Knowledge Base','Contact information not set'),
('wsserver-*','Real Time Dash','Contact information not set'),
('zookeeper-*','Real Time Dash','Contact information not set');
UNLOCK TABLES;
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `container_data`
--


--
-- Table structure for table `cronjob_history`
--

DROP TABLE IF EXISTS `cronjob_history`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cronjob_history` (
  `idcronjob_history` int(11) NOT NULL AUTO_INCREMENT,
  `datetime` datetime NOT NULL DEFAULT current_timestamp(),
  `result` varchar(200) NOT NULL,
  `id_cronjob` int(11) NOT NULL,
  `errors` varchar(500) DEFAULT NULL,
  PRIMARY KEY (`idcronjob_history`),
  KEY `cronjobid` (`id_cronjob`),
  CONSTRAINT `cronjobid` FOREIGN KEY (`id_cronjob`) REFERENCES `cronjobs` (`idcronjobs`) ON DELETE CASCADE ON UPDATE NO ACTION
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `cronjob_history`
--

--
-- Table structure for table `cronjobs`
--

DROP TABLE IF EXISTS `cronjobs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cronjobs` (
  `idcronjobs` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(45) NOT NULL,
  `command` varchar(400) NOT NULL,
  `category` int(11) NOT NULL,
  PRIMARY KEY (`idcronjobs`),
  KEY `category` (`category`),
  CONSTRAINT `category` FOREIGN KEY (`category`) REFERENCES `categories` (`idcategories`) ON DELETE NO ACTION ON UPDATE NO ACTION
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `cronjobs`
--

LOCK TABLES `cronjobs` WRITE;
/*!40000 ALTER TABLE `cronjobs` DISABLE KEYS */;
INSERT INTO `cronjobs` VALUES (1,'Internet connection','echo Online',1),(2,'This fails','sbsbsbsbs',1);
/*!40000 ALTER TABLE `cronjobs` ENABLE KEYS */;
UNLOCK TABLES;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `extra_resources`
--


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
) ENGINE=InnoDB  DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `getting_tests`
--

--
-- Table structure for table `ip_table`
--

DROP TABLE IF EXISTS `ip_table`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `ip_table` (
  `ip` varchar(45) NOT NULL,
  `hostname` varchar(45) NOT NULL,
  PRIMARY KEY (`ip`,`hostname`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `ip_table`
--

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `rebooting_containers`
--


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
-- Dumping data for table `summary_status`
--

LOCK TABLES `summary_status` WRITE;
/*!40000 ALTER TABLE `summary_status` DISABLE KEYS */;
INSERT INTO `summary_status` VALUES ('Authorization and Authentication','&#128994'),('Broker','&#128994'),('Dashboard','&#128994'),('Data Storage','&#128994'),('HLT','&#128994'),('Knowledge Base','&#128994'),('Process Logic','&#128994'),('Real Time Dash','&#128994'),('System','&#128994');
/*!40000 ALTER TABLE `summary_status` ENABLE KEYS */;
UNLOCK TABLES;

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
-- Dumping data for table `telegram_alert_pauses`
--

LOCK TABLES `telegram_alert_pauses` WRITE;
/*!40000 ALTER TABLE `telegram_alert_pauses` DISABLE KEYS */;
/*!40000 ALTER TABLE `telegram_alert_pauses` ENABLE KEYS */;
UNLOCK TABLES;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `test_ran`
--

LOCK TABLES `test_ran` WRITE;
/*!40000 ALTER TABLE `test_ran` DISABLE KEYS */;
/*!40000 ALTER TABLE `test_ran` ENABLE KEYS */;
UNLOCK TABLES;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `tests_results`
--

LOCK TABLES `tests_results` WRITE;
/*!40000 ALTER TABLE `tests_results` DISABLE KEYS */;
/*!40000 ALTER TABLE `tests_results` ENABLE KEYS */;
UNLOCK TABLES;

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
) ENGINE=InnoDB AUTO_INCREMENT=40 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `tests_table`
--

LOCK TABLES `tests_table` WRITE;
/*!40000 ALTER TABLE `tests_table` DISABLE KEYS */;
INSERT INTO `tests_table` VALUES (2,'opensearch-dashboards','curl -I -s http://proxy.$#k8-namespace#$.svc.cluster.local/kibana/ | awk \'NR==1{print $2}\' | ( read code && [ \"$code\" -eq 302 ] && echo \'Success <svg width=\"12\" height=\"12\" style=\"vertical-align: middle;\"><circle cx=\"6\" cy=\"6\" r=\"6\" fill=\"green\"/></svg>\' || echo \'Failure <svg width=\"12\" height=\"12\" style=\"vertical-align: middle;\"><circle cx=\"6\" cy=\"6\" r=\"6\" fill=\"red\"/></svg>\' ); date \"+%F at %H:%M:%S\"','curl -I -s http://opensearch-dashboards:5601/'),(3,'proxy','curl -I -s http:/proxy.$#k8-namespace#$.svc.cluster.local | awk \'NR==1{print $2}\' | ( read code && [ \"$code\" -eq 301 ] && echo \'Success <svg width=\"12\" height=\"12\" style=\"vertical-align: middle;\"><circle cx=\"6\" cy=\"6\" r=\"6\" fill=\"green\"/></svg>\' || echo \'Failure <svg width=\"12\" height=\"12\" style=\"vertical-align: middle;\"><circle cx=\"6\" cy=\"6\" r=\"6\" fill=\"red\"/></svg>\' ); date \"+%F at %H:%M:%S\"','curl -I -s http://dashtest/dashboardSmartCity/'),(4,'certbot','echo Not meant to be running nor tested','echo Not meant to be running nor tested'),(5,'dashboard-backend','echo Not meant to be tested','echo Not meant to be tested'),(6,'dashboard-builder','curl -I -s http://proxy.$#k8-namespace#$.svc.cluster.local/dashboardSmartCity/ | awk \'NR==1{print $2}\' | ( read code && [ \"$code\" -eq 302 ] && echo \'Success <svg width=\"12\" height=\"12\" style=\"vertical-align: middle;\"><circle cx=\"6\" cy=\"6\" r=\"6\" fill=\"green\"/></svg>\' || echo \'Failure <svg width=\"12\" height=\"12\" style=\"vertical-align: middle;\"><circle cx=\"6\" cy=\"6\" r=\"6\" fill=\"red\"/></svg>\' ); date \"+%F at %H:%M:%S\"','curl -I -s http://dashtest/dashboardSmartCity/'),(7,'dashboard-cron','echo Not meant to be tested','echo Not meant to be tested'),(8,'dashboarddb','if nc -z dashboarddb.$#k8-namespace#$.svc.cluster.local 3306; then echo \'Success <svg width=\"12\" height=\"12\" style=\"vertical-align: middle;\"><circle cx=\"6\" cy=\"6\" r=\"6\" fill=\"green\"/></svg>\'; else echo \'Failure <svg width=\"12\" height=\"12\" style=\"vertical-align: middle;\"><circle cx=\"6\" cy=\"6\" r=\"6\" fill=\"red\"/></svg>\'; fi; date \"+%F at %H:%M:%S\"','nc -z -v dashboarddb 3306'),(9,'geoserver','curl -I -s http://proxy.$#k8-namespace#$.svc.cluster.local/geoserver/ | awk \'NR==1{print $2}\' | ( read code && [ \"$code\" -eq 302 ] && echo \'Success <svg width=\"12\" height=\"12\" style=\"vertical-align: middle;\"><circle cx=\"6\" cy=\"6\" r=\"6\" fill=\"green\"/></svg>\' || echo \'Failure <svg width=\"12\" height=\"12\" style=\"vertical-align: middle;\"><circle cx=\"6\" cy=\"6\" r=\"6\" fill=\"red\"/></svg>\'; date \"+%F at %H:%M:%S\" )','curl -I -s http://dashtest/geoserver/'),(10,'geoserver-db','if nc -z geoserver-db.$#k8-namespace#$.svc.cluster.local 5432; then echo \'Success <svg width=\"12\" height=\"12\" style=\"vertical-align: middle;\"><circle cx=\"6\" cy=\"6\" r=\"6\" fill=\"green\"/></svg>\'; else echo \'Failure <svg width=\"12\" height=\"12\" style=\"vertical-align: middle;\"><circle cx=\"6\" cy=\"6\" r=\"6\" fill=\"red\"/></svg>\'; fi; date \"+%F at %H:%M:%S\"','nc -v -z geoserver-db 5432'),(11,'heatmap-api','echo Not meant to be tested','echo Not meant to be tested'),(12,'heatmap2geosrv','echo Not meant to be tested','echo Not meant to be tested'),(14,'iot-fiware-api','curl -I -s http://proxy.$#k8-namespace#$.svc.cluster.local/iot-directory/ | awk \'NR==1{print $2}\' | ( read code && [ \"$code\" -eq 302 ] && echo \'Success <svg width=\"12\" height=\"12\" style=\"vertical-align: middle;\"><circle cx=\"6\" cy=\"6\" r=\"6\" fill=\"green\"/></svg>\' || echo \'Failure <svg width=\"12\" height=\"12\" style=\"vertical-align: middle;\"><circle cx=\"6\" cy=\"6\" r=\"6\" fill=\"red\"/></svg>\' ); date \"+%F at %H:%M:%S\"','curl -I -s http://dashtest/iot-directory/'),(15,'iot-fiware-harvester','echo Not meant to be tested','echo Not meant to be tested'),(20,'keycloak','curl -I -s http://proxy.$#k8-namespace#$.svc.cluster.local/auth/admin/ | awk \'NR==1{print $2}\' | ( read code && [ \"$code\" -eq 302 ] && echo \'Success <svg width=\"12\" height=\"12\" style=\"vertical-align: middle;\"><circle cx=\"6\" cy=\"6\" r=\"6\" fill=\"green\"/></svg>\' || echo \'Failure <svg width=\"12\" height=\"12\" style=\"vertical-align: middle;\"><circle cx=\"6\" cy=\"6\" r=\"6\" fill=\"red\"/></svg>\' ); date \"+%F at %H:%M:%S\"','curl -I -s http://dashtest/auth/'),(21,'ldap-server','if nc -z ldap-server.$#k8-namespace#$.svc.cluster.local 389; then echo \'Success <svg width=\"12\" height=\"12\" style=\"vertical-align: middle;\"><circle cx=\"6\" cy=\"6\" r=\"6\" fill=\"green\"/></svg>\'; else echo \'Failure <svg width=\"12\" height=\"12\" style=\"vertical-align: middle;\"><circle cx=\"6\" cy=\"6\" r=\"6\" fill=\"red\"/></svg>\'; fi; date \"+%F at %H:%M:%S\"','nc -v -z ldap-server 389'),(23,'myldap','curl -I -s http://proxy.$#k8-namespace#$.svc.cluster.local/phpldapadmin/cmd.php | awk \'NR==1{print $2}\' | ( read code && [ \"$code\" -eq 302 ] && echo \'Success <svg width=\"12\" height=\"12\" style=\"vertical-align: middle;\"><circle cx=\"6\" cy=\"6\" r=\"6\" fill=\"green\"/></svg>\' || echo \'Failure <svg width=\"12\" height=\"12\" style=\"vertical-align: middle;\"><circle cx=\"6\" cy=\"6\" r=\"6\" fill=\"red\"/></svg>\' ); date \"+%F at %H:%M:%S\"','curl -I -s http://dashtest/phpldapadmin/cmd.php'),(24,'nifi','curl -I -s --insecure https://nifi.$#k8-namespace#$.svc.cluster.local:9090 | awk \'NR==1{print $2}\' | ( read code && [ \"$code\" -eq 200 ] && echo \'Success <svg width=\"12\" height=\"12\" style=\"vertical-align: middle;\"><circle cx=\"6\" cy=\"6\" r=\"6\" fill=\"green\"/></svg>\' || echo \'Failure <svg width=\"12\" height=\"12\" style=\"vertical-align: middle;\"><circle cx=\"6\" cy=\"6\" r=\"6\" fill=\"red\"/></svg>\'); date \"+%F at %H:%M:%S\"','curl -I -s --insecure https://nifi:9090'),(25,'od-build-api','curl -I -s http://proxy.$#k8-namespace#$.svc.cluster.local/odmm-build/api | grep -q \'NOT FOUND\' && echo \'Success <svg width=\"12\" height=\"12\" style=\"vertical-align: middle;\"><circle cx=\"6\" cy=\"6\" r=\"6\" fill=\"green\"/></svg>\' || echo \'Failure <svg width=\"12\" height=\"12\" style=\"vertical-align: middle;\"><circle cx=\"6\" cy=\"6\" r=\"6\" fill=\"red\"/></svg>\'; date \"+%F at %H:%M:%S\"','curl -I -s http://dashtest/odmm-build/api'),(26,'od-get-api','curl -I -s http://proxy.$#k8-namespace#$.svc.cluster.local/odmm/api | grep -q \'NOT FOUND\' && echo \'Success <svg width=\"12\" height=\"12\" style=\"vertical-align: middle;\"><circle cx=\"6\" cy=\"6\" r=\"6\" fill=\"green\"/></svg>\' || echo \'Failure <svg width=\"12\" height=\"12\" style=\"vertical-align: middle;\"><circle cx=\"6\" cy=\"6\" r=\"6\" fill=\"red\"/></svg>\'; date \"+%F at %H:%M:%S\"','curl -I -s http://dashtest/odmm/api'),(27,'od-insert-api','curl -I -s http://proxy.$#k8-namespace#$.svc.cluster.local/odmm-insert/api | grep -q \'NOT FOUND\' && echo \'Success <svg width=\"12\" height=\"12\" style=\"vertical-align: middle;\"><circle cx=\"6\" cy=\"6\" r=\"6\" fill=\"green\"/></svg>\' || echo \'Failure <svg width=\"12\" height=\"12\" style=\"vertical-align: middle;\"><circle cx=\"6\" cy=\"6\" r=\"6\" fill=\"red\"/></svg>\'; date \"+%F at %H:%M:%S\"','curl -I -s http://dashtest/odmm-insert/api'),(28,'od-postgis','if nc -z od-postgis.$#k8-namespace#$.svc.cluster.local 5432; then echo \'Success <svg width=\"12\" height=\"12\" style=\"vertical-align: middle;\"><circle cx=\"6\" cy=\"6\" r=\"6\" fill=\"green\"/></svg>\'; else echo \'Failure <svg width=\"12\" height=\"12\" style=\"vertical-align: middle;\"><circle cx=\"6\" cy=\"6\" r=\"6\" fill=\"red\"/></svg>\'; fi; date \"+%F at %H:%M:%S\"','nc -v -z od-postgis 5432'),(33,'personaldata','curl -I -s http://proxy.$#k8-namespace#$.svc.cluster.local/datamanager/ | awk \'NR==1{print $2}\' | ( read code && [ \"$code\" -eq 200 ] && echo \'Success <svg width=\"12\" height=\"12\" style=\"vertical-align: middle;\"><circle cx=\"6\" cy=\"6\" r=\"6\" fill=\"green\"/></svg>\' || echo \'Failure <svg width=\"12\" height=\"12\" style=\"vertical-align: middle;\"><circle cx=\"6\" cy=\"6\" r=\"6\" fill=\"red\"/></svg>\' ); date \"+%F at %H:%M:%S\"','curl -I -s http://dashtest/datamanager/'),(34,'servicemap','curl -I -s http://proxy.$#k8-namespace#$.svc.cluster.local/ServiceMap/ | awk \'NR==1{print $2}\' | ( read code && [ \"$code\" -eq 200 ] && echo \'Success <svg width=\"12\" height=\"12\" style=\"vertical-align: middle;\"><circle cx=\"6\" cy=\"6\" r=\"6\" fill=\"green\"/></svg>\' || echo \'Failure <svg width=\"12\" height=\"12\" style=\"vertical-align: middle;\"><circle cx=\"6\" cy=\"6\" r=\"6\" fill=\"red\"/></svg>\' ); date \"+%F at %H:%M:%S\"','curl -I -s http://dashtest/ServiceMap/'),(35,'solr-kb','curl -I -s http://solr-kb.$#k8-namespace#$.svc.cluster.local:8983/solr/ | awk \'NR==1{print $2}\' | ( read code && [ \"$code\" -eq 200 ] && echo \'Success <svg width=\"12\" height=\"12\" style=\"vertical-align: middle;\"><circle cx=\"6\" cy=\"6\" r=\"6\" fill=\"green\"/></svg>\' || echo \'Failure <svg width=\"12\" height=\"12\" style=\"vertical-align: middle;\"><circle cx=\"6\" cy=\"6\" r=\"6\" fill=\"red\"/></svg>\' ); date \"+%F at %H:%M:%S\"','curl -I -s http://solr-kb:8983/solr/'),(36,'synoptics','curl -I -s http://proxy.$#k8-namespace#$.svc.cluster.local/synoptics/ | awk \'NR==1{print $2}\' | ( read code && [ \"$code\" -eq 200 ] && echo \'Success <svg width=\"12\" height=\"12\" style=\"vertical-align: middle;\"><circle cx=\"6\" cy=\"6\" r=\"6\" fill=\"green\"/></svg>\' || echo \'Failure <svg width=\"12\" height=\"12\" style=\"vertical-align: middle;\"><circle cx=\"6\" cy=\"6\" r=\"6\" fill=\"red\"/></svg>\' ); date \"+%F at %H:%M:%S\"','curl -I -s http://dashtest/synoptics/'),(37,'varnish','curl -I -s http://varnish.$#k8-namespace#$.svc.cluster.local:6081/ | awk \'NR==1{print $2}\' | ( read code && [ \"$code\" -eq 403 ] && echo \'Success <svg width=\"12\" height=\"12\" style=\"vertical-align: middle;\"><circle cx=\"6\" cy=\"6\" r=\"6\" fill=\"green\"/></svg>\' || echo \'Failure <svg width=\"12\" height=\"12\" style=\"vertical-align: middle;\"><circle cx=\"6\" cy=\"6\" r=\"6\" fill=\"red\"/></svg>\' ); date \"+%F at %H:%M:%S\"','curl -I -s http://varnish:6081/'),(38,'virtuoso-kb','curl -I -s http://virtuoso-kb.$#k8-namespace#$.svc.cluster.local:8890/ | awk \'NR==1{print $2}\' | ( read code && [ \"$code\" -eq 200 ] && echo \'Success <svg width=\"12\" height=\"12\" style=\"vertical-align: middle;\"><circle cx=\"6\" cy=\"6\" r=\"6\" fill=\"green\"/></svg>\' || echo \'Failure <svg width=\"12\" height=\"12\" style=\"vertical-align: middle;\"><circle cx=\"6\" cy=\"6\" r=\"6\" fill=\"red\"/></svg>\' ); date \"+%F at %H:%M:%S\"','curl -I -s http://virtuoso-kb:8890/'),(39,'wsserver','curl -I -s http://proxy.$#k8-namespace#$.svc.cluster.local/wsserver/ | awk \'NR==1{print $2}\' | ( read code && [ \"$code\" -eq 400 ] && echo \'Success <svg width=\"12\" height=\"12\" style=\"vertical-align: middle;\"><circle cx=\"6\" cy=\"6\" r=\"6\" fill=\"green\"/></svg>\' || echo \'Failure <svg width=\"12\" height=\"12\" style=\"vertical-align: middle;\"><circle cx=\"6\" cy=\"6\" r=\"6\" fill=\"red\"/></svg>\' ); date \"+%F at %H:%M:%S\"','curl -I -s http://dashtest/wsserver/'),(40,'sumo-microsim','echo \'Success <svg width=\"12\" height=\"12\" style=\"vertical-align: middle;\"><circle cx=\"6\" cy=\"6\" r=\"6\" fill=\"green\"/></svg>\'','test ok'),(41,'sumoapp-manager','echo \'Failure <svg width=\"12\" height=\"12\" style=\"vertical-align: middle;\"><circle cx=\"6\" cy=\"6\" r=\"6\" fill=\"red\"/></svg>\'','test not ok');

/*!40000 ALTER TABLE `tests_table` ENABLE KEYS */;
UNLOCK TABLES;

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

DELIMITER $$
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
END$$
DELIMITER ;

-- Dump completed on 2025-07-01 10:36:19