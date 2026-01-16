USE checker;

ALTER TABLE `checker`.`cronjob_history` 
CHANGE COLUMN `result` `result` MEDIUMTEXT NOT NULL ,
CHANGE COLUMN `errors` `errors` MEDIUMTEXT NULL DEFAULT NULL ;

-- replace namespace with namespace of microx                                                                                                           here
--                                                                                                                                                       |
--                                                                                                                                                      \ /
--                                                                                                                                                       V
INSERT INTO `checker`.`cronjobs` (`idcronjobs`, `name`, `command`, `category`) VALUES (NULL, 'Crawler', 'kubectl exec -i deployment/dashboard-cron -n dashk8stest -- bash -s < scripts/read_crawler_logs.sh', '1');

alter table `checker`.`ip_table` CHARACTER SET = utf8mb4, ADD UNIQUE INDEX `hostname_UNIQUE` (`hostname` ASC) VISIBLE;

-- CHANGE COLUMN `hostname` `hostname` VARCHAR(45) CHARACTER SET 'utf8' NOT NULL ,

ALTER TABLE `checker`.`component_to_category` 
ADD COLUMN `kind` SET('Kubernetes', 'Docker') NOT NULL DEFAULT 'Kubernetes' AFTER `position`,
CHANGE COLUMN `position` `position` VARCHAR(45) NOT NULL DEFAULT 'localhost' ;

ALTER TABLE `checker`.`cronjobs` 
CHARACTER SET = utf8mb4 ,
CHANGE COLUMN `name` `name` VARCHAR(200) NOT NULL,
ADD COLUMN `where_to_run` VARCHAR(45) CHARACTER SET 'utf8mb4' NULL DEFAULT NULL AFTER `categrory`,
ADD COLUMN `disabled` TINYINT NOT NULL DEFAULT 0 AFTER `where_to_run`,
ADD CONSTRAINT `where_fk`
  FOREIGN KEY (`where_to_run`)
  REFERENCES `checker`.`where_to_run` (`hostname`)
  ON DELETE NO ACTION
  ON UPDATE NO ACTION;

alter table `checker`.`cronjob_history` CHARACTER SET = utf8mb4;
alter table `checker`.`host` CHARACTER SET = utf8mb4;
alter table `checker`.`host_data` CHARACTER SET = utf8mb4;