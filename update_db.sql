USE checker;

ALTER TABLE `checker`.`cronjob_history` 
CHANGE COLUMN `result` `result` MEDIUMTEXT NOT NULL ,
CHANGE COLUMN `errors` `errors` MEDIUMTEXT NULL DEFAULT NULL ;

-- replace namespace with namespace of microx                                                                                                         here
--                                                                                                                                                     |
--                                                                                                                                                    \ /
--                                                                                                                                                     V
INSERT INTO `checker`.`cronjobs` (`idcronjobs`, `name`, `command`, `category`) VALUES (NULL, 'Crawler', 'kubectl exec deployment/dashboard-cron -n dashk8stest -- bash -s < scripts/read_crawler_logs.sh', '1');
